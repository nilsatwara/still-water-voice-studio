import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ..models import Menu,MenuItem
from ..schemas.menus import ItemUpdate,ItemWrite,MenuCreate,MenuUpdate,ReorderRequest
from .page_service import PageConflict,PageMissing,slugify
class MenuService:
 async def list(self,s,public=False,location=None):
  q=select(Menu).options(selectinload(Menu.items)).order_by(Menu.name)
  if public:q=q.where(Menu.status=='active')
  if location:q=q.where(Menu.location==location)
  menus=list((await s.scalars(q)).unique().all())
  if public:
   for menu in menus:menu.items=[item for item in menu.items if item.enabled]
  return menus
 async def get(self,s,i):
  x=await s.scalar(select(Menu).where(Menu.id==i).options(selectinload(Menu.items)))
  if not x:raise PageMissing()
  return x
 async def _slug(self,s,value,exclude=None):
  value=slugify(value)
  if not value:raise PageConflict('Menu slug is invalid.')
  q=select(Menu.id).where(Menu.slug==value)
  if exclude:q=q.where(Menu.id!=exclude)
  if await s.scalar(q):raise PageConflict('Menu slug already exists.')
  return value
 async def create(self,s,d:MenuCreate,a):
  x=Menu(**d.model_dump(exclude={'slug'}),slug=await self._slug(s,d.slug or d.name),created_by=a,updated_by=a);s.add(x);await s.commit();return await self.get(s,x.id)
 async def update(self,s,i,d:MenuUpdate,a):
  x=await self.get(s,i);v=d.model_dump(exclude_unset=True)
  if 'slug'in v:v['slug']=await self._slug(s,v['slug'],x.id)
  for k,val in v.items():setattr(x,k,val)
  x.updated_by=a;await s.commit();return await self.get(s,i)
 async def add_item(self,s,menu_id,d:ItemWrite,a):
  await self.get(s,menu_id)
  if d.parent_id:
   parent=await s.get(MenuItem,d.parent_id)
   if not parent or parent.menu_id!=menu_id:raise PageConflict('Parent item must belong to the same menu.')
  x=MenuItem(menu_id=menu_id,**d.model_dump(),created_by=a,updated_by=a);s.add(x);await s.commit();await s.refresh(x);return x
 async def update_item(self,s,menu_id,item_id,d:ItemUpdate,a):
  x=await s.get(MenuItem,item_id)
  if not x or x.menu_id!=menu_id:raise PageMissing()
  v=d.model_dump(exclude_unset=True);url=v.get('url',x.url);page=v.get('page_id',x.page_id)
  if bool(url)==bool(page):raise PageConflict('Provide either a URL or an internal page.')
  if v.get('parent_id')==x.id:raise PageConflict('A menu item cannot be its own parent.')
  for k,val in v.items():setattr(x,k,val)
  x.updated_by=a;await s.commit();await s.refresh(x);return x
 async def reorder(self,s,menu_id,d:ReorderRequest,a):
  if len({item.id for item in d.items})!=len(d.items):raise PageConflict('Each menu item may appear only once.')
  rows=(await s.scalars(select(MenuItem).where(MenuItem.menu_id==menu_id))).all();by_id={x.id:x for x in rows}
  if any(i.id not in by_id or (i.parent_id and i.parent_id not in by_id) for i in d.items):raise PageConflict('All reordered items and parents must belong to this menu.')
  parents={i.id:i.parent_id for i in d.items}
  for start in parents:
   seen=set();current=start
   while current in parents and parents[current]:
    current=parents[current]
    if current in seen or current==start:raise PageConflict('Menu hierarchy cannot contain a cycle.')
    seen.add(current)
  for item in d.items:by_id[item.id].parent_id=item.parent_id;by_id[item.id].position=item.position;by_id[item.id].updated_by=a
  await s.commit();return await self.get(s,menu_id)
 async def delete_item(self,s,menu_id,item_id):
  x=await s.get(MenuItem,item_id)
  if not x or x.menu_id!=menu_id:raise PageMissing()
  await s.delete(x);await s.commit()
 async def delete(self,s,i):x=await self.get(s,i);await s.delete(x);await s.commit()
menu_service=MenuService()
