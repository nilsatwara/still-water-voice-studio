from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
import uuid
from PIL import Image,UnidentifiedImageError
from sqlalchemy import func,select
from fastapi import UploadFile
from ..core.config import settings
from ..models import Media
from ..schemas.media import MediaUpdate
from .page_service import PageConflict,PageMissing

FORMATS={'JPEG':('jpg','image/jpeg'),'PNG':('png','image/png'),'WEBP':('webp','image/webp'),'GIF':('gif','image/gif')}
class InvalidMedia(ValueError):pass
class LocalMediaStorage:
 def __init__(self,root:Path):self.root=root.resolve();self.root.mkdir(parents=True,exist_ok=True)
 def save(self,key,data):
  path=(self.root/key).resolve()
  if self.root not in path.parents:raise InvalidMedia('Invalid storage key.')
  path.write_bytes(data);return path
 def path(self,key):
  path=(self.root/key).resolve()
  if self.root not in path.parents:raise InvalidMedia('Invalid storage key.')
  return path
 def delete(self,key):self.path(key).unlink(missing_ok=True)
storage=LocalMediaStorage(settings.media_storage_root)
def inspect_image(data:bytes):
 try:
  with Image.open(BytesIO(data)) as image:
   image.verify();fmt=image.format
  with Image.open(BytesIO(data)) as image:width,height=image.size
 except (UnidentifiedImageError,OSError) as exc:raise InvalidMedia('The uploaded file is not a valid supported image.') from exc
 if fmt not in FORMATS:raise InvalidMedia('Supported image formats are JPEG, PNG, WebP and GIF.')
 if width<1 or height<1 or width*height>100_000_000:raise InvalidMedia('Image dimensions are invalid or too large.')
 ext,mime=FORMATS[fmt];return ext,mime,width,height
class MediaService:
 async def upload(self,s,file:UploadFile,actor):
  data=await file.read(settings.media_max_bytes+1)
  if not data:raise InvalidMedia('The uploaded image is empty.')
  if len(data)>settings.media_max_bytes:raise InvalidMedia('The uploaded image exceeds the configured size limit.')
  ext,mime,w,h=inspect_image(data);key=f'{datetime.now(timezone.utc):%Y/%m}/{uuid.uuid4().hex}.{ext}';storage.save(key,data)
  item=Media(original_filename=Path(file.filename or 'image').name[:255],storage_key=key,mime_type=mime,file_size=len(data),width=w,height=h,uploaded_by=actor,updated_by=actor);s.add(item)
  try:await s.commit();await s.refresh(item)
  except Exception:storage.delete(key);raise
  return item
 async def list(self,s,status,limit,offset):
  f=[] if status=='all' else [Media.status==status];total=await s.scalar(select(func.count()).select_from(Media).where(*f)) or 0;items=(await s.scalars(select(Media).where(*f).order_by(Media.created_at.desc()).limit(limit).offset(offset))).all();return list(items),total
 async def get(self,s,i):
  x=await s.get(Media,i)
  if not x:raise PageMissing()
  return x
 async def update(self,s,i,d:MediaUpdate,a):
  x=await self.get(s,i)
  for k,v in d.model_dump(exclude_unset=True).items():setattr(x,k,v)
  x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def trash(self,s,i,a):
  x=await self.get(s,i);x.status='trash';x.deleted_at=datetime.now(timezone.utc);x.deleted_by=a;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def restore(self,s,i,a):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Only trashed media can be restored.')
  x.status='active';x.deleted_at=None;x.deleted_by=None;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def delete(self,s,i):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Move this media item to trash before permanent deletion.')
  key=x.storage_key;await s.delete(x);await s.commit();storage.delete(key)
media_service=MediaService()
