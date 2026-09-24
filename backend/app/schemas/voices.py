from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


EngineId = Literal['edge', 'kokoro']
GenderValue = Literal['Male', 'Female']


class VoiceTagData(BaseModel):
    model_config = ConfigDict(extra='allow')

    ContentCategories: list[str] = Field(default_factory=list)
    VoicePersonalities: list[str] = Field(default_factory=list)


class Voice(BaseModel):
    """Public voice data with provider identifiers preserved verbatim."""
    model_config = ConfigDict(extra='forbid')

    Name: str
    ShortName: str
    Gender: GenderValue
    Locale: str
    LocaleName: str
    Engine: EngineId
    Uses: list[str]
    Age: str
    TagsSource: str
    VoiceTag: VoiceTagData = Field(default_factory=VoiceTagData)
    FriendlyName: str | None = None
    SuggestedCodec: str | None = None
    Status: str | None = None
    AuditionURL: str | None = None


class VoicesResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    engine: EngineId
    voices: list[Voice]
    count: int = Field(ge=0)
