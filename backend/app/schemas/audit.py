from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AuditOutletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_outlet_id: int
    outlet_id: int
    acceptance_status: str
    accepted_by: Optional[str] = None
    accepted_at: Optional[datetime] = None
    submission_status: str
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None


class AuditUploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upload_id: int
    filename: str
    rows_ingested: int
    rows_skipped: int
    uploaded_by: Optional[str] = None
    uploaded_at: datetime


class AuditAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: int
    outlet_id: int
    user_name: str
    status: str
    assigned_by: Optional[str] = None
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    name: str
    start_date: date
    expiry_date: date
    status: str
    runtime_schema: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    purged_at: Optional[datetime] = None
    outlets: List[AuditOutletOut] = []
    uploads: List[AuditUploadOut] = []
    assignments: List[AuditAssignmentOut] = []


class AuditCreate(BaseModel):
    name: str = Field(..., description="Human readable audit name")
    start_date: date
    expiry_date: date
    outlet_ids: List[int] = Field(..., description="Outlets included in this audit")
    created_by: Optional[str] = Field(default=None, description="Admin who created the audit")


class AuditAcceptance(BaseModel):
    outlet_id: int
    accepted_by: str
    acceptance_status: str = Field(default="accepted", description="accepted or rejected")


class AuditAssignmentCreate(BaseModel):
    outlet_id: int
    user_name: str
    assigned_by: Optional[str] = None


class AuditScanCreate(BaseModel):
    barcode: str
    qty: Decimal = Field(default=Decimal("1"))
    outlet_id: int
    user_name: str
    assignment_id: Optional[int] = None
    device_ref: Optional[str] = None


class AuditSummaryItem(BaseModel):
    barcode: str
    outlet_id: int
    article_name: Optional[str] = None
    division: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    category_6: Optional[str] = None
    book_qty: Decimal
    scanned_qty: Decimal
    variance: Decimal
    remaining: Decimal


class AuditUserSummaryItem(BaseModel):
    user_name: str
    outlet_id: int
    scan_count: int
    total_qty: Decimal


class AuditCategorySummaryItem(BaseModel):
    division: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    category_6: Optional[str] = None
    book_qty: Decimal
    scanned_qty: Decimal
    variance: Decimal
    remaining: Decimal
