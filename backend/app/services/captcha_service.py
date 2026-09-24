import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from ..core.config import settings
from ..models import CaptchaSetting
from ..schemas.captcha import CaptchaPublic,CaptchaUpdate
class CaptchaUnavailable(RuntimeError):pass
class CaptchaService:
 async def get(self,s):return await s.scalar(select(CaptchaSetting).where(CaptchaSetting.provider=='turnstile'))
 def public(self,row):
  if not row:return CaptchaPublic(enabled=False,site_key='',test_mode=True,surfaces={},tts_policy='never')
  return CaptchaPublic(enabled=row.enabled,site_key=row.site_key,test_mode=row.test_mode,surfaces={'signup':row.on_signup,'signin':row.on_signin,'forgot_password':row.on_forgot_password,'contact':row.on_contact,'api_key':row.on_api_key},tts_policy=row.tts_policy)
 async def update(self,s,d:CaptchaUpdate,actor):
  if d.enabled and not d.site_key:raise ValueError('Site key is required when CAPTCHA is enabled.')
  values=d.model_dump()|{'provider':'turnstile','updated_by':actor};stmt=insert(CaptchaSetting).values(**values).on_conflict_do_update(index_elements=['provider'],set_=values);await s.execute(stmt);await s.commit();return await self.get(s)
 async def verify(self,token,remote_ip=None):
  secret=settings.turnstile_secret_key
  if not secret:raise CaptchaUnavailable('CAPTCHA verification is not configured.')
  payload={'secret':secret,'response':token,'idempotency_key':str(uuid.uuid4())}
  if remote_ip:payload['remoteip']=remote_ip
  try:
   async with httpx.AsyncClient(timeout=10) as client:response=await client.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',data=payload);response.raise_for_status();data=response.json()
  except (httpx.HTTPError,ValueError) as exc:raise CaptchaUnavailable('CAPTCHA verification is temporarily unavailable.') from exc
  return bool(data.get('success'))
captcha_service=CaptchaService()
