import unittest
from backend.app.models import CaptchaSetting
from backend.app.schemas.captcha import CaptchaAdmin,CaptchaPublic
from backend.app.services.captcha_service import captcha_service
class CaptchaTests(unittest.TestCase):
 def test_secret_is_absent_from_database_and_public_schema(self):self.assertNotIn('secret',CaptchaSetting.__table__.columns);self.assertNotIn('secret_key',CaptchaPublic.model_fields);self.assertNotIn('secret_key',CaptchaAdmin.model_fields)
 def test_default_public_config_is_disabled(self):
  value=captcha_service.public(None);self.assertFalse(value.enabled);self.assertEqual(value.tts_policy,'never')
if __name__=='__main__':unittest.main()
