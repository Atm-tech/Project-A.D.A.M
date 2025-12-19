"""Remove supplier_name from pkb_products

Revision ID: d0f2a0a8b2c4
Revises: b9c63ddba8e6
Create Date: 2025-12-19 06:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d0f2a0a8b2c4"
down_revision: Union[str, Sequence[str], None] = "b9c63ddba8e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("pkb_products", "supplier_name")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "pkb_products",
        sa.Column("supplier_name", sa.String(length=150), nullable=True),
    )
