from datetime import datetime,timezone
import uuid
from sqlalchemy import func,or_,select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Post
from ..schemas.posts import PostCreate,PostUpdate
from .content_security import sanitize_content
from .page_service import PageConflict,PageMissing,slugify

class PostService:
 async def _slug(self,s,v,exclude=None):
  slug=slugify(v)
  if not slug:raise PageConflict('This post slug is invalid.')
  q=select(Post.id).where(Post.slug==slug)
  if exclude:q=q.where(Post.id!=exclude)
  if await s.scalar(q):raise PageConflict('A post with this slug already exists.')
  return slug
 async def list(self,s,status,search,limit,offset):
  f=[] if status=='all' else [Post.status==status]
  if search:f.append(or_(Post.title.ilike(f'%{search}%'),Post.slug.ilike(f'%{search}%')))
  total=await s.scalar(select(func.count()).select_from(Post).where(*f)) or 0
  return list((await s.scalars(select(Post).where(*f).order_by(Post.updated_at.desc()).limit(limit).offset(offset))).all()),total
 async def get(self,s,i):
  x=await s.get(Post,i)
  if not x:raise PageMissing()
  return x
 async def create(self,s,d:PostCreate,a:uuid.UUID):
  v=d.model_dump();v['slug']=await self._slug(s,d.slug or d.title);v['content']=sanitize_content(d.content)
  if d.status=='published':v['published_at']=datetime.now(timezone.utc)
  x=Post(**v,author_id=a,created_by=a,updated_by=a);s.add(x);await s.commit();await s.refresh(x);return x
 async def update(self,s,i,d:PostUpdate,a):
  x=await self.get(s,i)
  if x.status=='trash':raise PageConflict('Restore this post before editing it.')
  v=d.model_dump(exclude_unset=True)
  if 'slug'in v:v['slug']=await self._slug(s,v['slug'],x.id)
  if 'content'in v:v['content']=sanitize_content(v['content'])
  if v.get('status')=='published' and x.published_at is None:v['published_at']=datetime.now(timezone.utc)
  for k,val in v.items():setattr(x,k,val)
  x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def trash(self,s,i,a):
  x=await self.get(s,i);x.status='trash';x.deleted_at=datetime.now(timezone.utc);x.deleted_by=a;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def restore(self,s,i,a):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Only trashed posts can be restored.')
  x.status='draft';x.deleted_at=None;x.deleted_by=None;x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def delete(self,s,i):
  x=await self.get(s,i)
  if x.status!='trash':raise PageConflict('Move this post to trash before permanent deletion.')
  await s.delete(x);await s.commit()
post_service=PostService()
