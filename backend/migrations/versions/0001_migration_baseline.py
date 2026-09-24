"""Establish the PostgreSQL migration baseline.

Revision ID: 0001
Revises: None
"""
from collections.abc import Sequence


revision: str = '0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create no application tables; later revisions own schema changes."""
    pass


def downgrade() -> None:
    """The baseline contains no application schema to remove."""
    pass
