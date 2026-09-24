"""Kokoro service boundary without loading the model in the API process."""
from .legacy_adapter import LegacyCatalogAdapter


class KokoroTTSService:
    def __init__(self, adapter: LegacyCatalogAdapter):
        self._adapter = adapter

    def voices(self) -> list[dict]:
        return self._adapter.voices('kokoro')
