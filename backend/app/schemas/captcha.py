from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
class CaptchaUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid');enabled:bool=False;site_key:str=Field(default='',max_length=255);test_mode:bool=True;on_signup:bool=True;on_signin:bool=False;on_forgot_password:bool=True;on_contact:bool=True;on_api_key:bool=True;tts_policy:Literal['never','guest','guest_free','except_admin','all']='guest'
class CaptchaPublic(BaseModel):enabled:bool;site_key:str;test_mode:bool;surfaces:dict[str,bool];tts_policy:str
class CaptchaAdmin(CaptchaUpdate):secret_configured:bool
class TurnstileToken(BaseModel):token:str=Field(min_length=1,max_length=2048);remote_ip:str|None=None
class VerificationResult(BaseModel):success:bool
