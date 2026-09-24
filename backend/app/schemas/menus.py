import uuid
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
class MenuCreate(BaseModel):model_config=ConfigDict(extra='forbid');name:str=Field(min_length=1,max_length=120);slug:str|None=Field(default=None,max_length=120);location:Literal['header','footer','custom'];status:Literal['active','disabled']='active'
class MenuUpdate(BaseModel):model_config=ConfigDict(extra='forbid');name:str|None=Field(default=None,min_length=1,max_length=120);slug:str|None=Field(default=None,min_length=1,max_length=120);location:Literal['header','footer','custom']|None=None;status:Literal['active','disabled']|None=None
class ItemWrite(BaseModel):
 model_config=ConfigDict(extra='forbid');label:str=Field(min_length=1,max_length=120);url:str|None=Field(default=None,max_length=2048);page_id:uuid.UUID|None=None;parent_id:uuid.UUID|None=None;position:int=Field(default=0,ge=0,le=10000);open_in_new_tab:bool=False;enabled:bool=True
 @model_validator(mode='after')
 def destination(self):
  if bool(self.url)==bool(self.page_id):raise ValueError('Provide either a URL or an internal page.')
  if self.url and not (self.url.startswith('/') or self.url.startswith('https://') or self.url.startswith('http://')):raise ValueError('URL must be relative or use HTTP/HTTPS.')
  return self
class ItemUpdate(BaseModel):model_config=ConfigDict(extra='forbid');label:str|None=Field(default=None,min_length=1,max_length=120);url:str|None=Field(default=None,max_length=2048);page_id:uuid.UUID|None=None;parent_id:uuid.UUID|None=None;position:int|None=Field(default=None,ge=0,le=10000);open_in_new_tab:bool|None=None;enabled:bool|None=None
class MenuItemResponse(ItemWrite):model_config=ConfigDict(from_attributes=True,extra='forbid');id:uuid.UUID;menu_id:uuid.UUID
class MenuResponse(MenuCreate):model_config=ConfigDict(from_attributes=True,extra='forbid');id:uuid.UUID;slug:str;items:list[MenuItemResponse]=[]
class ReorderItem(BaseModel):id:uuid.UUID;parent_id:uuid.UUID|None=None;position:int=Field(ge=0,le=10000)
class ReorderRequest(BaseModel):items:list[ReorderItem]=Field(min_length=1,max_length=500)
