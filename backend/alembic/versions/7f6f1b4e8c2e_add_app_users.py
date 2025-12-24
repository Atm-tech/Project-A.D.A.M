"""Add app users table and seed demo accounts

Revision ID: 7f6f1b4e8c2e
Revises: 28d8c36a94d1
Create Date: 2025-12-20 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f6f1b4e8c2e"
down_revision: Union[str, Sequence[str], None] = "28d8c36a94d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("password", sa.String(length=150), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.outlet_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_app_users_user_id"), "app_users", ["user_id"], unique=False)

    # seed demo accounts
    op.execute(
        """
        INSERT INTO app_users (username, password, role)
        VALUES
            ('admin', 'admin@123', 'admin'),
            ('outlet', '1234', 'manager'),
            ('user', '1234', 'user')
        ON CONFLICT (username) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_app_users_user_id"), table_name="app_users")
    op.drop_table("app_users")
