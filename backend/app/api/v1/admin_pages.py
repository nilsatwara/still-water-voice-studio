from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.pages import PageCreate, PageListResponse, PageResponse, PageUpdate
from ...services.page_service import PageConflict, PageMissing, page_service

router=APIRouter(prefix='/admin/pages',tags=['admin-pages'])

def safe_error(exc:Exception):
    if isinstance(exc,PageMissing): raise HTTPException(404,'Page not found.')
    if isinstance(exc,PageConflict): raise HTTPException(409,str(exc))
    raise exc

@router.get('',response_model=PageListResponse)
async def pages(status:Literal['all','draft','published','trash']='all',limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),session:AsyncSession=Depends(get_database_session),_:Principal=Depends(require_permission('pages.view'))):
    items,total=await page_service.list(session,status,limit,offset); return PageListResponse(items=items,total=total,limit=limit,offset=offset)

@router.post('',response_model=PageResponse,status_code=201)
async def create_page(data:PageCreate,session:AsyncSession=Depends(get_database_session),actor:Principal=Depends(require_permission('pages.create'))):
    try:return await page_service.create(session,data,actor.user_id)
    except (PageMissing,PageConflict) as exc:safe_error(exc)

@router.get('/{page_id}',response_model=PageResponse)
async def get_page(page_id:uuid.UUID,session:AsyncSession=Depends(get_database_session),_:Principal=Depends(require_permission('pages.view'))):
    try:return await page_service.get(session,page_id)
    except (PageMissing,PageConflict) as exc:safe_error(exc)

@router.patch('/{page_id}',response_model=PageResponse)
async def update_page(page_id:uuid.UUID,data:PageUpdate,session:AsyncSession=Depends(get_database_session),actor:Principal=Depends(require_permission('pages.edit'))):
    try:return await page_service.update(session,page_id,data,actor.user_id)
    except (PageMissing,PageConflict) as exc:safe_error(exc)

@router.post('/{page_id}/trash',response_model=PageResponse)
async def trash_page(page_id:uuid.UUID,session:AsyncSession=Depends(get_database_session),actor:Principal=Depends(require_permission('pages.trash'))):
    try:return await page_service.trash(session,page_id,actor.user_id)
    except (PageMissing,PageConflict) as exc:safe_error(exc)

@router.post('/{page_id}/restore',response_model=PageResponse)
async def restore_page(page_id:uuid.UUID,session:AsyncSession=Depends(get_database_session),actor:Principal=Depends(require_permission('pages.restore'))):
    try:return await page_service.restore(session,page_id,actor.user_id)
    except (PageMissing,PageConflict) as exc:safe_error(exc)

@router.delete('/{page_id}',status_code=204)
async def delete_page(page_id:uuid.UUID,session:AsyncSession=Depends(get_database_session),_:Principal=Depends(require_permission('pages.delete_permanently'))):
    try:await page_service.delete(session,page_id); return Response(status_code=204)
    except (PageMissing,PageConflict) as exc:safe_error(exc)
