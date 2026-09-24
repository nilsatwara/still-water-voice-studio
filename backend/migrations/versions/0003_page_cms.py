"""Create page CMS table. Revision ID: 0003; Revises: 0002."""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0003'; down_revision='0002'; branch_labels=None; depends_on=None

def upgrade()->None:
    op.create_table('pages',
      sa.Column('title',sa.String(240),nullable=False),sa.Column('slug',sa.String(240),nullable=False),
      sa.Column('content',sa.Text(),server_default='',nullable=False),sa.Column('excerpt',sa.Text()),
      sa.Column('featured_image_id',sa.Uuid()),sa.Column('status',sa.String(20),server_default='draft',nullable=False),
      sa.Column('author_id',sa.Uuid(),nullable=False),sa.Column('template',sa.String(80),server_default='default',nullable=False),
      sa.Column('seo_title',sa.String(240)),sa.Column('seo_description',sa.String(500)),
      sa.Column('seo_keywords',postgresql.JSONB(),server_default='[]',nullable=False),sa.Column('canonical_url',sa.String(2048)),
      sa.Column('og_title',sa.String(240)),sa.Column('og_description',sa.String(500)),sa.Column('og_image_id',sa.Uuid()),
      sa.Column('robots_index',sa.Boolean(),server_default=sa.text('true'),nullable=False),sa.Column('robots_follow',sa.Boolean(),server_default=sa.text('true'),nullable=False),
      sa.Column('published_at',sa.DateTime(timezone=True)),sa.Column('created_by',sa.Uuid(),nullable=False),sa.Column('updated_by',sa.Uuid(),nullable=False),
      sa.Column('deleted_at',sa.DateTime(timezone=True)),sa.Column('deleted_by',sa.Uuid()),sa.Column('id',sa.Uuid(),nullable=False),
      sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),
      sa.CheckConstraint("status IN ('draft', 'published', 'trash')",name=op.f('ck_pages_valid_status')),
      sa.ForeignKeyConstraint(['author_id'],['users.id'],ondelete='RESTRICT',name=op.f('fk_pages_author_id_users')),
      sa.ForeignKeyConstraint(['created_by'],['users.id'],ondelete='RESTRICT',name=op.f('fk_pages_created_by_users')),
      sa.ForeignKeyConstraint(['updated_by'],['users.id'],ondelete='RESTRICT',name=op.f('fk_pages_updated_by_users')),
      sa.ForeignKeyConstraint(['deleted_by'],['users.id'],ondelete='SET NULL',name=op.f('fk_pages_deleted_by_users')),
      sa.PrimaryKeyConstraint('id',name=op.f('pk_pages')),sa.UniqueConstraint('slug',name=op.f('uq_pages_slug')))
    for column in ('status','created_at','published_at'):op.create_index(f'ix_pages_{column}','pages',[column])

def downgrade()->None:
    for column in ('published_at','created_at','status'):op.drop_index(f'ix_pages_{column}',table_name='pages')
    op.drop_table('pages')
