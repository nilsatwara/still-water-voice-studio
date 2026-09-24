from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel,ConfigDict,Field

class PostCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str=Field(min_length=1,max_length=240); slug:str|None=Field(default=None,max_length=240); content:str=Field(default='',max_length=1_000_000); excerpt:str|None=Field(default=None,max_length=2000); status:Literal['draft','published']='draft'; seo_title:str|None=Field(default=None,max_length=240); seo_description:str|None=Field(default=None,max_length=500); seo_keywords:list[str]=Field(default_factory=list,max_length=30); canonical_url:str|None=Field(default=None,max_length=2048); og_title:str|None=Field(default=None,max_length=240); og_description:str|None=Field(default=None,max_length=500); robots_index:bool=True; robots_follow:bool=True
class PostUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    title:str|None=Field(default=None,min_length=1,max_length=240); slug:str|None=Field(default=None,min_length=1,max_length=240); content:str|None=Field(default=None,max_length=1_000_000); excerpt:str|None=Field(default=None,max_length=2000); status:Literal['draft','published']|None=None; seo_title:str|None=Field(default=None,max_length=240); seo_description:str|None=Field(default=None,max_length=500); seo_keywords:list[str]|None=Field(default=None,max_length=30); canonical_url:str|None=Field(default=None,max_length=2048); og_title:str|None=Field(default=None,max_length=240); og_description:str|None=Field(default=None,max_length=500); robots_index:bool|None=None; robots_follow:bool|None=None
class PostResponse(PostCreate):
    model_config=ConfigDict(from_attributes=True,extra='forbid'); id:uuid.UUID; slug:str; status:Literal['draft','published','trash']; author_id:uuid.UUID; created_at:datetime; updated_at:datetime; published_at:datetime|None; deleted_at:datetime|None
class PostListResponse(BaseModel): items:list[PostResponse]; total:int; limit:int; offset:int
