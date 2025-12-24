import logging
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.deps import get_db
from app.models.audit import Audit
from app.schemas.audit import (
    AuditAcceptance,
    AuditCategorySummaryItem,
    AuditAssignmentCreate,
    AuditCreate,
    AuditOut,
    AuditScanCreate,
    AuditSummaryItem,
    AuditUserSummaryItem,
)
from app.services.audit_service import (
    assign_user,
    create_audit,
    ingest_expected_from_df,
    mark_outlet_acceptance,
    purge_audit,
    record_scan,
    submit_assignment,
    submit_outlet,
    summarize,
    summarize_by_category,
    summarize_by_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_ROWS = 50000
MAX_COLUMNS = 120
ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xltx", ".xltm", ".csv")


def _load_df(content: bytes, filename: str) -> pd.DataFrame:
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel/CSV files are allowed.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(content), dtype=str)
        else:
            df = pd.read_excel(BytesIO(content), dtype=str)
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Unable to read audit upload %s: %s", filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read file: {exc}",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file has no data rows.",
        )
    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds row limit ({MAX_ROWS}).",
        )
    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds column limit ({MAX_COLUMNS}).",
        )
    return df


def _get_audit(db: Session, audit_id: int) -> Audit:
    audit = (
        db.query(Audit)
        .options(
            joinedload(Audit.outlets),
            joinedload(Audit.assignments),
            joinedload(Audit.uploads),
        )
        .filter(Audit.audit_id == audit_id)
        .first()
    )
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return audit


@router.post(
    "/",
    response_model=AuditOut,
    summary="Create a new audit",
    tags=["Audit"],
)
def create_audit_route(payload: AuditCreate, db: Session = Depends(get_db)):
    try:
        audit = create_audit(db, payload)
    except Exception as exc:
        logger.error("Failed to create audit: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return audit


@router.get(
    "/{audit_id}",
    response_model=AuditOut,
    summary="Fetch audit with outlets, assignments, uploads",
    tags=["Audit"],
)
def get_audit(audit_id: int, db: Session = Depends(get_db)):
    return _get_audit(db, audit_id)


@router.get(
    "",
    response_model=List[AuditOut],
    summary="List audits",
    tags=["Audit"],
)
def list_audits(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    rows = (
        db.query(Audit)
        .options(
            joinedload(Audit.outlets),
            joinedload(Audit.assignments),
            joinedload(Audit.uploads),
        )
        .order_by(Audit.audit_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


@router.post(
    "/{audit_id}/upload",
    summary="Upload expected stock CSV/XLSX for an audit",
    tags=["Audit"],
)
async def upload_expected(
    audit_id: int,
    file: UploadFile = File(...),
    uploaded_by: Optional[str] = None,
    db: Session = Depends(get_db),
):
    audit = _get_audit(db, audit_id)
    content = await file.read()
    df = _load_df(content, file.filename)
    try:
        stats = ingest_expected_from_df(db, audit, df, uploaded_by=uploaded_by, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"status": "success", "filename": file.filename, **stats}


@router.post(
    "/{audit_id}/outlets/accept",
    response_model=AuditOut,
    summary="Outlet manager acceptance/rejection",
    tags=["Audit"],
)
def accept_audit(audit_id: int, payload: AuditAcceptance, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    try:
        mark_outlet_acceptance(db, audit, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.refresh(audit)
    return audit


@router.post(
    "/{audit_id}/assignments",
    response_model=AuditOut,
    summary="Assign user to an outlet for this audit",
    tags=["Audit"],
)
def assign_user_route(audit_id: int, payload: AuditAssignmentCreate, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    try:
        assign_user(db, audit, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.refresh(audit)
    return audit


@router.post(
    "/{audit_id}/scan",
    summary="Record a scan from a user device",
    tags=["Audit"],
)
def scan_item(audit_id: int, payload: AuditScanCreate, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    try:
        result = record_scan(db, audit, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return result


@router.get(
    "/{audit_id}/summary",
    response_model=List[AuditSummaryItem],
    summary="Real-time summary per barcode/outlet",
    tags=["Audit"],
)
def audit_summary(audit_id: int, outlet_id: Optional[int] = None, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    return summarize(audit, outlet_id)


@router.get(
    "/{audit_id}/summary/by-category",
    response_model=List[AuditCategorySummaryItem],
    summary="Aggregated summary by division/section/department/category_6",
    tags=["Audit"],
)
def audit_summary_by_category(audit_id: int, outlet_id: Optional[int] = None, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    return summarize_by_category(audit, outlet_id)


@router.get(
    "/{audit_id}/user-summary",
    response_model=List[AuditUserSummaryItem],
    summary="Contribution summary per user/outlet",
    tags=["Audit"],
)
def audit_user_summary(audit_id: int, outlet_id: Optional[int] = None, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    return summarize_by_user(audit, outlet_id)


@router.post(
    "/{audit_id}/assignments/{assignment_id}/submit",
    response_model=AuditOut,
    summary="User submits their assignment (locks further scans for that user)",
    tags=["Audit"],
)
def submit_assignment_route(audit_id: int, assignment_id: int, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    try:
        submit_assignment(db, audit, assignment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.refresh(audit)
    return audit


@router.post(
    "/{audit_id}/outlets/{outlet_id}/submit",
    response_model=AuditOut,
    summary="Outlet manager submits outlet audit (locks outlet scans)",
    tags=["Audit"],
)
def submit_outlet_route(audit_id: int, outlet_id: int, submitted_by: Optional[str] = None, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    try:
        submit_outlet(db, audit, outlet_id, submitted_by=submitted_by)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    db.refresh(audit)
    return audit


@router.post(
    "/{audit_id}/purge",
    summary="Purge an audit runtime database",
    tags=["Audit"],
)
def purge_audit_route(audit_id: int, db: Session = Depends(get_db)):
    audit = _get_audit(db, audit_id)
    purge_audit(db, audit)
    return {"status": "purged", "audit_id": audit_id}
