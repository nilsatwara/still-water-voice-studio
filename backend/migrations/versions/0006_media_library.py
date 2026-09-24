"""Create media library. Revision 0006."""
from alembic import op
import sqlalchemy as sa
revision='0006';down_revision='0005';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('media',sa.Column('original_filename',sa.String(255),nullable=False),sa.Column('storage_key',sa.String(255),nullable=False),sa.Column('mime_type',sa.String(80),nullable=False),sa.Column('file_size',sa.Integer(),nullable=False),sa.Column('width',sa.Integer(),nullable=False),sa.Column('height',sa.Integer(),nullable=False),sa.Column('alt_text',sa.String(500)),sa.Column('caption',sa.Text()),sa.Column('status',sa.String(20),server_default='active',nullable=False),sa.Column('uploaded_by',sa.Uuid(),nullable=False),sa.Column('updated_by',sa.Uuid(),nullable=False),sa.Column('deleted_at',sa.DateTime(timezone=True)),sa.Column('deleted_by',sa.Uuid()),sa.Column('id',sa.Uuid(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.CheckConstraint("status IN ('active', 'trash')",name=op.f('ck_media_valid_status')),sa.ForeignKeyConstraint(['uploaded_by'],['users.id'],ondelete='RESTRICT',name=op.f('fk_media_uploaded_by_users')),sa.ForeignKeyConstraint(['updated_by'],['users.id'],ondelete='RESTRICT',name=op.f('fk_media_updated_by_users')),sa.ForeignKeyConstraint(['deleted_by'],['users.id'],ondelete='SET NULL',name=op.f('fk_media_deleted_by_users')),sa.PrimaryKeyConstraint('id',name=op.f('pk_media')),sa.UniqueConstraint('storage_key',name=op.f('uq_media_storage_key')))
 for c in ('status','created_at','uploaded_by'):op.create_index(f'ix_media_{c}','media',[c])
def downgrade():
 for c in ('uploaded_by','created_at','status'):op.drop_index(f'ix_media_{c}',table_name='media')
 op.drop_table('media')
