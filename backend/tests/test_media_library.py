from io import BytesIO
import unittest
from PIL import Image
from backend.app.models import Media
from backend.app.services.media_service import InvalidMedia,inspect_image
class MediaLibraryTests(unittest.TestCase):
 def test_validates_signature_and_reads_dimensions(self):
  output=BytesIO();Image.new('RGB',(32,18),'red').save(output,format='PNG');ext,mime,w,h=inspect_image(output.getvalue());self.assertEqual((ext,mime,w,h),('png','image/png',32,18))
 def test_rejects_fake_image_extension_content(self):
  with self.assertRaises(InvalidMedia):inspect_image(b'not an image')
 def test_media_schema_keeps_binary_out_of_postgresql(self):
  columns=set(Media.__table__.columns.keys());self.assertTrue({'storage_key','mime_type','file_size','width','height','alt_text','caption'}<=columns);self.assertNotIn('data',columns)
if __name__=='__main__':unittest.main()
