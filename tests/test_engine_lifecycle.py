import asyncio
import os
import sys
import unittest
from unittest.mock import patch

from audio_engine import AudioEngine
from voice_catalog import capabilities, require_engine


class EngineConfigurationTests(unittest.TestCase):
    def test_lightweight_profile_disables_every_local_engine(self):
        clean = {key:value for key,value in os.environ.items() if not key.startswith('ENABLE_')}
        clean['STILLWATER_PROFILE'] = 'lightweight'
        with patch.dict(os.environ, clean, clear=True):
            result = capabilities()
            self.assertTrue(result['edge']['ready'])
            for engine in ('kokoro','piper','kitten','chatterbox'):
                self.assertFalse(result[engine]['enabled'])
                self.assertFalse(result[engine]['ready'])
                with self.assertRaisesRegex(ValueError, 'disabled'):
                    require_engine(engine)

    def test_individual_flag_overrides_lightweight_default(self):
        with patch.dict(os.environ, {'STILLWATER_PROFILE':'lightweight','ENABLE_PIPER':'true'}, clear=False):
            self.assertTrue(capabilities()['piper']['enabled'])


class EngineIdleReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_idle_timer_releases_in_process_models(self):
        engine = AudioEngine()
        engine._idle_timeout = .02
        engine._kitten_model = object()
        engine._piper_models['voice'] = object()
        engine._schedule_unload('kitten')
        engine._schedule_unload('piper')
        await asyncio.sleep(.08)
        self.assertIsNone(engine._kitten_model)
        self.assertFalse(engine._piper_models)
        await engine.close()

    async def test_idle_timer_stops_chatterbox_worker(self):
        engine = AudioEngine()
        engine._idle_timeout = .02
        engine._chatterbox_process = await asyncio.create_subprocess_exec(
            sys.executable, '-c', 'import time; time.sleep(60)')
        engine._schedule_unload('chatterbox')
        await asyncio.sleep(.15)
        self.assertIsNone(engine._chatterbox_process)
        await engine.close()
