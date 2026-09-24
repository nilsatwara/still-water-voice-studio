from typing import Literal
import uuid
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.taxonomy import TaxonomyCreate,TaxonomyUpdate,TaxonomyResponse,TaxonomyListResponse
from ...services.page_service import PageConflict,PageMissing
from ...services.taxonomy_service import category_service,tag_service
router=APIRouter(prefix='/admin',tags=['admin-taxonomy'])
def service(kind):return category_service if kind=='categories' else tag_service
def failure(e,kind):
 if isinstance(e,PageMissing):raise HTTPException(404,f'{kind[:-1].title()} not found.')
 raise HTTPException(409,str(e))
def permission(kind,action):return require_permission(f'{kind}.{action}')
for kind in ('categories','tags'):
 def register(kind=kind):
  @router.get(f'/{kind}',response_model=TaxonomyListResponse,name=f'list_{kind}')
  async def listing(status:Literal['all','active','trash']='all',limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0),s:AsyncSession=Depends(get_database_session),_=Depends(permission(kind,'view'))):
   items,total=await service(kind).list(s,status,limit,offset);return TaxonomyListResponse(items=items,total=total,limit=limit,offset=offset)
  @router.post(f'/{kind}',response_model=TaxonomyResponse,status_code=201,name=f'create_{kind}')
  async def create(d:TaxonomyCreate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(permission(kind,'create'))):
   try:return await service(kind).create(s,d,a.user_id)
   except (PageConflict,PageMissing) as e:failure(e,kind)
  @router.patch(f'/{kind}/{{i}}',response_model=TaxonomyResponse,name=f'update_{kind}')
  async def update(i:uuid.UUID,d:TaxonomyUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(permission(kind,'edit'))):
   try:return await service(kind).update(s,i,d,a.user_id)
   except (PageConflict,PageMissing) as e:failure(e,kind)
  @router.post(f'/{kind}/{{i}}/trash',response_model=TaxonomyResponse,name=f'trash_{kind}')
  async def trash(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(permission(kind,'trash'))):
   try:return await service(kind).trash(s,i,a.user_id)
   except (PageConflict,PageMissing) as e:failure(e,kind)
  @router.post(f'/{kind}/{{i}}/restore',response_model=TaxonomyResponse,name=f'restore_{kind}')
  async def restore(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(permission(kind,'restore'))):
   try:return await service(kind).restore(s,i,a.user_id)
   except (PageConflict,PageMissing) as e:failure(e,kind)
  @router.delete(f'/{kind}/{{i}}',status_code=204,name=f'delete_{kind}')
  async def delete(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(permission(kind,'delete_permanently'))):
   try:await service(kind).delete(s,i);return Response(status_code=204)
   except (PageConflict,PageMissing) as e:failure(e,kind)
 register()
