from datetime import datetime
import uuid
from pydantic import BaseModel,ConfigDict,Field
class MediaUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid');alt_text:str|None=Field(default=None,max_length=500);caption:str|None=Field(default=None,max_length=4000)
class MediaResponse(MediaUpdate):
 model_config=ConfigDict(from_attributes=True,extra='forbid');id:uuid.UUID;original_filename:str;mime_type:str;file_size:int;width:int;height:int;status:str;uploaded_by:uuid.UUID;created_at:datetime;updated_at:datetime;deleted_at:datetime|None;url:str
class MediaListResponse(BaseModel):items:list[MediaResponse];total:int;limit:int;offset:int
