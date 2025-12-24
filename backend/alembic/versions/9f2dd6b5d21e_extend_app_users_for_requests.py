"""Extend app_users for requests/approvals

Revision ID: 9f2dd6b5d21e
Revises: 7f6f1b4e8c2e
Create Date: 2025-12-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2dd6b5d21e"
down_revision: Union[str, Sequence[str], None] = "7f6f1b4e8c2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("app_users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column("app_users", sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
    op.add_column("app_users", sa.Column("requested_outlet_id", sa.Integer(), nullable=True))
    op.add_column("app_users", sa.Column("approved_by", sa.String(length=150), nullable=True))
    op.add_column("app_users", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_app_users_username", "app_users", ["username"])
    op.create_unique_constraint("uq_app_users_phone", "app_users", ["phone"])


def downgrade() -> None:
    op.drop_constraint("uq_app_users_phone", "app_users", type_="unique")
    op.drop_constraint("uq_app_users_username", "app_users", type_="unique")
    op.drop_column("app_users", "approved_at")
    op.drop_column("app_users", "approved_by")
    op.drop_column("app_users", "requested_outlet_id")
    op.drop_column("app_users", "status")
    op.drop_column("app_users", "phone")
    op.drop_column("app_users", "full_name")
