"""Add audit module tables

Revision ID: 28d8c36a94d1
Revises: f2c4a4b7e2a9
Create Date: 2025-12-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "28d8c36a94d1"
down_revision: Union[str, Sequence[str], None] = "f2c4a4b7e2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audits",
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending_acceptance"),
        sa.Column("runtime_schema", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("audit_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_audits_audit_id"), "audits", ["audit_id"], unique=False)

    op.create_table(
        "audit_outlets",
        sa.Column("audit_outlet_id", sa.Integer(), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("acceptance_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("accepted_by", sa.String(length=150), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("submitted_by", sa.String(length=150), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.audit_id"]),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.outlet_id"]),
        sa.PrimaryKeyConstraint("audit_outlet_id"),
        sa.UniqueConstraint("audit_id", "outlet_id", name="uq_audit_outlets_audit_outlet"),
    )
    op.create_index(op.f("ix_audit_outlets_audit_outlet_id"), "audit_outlets", ["audit_outlet_id"], unique=False)

    op.create_table(
        "audit_assignments",
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("audit_outlet_id", sa.Integer(), nullable=True),
        sa.Column("outlet_id", sa.Integer(), nullable=False),
        sa.Column("user_name", sa.String(length=150), nullable=False),
        sa.Column("assigned_by", sa.String(length=150), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="assigned"),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.audit_id"]),
        sa.ForeignKeyConstraint(["audit_outlet_id"], ["audit_outlets.audit_outlet_id"]),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_index(op.f("ix_audit_assignments_assignment_id"), "audit_assignments", ["assignment_id"], unique=False)
    op.create_index("ix_audit_assignments_outlet_id", "audit_assignments", ["outlet_id"], unique=False)
    op.create_index("ix_audit_assignments_user_name", "audit_assignments", ["user_name"], unique=False)

    op.create_table(
        "audit_uploads",
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("rows_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.audit_id"]),
        sa.PrimaryKeyConstraint("upload_id"),
    )
    op.create_index(op.f("ix_audit_uploads_upload_id"), "audit_uploads", ["upload_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_uploads_upload_id"), table_name="audit_uploads")
    op.drop_table("audit_uploads")

    op.drop_index("ix_audit_assignments_user_name", table_name="audit_assignments")
    op.drop_index("ix_audit_assignments_outlet_id", table_name="audit_assignments")
    op.drop_index(op.f("ix_audit_assignments_assignment_id"), table_name="audit_assignments")
    op.drop_table("audit_assignments")

    op.drop_index(op.f("ix_audit_outlets_audit_outlet_id"), table_name="audit_outlets")
    op.drop_table("audit_outlets")

    op.drop_index(op.f("ix_audits_audit_id"), table_name="audits")
    op.drop_table("audits")
