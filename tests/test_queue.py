import asyncio
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from server import Studio


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.studio = Studio(Path(self.temp.name))
        self.studio.voices = [{'ShortName': 'en-US-AndrewNeural'}]
        self.task = None

    async def asyncTearDown(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.studio.db.close()
        self.temp.cleanup()

    def add(self, text):
        return self.studio.add([{'text': text}])[0]

    async def until(self, condition):
        for _ in range(200):
            if condition():
                return
            await asyncio.sleep(.01)
        self.fail('Queue did not reach expected state')

    async def test_failed_first_job_blocks_second_until_recovery(self):
        first, second = self.add('First script.'), self.add('Second script.')
        calls = []

        async def synth(job, stem, progress):
            calls.append(job['id'])
            if len(calls) == 1:
                raise ConnectionError('Simulated network interruption')
            return 12.5

        self.studio.synthesize = synth
        self.task = asyncio.create_task(self.studio.worker())
        await self.until(lambda: self.studio.jobs()[0]['status'] == 'retrying')
        await asyncio.sleep(.08)
        self.assertEqual(calls, [first])
        self.assertEqual(self.studio.jobs()[1]['status'], 'queued')
        self.studio.update(first, next_retry=0)
        self.studio.wake.set()
        await self.until(lambda: self.studio.jobs()[1]['status'] == 'completed')
        self.assertEqual(calls, [first, first, second])

    async def test_pause_and_restart_preserve_queue(self):
        first = self.add('Recover me.')
        self.studio.update(first, status='running', progress=.5)
        self.studio.db.execute("INSERT INTO settings VALUES('paused','1')")
        self.studio.db.commit()
        self.studio.db.close()
        self.studio = Studio(Path(self.temp.name))
        self.assertTrue(self.studio.paused())
        self.assertEqual(self.studio.jobs()[0]['status'], 'queued')
        self.assertEqual(self.studio.jobs()[0]['progress'], 0)
        calls = []
        async def synth(job, stem, progress):
            calls.append(job['id'])
            return 1
        self.studio.synthesize = synth
        self.task = asyncio.create_task(self.studio.worker())
        await asyncio.sleep(.05)
        self.assertEqual(calls, [])
        self.studio.db.execute("UPDATE settings SET value='0' WHERE key='paused'")
        self.studio.db.commit()
        self.studio.wake.set()
        await self.until(lambda: self.studio.jobs()[0]['status'] == 'completed')
        self.assertEqual(calls, [first])

    async def test_invalid_batch_is_atomic(self):
        with self.assertRaises(ValueError):
            self.studio.add([{'text':'Valid script'}, {'text':'', 'speed':2}])
        self.assertEqual(self.studio.jobs(), [])

    async def test_all_six_speeds_and_bounds(self):
        for speed in (.5,.6,.7,.8,.9,1):
            self.assertEqual(self.studio.validate({'text':'Hello', 'speed':speed})['speed'], speed)
        for raw in ({'speed':1.25}, {'pitch':100}, {'voice':'missing'}, {'text':'x'*40001}):
            with self.assertRaises(ValueError):
                self.studio.validate({'text':'Hello', **raw})

    async def test_midstream_failure_discards_partial_audio(self):
        class BrokenStream:
            def __init__(self, *args, **kwargs):
                pass
            async def stream(self):
                yield {'type':'audio', 'data':b'partial audio'*100}
                raise ConnectionError('Connection lost halfway through')
        stem = self.studio.outputs / 'interrupted'
        with patch('server.edge_tts.Communicate', BrokenStream):
            with self.assertRaises(ConnectionError):
                await self.studio.synthesize(self.studio.validate({'text':'A complete script.'}), stem)
        self.assertFalse(stem.with_suffix('.part').exists())
        self.assertFalse(stem.with_suffix('.mp3').exists())

    async def test_truncated_script_is_not_published(self):
        class TruncatedStream:
            def __init__(self, *args, **kwargs):
                pass
            async def stream(self):
                yield {'type':'audio', 'data':b'audio'*100}
                yield {'type':'WordBoundary', 'offset':0, 'duration':10000000, 'text':'First sentence.'}
        stem = self.studio.outputs / 'truncated'
        with patch('server.edge_tts.Communicate', TruncatedStream):
            with self.assertRaisesRegex(RuntimeError, 'full script'):
                await self.studio.synthesize(self.studio.validate({'text':'First sentence. Missing final sentence.'}), stem)
        self.assertFalse(stem.with_suffix('.part').exists())
        self.assertFalse(stem.with_suffix('.mp3').exists())


if __name__ == '__main__':
    unittest.main()
