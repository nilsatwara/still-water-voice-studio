import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audio_engine import AudioEngine
from server import Studio
from speech_text import split_batch, caption_groups


class BatchTests(unittest.TestCase):
    def test_long_and_markdown_separators_preserve_prose(self):
        text='First well-being script.\n\n**'+'-'*89+'**\r\nSecond script.\n--------------------\nThird script.'
        self.assertEqual(split_batch(text),['First well-being script.','Second script.','Third script.'])
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            studio.voices=[{'ShortName':'en-US-AndrewNeural'}]
            studio.add([{'text':text,'title':'Prayer','speed':.8}])
            self.assertEqual([j['text'] for j in studio.jobs()],split_batch(text))
            self.assertTrue(all(j['speed']==.8 for j in studio.jobs()))
            studio.db.close()

    def test_combining_marks_are_not_split(self):
        text='શાંતિપૂર્ણજીવનમાટેહાર્દિકશુભેચ્છાઓ'
        cues=caption_groups([{'text':text,'start':0,'end':4}],width=24)
        self.assertEqual(cues[0]['text'],text)


class WorkerCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def run_failure(self, cancel):
        # Real venv launcher + a descendant holding master.wav open reproduces
        # the Windows failure without loading the large speech model.
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            child="import pathlib,time,sys; p=pathlib.Path(sys.argv[1]); f=(p/'master.wav').open('wb'); (p/'progress.json').write_text('{\"progress\":0.1}'); time.sleep(120)"
            (root/'kokoro_worker.py').write_text('import subprocess,sys\np=subprocess.Popen([sys.executable,"-c",'+repr(child)+',sys.argv[1]])\np.wait()\n')
            started=asyncio.Event()
            def progress(value):
                started.set()
                if not cancel: raise RuntimeError('original callback failure')
            with patch('audio_engine.ROOT',root):
                task=asyncio.create_task(AudioEngine().generate({'engine':'kokoro','text':'Hello'},root/'outputs'/'check',progress))
                await asyncio.wait_for(started.wait(),20)
                if cancel:
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError): await task
                else:
                    with self.assertRaisesRegex(RuntimeError,'original callback failure'): await task
            self.assertEqual(list((root/'outputs').iterdir()),[])

    async def test_cancel_reaps_descendants_and_removes_locked_files(self):
        await self.run_failure(True)

    async def test_other_exception_is_not_masked_by_file_lock(self):
        await self.run_failure(False)
