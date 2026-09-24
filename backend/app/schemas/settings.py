from typing import Any
from pydantic import BaseModel,ConfigDict
class SettingUpdate(BaseModel):model_config=ConfigDict(extra='forbid');value:Any
class SettingResponse(BaseModel):namespace:str;key:str;value:Any;is_public:bool
class SettingsResponse(BaseModel):settings:dict[str,dict[str,Any]]
