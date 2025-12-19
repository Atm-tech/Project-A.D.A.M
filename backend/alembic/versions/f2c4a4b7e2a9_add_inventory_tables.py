"""Add closing stock, sales, and perpetual closing tables

Revision ID: f2c4a4b7e2a9
Revises: e8739d0d6b8f
Create Date: 2025-12-19 07:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c4a4b7e2a9"
down_revision: Union[str, Sequence[str], None] = "e8739d0d6b8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "closing_stock",
        sa.Column("closing_id", sa.Integer(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=False),
        sa.Column("qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.outlet_id"]),
        sa.PrimaryKeyConstraint("closing_id"),
    )
    op.create_index(op.f("ix_closing_stock_closing_id"), "closing_stock", ["closing_id"], unique=False)
    op.create_index("ix_closing_stock_barcode", "closing_stock", ["barcode"], unique=False)
    op.create_index("ix_closing_stock_outlet_id", "closing_stock", ["outlet_id"], unique=False)

    op.create_table(
        "sales",
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=False),
        sa.Column("qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("sale_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.outlet_id"]),
        sa.PrimaryKeyConstraint("sale_id"),
    )
    op.create_index(op.f("ix_sales_sale_id"), "sales", ["sale_id"], unique=False)
    op.create_index("ix_sales_barcode", "sales", ["barcode"], unique=False)
    op.create_index("ix_sales_outlet_id", "sales", ["outlet_id"], unique=False)
    op.create_index("ix_sales_sale_date", "sales", ["sale_date"], unique=False)

    op.create_table(
        "perpetual_closing",
        sa.Column("perpetual_id", sa.Integer(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=False),
        sa.Column("qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.outlet_id"]),
        sa.PrimaryKeyConstraint("perpetual_id"),
    )
    op.create_index(op.f("ix_perpetual_closing_perpetual_id"), "perpetual_closing", ["perpetual_id"], unique=False)
    op.create_index("ix_perpetual_closing_barcode", "perpetual_closing", ["barcode"], unique=False)
    op.create_index("ix_perpetual_closing_outlet_id", "perpetual_closing", ["outlet_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_perpetual_closing_outlet_id", table_name="perpetual_closing")
    op.drop_index("ix_perpetual_closing_barcode", table_name="perpetual_closing")
    op.drop_index(op.f("ix_perpetual_closing_perpetual_id"), table_name="perpetual_closing")
    op.drop_table("perpetual_closing")

    op.drop_index("ix_sales_sale_date", table_name="sales")
    op.drop_index("ix_sales_outlet_id", table_name="sales")
    op.drop_index("ix_sales_barcode", table_name="sales")
    op.drop_index(op.f("ix_sales_sale_id"), table_name="sales")
    op.drop_table("sales")

    op.drop_index("ix_closing_stock_outlet_id", table_name="closing_stock")
    op.drop_index("ix_closing_stock_barcode", table_name="closing_stock")
    op.drop_index(op.f("ix_closing_stock_closing_id"), table_name="closing_stock")
    op.drop_table("closing_stock")
