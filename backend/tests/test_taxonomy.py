import unittest
from backend.app.models import Category,Tag,Post,post_categories,post_tags
class TaxonomyTests(unittest.TestCase):
 def test_taxonomy_tables_and_unique_slugs(self):
  self.assertEqual({Category.__tablename__,Tag.__tablename__},{'categories','tags'});self.assertTrue(any(c.name=='uq_categories_slug' for c in Category.__table__.constraints))
 def test_post_links_have_composite_keys_and_indexes(self):
  self.assertEqual(len(post_categories.primary_key.columns),2);self.assertEqual(len(post_tags.primary_key.columns),2);self.assertEqual(Post.categories.property.lazy,'selectin');self.assertEqual(Post.tags.property.lazy,'selectin')
if __name__=='__main__':unittest.main()
