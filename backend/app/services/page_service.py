from datetime import datetime, timezone
import re, unicodedata, uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Page
from ..schemas.pages import PageCreate, PageUpdate
from .content_security import sanitize_content

RESERVED_SLUGS=frozenset({'admin','api','login','signup','profile','blog','category','tag','robots.txt','sitemap.xml'})

class PageConflict(Exception): pass
class PageMissing(Exception): pass

def slugify(value:str)->str:
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',value)).strip('-')[:240]

class PageService:
    async def _slug(self,session:AsyncSession,value:str,exclude:uuid.UUID|None=None)->str:
        slug=slugify(value)
        if not slug or slug in RESERVED_SLUGS: raise PageConflict('This page slug is reserved or invalid.')
        query=select(Page.id).where(Page.slug==slug)
        if exclude: query=query.where(Page.id!=exclude)
        if await session.scalar(query): raise PageConflict('A page with this slug already exists.')
        return slug
    async def list(self,session,status,limit,offset):
        filters=[] if status=='all' else [Page.status==status]
        total=await session.scalar(select(func.count()).select_from(Page).where(*filters)) or 0
        items=(await session.scalars(select(Page).where(*filters).order_by(Page.updated_at.desc()).limit(limit).offset(offset))).all()
        return list(items),total
    async def get(self,session,page_id):
        page=await session.get(Page,page_id)
        if not page: raise PageMissing()
        return page
    async def create(self,session,data:PageCreate,actor:uuid.UUID):
        values=data.model_dump(); values['slug']=await self._slug(session,data.slug or data.title); values['content']=sanitize_content(data.content)
        if data.status=='published': values['published_at']=datetime.now(timezone.utc)
        page=Page(**values,author_id=actor,created_by=actor,updated_by=actor); session.add(page); await session.commit(); await session.refresh(page); return page
    async def update(self,session,page_id,data:PageUpdate,actor:uuid.UUID):
        page=await self.get(session,page_id)
        if page.status=='trash': raise PageConflict('Restore this page before editing it.')
        values=data.model_dump(exclude_unset=True)
        if 'slug' in values: values['slug']=await self._slug(session,values['slug'],page.id)
        if 'content' in values: values['content']=sanitize_content(values['content'])
        if values.get('status')=='published' and page.published_at is None: values['published_at']=datetime.now(timezone.utc)
        for key,value in values.items(): setattr(page,key,value)
        page.updated_by=actor; await session.commit(); await session.refresh(page); return page
    async def trash(self,session,page_id,actor):
        page=await self.get(session,page_id); page.status='trash'; page.deleted_at=datetime.now(timezone.utc); page.deleted_by=actor; page.updated_by=actor; await session.commit(); await session.refresh(page); return page
    async def restore(self,session,page_id,actor):
        page=await self.get(session,page_id)
        if page.status!='trash': raise PageConflict('Only trashed pages can be restored.')
        page.status='draft'; page.deleted_at=None; page.deleted_by=None; page.updated_by=actor; await session.commit(); await session.refresh(page); return page
    async def delete(self,session,page_id):
        page=await self.get(session,page_id)
        if page.status!='trash': raise PageConflict('Move this page to trash before permanent deletion.')
        await session.delete(page); await session.commit()

page_service=PageService()
