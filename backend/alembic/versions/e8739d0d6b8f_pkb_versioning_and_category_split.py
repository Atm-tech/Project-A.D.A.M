"""Add PKB versioning and category grouping; extend purchase tables with category_6

Revision ID: e8739d0d6b8f
Revises: d0f2a0a8b2c4
Create Date: 2025-12-19 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8739d0d6b8f"
down_revision: Union[str, Sequence[str], None] = "d0f2a0a8b2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PKB: add category grouping + version, relax barcode uniqueness
    op.add_column("pkb_products", sa.Column("category_group", sa.String(length=50), nullable=True))
    op.add_column("pkb_products", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.drop_index("ix_pkb_products_barcode", table_name="pkb_products")
    op.create_index("ix_pkb_products_barcode", "pkb_products", ["barcode"], unique=False)
    op.create_index(
        "ix_pkb_products_barcode_version",
        "pkb_products",
        ["barcode", "version"],
        unique=True,
    )

    # Purchase tables: store category_6 + grouping for downstream analysis
    op.add_column("purchase_raw", sa.Column("category_6", sa.String(length=150), nullable=True))
    op.add_column("purchase_raw", sa.Column("category_group", sa.String(length=50), nullable=True))
    op.add_column("purchase_processed", sa.Column("category_6", sa.String(length=150), nullable=True))
    op.add_column("purchase_processed", sa.Column("category_group", sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("purchase_processed", "category_group")
    op.drop_column("purchase_processed", "category_6")
    op.drop_column("purchase_raw", "category_group")
    op.drop_column("purchase_raw", "category_6")

    op.drop_index("ix_pkb_products_barcode_version", table_name="pkb_products")
    op.drop_index("ix_pkb_products_barcode", table_name="pkb_products")
    op.create_index("ix_pkb_products_barcode", "pkb_products", ["barcode"], unique=True)
    op.drop_column("pkb_products", "version")
    op.drop_column("pkb_products", "category_group")
