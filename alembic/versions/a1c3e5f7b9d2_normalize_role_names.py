"""normalize role names

Revision ID: a1c3e5f7b9d2
Revises: bd20b49d2256
Create Date: 2026-03-11

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1c3e5f7b9d2'
down_revision: Union[str, Sequence[str], None] = 'bd20b49d2256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalize role values to lowercase standard: admin | instructor | user."""
    op.execute("UPDATE users SET role = 'instructor' WHERE role = 'Instructor'")
    op.execute("UPDATE users SET role = 'user' WHERE role = 'learner'")


def downgrade() -> None:
    """Revert role values to previous state."""
    op.execute("UPDATE users SET role = 'learner' WHERE role = 'user'")
    op.execute("UPDATE users SET role = 'Instructor' WHERE role = 'instructor'")
