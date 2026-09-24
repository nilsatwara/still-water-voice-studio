"""Edge TTS service boundary without changing legacy synthesis."""
from .legacy_adapter import LegacyCatalogAdapter


class EdgeTTSService:
    def __init__(self, adapter: LegacyCatalogAdapter):
        self._adapter = adapter

    def voices(self) -> list[dict]:
        return self._adapter.voices('edge')
