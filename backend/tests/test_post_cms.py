import unittest
from backend.app.models import Post
from backend.app.services.post_service import slugify
class PostCMSTests(unittest.TestCase):
 def test_post_schema_has_publish_trash_and_seo_fields(self):
  self.assertTrue({'slug','status','published_at','deleted_at','seo_title','og_title','author_id'}<=set(Post.__table__.columns.keys()))
 def test_post_slug_generation(self):self.assertEqual(slugify('News & Morning Updates'),'news-morning-updates')
if __name__=='__main__':unittest.main()
