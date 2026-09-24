import json
import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.capabilities import CapabilitiesResponse
from backend.app.schemas.health import HealthResponse
from backend.app.schemas.voices import VoicesResponse
from backend.app.services.legacy_adapter import LegacyCatalogAdapter, PROJECT_ROOT
from voice_catalog import LANGUAGES, capabilities, enrich, kokoro_voices
from audio_engine import FORMATS


class SidecarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.adapter = LegacyCatalogAdapter()

    def test_health_contract_is_minimal_and_safe(self):
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'service': 'tts-api', 'api_version': 'v1'})
        HealthResponse.model_validate(response.json())

    def test_edge_voices_match_cached_legacy_catalog(self):
        source = json.loads((PROJECT_ROOT / 'data' / 'voices.json').read_text(encoding='utf-8'))
        expected = [enrich(voice, 'edge') for voice in source]
        response = self.client.get('/api/v1/voices', params={'engine': 'edge'})
        self.assertEqual(response.status_code, 200)
        payload = VoicesResponse.model_validate(response.json())
        self.assertEqual(payload.count, len(expected))
        self.assertEqual([voice.ShortName for voice in payload.voices], [voice['ShortName'] for voice in expected])
        self.assertEqual([voice.Locale for voice in payload.voices], [voice['Locale'] for voice in expected])
        self.assertTrue(all(voice.Engine == 'edge' for voice in payload.voices))

    def test_kokoro_voices_match_legacy_catalog(self):
        expected = kokoro_voices()
        response = self.client.get('/api/v1/voices', params={'engine': 'kokoro'})
        self.assertEqual(response.status_code, 200)
        payload = VoicesResponse.model_validate(response.json())
        self.assertEqual(payload.count, len(expected))
        self.assertEqual([voice.ShortName for voice in payload.voices], [voice['ShortName'] for voice in expected])
        self.assertEqual([voice.Locale for voice in payload.voices], [voice['Locale'] for voice in expected])
        self.assertTrue(all(voice.Engine == 'kokoro' for voice in payload.voices))

    def test_capabilities_preserve_legacy_values_and_identifiers(self):
        response = self.client.get('/api/v1/capabilities')
        self.assertEqual(response.status_code, 200)
        payload = CapabilitiesResponse.model_validate(response.json())
        self.assertEqual(payload.engines['edge'].model_dump(), capabilities()['edge'])
        self.assertEqual(payload.engines['kokoro'].model_dump(), capabilities()['kokoro'])
        self.assertEqual(payload.formats, {key: value[0] for key, value in FORMATS.items()})
        self.assertEqual(
            [(item.code, item.locale, item.name) for item in payload.languages],
            [(code, locale, name) for code, (locale, name) in LANGUAGES.items()],
        )

    def test_invalid_or_missing_engine_is_safe_4xx(self):
        for params in ({'engine': 'unknown'}, {}):
            response = self.client.get('/api/v1/voices', params=params)
            self.assertEqual(response.status_code, 422)
            text = response.text.lower()
            self.assertNotIn('traceback', text)
            self.assertNotIn(str(PROJECT_ROOT).lower(), text)

    def test_cors_is_restrictive(self):
        allowed = self.client.get('/api/v1/health', headers={'Origin': 'http://127.0.0.1:8766'})
        self.assertEqual(allowed.headers.get('access-control-allow-origin'), 'http://127.0.0.1:8766')
        denied = self.client.get('/api/v1/health', headers={'Origin': 'https://untrusted.example'})
        self.assertNotIn('access-control-allow-origin', denied.headers)

    def test_adapter_rejects_unknown_engine_without_fallback(self):
        with self.assertRaisesRegex(ValueError, '^Unsupported engine\\.$'):
            self.adapter.voices('unknown')  # type: ignore[arg-type]

    def test_admin_access_endpoint_fails_closed(self):
        response = self.client.get('/api/v1/admin/access', headers={'X-Role': 'SUPER_ADMIN'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], 'Authentication is required.')
