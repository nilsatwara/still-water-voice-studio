import unittest

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from backend.app.models import Permission, Role, User, role_permissions, user_roles


class IdentityModelTests(unittest.TestCase):
    def test_normalized_identity_tables_are_registered(self):
        self.assertEqual(
            {User.__tablename__, Role.__tablename__, Permission.__tablename__, user_roles.name, role_permissions.name},
            {'users', 'roles', 'permissions', 'user_roles', 'role_permissions'},
        )

    def test_user_schema_has_uuid_unique_email_and_status_guard(self):
        ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn('UUID NOT NULL', ddl)
        self.assertIn('uq_users_email UNIQUE (email)', ddl)
        self.assertIn('ck_users_valid_status CHECK', ddl)

    def test_assignment_tables_use_composite_keys_and_cascades(self):
        self.assertEqual([column.name for column in user_roles.primary_key.columns], ['user_id', 'role_id'])
        self.assertEqual([column.name for column in role_permissions.primary_key.columns], ['role_id', 'permission_id'])
        self.assertTrue(all(foreign_key.ondelete == 'CASCADE' for foreign_key in role_permissions.foreign_keys))

    def test_relationships_use_selectin_loading(self):
        self.assertEqual(User.roles.property.lazy, 'selectin')
        self.assertEqual(Role.permissions.property.lazy, 'selectin')


if __name__ == '__main__':
    unittest.main()
