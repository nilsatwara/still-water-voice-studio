import unittest

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CreateTable

from backend.app.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FoundationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = 'foundation_records'
    __table_args__ = (UniqueConstraint('slug'),)

    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)


class ModelFoundationTests(unittest.TestCase):
    def test_foundation_compiles_as_postgresql_schema(self):
        ddl = str(CreateTable(FoundationRecord.__table__).compile(dialect=postgresql.dialect()))
        self.assertIn('UUID NOT NULL', ddl)
        self.assertIn('TIMESTAMP WITH TIME ZONE', ddl)
        self.assertIn('CONSTRAINT pk_foundation_records PRIMARY KEY', ddl)
        self.assertIn('CONSTRAINT uq_foundation_records_slug UNIQUE', ddl)

    def test_uuid_default_generates_distinct_identifiers(self):
        first = FoundationRecord.__table__.c.id.default.arg(None)
        second = FoundationRecord.__table__.c.id.default.arg(None)
        self.assertNotEqual(first, second)

    def test_timestamp_columns_are_server_initialized(self):
        self.assertIsNotNone(FoundationRecord.__table__.c.created_at.server_default)
        self.assertIsNotNone(FoundationRecord.__table__.c.updated_at.server_default)
        self.assertIsNotNone(FoundationRecord.__table__.c.updated_at.onupdate)


if __name__ == '__main__':
    unittest.main()
