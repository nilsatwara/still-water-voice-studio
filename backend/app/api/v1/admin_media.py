from typing import Literal
import uuid
from fastapi import APIRouter,Depends,File,HTTPException,Query,Response,UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.media import MediaListResponse,MediaResponse,MediaUpdate
from ...services.media_service import InvalidMedia,media_service,storage
from ...services.page_service import PageConflict,PageMissing
router=APIRouter(tags=['media'])
def fail(e):
 if isinstance(e,PageMissing):raise HTTPException(404,'Media item not found.')
 if isinstance(e,(InvalidMedia,PageConflict)):raise HTTPException(400,str(e))
 raise e
@router.get('/admin/media',response_model=MediaListResponse)
async def listing(status:Literal['all','active','trash']='all',limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('media.view'))):
 items,total=await media_service.list(s,status,limit,offset);return MediaListResponse(items=items,total=total,limit=limit,offset=offset)
@router.post('/admin/media',response_model=MediaResponse,status_code=201)
async def upload(file:UploadFile=File(...),s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('media.upload'))):
 try:return await media_service.upload(s,file,a.user_id)
 except Exception as e:fail(e)
@router.post('/admin/media/bulk',response_model=list[MediaResponse],status_code=201)
async def bulk(files:list[UploadFile]=File(...),s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('media.upload'))):
 if not 1<=len(files)<=20:raise HTTPException(400,'Upload between 1 and 20 images at a time.')
 result=[]
 try:
  for file in files:result.append(await media_service.upload(s,file,a.user_id))
  return result
 except Exception as e:fail(e)
@router.patch('/admin/media/{i}',response_model=MediaResponse)
async def update(i:uuid.UUID,d:MediaUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('media.edit'))):
 try:return await media_service.update(s,i,d,a.user_id)
 except Exception as e:fail(e)
@router.post('/admin/media/{i}/trash',response_model=MediaResponse)
async def trash(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('media.delete'))):
 try:return await media_service.trash(s,i,a.user_id)
 except Exception as e:fail(e)
@router.post('/admin/media/{i}/restore',response_model=MediaResponse)
async def restore(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('media.restore'))):
 try:return await media_service.restore(s,i,a.user_id)
 except Exception as e:fail(e)
@router.delete('/admin/media/{i}',status_code=204)
async def delete(i:uuid.UUID,s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('media.delete_permanently'))):
 try:await media_service.delete(s,i);return Response(status_code=204)
 except Exception as e:fail(e)
@router.get('/media/{i}')
async def serve(i:uuid.UUID,s:AsyncSession=Depends(get_database_session)):
 try:item=await media_service.get(s,i)
 except Exception as e:fail(e)
 if item.status!='active':raise HTTPException(404,'Media item not found.')
 path=storage.path(item.storage_key)
 if not path.is_file():raise HTTPException(404,'Media file not found.')
 return FileResponse(path,media_type=item.mime_type,headers={'X-Content-Type-Options':'nosniff','Content-Disposition':'inline'})
