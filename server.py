"""Local Edge TTS Studio: persistent FIFO queue and browser interface."""
import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
import uuid
import math
import tempfile
import zipfile
import hmac
from urllib.parse import urlsplit

import edge_tts
import imageio_ffmpeg
import soundfile as sf
from aiohttp import web
from audio_engine import AudioEngine, FORMATS, command
from voice_catalog import (kokoro_voices, kitten_voices, piper_voices, chatterbox_voices,
                           enrich, capabilities, require_engine, USES, AGES)
from speech_text import split_script, split_batch
from preview_samples import sample_for
from user_errors import friendly_error
from auditions import audition_url
from documents import import_document

ROOT = Path(__file__).resolve().parent
SPEEDS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def configured_data_dir():
    """Use persistent storage in production and retain the local data folder."""
    return Path(os.getenv('STILLWATER_DATA_DIR', str(ROOT / 'data'))).expanduser().resolve()


def allowed_hosts(port):
    hosts = {'127.0.0.1', 'localhost', f'127.0.0.1:{port}', f'localhost:{port}'}
    for value in (os.getenv('RENDER_EXTERNAL_HOSTNAME', ''), os.getenv('ALLOWED_HOSTS', '')):
        for host in value.split(','):
            host = host.strip().lower()
            if host:
                hosts.add(urlsplit(host).netloc or host)
    return hosts


def valid_basic_auth(request):
    password = os.getenv('STILLWATER_PASSWORD', '')
    if not password:
        return True
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Basic '):
        return False
    try:
        raw = base64.b64decode(authorization[6:], validate=True).decode('utf-8')
        username, supplied_password = raw.split(':', 1)
    except (ValueError, UnicodeDecodeError):
        return False
    expected_username = os.getenv('STILLWATER_USERNAME', 'stillwater')
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(supplied_password, password)


class Studio:
    def __init__(self, data):
        self.data = Path(data)
        self.outputs = self.data / 'outputs'
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.data / 'studio.sqlite3')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE,
                title TEXT, text TEXT, voice TEXT, speed REAL, pitch INTEGER,
                volume INTEGER, status TEXT DEFAULT 'queued', attempts INTEGER DEFAULT 0,
                progress REAL DEFAULT 0, error TEXT DEFAULT '', next_retry REAL DEFAULT 0,
                created REAL, started REAL, completed REAL, duration REAL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS voice_tags (id TEXT PRIMARY KEY, value TEXT);
        ''')
        columns={r[1] for r in self.db.execute('PRAGMA table_info(jobs)')}
        for name,definition in [('engine',"TEXT DEFAULT 'edge'"),('options',"TEXT DEFAULT '{}'"),
                                ('group_title',"TEXT DEFAULT ''"),('part_number','INTEGER DEFAULT 0')]:
            if name not in columns: self.db.execute(f'ALTER TABLE jobs ADD COLUMN {name} {definition}')
        # Preserve queue order and repair both legacy title formats. Older
        # versions either appended "· Part N"/"· N" or used the first 55
        # script characters as the title when the title field was blank.
        counters={}
        rows=self.db.execute('SELECT seq,title,text,group_title,part_number FROM jobs ORDER BY seq').fetchall()
        for row in rows:
            stored=(row['title'] or '').strip()
            automatic=stored==(row['text'] or '')[:55].strip()
            if automatic:
                title='Untitled recording'
            else:
                title=re.sub(r'\s*·\s*(?:Part\s+)?\d+\s*$', '',
                             (row['group_title'] or stored), flags=re.IGNORECASE).strip()
                title=title or 'Untitled recording'
            key=title.casefold(); counters[key]=counters.get(key,0)+1
            if row['group_title']!=title or row['part_number']!=counters[key]:
                self.db.execute('UPDATE jobs SET group_title=?,part_number=? WHERE seq=?',
                                (title,counters[key],row['seq']))
        self.db.execute("UPDATE jobs SET status='queued', progress=0, error='Resuming after app restart' WHERE status='running'")
        self.db.commit()
        self.voices = []
        self.voice_warning = ''
        self.preview_locks = {'edge': asyncio.Lock(), 'kokoro': asyncio.Lock(), 'kitten': asyncio.Lock(), 'piper': asyncio.Lock(), 'chatterbox': asyncio.Lock()}
        self.wake = asyncio.Event()
        self.active_task = None
        self.active_id = None
        self.audio = AudioEngine()

    def update(self, job_id, **fields):
        self.db.execute('UPDATE jobs SET ' + ','.join(f'{k}=?' for k in fields) + ' WHERE id=?', [*fields.values(), job_id])
        self.db.commit()

    def jobs(self):
        jobs=[self.unpack(r) for r in self.db.execute('SELECT * FROM jobs ORDER BY seq')]
        for job in jobs:
            job['files']=[ext for ext in ('mp3','wav','srt','vtt','json') if (self.outputs/(job['id']+'.'+ext)).is_file()] if job['status']=='completed' else []
            manifest=self.outputs/'live'/job['id']/'manifest.json'
            if job.get('live_preview') and manifest.is_file() and job['status'] in ('running','completed'):
                try: job['live']=json.loads(manifest.read_text(encoding='utf-8'))
                except (OSError,ValueError): pass
        return jobs

    def delete_recording(self, job_id):
        row = self.db.execute('SELECT status FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise ValueError('This recording no longer exists.')
        if row['status'] in ('queued', 'running', 'retrying'):
            raise ValueError('Cancel this script before deleting it.')

        output_root = self.outputs.resolve()
        for path in self.outputs.glob(job_id + '.*'):
            if path.is_file() and path.resolve().parent == output_root:
                path.unlink()
        live_root = (self.outputs / 'live').resolve()
        live_dir = self.outputs / 'live' / job_id
        if live_dir.exists() and live_dir.resolve().parent == live_root:
            shutil.rmtree(live_dir)

        self.db.execute('DELETE FROM jobs WHERE id=?', (job_id,))
        self.db.commit()

    @staticmethod
    def unpack(row):
        job=dict(row)
        job.update(json.loads(job.pop('options','{}')))
        return job

    def catalog(self, engine='edge'):
        if not capabilities().get(engine, {}).get('ready'):
            return []
        voices=(kokoro_voices() if engine=='kokoro' else kitten_voices() if engine=='kitten' else
                piper_voices() if engine=='piper' else chatterbox_voices(self.data) if engine=='chatterbox' else
                [enrich(v,'edge') for v in self.voices])
        overrides={r['id']:json.loads(r['value']) for r in self.db.execute('SELECT * FROM voice_tags')}
        for voice in voices:
            voice['AuditionURL']=audition_url(self.data,engine,voice['ShortName'])
            key=engine+':'+voice['ShortName']
            if key in overrides: voice.update(overrides[key],TagsSource='Your listening tags')
        return voices

    def paused(self):
        row = self.db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()
        return bool(row and row[0] == '1')

    async def refresh_voices(self):
        cache = self.data / 'voices.json'
        try:
            self.voices = await asyncio.wait_for(edge_tts.list_voices(), 25)
            cache.write_text(json.dumps(self.voices), encoding='utf-8')
            self.voice_warning = ''
        except Exception as exc:
            if cache.exists():
                self.voices = json.loads(cache.read_text(encoding='utf-8'))
            self.voice_warning = f'Could not refresh voices. {"Using saved voice list. " if self.voices else "Check your internet and refresh voices. "}{type(exc).__name__}: {exc}'

    def validate(self, raw):
        if not isinstance(raw, dict):
            raise ValueError('Each script must be an object.')
        text = str(raw.get('text', '')).strip()
        if not text or not any(c.isalnum() for c in text):
            raise ValueError('Enter a script containing words.')
        if len(text) > 40000:
            raise ValueError('Each script can contain up to 40,000 characters.')
        engine=str(raw.get('engine','edge'))
        require_engine(engine)
        voice = str(raw.get('voice', 'af_heart' if engine=='kokoro' else 'Jasper' if engine=='kitten' else 'en_US-hfc_female-medium' if engine=='piper' else 'builtin' if engine=='chatterbox' else 'en-US-AndrewNeural'))
        available={v['ShortName'] for v in self.catalog(engine)}
        if voice not in available:
            raise ValueError('Choose a voice from the available voice list.')
        speed = float(raw.get('speed', 0.8))
        pitch = int(raw.get('pitch', -5))
        volume = int(raw.get('volume', 0))
        if not .5<=speed<=(1 if engine=='edge' else 2) or not -50 <= pitch <= 50 or not -50 <= volume <= 50:
            raise ValueError('Speed must be 0.5–1.0 for Edge or 0.5–2.0 for local engines; pitch/volume must be -50 to +50.')
        options={
            'export_format':str(raw.get('export_format','mp3_44100_192')),
            'normalize':bool(raw.get('normalize',True)), 'output_gain':float(raw.get('output_gain',0)),
            'paragraph_pause':float(raw.get('paragraph_pause',0)),
            'subtitle_width':int(raw.get('subtitle_width',42)), 'subtitle_seconds':float(raw.get('subtitle_seconds',6)),
            'seed':int(raw.get('seed',12345)), 'device':str(raw.get('device','cpu')), 'blend':[],
            'live_preview':bool(raw.get('live_preview',False)) if engine=='kokoro' else False,
            'temperature':float(raw.get('temperature',.8)), 'top_p':float(raw.get('top_p',.95)),
            'top_k':int(raw.get('top_k',1000)), 'repetition_penalty':float(raw.get('repetition_penalty',1.2)),
        }
        if options['export_format'] not in FORMATS: raise ValueError('Select an available export format.')
        if not -12<=options['output_gain']<=6 or not 0<=options['paragraph_pause']<=5: raise ValueError('Output gain or paragraph pause is out of range.')
        if not 24<=options['subtitle_width']<=48 or not 2<=options['subtitle_seconds']<=10: raise ValueError('Invalid subtitle layout settings.')
        if not 0<=options['seed']<=2147483647 or options['device'] not in ('cpu','auto','cuda'): raise ValueError('Invalid Kokoro runtime settings.')
        if not .05<=options['temperature']<=2 or not .05<=options['top_p']<=1 or not 1<=options['top_k']<=1000 or not 1<=options['repetition_penalty']<=2:
            raise ValueError('Invalid Chatterbox sampling settings.')
        split_script(text, options['paragraph_pause'])
        if engine in ('kokoro','kitten','piper','chatterbox'):
            pitch=volume=0
        if engine=='kokoro':
            blend=raw.get('blend',[])
            if not isinstance(blend,list) or len(blend)>8: raise ValueError('Blend up to eight Kokoro voices.')
            for item in blend:
                blend_voice=str(item['voice'])
                weight=float(item['weight'])
                if blend_voice not in available or blend_voice[0]!=voice[0] or not math.isfinite(weight) or weight<=0:
                    raise ValueError('Blend voices from the same language with positive weights.')
                options['blend'].append({'voice':blend_voice,'weight':weight})
            if blend and voice not in {v['voice'] for v in options['blend']}:
                raise ValueError('Include the selected primary voice in the blend.')
        return dict(title=str(raw.get('title', '')).strip()[:120] or text[:55], text=text,
                    voice=voice, speed=round(speed,2), pitch=pitch, volume=volume, engine=engine,
                    options=json.dumps(options))

    def add(self, items):
        expanded = []
        for item in items:
            if not isinstance(item, dict): raise ValueError('Each script must contain text and voice settings.')
            parts = split_batch(str(item.get('text', '')))
            if not parts: raise ValueError('Enter a script containing words.')
            title = str(item.get('title', '')).strip() or 'Untitled recording'
            for part in parts:
                expanded.append({**item, 'text': part, 'title': title})
        if len(expanded)>50: raise ValueError('Add up to 50 script parts at a time. Use fewer separator lines or submit smaller batches.')
        validated = [self.validate(item) for item in expanded]
        ids = []
        with self.db:
            for item in validated:
                job_id = uuid.uuid4().hex
                group_title=item['title'] or 'Untitled recording'
                row=self.db.execute('SELECT COALESCE(MAX(part_number),0) FROM jobs WHERE group_title=? COLLATE NOCASE',
                                    (group_title,)).fetchone()
                part_number=int(row[0])+1
                self.db.execute('INSERT INTO jobs(id,title,text,voice,speed,pitch,volume,engine,options,created,group_title,part_number) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                                [job_id, *item.values(), time.time(),group_title,part_number])
                ids.append(job_id)
        self.wake.set()
        return ids

    async def synthesize(self, job, stem, progress=None):
        return await self.audio.generate(job, stem, progress)

    async def process(self, job):
        attempts = job['attempts'] + 1
        self.update(job['id'], status='running', attempts=attempts, progress=0, error='', started=time.time(), next_retry=0)
        try:
            duration = await self.synthesize(job, self.outputs / job['id'],
                lambda p: self.update(job['id'], progress=p))
            self.update(job['id'], status='completed', progress=1, completed=time.time(), duration=duration)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            delay = (5, 15, 30, 60)[min(attempts - 1, 3)]
            self.update(job['id'], status='retrying', progress=0,
                        error=friendly_error(exc), next_retry=time.time() + delay)
            logging.exception('Job %s attempt %s failed', job['id'], attempts)

    async def worker(self):
        while True:
            self.wake.clear()
            row = self.db.execute("SELECT * FROM jobs WHERE status IN ('queued','retrying','running') ORDER BY seq LIMIT 1").fetchone()
            if row and not self.paused() and row['next_retry'] <= time.time():
                self.active_id = row['id']
                self.active_task = asyncio.create_task(self.process(self.unpack(row)))
                try:
                    await self.active_task
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                finally:
                    self.active_task = None
                    self.active_id = None
                continue
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass


@web.middleware
async def errors(request, handler):
    # Accept the local development hosts plus the explicit Render/custom host.
    # Mutating requests remain same-origin to prevent third-party sites from
    # submitting synthesis jobs through a user's browser.
    request_host = request.host.lower()
    if request_host not in request.app['allowed_hosts'] and request_host.split(':', 1)[0] not in request.app['allowed_hosts']:
        raise web.HTTPForbidden(text='This host is not allowed')
    if request.path != '/health' and not valid_basic_auth(request):
        raise web.HTTPUnauthorized(
            text='Sign in to Stillwater Voice Studio.',
            headers={'WWW-Authenticate': 'Basic realm="Stillwater Voice Studio", charset="UTF-8"'},
        )
    if request.method == 'POST':
        origin = request.headers.get('Origin')
        allowed_origins = {item.strip().rstrip('/') for item in os.getenv('ALLOWED_ORIGINS', '').split(',') if item.strip()}
        if origin and urlsplit(origin).netloc.lower() != request_host and origin.rstrip('/') not in allowed_origins:
            raise web.HTTPForbidden(text='Cross-origin requests are not allowed')
        if request.content_type != 'application/json':
            raise web.HTTPUnsupportedMediaType(text='Use application/json')
    try:
        return await handler(request)
    except (ValueError, TypeError, KeyError) as exc:
        return web.json_response({'error': str(exc)}, status=400)
    except web.HTTPException:
        raise
    except Exception as exc:
        logging.exception('Request failed')
        return web.json_response({'error': friendly_error(exc)}, status=500)


def make_app(data=None, port=8766):
    data = configured_data_dir() if data is None else Path(data)
    studio = Studio(data)
    app = web.Application(middlewares=[errors], client_max_size=24 * 1024 * 1024)
    app['studio'] = studio
    app['port'] = port
    app['allowed_hosts'] = allowed_hosts(port)
    app['background_tasks'] = set()
    exports={}

    async def index(request):
        return web.FileResponse(ROOT / 'static-v2' / 'index.html', headers={'Cache-Control': 'no-cache'})

    async def health(request):
        # Keep this probe independent of TTS/model loading. Opening the queue
        # database is already part of normal application startup.
        return web.json_response({'status': 'ok', 'service': 'stillwater-voice-studio'})

    async def voice_cloning(request):
        return web.FileResponse(ROOT / 'static-v2' / 'voice-cloning.html', headers={'Cache-Control': 'no-cache'})

    async def voices(request):
        engine=request.query.get('engine','edge')
        if engine not in ('edge','kokoro','kitten','piper','chatterbox'): raise ValueError('Unknown engine')
        engine_capabilities=capabilities()
        capability=engine_capabilities[engine]
        warning=(studio.voice_warning if engine=='edge' else
                 '' if capability['ready'] else f"{capability['name']} is unavailable on this server. {capability['reason']}")
        return web.json_response({'voices': studio.catalog(engine), 'warning':warning,
                                 'capabilities':engine_capabilities,
                                 'formats':{k:v[0] for k,v in FORMATS.items()},'uses':USES,'ages':AGES})

    async def refresh(request):
        await studio.refresh_voices()
        return await voices(request)

    async def state(request):
        return web.json_response({'jobs': studio.jobs(), 'paused': studio.paused(), 'server_time': time.time()})

    async def add(request):
        raw = await request.json()
        items = raw.get('jobs')
        if not isinstance(items, list) or not 1 <= len(items) <= 50:
            raise ValueError('Add between 1 and 50 scripts at a time.')
        return web.json_response({'ids': studio.add(items)})

    async def queue(request):
        raw = await request.json()
        paused = bool(raw.get('paused'))
        studio.db.execute("INSERT OR REPLACE INTO settings VALUES('paused',?)", ('1' if paused else '0',))
        studio.db.commit()
        studio.wake.set()
        return web.json_response({'paused': paused})

    async def action(request):
        job_id = request.match_info['job_id']
        row = studio.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise web.HTTPNotFound()
        raw = await request.json()
        operation = raw.get('action')
        if operation == 'cancel' and row['status'] in ('queued', 'retrying', 'running'):
            studio.update(job_id, status='cancelled', next_retry=0, error='Cancelled by you')
            if studio.active_id == job_id and studio.active_task:
                task = studio.active_task
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        elif operation == 'retry' and row['status'] == 'retrying':
            updates = studio.validate(raw['job']) if 'job' in raw else {}
            studio.update(job_id, **updates, status='queued', error='', next_retry=0)
        elif operation == 'delete':
            studio.delete_recording(job_id)
        else:
            raise ValueError('That action is no longer available for this script.')
        studio.wake.set()
        return web.json_response({'ok': True})

    async def delete_recordings(request):
        raw=await request.json()
        ids=raw.get('ids')
        if not isinstance(ids,list) or not 1<=len(ids)<=500 or len(ids)!=len(set(ids)):
            raise ValueError('Choose between 1 and 500 unique recordings to delete.')
        if any(not isinstance(job_id,str) or not re.fullmatch(r'[a-f0-9]{32}',job_id) for job_id in ids):
            raise ValueError('The selected recording list is invalid.')
        rows=studio.db.execute('SELECT id,status FROM jobs WHERE id IN ('+','.join('?' for _ in ids)+')',ids).fetchall()
        if len(rows)!=len(ids): raise ValueError('One or more selected recordings no longer exist. Refresh and try again.')
        if any(row['status'] in ('queued','running','retrying') for row in rows):
            raise ValueError('Cancel active scripts before deleting them.')
        for job_id in ids: studio.delete_recording(job_id)
        return web.json_response({'deleted':len(ids)})

    async def preview(request):
        raw = await request.json()
        engine=raw.get('engine','edge')
        voice=raw.get('voice','')
        if raw.get('audition'):
            url=audition_url(studio.data,engine,voice)
            if url:
                speed=float(raw.get('speed',.8))
                if not .5<=speed<=(1 if engine=='edge' else 2): raise ValueError('Choose a supported preview speed.')
                return web.json_response({'url':url,'voice':voice,'engine':engine,'playback_rate':speed,'sample_language':sample_for(voice,studio.catalog(engine))[1]})
        parts=split_batch(str(raw.get('text','')))
        text=parts[0] if parts else ''
        sample, sample_language=sample_for(raw.get('voice'),studio.catalog(raw.get('engine','edge')))
        if len(text)>350:
            text=text[:350]
            if text.rfind('[')>text.rfind(']'): text=text[:text.rfind('[')]
            text=text.rsplit(' ',1)[0]
        raw['text'] = text or sample
        if raw.get('audition'):
            raw.update(blend=[],pitch=0,volume=0,normalize=True,output_gain=0,paragraph_pause=0)
        raw['live_preview']=False
        job = studio.unpack(studio.validate(raw))
        key = 'preview-' + hashlib.sha256(('v3'+json.dumps(job, sort_keys=True)).encode()).hexdigest()[:24]
        stem = studio.outputs / key
        async def prepare():
            if stem.with_suffix('.mp3').exists(): return
            async with studio.preview_locks[job['engine']]:
                if not stem.with_suffix('.mp3').exists():
                    await studio.synthesize(job, stem)
        # Switching voices aborts the browser request. Stop that obsolete worker
        # (or lock waiter) too, so it cannot delay the newly chosen preview.
        task=asyncio.create_task(prepare())
        transport=request.transport
        try:
            while not task.done():
                await asyncio.wait({task},timeout=.25)
                if transport is not None and transport.is_closing():
                    raise asyncio.CancelledError()
            await task
        finally:
            if not task.done():
                task.cancel()
                try: await task
                except asyncio.CancelledError: pass
        return web.json_response({'url': f'/files/{key}.mp3', 'voice':job['voice'], 'engine':job['engine'], 'sample_language':sample_language})

    async def file(request):
        name = request.match_info['name']
        if not re.fullmatch(r'(?:[a-f0-9]{32}|preview-[a-f0-9]{24})\.(mp3|wav|srt|vtt|json)', name):
            raise web.HTTPNotFound()
        path = studio.outputs / name
        if not path.is_file():
            raise web.HTTPNotFound()
        if not name.startswith('preview-'):
            row = studio.db.execute('SELECT status,title FROM jobs WHERE id=?', (path.stem,)).fetchone()
            if not row or row['status'] != 'completed':
                raise web.HTTPNotFound()
        headers = {}
        if 'download' in request.query:
            title = re.sub(r'[^a-zA-Z0-9 _-]', '', row['title'])[:80].strip() if not name.startswith('preview-') else 'voice-preview'
            headers['Content-Disposition'] = f'attachment; filename="{title or "audio"}{path.suffix}"'
        return web.FileResponse(path, headers=headers)

    async def audition_file(request):
        name=request.match_info['name']
        if not re.fullmatch(r'[a-f0-9]{24}\.mp3',name): raise web.HTTPNotFound()
        path=studio.data/'auditions'/name
        if not path.is_file(): raise web.HTTPNotFound()
        return web.FileResponse(path,headers={'Cache-Control':'public, max-age=31536000, immutable'})

    async def tags(request):
        raw=await request.json()
        engine=raw.get('engine','edge')
        voice=raw.get('voice')
        if voice not in {v['ShortName'] for v in studio.catalog(engine)}: raise ValueError('Unknown voice.')
        age=raw.get('age','unclassified')
        uses=raw.get('uses',[])
        if age not in AGES or not isinstance(uses,list) or any(u not in USES for u in uses): raise ValueError('Invalid listening tags.')
        studio.db.execute('INSERT OR REPLACE INTO voice_tags VALUES(?,?)',(engine+':'+voice,json.dumps({'Age':age,'Uses':uses})))
        studio.db.commit()
        return web.json_response({'ok':True})

    async def live_audio(request):
        job_id=request.match_info['job_id']
        name=request.match_info['name']
        if not re.fullmatch('[a-f0-9]{32}',job_id) or not re.fullmatch(r'[a-f0-9]{12}-[0-9]{5}\.wav',name): raise web.HTTPNotFound()
        row=studio.db.execute('SELECT status FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not row or row['status'] not in ('running','completed'): raise web.HTTPNotFound()
        path=studio.outputs/'live'/job_id/name
        if not path.is_file(): raise web.HTTPNotFound()
        return web.FileResponse(path)

    async def imports(request):
        raw=await request.json()
        chapters=await asyncio.to_thread(import_document,raw)
        return web.json_response({'chapters':chapters})

    async def add_chatterbox_voice(request):
        require_engine('chatterbox')
        raw=await request.json()
        name=str(raw.get('name','')).strip()[:60]
        encoded=raw.get('content')
        if not name: raise ValueError('Enter a name for the cloned voice.')
        if not isinstance(encoded,str): raise ValueError('Choose a reference audio file.')
        try: payload=base64.b64decode(encoded,validate=True)
        except Exception: raise ValueError('The reference audio could not be read.')
        if not 1000<=len(payload)<=15*1024*1024: raise ValueError('Reference audio must be under 15 MB.')
        voice_id='clone-'+uuid.uuid4().hex
        voice_dir=studio.data/'chatterbox-voices'; voice_dir.mkdir(exist_ok=True)
        target=voice_dir/(voice_id+'.wav')
        with tempfile.TemporaryDirectory(prefix='voice-',dir=voice_dir) as temp:
            source=Path(temp)/'reference.bin'; source.write_bytes(payload)
            prepared=Path(temp)/'reference.wav'
            try:
                await command(imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',source,'-t','30',
                              '-ar','24000','-ac','1','-c:a','pcm_s16le',prepared)
                seconds=sf.info(prepared).duration
                if seconds<=5: raise ValueError('Use a clean reference clip longer than 5 seconds.')
                samples,_=sf.read(prepared,dtype='float32')
                rms=float((samples*samples).mean() ** .5) if len(samples) else 0
                if rms<.001: raise ValueError('The reference is silent or too quiet. Use a clear voice recording.')
                os.replace(prepared,target)
            except ValueError: raise
            except Exception: raise ValueError('Use a valid WAV, MP3, M4A or FLAC reference recording.')
        metadata=voice_dir/(voice_id+'.json')
        metadata.write_text(json.dumps({'name':name,'duration':round(seconds,2),'created':time.time()},ensure_ascii=False),encoding='utf-8')
        return web.json_response({'voice':next(v for v in chatterbox_voices(studio.data) if v['ShortName']==voice_id)})

    async def delete_chatterbox_voices(request):
        raw=await request.json()
        ids=raw.get('ids')
        if not isinstance(ids,list) or not 1<=len(ids)<=100 or len(ids)!=len(set(ids)):
            raise ValueError('Choose between 1 and 100 unique cloned voices to delete.')
        if any(not isinstance(voice,str) or not re.fullmatch(r'clone-[a-f0-9]{32}',voice) for voice in ids):
            raise ValueError('The selected cloned voice list is invalid.')
        placeholders=','.join('?' for _ in ids)
        active=studio.db.execute(f"SELECT voice FROM jobs WHERE voice IN ({placeholders}) AND status IN ('queued','running','retrying') LIMIT 1",ids).fetchone()
        if active: raise ValueError('Cancel or finish queued recordings that use this cloned voice before deleting it.')
        folder=(studio.data/'chatterbox-voices').resolve(); deleted=0
        for voice in ids:
            wav=folder/(voice+'.wav'); metadata=folder/(voice+'.json')
            if not wav.is_file() or not metadata.is_file():
                raise ValueError('One or more cloned voices no longer exist. Refresh and try again.')
        for voice in ids:
            for extension in ('.wav','.json'):
                path=(folder/(voice+extension)).resolve()
                if path.parent==folder: path.unlink(missing_ok=True)
            deleted+=1
        return web.json_response({'deleted':deleted})

    async def archive(request):
        wanted=request.query.get('ids','').split(',') if request.query.get('ids') else None
        completed=[j for j in studio.jobs() if j['status']=='completed' and (wanted is None or j['id'] in wanted)]
        if not completed: raise ValueError('Choose at least one completed recording.')
        export_dir=studio.data/'exports'
        export_dir.mkdir(exist_ok=True)
        merge=request.query.get('merge')=='1'
        mega=request.query.get('mega')=='1'
        if mega and not merge: raise ValueError('Mega download requires merged recordings.')
        if merge:
            from recording_export import validate_merge
            validate_merge(completed)
        with tempfile.TemporaryDirectory(prefix='bundle-',dir=export_dir) as folder:
            folder=Path(folder)
            if merge:
                from recording_export import merge_recordings
                await merge_recordings(completed,studio.outputs,folder)
            def build():
                with zipfile.ZipFile(folder/'recordings.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as bundle:
                    if not mega:
                        for index,job in enumerate(completed,1):
                            title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','',job['title']).strip(' .')[:80] or 'recording'
                            for ext in ('mp3','wav','srt','vtt','json'):
                                source=studio.outputs/(job['id']+'.'+ext)
                                if source.exists(): bundle.write(source,f'{index:02d} - {title}/{title}.{ext}')
                    merged_extensions=('mp3','srt','vtt') if mega else ('mp3','wav','srt','vtt','json')
                    for ext in merged_extensions:
                        source=folder/('merged.'+ext)
                        if source.exists(): bundle.write(source,'Mega recording/Stillwater-mega-recording.'+ext)
            await asyncio.to_thread(build)
            filename='Stillwater-mega-recording.zip' if mega else 'Stillwater-recordings.zip'
            response=web.StreamResponse(headers={'Content-Type':'application/zip','Content-Disposition':f'attachment; filename="{filename}"',
                'Content-Length':str((folder/'recordings.zip').stat().st_size)})
            await response.prepare(request)
            with (folder/'recordings.zip').open('rb') as source:
                while chunk:=source.read(256*1024): await response.write(chunk)
            await response.write_eof()
            return response

    async def start_export(request):
        raw=await request.json()
        wanted=raw.get('ids')
        if not isinstance(wanted,list) or not wanted or any(not isinstance(value,str) for value in wanted):
            raise ValueError('Choose completed recordings to merge.')
        completed=[j for j in studio.jobs() if j['status']=='completed' and j['id'] in wanted]
        from recording_export import validate_merge
        validate_merge(completed)
        export_id=uuid.uuid4().hex
        export_dir=studio.data/'exports'; export_dir.mkdir(exist_ok=True)
        status={'id':export_id,'status':'working','progress':0.0,'stage':'Starting merge',
                'filename':'Stillwater-mega-recording.zip'}
        exports[export_id]=status

        async def build_export():
            folder=export_dir/(export_id+'.work')
            archive_path=export_dir/(export_id+'.zip')
            try:
                if folder.exists(): shutil.rmtree(folder)
                folder.mkdir()
                from recording_export import merge_recordings
                def progress(value,stage): status.update(progress=round(value,3),stage=stage)
                await merge_recordings(completed,studio.outputs,folder,progress)
                status.update(progress=.95,stage='Compressing MP3 and captions into ZIP')
                def package():
                    with zipfile.ZipFile(archive_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as bundle:
                        for ext in ('mp3','srt','vtt'):
                            bundle.write(folder/('merged.'+ext),'Mega recording/Stillwater-mega-recording.'+ext)
                await asyncio.to_thread(package)
                status.update(status='ready',progress=1.0,stage='Mega recording ready',
                              url=f'/api/exports/{export_id}/download')
            except Exception as exc:
                logging.exception('Export %s failed',export_id)
                status.update(status='failed',stage='Merge failed',error=friendly_error(exc))
            finally:
                if folder.exists(): shutil.rmtree(folder,ignore_errors=True)
        status['task']=asyncio.create_task(build_export())
        return web.json_response({key:value for key,value in status.items() if key!='task'})

    async def export_status(request):
        status=exports.get(request.match_info['export_id'])
        if not status: raise web.HTTPNotFound()
        return web.json_response({key:value for key,value in status.items() if key!='task'})

    async def export_download(request):
        export_id=request.match_info['export_id']
        status=exports.get(export_id)
        path=studio.data/'exports'/(export_id+'.zip')
        if not status or status['status']!='ready' or not path.is_file(): raise web.HTTPNotFound()
        return web.FileResponse(path,headers={'Content-Disposition':'attachment; filename="Stillwater-mega-recording.zip"'})

    async def lifecycle(app):
        await studio.refresh_voices()
        task = asyncio.create_task(studio.worker())
        yield
        task.cancel()
        for export in exports.values():
            export_task=export.get('task')
            if export_task and not export_task.done(): export_task.cancel()
        export_tasks=[value.get('task') for value in exports.values() if value.get('task')]
        if export_tasks: await asyncio.gather(*export_tasks,return_exceptions=True)
        await studio.audio.close()
        try:
            await task
        except asyncio.CancelledError:
            pass
        studio.db.close()

    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/health', health)
    app.router.add_get('/', index)
    app.router.add_get('/voice-cloning', voice_cloning)
    app.router.add_get('/api/voices', voices)
    app.router.add_post('/api/voices/refresh', refresh)
    app.router.add_get('/api/state', state)
    app.router.add_post('/api/jobs', add)
    app.router.add_post('/api/queue', queue)
    app.router.add_post('/api/jobs/{job_id}', action)
    app.router.add_post('/api/recordings/delete', delete_recordings)
    app.router.add_post('/api/preview', preview)
    app.router.add_post('/api/voice-tags', tags)
    app.router.add_get('/api/live/{job_id}/{name}', live_audio)
    app.router.add_post('/api/import', imports)
    app.router.add_post('/api/chatterbox/voices', add_chatterbox_voice)
    app.router.add_post('/api/chatterbox/voices/delete', delete_chatterbox_voices)
    app.router.add_get('/api/archive', archive)
    app.router.add_post('/api/exports', start_export)
    app.router.add_get('/api/exports/{export_id}', export_status)
    app.router.add_get('/api/exports/{export_id}/download', export_download)
    app.router.add_get('/files/{name}', file)
    app.router.add_get('/auditions/{name}', audition_file)
    app.router.add_static('/static/', ROOT / 'static-v2')
    return app


if __name__ == '__main__':
    try:
        default_port = int(os.getenv('PORT', '8766'))
    except ValueError as exc:
        raise SystemExit('PORT must be an integer.') from exc
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=os.getenv('HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=default_port)
    parser.add_argument('--data-dir', type=Path, default=configured_data_dir())
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    web.run_app(make_app(args.data_dir, args.port), host=args.host, port=args.port)
