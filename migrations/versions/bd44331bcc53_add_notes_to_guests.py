"""add notes to guests

Revision ID: bd44331bcc53
Revises: 
Create Date: 2025-09-17 12:29:18.524496

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd44331bcc53'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'notes' column to guests table."""
    op.add_column("guests", sa.Column("notes", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove 'notes' column from guests table (⚠️ SQLite has limitations)."""
    # SQLite doesn’t support DROP COLUMN directly.
    # In production DBs (Postgres/MySQL) this would work:
    # op.drop_column("guests", "notes")
    #
    # For SQLite you may need to recreate the table if downgrade is required.
    pass
