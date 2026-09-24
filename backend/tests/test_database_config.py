import os
import unittest
from unittest.mock import patch

from backend.app.core.config import Settings
from backend.app.core.database import Database


class PostgreSQLConfigurationTests(unittest.TestCase):
    def settings(self, **environment: str) -> Settings:
        with patch.dict(os.environ, environment, clear=True):
            return Settings.from_env()

    def test_database_is_optional_during_migration(self):
        config = self.settings()
        self.assertIsNone(config.database_url)
        self.assertFalse(Database(config).configured)

    def test_postgresql_url_is_normalized_for_async_psycopg(self):
        config = self.settings(DATABASE_URL='postgresql://user:secret@db.example/studio')
        self.assertEqual(config.database_url, 'postgresql+psycopg://user:secret@db.example/studio')
        self.assertTrue(Database(config).configured)

    def test_database_credentials_are_hidden_from_settings_repr(self):
        config = self.settings(DATABASE_URL='postgresql://user:secret@localhost/studio')
        self.assertNotIn('secret', repr(config))
        self.assertNotIn('DATABASE_URL', repr(config))

    def test_non_postgresql_url_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'must use PostgreSQL'):
            self.settings(DATABASE_URL='mysql://user:secret@localhost/studio')

    def test_pool_configuration_is_environment_driven(self):
        config = self.settings(
            DB_POOL_SIZE='8', DB_MAX_OVERFLOW='12',
            DB_POOL_TIMEOUT='20', DB_POOL_RECYCLE='900',
        )
        self.assertEqual(
            (config.db_pool_size, config.db_max_overflow, config.db_pool_timeout, config.db_pool_recycle),
            (8, 12, 20, 900),
        )

    def test_invalid_pool_configuration_fails_fast(self):
        with self.assertRaisesRegex(ValueError, 'DB_POOL_SIZE'):
            self.settings(DB_POOL_SIZE='0')


if __name__ == '__main__':
    unittest.main()
