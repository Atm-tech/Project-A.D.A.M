"""Merge heads 1a2b3c4d5e6f and 9f2dd6b5d21e

Revision ID: 2b3c4d5e6f70
Revises: 1a2b3c4d5e6f, 9f2dd6b5d21e
Create Date: 2025-12-25 21:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f70"
down_revision: Union[str, Sequence[str], None] = ("1a2b3c4d5e6f", "9f2dd6b5d21e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge point; no-op.
    pass


def downgrade() -> None:
    # Merge point; no-op.
    pass
