import unittest
from backend.app.models import SiteSetting
from backend.app.services.settings_service import DEFINITIONS,InvalidSetting,validate_setting
class SiteSettingsTests(unittest.TestCase):
 def test_known_settings_are_typed(self):self.assertIs(validate_setting('general','site_name','Stillwater'),DEFINITIONS['general']['site_name'])
 def test_unknown_settings_cannot_be_stored(self):
  with self.assertRaises(InvalidSetting):validate_setting('general','database_password','secret')
 def test_private_settings_are_not_public(self):self.assertFalse(DEFINITIONS['general']['admin_email'].public);self.assertFalse(DEFINITIONS['general']['timezone'].public)
 def test_settings_have_unique_namespace_key(self):self.assertTrue(any(c.name=='uq_site_settings_namespace_key' for c in SiteSetting.__table__.constraints))
if __name__=='__main__':unittest.main()
