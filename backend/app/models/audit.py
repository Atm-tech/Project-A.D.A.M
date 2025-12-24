from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Audit(Base):
    __tablename__ = "audits"

    audit_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="pending_acceptance")  # pending_acceptance/active/awaiting_admin/purged/rejected
    runtime_schema = Column(String(120), nullable=True)

    created_by = Column(String(150))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    purged_at = Column(DateTime(timezone=True))

    outlets = relationship("AuditOutlet", back_populates="audit", cascade="all, delete-orphan")
    uploads = relationship("AuditUpload", back_populates="audit", cascade="all, delete-orphan")
    assignments = relationship("AuditAssignment", back_populates="audit", cascade="all, delete-orphan")


class AuditOutlet(Base):
    __tablename__ = "audit_outlets"
    __table_args__ = (
        UniqueConstraint("audit_id", "outlet_id", name="uq_audit_outlets_audit_outlet"),
    )

    audit_outlet_id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.audit_id"), nullable=False)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)

    acceptance_status = Column(String(20), nullable=False, default="pending")  # pending/accepted/rejected
    accepted_by = Column(String(150))
    accepted_at = Column(DateTime(timezone=True))

    submission_status = Column(String(20), nullable=False, default="open")  # open/submitted
    submitted_by = Column(String(150))
    submitted_at = Column(DateTime(timezone=True))

    audit = relationship("Audit", back_populates="outlets")


class AuditAssignment(Base):
    __tablename__ = "audit_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.audit_id"), nullable=False)
    audit_outlet_id = Column(Integer, ForeignKey("audit_outlets.audit_outlet_id"), nullable=True)
    outlet_id = Column(Integer, nullable=False)

    user_name = Column(String(150), nullable=False)
    assigned_by = Column(String(150))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    submitted_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="assigned")  # assigned/active/submitted

    audit = relationship("Audit", back_populates="assignments")


class AuditUpload(Base):
    __tablename__ = "audit_uploads"

    upload_id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("audits.audit_id"), nullable=False)

    filename = Column(String(255), nullable=False)
    rows_ingested = Column(Integer, nullable=False, default=0)
    rows_skipped = Column(Integer, nullable=False, default=0)
    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    audit = relationship("Audit", back_populates="uploads")
