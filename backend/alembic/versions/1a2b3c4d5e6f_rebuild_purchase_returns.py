"""Rebuild purchase_returns table to match GRT file layout

Revision ID: 1a2b3c4d5e6f
Revises: f2c4a4b7e2a9
Create Date: 2025-12-25 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "f2c4a4b7e2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop any existing purchase_returns table and recreate with new schema."""
    op.execute("DROP TABLE IF EXISTS purchase_returns")

    op.create_table(
        "purchase_returns",
        sa.Column("grt_id", sa.Integer(), primary_key=True, index=True),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.outlet_id"), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=False),
        sa.Column("article_name", sa.String(length=255), nullable=True),
        sa.Column("invoice_no", sa.String(length=100), nullable=True),
        sa.Column("entry_no", sa.String(length=100), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("supplier_name", sa.String(length=150), nullable=False),
        sa.Column("category_6", sa.String(length=150), nullable=True),
        sa.Column("qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_purchase_returns_barcode", "purchase_returns", ["barcode"])
    op.create_index("ix_purchase_returns_outlet_id", "purchase_returns", ["outlet_id"])
    op.create_index("ix_purchase_returns_entry_date", "purchase_returns", ["entry_date"])


def downgrade() -> None:
    """Drop purchase_returns table."""
    op.drop_index("ix_purchase_returns_entry_date", table_name="purchase_returns")
    op.drop_index("ix_purchase_returns_outlet_id", table_name="purchase_returns")
    op.drop_index("ix_purchase_returns_barcode", table_name="purchase_returns")
    op.drop_table("purchase_returns")
