import os
from pathlib import Path
import subprocess
import unittest

from alembic.config import Config
from alembic.script import ScriptDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG = PROJECT_ROOT / 'backend' / 'alembic.ini'


class MigrationFoundationTests(unittest.TestCase):
    def test_migration_history_is_linear_from_baseline(self):
        config = Config(str(ALEMBIC_CONFIG))
        scripts = ScriptDirectory.from_config(config)
        self.assertEqual(scripts.get_heads(), ['0009'])
        baseline = scripts.get_revision('0001')
        self.assertIsNotNone(baseline)
        self.assertIsNone(baseline.down_revision)
        self.assertEqual(scripts.get_revision('0002').down_revision, '0001')
        self.assertEqual(scripts.get_revision('0003').down_revision, '0002')
        self.assertEqual(scripts.get_revision('0004').down_revision, '0003')
        self.assertEqual(scripts.get_revision('0005').down_revision, '0004')
        self.assertEqual(scripts.get_revision('0006').down_revision, '0005')
        self.assertEqual(scripts.get_revision('0007').down_revision, '0006')
        self.assertEqual(scripts.get_revision('0008').down_revision, '0007')
        self.assertEqual(scripts.get_revision('0009').down_revision, '0008')

    def test_offline_upgrade_generates_postgresql_sql_without_connection(self):
        environment = os.environ.copy()
        environment['DATABASE_URL'] = 'postgresql+psycopg://user:secret@localhost/stillwater'
        result = subprocess.run(
            [
                str(PROJECT_ROOT / '.venv' / 'Scripts' / 'python.exe'),
                '-m', 'alembic', '-c', str(ALEMBIC_CONFIG),
                'upgrade', 'head', '--sql',
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CREATE TABLE alembic_version', result.stdout)
        self.assertIn("'0009'", result.stdout)
        self.assertNotIn('secret', result.stdout)


if __name__ == '__main__':
    unittest.main()
