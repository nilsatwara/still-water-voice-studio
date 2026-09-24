from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import require_permission
from ...core.config import settings
from ...core.database import get_database_session
from ...core.security import Principal
from ...schemas.captcha import CaptchaAdmin,CaptchaPublic,CaptchaUpdate,TurnstileToken,VerificationResult
from ...services.captcha_service import CaptchaUnavailable,captcha_service
router=APIRouter(tags=['captcha'])
@router.get('/captcha',response_model=CaptchaPublic)
async def public(s:AsyncSession=Depends(get_database_session)):return captcha_service.public(await captcha_service.get(s))
@router.get('/admin/settings/captcha',response_model=CaptchaAdmin)
async def admin(s:AsyncSession=Depends(get_database_session),_=Depends(require_permission('settings.captcha'))):
 row=await captcha_service.get(s);base=CaptchaUpdate() if not row else CaptchaUpdate.model_validate(row,from_attributes=True);return CaptchaAdmin(**base.model_dump(),secret_configured=bool(settings.turnstile_secret_key))
@router.put('/admin/settings/captcha',response_model=CaptchaAdmin)
async def update(d:CaptchaUpdate,s:AsyncSession=Depends(get_database_session),a:Principal=Depends(require_permission('settings.captcha'))):
 try:row=await captcha_service.update(s,d,a.user_id);return CaptchaAdmin(**CaptchaUpdate.model_validate(row,from_attributes=True).model_dump(),secret_configured=bool(settings.turnstile_secret_key))
 except ValueError as exc:raise HTTPException(422,str(exc)) from exc
@router.post('/captcha/verify',response_model=VerificationResult)
async def verify(d:TurnstileToken):
 try:return VerificationResult(success=await captcha_service.verify(d.token,d.remote_ip))
 except CaptchaUnavailable as exc:raise HTTPException(503,str(exc)) from exc
