import unittest,uuid
from pydantic import ValidationError
from backend.app.models import Menu,MenuItem
from backend.app.schemas.menus import ItemWrite,ReorderItem,ReorderRequest
class MenuTests(unittest.TestCase):
 def test_models_support_hierarchy_and_order(self):self.assertIn('parent_id',MenuItem.__table__.columns);self.assertIn('position',MenuItem.__table__.columns);self.assertEqual(Menu.items.property.lazy,'selectin')
 def test_item_requires_exactly_one_safe_destination(self):
  with self.assertRaises(ValidationError):ItemWrite(label='Bad')
  with self.assertRaises(ValidationError):ItemWrite(label='Bad',url='javascript:bad()')
  self.assertEqual(ItemWrite(label='Home',url='/').url,'/')
 def test_reorder_rejects_empty_payload(self):
  with self.assertRaises(ValidationError):ReorderRequest(items=[])
if __name__=='__main__':unittest.main()
