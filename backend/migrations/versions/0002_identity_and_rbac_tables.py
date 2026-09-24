"""Create users, roles, permissions, and assignment tables.

Revision ID: 0002
Revises: 0001
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'permissions',
        sa.Column('code', sa.String(length=120), nullable=False),
        sa.Column('group', sa.String(length=60), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
        sa.UniqueConstraint('code', name=op.f('uq_permissions_code')),
    )
    op.create_index(op.f('ix_permissions_group'), 'permissions', ['group'], unique=False)

    op.create_table(
        'roles',
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active', 'disabled')", name=op.f('ck_roles_valid_status')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('name', name=op.f('uq_roles_name')),
    )
    op.create_index('ix_roles_status', 'roles', ['status'], unique=False)

    op.create_table(
        'users',
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'suspended', 'disabled')",
            name=op.f('ck_users_valid_status'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )
    op.create_index('ix_users_created_at', 'users', ['created_at'], unique=False)
    op.create_index('ix_users_status', 'users', ['status'], unique=False)

    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('permission_id', sa.Uuid(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_role_permissions_role_id_roles'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions')),
    )
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'], unique=False)

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name=op.f('fk_user_roles_assigned_by_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles')),
    )
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index('ix_role_permissions_permission_id', table_name='role_permissions')
    op.drop_table('role_permissions')
    op.drop_index('ix_users_status', table_name='users')
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_roles_status', table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_permissions_group'), table_name='permissions')
    op.drop_table('permissions')
