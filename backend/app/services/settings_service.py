from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
import uuid
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import SiteSetting

@dataclass(frozen=True)
class Definition:
 type:type;default:Any;public:bool=True;maximum:int=500
DEFINITIONS={
 'general':{'site_name':Definition(str,'Stillwater',maximum=120),'tagline':Definition(str,'Words worth hearing.',maximum=240),'site_url':Definition(str,'',maximum=2048),'admin_email':Definition(str,'',False,320),'timezone':Definition(str,'UTC',False,80),'date_format':Definition(str,'MMM d, yyyy',maximum=40)},
 'branding':{'logo_media_id':Definition(str,''),'dark_logo_media_id':Definition(str,''),'favicon_media_id':Definition(str,''),'default_social_image_media_id':Definition(str,'')},
 'homepage':{'hero_title':Definition(str,'Give every word a voice worth hearing.',maximum=240),'hero_subtitle':Definition(str,'Natural voice creation with Edge TTS and Kokoro.',maximum=500),'primary_cta_label':Definition(str,'Explore voices',maximum=80),'primary_cta_url':Definition(str,'/#voices',maximum=2048),'secondary_cta_label':Definition(str,'',maximum=80),'secondary_cta_url':Definition(str,'',maximum=2048)},
}
class InvalidSetting(ValueError):pass
def validate_setting(namespace,key,value):
 try:d=DEFINITIONS[namespace][key]
 except KeyError as exc:raise InvalidSetting('This setting is not supported.') from exc
 if not isinstance(value,d.type):raise InvalidSetting(f'{namespace}.{key} must be {d.type.__name__}.')
 if isinstance(value,str) and len(value)>d.maximum:raise InvalidSetting(f'{namespace}.{key} is too long.')
 if key.endswith('_url') or key=='site_url':
  if value and not (value.startswith('/') or urlparse(value).scheme in {'http','https'}):raise InvalidSetting('URL must be relative or use HTTP/HTTPS.')
 if key=='admin_email' and value and ('@' not in value or value.startswith('@') or value.endswith('@')):raise InvalidSetting('Admin email is invalid.')
 if key=='timezone':
  try:ZoneInfo(value)
  except ZoneInfoNotFoundError as exc:raise InvalidSetting('Timezone is invalid.') from exc
 return d
class SettingsService:
 async def set(self,s:AsyncSession,namespace,key,value,actor:uuid.UUID):
  d=validate_setting(namespace,key,value);statement=insert(SiteSetting).values(namespace=namespace,key=key,value=value,is_public=d.public,updated_by=actor).on_conflict_do_update(constraint='uq_site_settings_namespace_key',set_={'value':value,'is_public':d.public,'updated_by':actor});await s.execute(statement);await s.commit();return namespace,key,value,d.public
 async def all(self,s,public_only=False):
  q=select(SiteSetting)
  if public_only:q=q.where(SiteSetting.is_public.is_(True))
  rows=(await s.scalars(q.order_by(SiteSetting.namespace,SiteSetting.key))).all();result={}
  for namespace,items in DEFINITIONS.items():
   for key,d in items.items():
    if not public_only or d.public:result.setdefault(namespace,{})[key]=d.default
  for row in rows:result.setdefault(row.namespace,{})[row.key]=row.value
  return result
settings_service=SettingsService()
