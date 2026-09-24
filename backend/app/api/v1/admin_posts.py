from typing import Literal
import uuid
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.posts import PostCreate,PostUpdate,PostResponse,PostListResponse
from ...services.page_service import PageConflict,PageMissing
from ...services.post_service import post_service
router=APIRouter(prefix='/admin/posts',tags=['admin-posts'])
def err(e):
 if isinstance(e,PageMissing):raise HTTPException(404,'Post not found.')
 raise HTTPException(409,str(e))
@router.get('',response_model=PostListResponse)
async def listing(status:Literal['all','draft','published','trash']='all',search:str|None=Query(None,max_length=120),limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('posts.view'))):
 items,total=await post_service.list(s,status,search,limit,offset);return PostListResponse(items=items,total=total,limit=limit,offset=offset)
@router.post('',response_model=PostResponse,status_code=201)
async def create(d:PostCreate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('posts.create'))):
 try:return await post_service.create(s,d,a.user_id)
 except (PageConflict,PageMissing) as e:err(e)
@router.get('/{i}',response_model=PostResponse)
async def get(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('posts.view'))):
 try:return await post_service.get(s,i)
 except (PageConflict,PageMissing) as e:err(e)
@router.patch('/{i}',response_model=PostResponse)
async def update(i:uuid.UUID,d:PostUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('posts.edit'))):
 try:return await post_service.update(s,i,d,a.user_id)
 except (PageConflict,PageMissing) as e:err(e)
@router.post('/{i}/trash',response_model=PostResponse)
async def trash(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('posts.trash'))):
 try:return await post_service.trash(s,i,a.user_id)
 except (PageConflict,PageMissing) as e:err(e)
@router.post('/{i}/restore',response_model=PostResponse)
async def restore(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('posts.restore'))):
 try:return await post_service.restore(s,i,a.user_id)
 except (PageConflict,PageMissing) as e:err(e)
@router.delete('/{i}',status_code=204)
async def delete(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('posts.delete_permanently'))):
 try:await post_service.delete(s,i);return Response(status_code=204)
 except (PageConflict,PageMissing) as e:err(e)
