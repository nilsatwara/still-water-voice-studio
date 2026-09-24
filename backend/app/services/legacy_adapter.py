"""Narrow compatibility boundary around the existing root-level modules.

The working TTS modules remain at the repository root during migration. This
adapter resolves that root once and imports only public catalog constants and
functions. API routes must depend on services, never import legacy modules.
The path bridge can be removed after the TTS services move into backend/app.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Literal


PROJECT_ROOT = Path(__file__).resolve().parents[3]
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)

from audio_engine import FORMATS  # noqa: E402
from voice_catalog import AGES, LANGUAGES, USES, capabilities, enrich, kokoro_voices  # noqa: E402

EngineId = Literal['edge', 'kokoro']


class LegacyCatalogAdapter:
    """Read-only access to the same definitions used by the aiohttp app."""

    def _edge_source(self) -> list[dict[str, Any]]:
        cache = PROJECT_ROOT / 'data' / 'voices.json'
        if not cache.is_file():
            raise RuntimeError('The Edge voice catalog is not available.')
        value = json.loads(cache.read_text(encoding='utf-8'))
        if not isinstance(value, list):
            raise RuntimeError('The Edge voice catalog is invalid.')
        return value

    def voices(self, engine: EngineId) -> list[dict[str, Any]]:
        if engine == 'edge':
            result = [enrich(voice, 'edge') for voice in self._edge_source()]
        elif engine == 'kokoro':
            result = kokoro_voices()
        else:
            raise ValueError('Unsupported engine.')
        # Prevent response serialization from mutating legacy catalog objects.
        return deepcopy(result)

    def capabilities(self) -> dict[str, Any]:
        engines = deepcopy(capabilities())
        formats = {identifier: definition[0] for identifier, definition in FORMATS.items()}
        languages = [
            {'code': code, 'locale': locale, 'name': name}
            for code, (locale, name) in LANGUAGES.items()
        ]
        return {
            'engines': engines,
            'formats': formats,
            'languages': languages,
            'uses': list(USES),
            'ages': list(AGES),
        }
