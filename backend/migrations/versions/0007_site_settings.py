"""Create controlled site settings. Revision 0007."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0007';down_revision='0006';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('site_settings',sa.Column('namespace',sa.String(50),nullable=False),sa.Column('key',sa.String(100),nullable=False),sa.Column('value',postgresql.JSONB(),nullable=False),sa.Column('is_public',sa.Boolean(),server_default=sa.text('false'),nullable=False),sa.Column('updated_by',sa.Uuid(),nullable=False),sa.Column('id',sa.Uuid(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.ForeignKeyConstraint(['updated_by'],['users.id'],ondelete='RESTRICT',name=op.f('fk_site_settings_updated_by_users')),sa.PrimaryKeyConstraint('id',name=op.f('pk_site_settings')),sa.UniqueConstraint('namespace','key',name='uq_site_settings_namespace_key'))
 op.create_index('ix_site_settings_namespace','site_settings',['namespace']);op.create_index('ix_site_settings_is_public','site_settings',['is_public'])
def downgrade():
 op.drop_index('ix_site_settings_is_public',table_name='site_settings');op.drop_index('ix_site_settings_namespace',table_name='site_settings');op.drop_table('site_settings')
