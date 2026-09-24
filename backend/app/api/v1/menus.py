import uuid
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.menus import *
from ...services.menu_service import menu_service
from ...services.page_service import PageConflict,PageMissing
router=APIRouter(tags=['menus'])
def fail(e):
 if isinstance(e,PageMissing):raise HTTPException(404,'Menu or item not found.')
 raise HTTPException(409,str(e))
@router.get('/menus/{location}',response_model=list[MenuResponse])
async def public_menus(location:str,s:AsyncSession=Depends(get_database_session)):
 if location not in {'header','footer','custom'}:raise HTTPException(404,'Menu location not found.')
 return await menu_service.list(s,True,location)
@router.get('/admin/menus',response_model=list[MenuResponse])
async def menus(s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('menus.view'))):return await menu_service.list(s)
@router.post('/admin/menus',response_model=MenuResponse,status_code=201)
async def create(d:MenuCreate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('menus.create'))):
 try:return await menu_service.create(s,d,a.user_id)
 except (PageConflict,PageMissing) as e:fail(e)
@router.patch('/admin/menus/{i}',response_model=MenuResponse)
async def update(i:uuid.UUID,d:MenuUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('menus.edit'))):
 try:return await menu_service.update(s,i,d,a.user_id)
 except (PageConflict,PageMissing) as e:fail(e)
@router.post('/admin/menus/{i}/items',response_model=MenuItemResponse,status_code=201)
async def add_item(i:uuid.UUID,d:ItemWrite,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('menus.edit'))):
 try:return await menu_service.add_item(s,i,d,a.user_id)
 except (PageConflict,PageMissing) as e:fail(e)
@router.patch('/admin/menus/{i}/items/{item}',response_model=MenuItemResponse)
async def update_item(i:uuid.UUID,item:uuid.UUID,d:ItemUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('menus.edit'))):
 try:return await menu_service.update_item(s,i,item,d,a.user_id)
 except (PageConflict,PageMissing) as e:fail(e)
@router.put('/admin/menus/{i}/order',response_model=MenuResponse)
async def reorder(i:uuid.UUID,d:ReorderRequest,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('menus.edit'))):
 try:return await menu_service.reorder(s,i,d,a.user_id)
 except (PageConflict,PageMissing) as e:fail(e)
@router.delete('/admin/menus/{i}/items/{item}',status_code=204)
async def delete_item(i:uuid.UUID,item:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('menus.edit'))):
 try:await menu_service.delete_item(s,i,item);return Response(status_code=204)
 except (PageConflict,PageMissing) as e:fail(e)
@router.delete('/admin/menus/{i}',status_code=204)
async def delete_menu(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('menus.delete'))):
 try:await menu_service.delete(s,i);return Response(status_code=204)
 except (PageConflict,PageMissing) as e:fail(e)
