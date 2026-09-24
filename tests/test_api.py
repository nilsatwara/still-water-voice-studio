import asyncio
import base64
import io
import os
import socket
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import numpy as np
import soundfile as sf
from aiohttp.test_utils import TestClient, TestServer
from server import make_app


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        app = make_app(self.temp.name, port)
        self.studio = app['studio']
        async def voices():
            self.studio.voices = [{'ShortName':'en-US-AndrewNeural'}]
        self.studio.refresh_voices = voices
        self.client = TestClient(TestServer(app,port=port))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def until(self, condition):
        for _ in range(200):
            if condition(): return
            await asyncio.sleep(.01)
        self.fail('Expected state was not reached')

    async def test_health_is_lightweight_and_available(self):
        response = await self.client.get('/health')
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['status'], 'ok')

    async def test_optional_basic_auth_protects_studio_but_not_health(self):
        credentials = base64.b64encode(b'stillwater:test-password').decode('ascii')
        with patch.dict(os.environ, {'STILLWATER_PASSWORD': 'test-password'}, clear=False):
            self.assertEqual((await self.client.get('/health')).status, 200)
            self.assertEqual((await self.client.get('/')).status, 401)
            response = await self.client.get('/', headers={'Authorization': f'Basic {credentials}'})
            self.assertEqual(response.status, 200)

    async def test_cancel_running_job_starts_next_once(self):
        calls=[]
        async def synth(job, stem, progress):
            calls.append(job['text'])
            if job['text']=='First':
                await asyncio.sleep(100)
            return 1
        self.studio.synthesize=synth
        response=await self.client.post('/api/jobs',json={'jobs':[{'text':'First'},{'text':'Second'}]})
        ids=(await response.json())['ids']
        await self.until(lambda: calls==['First'])
        response=await self.client.post('/api/jobs/'+ids[0],json={'action':'cancel'})
        self.assertEqual(response.status,200)
        await self.until(lambda:self.studio.jobs()[1]['status']=='completed')
        self.assertEqual(calls,['First','Second'])
        self.assertEqual(self.studio.jobs()[0]['status'],'cancelled')

    async def test_edit_retry_keeps_original_position_and_settings(self):
        calls=[]
        async def synth(job, stem, progress):
            calls.append(job['text'])
            if job['text']=='Broken': raise RuntimeError('Needs editing')
            self.assertEqual(job['speed'], .9 if job['text']=='Fixed' else .8)
            return 1
        self.studio.synthesize=synth
        response=await self.client.post('/api/jobs',json={'jobs':[{'text':'Broken'},{'text':'Next'}]})
        ids=(await response.json())['ids']
        await self.until(lambda:self.studio.jobs()[0]['status']=='retrying')
        await self.client.post('/api/queue',json={'paused':True})
        response=await self.client.post('/api/jobs/'+ids[0],json={'action':'retry','job':{'text':'Fixed','speed':.9}})
        self.assertEqual(response.status,200)
        self.assertEqual(calls,['Broken'])
        await self.client.post('/api/queue',json={'paused':False})
        await self.until(lambda:self.studio.jobs()[1]['status']=='completed')
        self.assertEqual(calls,['Broken','Fixed','Next'])

    async def test_cross_origin_and_invalid_submission_rejected(self):
        response=await self.client.post('/api/jobs',json={'jobs':[{'text':'Hello'}]},headers={'Origin':'https://example.com'})
        self.assertEqual(response.status,403)
        response=await self.client.post('/api/jobs',json={'jobs':[{'text':'Hello'},{'text':''}]})
        self.assertEqual(response.status,400)
        self.assertEqual(self.studio.jobs(),[])

    async def test_delete_recording_removes_database_row_and_all_assets(self):
        job_id = self.studio.add([{'text':'Old recording'}])[0]
        self.studio.update(job_id, status='cancelled')
        for extension in ('mp3', 'wav', 'srt', 'vtt', 'json'):
            (self.studio.outputs / f'{job_id}.{extension}').write_text('test', encoding='utf-8')
        live_dir = self.studio.outputs / 'live' / job_id
        live_dir.mkdir(parents=True)
        (live_dir / 'segment.wav').write_text('test', encoding='utf-8')

        response = await self.client.post('/api/jobs/' + job_id, json={'action':'delete'})

        self.assertEqual(response.status, 200)
        self.assertEqual(self.studio.jobs(), [])
        self.assertEqual(list(self.studio.outputs.glob(job_id + '.*')), [])
        self.assertFalse(live_dir.exists())

    async def test_active_recording_must_be_cancelled_before_delete(self):
        await self.client.post('/api/queue', json={'paused':True})
        job_id = self.studio.add([{'text':'Still queued'}])[0]

        response = await self.client.post('/api/jobs/' + job_id, json={'action':'delete'})

        self.assertEqual(response.status, 400)
        self.assertEqual((await response.json())['error'], 'Cancel this script before deleting it.')
        self.assertEqual(self.studio.jobs()[0]['id'], job_id)

    async def test_selected_recordings_can_be_deleted_together(self):
        first,second=self.studio.add([{'text':'First old recording'},{'text':'Second old recording'}])
        self.studio.update(first,status='completed')
        self.studio.update(second,status='completed')
        for job_id in (first,second):
            (self.studio.outputs/f'{job_id}.mp3').write_text('audio',encoding='utf-8')
        response=await self.client.post('/api/recordings/delete',json={'ids':[first,second]})
        self.assertEqual(response.status,200)
        self.assertEqual((await response.json())['deleted'],2)
        self.assertEqual(self.studio.jobs(),[])
        self.assertFalse(any((self.studio.outputs/f'{job_id}.mp3').exists() for job_id in (first,second)))

    async def test_selected_chatterbox_clones_can_be_deleted_together(self):
        folder=self.studio.data/'chatterbox-voices'; folder.mkdir()
        ids=['clone-'+'1'*32,'clone-'+'2'*32]
        for voice in ids:
            (folder/(voice+'.wav')).write_bytes(b'wave')
            (folder/(voice+'.json')).write_text('{"name":"Test clone"}',encoding='utf-8')
        response=await self.client.post('/api/chatterbox/voices/delete',json={'ids':ids})
        self.assertEqual(response.status,200)
        self.assertEqual((await response.json())['deleted'],2)
        self.assertEqual(list(folder.iterdir()),[])

    async def test_mega_recording_requires_two_parts_and_has_five_hour_limit(self):
        await self.client.post('/api/queue', json={'paused':True})
        first,second=self.studio.add([{'text':'First part'},{'text':'Second part'}])
        self.studio.update(first,status='completed',duration=4*60*60)
        self.studio.update(second,status='completed',duration=2*60*60)

        response=await self.client.get(f'/api/archive?merge=1&mega=1&ids={first}')
        self.assertEqual(response.status,400)
        self.assertIn('at least two', (await response.json())['error'])

        response=await self.client.get(f'/api/archive?merge=1&mega=1&ids={first},{second}')
        self.assertEqual(response.status,400)
        self.assertIn('limited to 5 hours', (await response.json())['error'])

    async def test_mega_download_contains_one_audio_and_synchronized_caption_set(self):
        await self.client.post('/api/queue', json={'paused':True})
        first,second=self.studio.add([{'text':'First part'},{'text':'Second part'}])
        for index,job_id in enumerate((first,second),1):
            self.studio.update(job_id,status='completed',duration=1)
            sf.write(self.studio.outputs/f'{job_id}.wav',np.zeros(24000,dtype=np.float32),24000)
            (self.studio.outputs/f'{job_id}.srt').write_text(
                f'1\n00:00:00,000 --> 00:00:01,000\nPart {index}\n\n',encoding='utf-8')

        response=await self.client.get(f'/api/archive?merge=1&mega=1&ids={first},{second}')

        self.assertEqual(response.status,200)
        archive=zipfile.ZipFile(io.BytesIO(await response.read()))
        names=archive.namelist()
        self.assertEqual(sum(name.endswith('.mp3') for name in names),1)
        self.assertEqual(sum(name.endswith('.srt') for name in names),1)
        self.assertEqual(sum(name.endswith('.vtt') for name in names),1)
        merged_srt=archive.read(next(name for name in names if name.endswith('.srt'))).decode()
        self.assertIn('00:00:01,000 --> 00:00:02,000',merged_srt)

    async def test_background_mega_export_reports_progress_and_downloads(self):
        await self.client.post('/api/queue', json={'paused':True})
        first,second=self.studio.add([{'text':'First part'},{'text':'Second part'}])
        for index,job_id in enumerate((first,second),1):
            self.studio.update(job_id,status='completed',duration=1)
            sf.write(self.studio.outputs/f'{job_id}.wav',np.zeros(24000,dtype=np.float32),24000)
            (self.studio.outputs/f'{job_id}.srt').write_text(
                f'1\n00:00:00,000 --> 00:00:01,000\nPart {index}\n\n',encoding='utf-8')
        response=await self.client.post('/api/exports',json={'ids':[first,second]})
        self.assertEqual(response.status,200)
        export=await response.json()
        progress=[]
        for _ in range(100):
            status_response=await self.client.get('/api/exports/'+export['id'])
            status=await status_response.json(); progress.append(status['progress'])
            if status['status']!='working': break
            await asyncio.sleep(.05)
        self.assertEqual(status['status'],'ready',status)
        self.assertEqual(status['progress'],1)
        self.assertEqual(progress,sorted(progress))
        download=await self.client.get(status['url'])
        self.assertEqual(download.status,200)
        bundle=zipfile.ZipFile(io.BytesIO(await download.read()))
        self.assertEqual(sum(name.endswith('.mp3') for name in bundle.namelist()),1)
        self.assertEqual(sum(name.endswith('.srt') for name in bundle.namelist()),1)
        self.assertEqual(sum(name.endswith('.vtt') for name in bundle.namelist()),1)
