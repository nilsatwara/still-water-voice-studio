from typing import Literal
from .legacy_adapter import LegacyCatalogAdapter
from .edge_tts_service import EdgeTTSService
from .kokoro_tts_service import KokoroTTSService
from ..schemas.capabilities import CapabilitiesResponse
from ..schemas.voices import VoicesResponse


EngineId = Literal['edge', 'kokoro']


class VoiceService:
    def __init__(self, adapter: LegacyCatalogAdapter | None = None):
        self.adapter = adapter or LegacyCatalogAdapter()
        self.edge = EdgeTTSService(self.adapter)
        self.kokoro = KokoroTTSService(self.adapter)

    def voices(self, engine: EngineId) -> VoicesResponse:
        voices = self.edge.voices() if engine == 'edge' else self.kokoro.voices()
        return VoicesResponse(engine=engine, voices=voices, count=len(voices))

    def capabilities(self) -> CapabilitiesResponse:
        return CapabilitiesResponse.model_validate(self.adapter.capabilities())


voice_service = VoiceService()
