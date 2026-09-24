from datetime import datetime,timezone
from sqlalchemy import func,select
from ..models import Category,Tag
from ..schemas.taxonomy import TaxonomyCreate,TaxonomyUpdate
from .page_service import PageConflict,PageMissing,slugify
class TaxonomyService:
 def __init__(self,model):self.model=model
 async def list(self,s,status,limit,offset):
  f=[] if status=='all' else [self.model.status==status];total=await s.scalar(select(func.count()).select_from(self.model).where(*f)) or 0;items=(await s.scalars(select(self.model).where(*f).order_by(self.model.name).limit(limit).offset(offset))).all();return list(items),total
 async def get(self,s,i):
  x=await s.get(self.model,i)
  if not x:raise PageMissing()
  return x
 async def _slug(self,s,value,exclude=None):
  value=slugify(value)
  if not value:raise PageConflict('Slug is invalid.')
  q=select(self.model.id).where(self.model.slug==value)
  if exclude:q=q.where(self.model.id!=exclude)
  if await s.scalar(q):raise PageConflict('This slug already exists.')
  return value
 async def create(self,s,d:TaxonomyCreate,a):
  x=self.model(**d.model_dump(exclude={'slug'}),slug=await self._slug(s,d.slug or d.name),created_by=a,updated_by=a);s.add(x);await s.commit();await s.refresh(x);return x
 async def update(self,s,i,d:TaxonomyUpdate,a):
  x=await self.get(s,i)
  if x.status=='trash':raise PageConflict('Restore this item before editing it.')
  v=d.model_dump(exclude_unset=True)
  if 'slug'in v:v['slug']=await self._slug(s,v['slug'],x.id)
  for k,val in v.items():setattr(x,k,val)
  x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def trash(self,s,i,a):
  x=await self.get(s,i);x.status='trash';x.deleted_at=datetime.now(timezone.utc);x.deleted_by=a;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def restore(self,s,i,a):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Only trashed items can be restored.')
  x.status='active';x.deleted_at=None;x.deleted_by=None;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def delete(self,s,i):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Move this item to trash before permanent deletion.')
  await s.delete(x);await s.commit()
category_service=TaxonomyService(Category);tag_service=TaxonomyService(Tag)
