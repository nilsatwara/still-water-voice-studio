"""Fixed-voice synthesis, sample-accurate pauses, encoding, and subtitle export."""
import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid
import unicodedata
import psutil
import gc
import importlib.util
from collections import OrderedDict

import edge_tts
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from speech_text import split_script, caption_groups, write_subtitles

ROOT=Path(__file__).resolve().parent
MODEL_ROOT=Path(os.getenv('STILLWATER_MODEL_DIR',str(ROOT/'models'))).expanduser().resolve()
RATE=24000
NO_WINDOW=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
FORMATS={
    'mp3_44100_128':('MP3 · 44.1 kHz · 128 kbps',44100,128),
    'mp3_44100_192':('MP3 · 44.1 kHz · 192 kbps',44100,192),
    'mp3_44100_256':('MP3 · 44.1 kHz · 256 kbps',44100,256),
    'mp3_44100_320':('MP3 · 44.1 kHz · 320 kbps',44100,320),
    'mp3_48000_320':('MP3 · 48 kHz · 320 kbps',48000,320),
    'wav_24000':('WAV · 24 kHz · 24-bit PCM (native rate)',24000,192),
    'wav_44100':('WAV · 44.1 kHz · 24-bit PCM',44100,192),
    'wav_48000':('WAV · 48 kHz · 24-bit PCM',48000,192),
}


async def stop_process_tree(process):
    """Windows venv python is a launcher: reap its actual worker as well."""
    if process.returncode is not None:
        return
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    for child in reversed(children):
        try: child.kill()
        except psutil.NoSuchProcess: pass
    try: process.kill()
    except ProcessLookupError: pass
    await process.wait()
    if children:
        _, alive = await asyncio.to_thread(psutil.wait_procs, children, timeout=10)
        if alive:
            raise RuntimeError('The local speech worker is still stopping. Please retry shortly.')


async def command(*args):
    process=await asyncio.create_subprocess_exec(*map(str,args),stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,creationflags=NO_WINDOW)
    try:
        out,err=await process.communicate()
    except BaseException:
        await stop_process_tree(process)
        await process.communicate()
        raise
    if process.returncode: raise RuntimeError(err.decode('utf-8',errors='replace')[-2000:])
    return out


def normalized(value):
    return ''.join(c.casefold() for c in value if c.isalnum())


class AudioEngine:
    def __init__(self):
        self.kokoro_lock=asyncio.Lock()
        self.kitten_lock=asyncio.Lock()
        self._kitten_model=None
        self.piper_lock=asyncio.Lock()
        # Keep recent packs warm without retaining every installed model.
        self._piper_models=OrderedDict()
        self._piper_cache_limit=max(1,int(os.getenv('PIPER_MODEL_CACHE_SIZE','2')))
        self.chatterbox_lock=asyncio.Lock()
        self._chatterbox_process=None
        self._idle_timeout=max(0,float(os.getenv('MODEL_IDLE_TIMEOUT_SECONDS','600')))
        self._idle_tasks={}

    async def close(self):
        idle_tasks=list(self._idle_tasks.values())
        self._idle_tasks.clear()
        for task in idle_tasks: task.cancel()
        if idle_tasks: await asyncio.gather(*idle_tasks,return_exceptions=True)
        if self._chatterbox_process and self._chatterbox_process.returncode is None:
            await stop_process_tree(self._chatterbox_process)
        self._chatterbox_process=None
        self._kitten_model=None
        self._piper_models.clear()
        gc.collect()

    def _schedule_unload(self,engine):
        if self._idle_timeout<=0 or engine not in ('kitten','piper','chatterbox'): return
        previous=self._idle_tasks.pop(engine,None)
        if previous: previous.cancel()
        task=asyncio.create_task(self._unload_after_idle(engine))
        self._idle_tasks[engine]=task
        task.add_done_callback(lambda completed,name=engine:
            self._idle_tasks.pop(name,None) if self._idle_tasks.get(name) is completed else None)

    async def _unload_after_idle(self,engine):
        await asyncio.sleep(self._idle_timeout)
        await self._release_engine(engine)

    async def _release_engine(self,engine):
        lock={'kitten':self.kitten_lock,'piper':self.piper_lock,
              'chatterbox':self.chatterbox_lock}.get(engine)
        if lock is None: return
        async with lock:
            if engine=='kitten': self._kitten_model=None
            elif engine=='piper': self._piper_models.clear()
            elif self._chatterbox_process and self._chatterbox_process.returncode is None:
                await stop_process_tree(self._chatterbox_process)
                self._chatterbox_process=None
            gc.collect()

    async def unload(self,engine):
        """Immediately release a retained model when it is not generating."""
        task=self._idle_tasks.pop(engine,None)
        if task: task.cancel()
        await self._release_engine(engine)

    async def _chatterbox_worker(self):
        process=self._chatterbox_process
        if process and process.returncode is None: return process
        configured=os.getenv('CHATTERBOX_PYTHON')
        candidates=[Path(configured).expanduser() if configured else None,
                    ROOT/'.venv-chatterbox'/'Scripts'/'python.exe',
                    ROOT/'.venv-chatterbox'/'bin'/'python']
        python=next((path for path in candidates if path and path.is_file()),None)
        if python is None and importlib.util.find_spec('chatterbox') is not None: python=Path(sys.executable)
        if python is None: raise RuntimeError('Chatterbox Nano environment is not installed. Run setup_chatterbox.py.')
        process=await asyncio.create_subprocess_exec(str(python),str(ROOT/'chatterbox_worker.py'),
            stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
            creationflags=NO_WINDOW)
        self._chatterbox_process=process
        while True:
            line=await asyncio.wait_for(process.stdout.readline(),180)
            if not line: raise RuntimeError('Chatterbox Nano stopped while loading the model.')
            message=json.loads(line)
            if message.get('event')=='ready': return process

    async def warm_chatterbox(self):
        """Load Nano in the isolated worker while the user chooses a voice."""
        async with self.chatterbox_lock:
            await self._chatterbox_worker()

    async def chatterbox(self,job,folder,progress):
        """Persistent isolated Nano worker with CPU-safe thread limits."""
        async with self.chatterbox_lock:
            process=await self._chatterbox_worker()
            request={**job,'folder':str(folder.resolve())}
            job_path=folder/'chatterbox-job.json'
            job_path.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
            try:
                process.stdin.write((str(job_path.resolve())+'\n').encode())
                await process.stdin.drain()
                while True:
                    line=await asyncio.wait_for(process.stdout.readline(),3600)
                    if not line: raise RuntimeError('Chatterbox Nano worker stopped unexpectedly.')
                    message=json.loads(line)
                    if message.get('event')=='progress' and progress: progress(float(message['progress']))
                    elif message.get('event')=='error': raise RuntimeError('Chatterbox Nano: '+message['error'])
                    elif message.get('event')=='done': break
            except BaseException:
                if process.returncode is None: await stop_process_tree(process)
                self._chatterbox_process=None
                raise
            timing=json.loads((folder/'timing-raw.json').read_text(encoding='utf-8'))
            speed=float(job['speed']); ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
            await command(ffmpeg,'-v','error','-y','-i',folder/'master-raw.wav','-filter:a',f'atempo={speed}',
                          '-ar',RATE,'-ac','1','-c:a','pcm_s24le',folder/'master.wav')
            if speed!=1:
                for word in timing['words']:
                    word['start']/=speed; word['end']/=speed
                for segment in timing['segments']:
                    segment['start']/=speed; segment['end']/=speed
                timing['duration']/=speed
            timing['native_sample_rate']=RATE
            return timing

    async def edge(self,job,folder,progress):
        words=[]
        segments=[]
        duration=0
        spoken=0
        pieces=split_script(job['text'],job.get('paragraph_pause',0))
        total=sum(len(value) for kind,value in pieces if kind=='text')
        with sf.SoundFile(folder/'master.wav',mode='w',samplerate=RATE,channels=1,subtype='PCM_24') as master:
            for index,(kind,value) in enumerate(pieces):
                if kind=='silence':
                    samples=np.zeros(round(value*RATE),dtype=np.float32)
                    master.write(samples)
                    segments.append({'type':'silence','start':duration,'end':duration+len(samples)/RATE})
                    duration+=len(samples)/RATE
                    continue
                # Voice, prosody and format never change on retries or at pause boundaries.
                talk=edge_tts.Communicate(value,job['voice'],rate=f"{round((job['speed']-1)*100):+d}%",
                    pitch=f"{job['pitch']:+d}Hz",volume=f"{job['volume']:+d}%",boundary='WordBoundary',
                    connect_timeout=15,receive_timeout=60)
                part=folder/f'edge-{index}.mp3'
                timing=[]
                chunk_spoken=0
                last_progress=0
                with part.open('wb') as output:
                    async for chunk in talk.stream():
                        if chunk['type']=='audio': output.write(chunk['data'])
                        elif chunk['type']=='WordBoundary':
                            timing.append({'text':chunk['text'],'start':chunk['offset']/1e7,
                                           'end':(chunk['offset']+chunk['duration'])/1e7})
                            chunk_spoken+=len(chunk['text'])
                            if progress and time.monotonic()-last_progress>.5:
                                progress(min(.9,(spoken+chunk_spoken)/max(1,total)))
                                last_progress=time.monotonic()
                if not timing or part.stat().st_size<100: raise RuntimeError('Edge returned incomplete audio or no timings.')
                expected=normalized(value)
                received=normalized(' '.join(w['text'] for w in timing))
                if len(received)<len(expected)*.97 or not received.endswith(expected[-60:]):
                    raise RuntimeError('The service ended before the full script was spoken. Retrying the complete script.')
                pcm=await command(imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',part,'-f','f32le','-ac','1','-ar',RATE,'pipe:1')
                samples=np.frombuffer(pcm,dtype='<f4')
                length=len(samples)/RATE
                # Preserve source punctuation between Edge's word boundaries.
                cursor=0
                for i,word in enumerate(timing):
                    found=value.find(word['text'],cursor)
                    if found>=0:
                        stop=found+len(word['text'])
                        trailing=''
                        for character in value[stop:]:
                            if character in '[]' or unicodedata.category(character)[0] not in 'PS': break
                            trailing+=character
                        prefix=value[cursor:found]
                        word['text']+=trailing
                        word['prefix']=prefix if prefix.strip() else (' ' if i else '')
                        cursor=stop+len(trailing)
                    else: word['prefix']=' ' if i else ''
                    word['start']=duration+min(length,max(0,word['start']))
                    word['end']=duration+min(length,max(0,word['end']))
                    words.append(word)
                master.write(samples)
                segments.append({'type':'speech','start':duration,'end':duration+length,'text':value})
                duration+=length
                spoken+=len(value)
        return {'words':words,'segments':segments,'duration':duration,'source':'edge','native_sample_rate':RATE,'voice':job['voice']}

    async def kokoro(self,job,folder,progress,stem):
        async with self.kokoro_lock:
            job=dict(job)
            if job.get('live_preview'):
                live_folder=stem.parent/'live'/stem.name
                live_folder.mkdir(parents=True,exist_ok=True)
                job.update(_live_folder=str(live_folder.resolve()),_live_run=uuid.uuid4().hex[:12])
                (live_folder/'manifest.json').write_text(json.dumps({'run':job['_live_run'],'files':[]}),encoding='utf-8')
            (folder/'job.json').write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
            with (folder/'worker.log').open('wb') as log:
                process=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'kokoro_worker.py'),str(folder),
                    stdout=log,stderr=log,creationflags=NO_WINDOW)
                try:
                    while process.returncode is None:
                        try: await asyncio.wait_for(process.wait(),.5)
                        except asyncio.TimeoutError: pass
                        path=folder/'progress.json'
                        if progress and path.exists():
                            try: progress(json.loads(path.read_text(encoding='utf-8'))['progress'])
                            except (OSError,ValueError): pass
                except BaseException:
                    # Reap descendants BEFORE the log handle closes and the temporary
                    # directory is removed. Otherwise WinError 32 masks cancellation.
                    await stop_process_tree(process)
                    raise
                if process.returncode:
                    error=folder/'error.txt'
                    detail=error.read_text(encoding='utf-8') if error.exists() else (folder/'worker.log').read_text(encoding='utf-8',errors='replace')[-1800:]
                    raise RuntimeError('Kokoro: '+detail)
            return json.loads((folder/'timing.json').read_text(encoding='utf-8'))

    async def isolated_local(self,engine,job,folder,progress):
        """Run an ONNX engine once so the OS reclaims all native model memory."""
        (folder/'job.json').write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
        with (folder/'worker.log').open('wb') as log:
            process=await asyncio.create_subprocess_exec(
                sys.executable,str(ROOT/'local_engine_worker.py'),engine,str(folder),
                stdout=log,stderr=log,creationflags=NO_WINDOW)
            try:
                while process.returncode is None:
                    try: await asyncio.wait_for(process.wait(),.25)
                    except asyncio.TimeoutError: pass
                    path=folder/'progress.json'
                    if progress and path.exists():
                        try: progress(json.loads(path.read_text(encoding='utf-8'))['progress'])
                        except (OSError,ValueError): pass
            except BaseException:
                await stop_process_tree(process)
                raise
            if process.returncode:
                error=folder/'error.txt'
                detail=(error.read_text(encoding='utf-8') if error.exists() else
                        (folder/'worker.log').read_text(encoding='utf-8',errors='replace')[-1800:])
                raise RuntimeError(engine.title()+': '+detail)
        return json.loads((folder/'timing.json').read_text(encoding='utf-8'))

    async def kitten(self,job,folder,progress):
        """Fast, persistent ONNX inference for low-power English CPU systems."""
        async with self.kitten_lock:
            if self._kitten_model is None:
                from kittentts import KittenTTS
                self._kitten_model=await asyncio.to_thread(
                    KittenTTS,'KittenML/kitten-tts-micro-0.8',str(MODEL_ROOT/'kitten'))
            pieces=split_script(job['text'],job.get('paragraph_pause',0))
            total=sum(len(value) for kind,value in pieces if kind=='text')
            spoken=0
            duration=0.0
            words=[]
            segments=[]
            with sf.SoundFile(folder/'master.wav',mode='w',samplerate=RATE,channels=1,subtype='PCM_24') as master:
                for kind,value in pieces:
                    if kind=='silence':
                        samples=np.zeros(round(value*RATE),dtype=np.float32)
                        master.write(samples)
                        segments.append({'type':'silence','start':duration,'end':duration+len(samples)/RATE})
                        duration+=len(samples)/RATE
                        continue
                    samples=await asyncio.to_thread(self._kitten_model.generate,value,
                                                    job['voice'],job['speed'])
                    samples=np.asarray(samples,dtype=np.float32).reshape(-1)
                    if not len(samples): raise RuntimeError('Kitten returned no audio.')
                    length=len(samples)/RATE
                    tokens=list(re.finditer(r"\S+",value))
                    weight=sum(max(1,len(match.group())) for match in tokens) or 1
                    cursor=0
                    for index,match in enumerate(tokens):
                        share=max(1,len(match.group()))/weight
                        start=duration+length*cursor/weight
                        cursor+=max(1,len(match.group()))
                        words.append({'text':match.group(),'prefix':value[tokens[index-1].end():match.start()] if index else value[:match.start()],
                                      'start':start,'end':duration+length*cursor/weight})
                    master.write(samples)
                    segments.append({'type':'speech','start':duration,'end':duration+length,'text':value})
                    duration+=length
                    spoken+=len(value)
                    if progress: progress(min(.9,spoken/max(1,total)))
            return {'words':words,'segments':segments,'duration':duration,'source':'kitten',
                    'native_sample_rate':RATE,'voice':job['voice'],'timing_method':'measured proportional word timing'}

    async def piper(self,job,folder,progress):
        """Very fast American English ONNX voices with a small resident model cache."""
        async with self.piper_lock:
            from piper import PiperVoice
            from piper.config import SynthesisConfig
            from scipy.signal import resample_poly
            voice_parts=job['voice'].split('::',1)
            model_id=voice_parts[0]
            speaker_id=int(voice_parts[1]) if len(voice_parts)>1 else None
            model_path=MODEL_ROOT/'piper'/(model_id+'.onnx')
            if not model_path.is_file(): raise RuntimeError('The selected Piper voice pack is not installed.')
            model=self._piper_models.pop(model_id,None)
            if model is None:
                model=await asyncio.to_thread(PiperVoice.load,model_path)
            self._piper_models[model_id]=model
            while len(self._piper_models)>self._piper_cache_limit:
                _,expired=self._piper_models.popitem(last=False)
                del expired
                gc.collect()

            def render(text):
                config=SynthesisConfig(speaker_id=speaker_id,length_scale=1/max(.5,job['speed']))
                chunks=list(model.synthesize(text,config))
                if not chunks: return np.empty(0,dtype=np.float32)
                samples=np.concatenate([np.asarray(chunk.audio_float_array,dtype=np.float32).reshape(-1) for chunk in chunks])
                source_rate=chunks[0].sample_rate
                return resample_poly(samples,RATE,source_rate).astype(np.float32) if source_rate!=RATE else samples

            pieces=split_script(job['text'],job.get('paragraph_pause',0))
            total=sum(len(value) for kind,value in pieces if kind=='text')
            spoken=0
            duration=0.0
            words=[]
            segments=[]
            with sf.SoundFile(folder/'master.wav',mode='w',samplerate=RATE,channels=1,subtype='PCM_24') as master:
                for kind,value in pieces:
                    if kind=='silence':
                        samples=np.zeros(round(value*RATE),dtype=np.float32)
                        master.write(samples)
                        segments.append({'type':'silence','start':duration,'end':duration+len(samples)/RATE})
                        duration+=len(samples)/RATE
                        continue
                    samples=await asyncio.to_thread(render,value)
                    if not len(samples): raise RuntimeError('Piper returned no audio.')
                    length=len(samples)/RATE
                    tokens=list(re.finditer(r"\S+",value))
                    weight=sum(max(1,len(match.group())) for match in tokens) or 1
                    cursor=0
                    for index,match in enumerate(tokens):
                        start=duration+length*cursor/weight
                        cursor+=max(1,len(match.group()))
                        words.append({'text':match.group(),'prefix':value[tokens[index-1].end():match.start()] if index else value[:match.start()],
                                      'start':start,'end':duration+length*cursor/weight})
                    master.write(samples)
                    segments.append({'type':'speech','start':duration,'end':duration+length,'text':value})
                    duration+=length
                    spoken+=len(value)
                    if progress: progress(min(.9,spoken/max(1,total)))
            return {'words':words,'segments':segments,'duration':duration,'source':'piper',
                    'native_sample_rate':22050,'voice':job['voice'],'timing_method':'measured proportional word timing'}

    async def _generate(self,job,stem,progress=None):
        stem.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=stem.name+'-',dir=stem.parent) as temp:
            folder=Path(temp)
            async with asyncio.timeout(3600):
                if job.get('engine')=='kokoro':
                    timing=await self.kokoro(job,folder,progress,stem)
                elif job.get('engine') in ('kitten','piper') and os.getenv('ISOLATE_LOCAL_ENGINES','').lower() in ('1','true','yes','on'):
                    timing=await self.isolated_local(job['engine'],job,folder,progress)
                elif job.get('engine')=='kitten':
                    timing=await self.kitten(job,folder,progress)
                elif job.get('engine')=='piper':
                    timing=await self.piper(job,folder,progress)
                elif job.get('engine')=='chatterbox':
                    timing=await self.chatterbox(job,folder,progress)
                else:
                    timing=await self.edge(job,folder,progress)
                # Whole-recording gain: never normalize different segments independently.
                samples,sr=sf.read(folder/'master.wav',dtype='float32')
                peak=float(np.max(np.abs(samples))) if len(samples) else 0
                if peak<=0 or not np.isfinite(samples).all(): raise RuntimeError('The generated recording is silent or invalid.')
                gain=10**(job.get('output_gain',0)/20)
                if job.get('normalize',True): gain*=10**(-1/20)/peak
                gain=min(gain,10**(-.2/20)/peak)
                sf.write(folder/'processed.wav',samples*gain,sr,subtype='PCM_24')
                del samples
                name,out_rate,bitrate=FORMATS[job.get('export_format','mp3_44100_192')]
                mp3_rate=44100 if out_rate<32000 else out_rate
                ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
                for extension,codec_args in [('mp3',['-codec:a','libmp3lame','-b:a',f'{bitrate}k']),('wav',['-codec:a','pcm_s24le'])]:
                    await command(ffmpeg,'-v','error','-y','-i',folder/'processed.wav','-ar',mp3_rate if extension=='mp3' else out_rate,'-ac','1',*codec_args,folder/f'final.{extension}')
                length=sf.info(folder/'processed.wav').duration
                captions=caption_groups(timing['words'],job.get('subtitle_width',42),job.get('subtitle_seconds',6))
                captions=write_subtitles(folder/'final',captions,length)
                timing.update(duration=length,captions=captions,export_format=name,export_sample_rate=mp3_rate,export_wav_sample_rate=out_rate,
                              export_mp3_kbps=bitrate,settings=job,applied_gain=gain)
                (folder/'final.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding='utf-8')
                # Only publish a fully successful audio + subtitle set. Failed retries leave no partial result.
                for ext in ('mp3','wav','srt','vtt','json'):
                    os.replace(folder/f'final.{ext}',stem.with_suffix('.'+ext))
                if progress: progress(1)
                return length

    async def generate(self,job,stem,progress=None):
        from voice_catalog import require_engine
        engine=job.get('engine','edge')
        require_engine(engine)
        previous=self._idle_tasks.pop(engine,None)
        if previous: previous.cancel()
        try:
            return await self._generate(job,stem,progress)
        finally:
            self._schedule_unload(engine)
