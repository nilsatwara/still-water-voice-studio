from datetime import datetime
import uuid
from pydantic import BaseModel,ConfigDict,Field
class TaxonomyCreate(BaseModel):
 model_config=ConfigDict(extra='forbid');name:str=Field(min_length=1,max_length=120);slug:str|None=Field(default=None,max_length=140);description:str|None=Field(default=None,max_length=2000)
class TaxonomyUpdate(BaseModel):
 model_config=ConfigDict(extra='forbid');name:str|None=Field(default=None,min_length=1,max_length=120);slug:str|None=Field(default=None,min_length=1,max_length=140);description:str|None=Field(default=None,max_length=2000)
class TaxonomyResponse(TaxonomyCreate):
 model_config=ConfigDict(from_attributes=True,extra='forbid');id:uuid.UUID;slug:str;status:str;created_at:datetime;updated_at:datetime;deleted_at:datetime|None
class TaxonomyListResponse(BaseModel):items:list[TaxonomyResponse];total:int;limit:int;offset:int
