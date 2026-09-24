from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class EngineCapabilities(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    enabled: bool
    ready: bool
    reason: str
    local: bool
    speed_min: float
    speed_max: float
    pitch: bool
    volume: bool
    blend: bool
    source: str
    timing: str


class LanguageMetadata(BaseModel):
    model_config = ConfigDict(extra='forbid')

    code: str
    locale: str
    name: str


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    engines: dict[Literal['edge', 'kokoro', 'kitten', 'piper', 'chatterbox'], EngineCapabilities]
    formats: dict[str, str]
    languages: list[LanguageMetadata]
    uses: list[str]
    ages: list[str]
