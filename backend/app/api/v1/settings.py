from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.settings import SettingResponse,SettingsResponse,SettingUpdate
from ...services.settings_service import InvalidSetting,settings_service
router=APIRouter(tags=['settings'])
@router.get('/site-settings',response_model=SettingsResponse)
async def public_settings(s:AsyncSession=Depends(get_database_session)):return SettingsResponse(settings=await settings_service.all(s,True))
@router.get('/admin/settings',response_model=SettingsResponse)
async def admin_settings(s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('settings.general'))):return SettingsResponse(settings=await settings_service.all(s))
@router.put('/admin/settings/{namespace}/{key}',response_model=SettingResponse)
async def update_setting(namespace:str,key:str,data:SettingUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('settings.general'))):
 try:n,k,v,p=await settings_service.set(s,namespace,key,data.value,a.user_id);return SettingResponse(namespace=n,key=k,value=v,is_public=p)
 except InvalidSetting as exc:raise HTTPException(422,str(exc)) from exc
