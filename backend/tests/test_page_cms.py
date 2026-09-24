import unittest
from backend.app.models import Page
from backend.app.services.content_security import sanitize_content
from backend.app.services.page_service import RESERVED_SLUGS, slugify

class PageCMSTests(unittest.TestCase):
    def test_page_schema_has_lifecycle_and_audit_fields(self):
        columns=set(Page.__table__.columns.keys())
        self.assertTrue({'slug','status','published_at','deleted_at','created_by','updated_by','deleted_by'} <= columns)
    def test_slug_generation_and_reserved_routes(self):
        self.assertEqual(slugify('  Morning Prayer & Hope  '),'morning-prayer-hope')
        self.assertIn('admin',RESERVED_SLUGS); self.assertIn('api',RESERVED_SLUGS)
    def test_html_sanitizer_removes_xss(self):
        dirty='<p onclick="bad()">Hello<script>alert(1)</script><a href="javascript:bad()">link</a></p>'
        clean=sanitize_content(dirty)
        self.assertNotIn('onclick',clean); self.assertNotIn('script',clean); self.assertNotIn('javascript:',clean); self.assertIn('<p>Hello',clean)

if __name__=='__main__': unittest.main()
