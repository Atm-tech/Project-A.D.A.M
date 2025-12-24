from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    func,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.audit import Audit, AuditAssignment, AuditOutlet, AuditUpload
from app.models.outlet import Outlet, OutletAlias
from app.models.pkb import PKBProduct
from app.schemas.audit import (
    AuditAcceptance,
    AuditCategorySummaryItem,
    AuditAssignmentCreate,
    AuditCreate,
    AuditScanCreate,
    AuditSummaryItem,
    AuditUserSummaryItem,
)
from app.utils.text_cleaner import normalize_barcode, normalize_name


def _normalize_header(header: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(header))
    return "_".join([segment for segment in cleaned.split("_") if segment])


def _clean_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _find_outlet(db: Session, site_name: str) -> Outlet | None:
    norm = normalize_name(site_name)
    outlet = db.query(Outlet).filter(func.upper(Outlet.outlet_name) == norm).first()
    if outlet:
        return outlet
    alias = db.query(OutletAlias).filter(func.upper(OutletAlias.alias_name) == norm).first()
    return alias.outlet if alias else None


class AuditRuntimeStore:
    """Manage per-audit runtime schemas and tables."""

    def __init__(self, engine_obj: Engine):
        self.engine = engine_obj

    def _schema_name(self, audit_id: int) -> str:
        return f"audit_runtime_{audit_id}"

    def _build_tables(self, schema: str) -> Tuple[MetaData, Table, Table]:
        metadata = MetaData(schema=schema)
        expected = Table(
            "expected_stock",
            metadata,
            Column("expected_id", Integer, primary_key=True, index=True),
            Column("barcode", String(50), nullable=False),
            Column("article_name", String(255)),
            Column("division", String(150)),
            Column("section", String(150)),
            Column("department", String(150)),
            Column("category_6", String(150)),
            Column("pkb_id", Integer),
            Column("outlet_id", Integer, nullable=False),
            Column("book_qty", Numeric(12, 3), nullable=False),
            Column("uploaded_by", String(150)),
            Column("created_at", DateTime(timezone=True), server_default=func.now()),
        )
        scans = Table(
            "scan_events",
            metadata,
            Column("scan_id", Integer, primary_key=True, index=True),
            Column("barcode", String(50), nullable=False),
            Column("outlet_id", Integer, nullable=False),
            Column("qty", Numeric(12, 3), nullable=False, default=1),
            Column("user_name", String(150), nullable=False),
            Column("assignment_id", Integer),
            Column("device_ref", String(150)),
            Column("scanned_at", DateTime(timezone=True), server_default=func.now()),
        )
        return metadata, expected, scans

    def ensure_schema(self, schema: str) -> Tuple[Table, Table]:
        metadata, expected, scans = self._build_tables(schema)
        with self.engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        metadata.create_all(self.engine)
        return expected, scans

    def drop_schema(self, schema: str) -> None:
        if not schema:
            return
        with self.engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))

    def ingest_expected_rows(
        self,
        schema: str,
        rows: List[Dict[str, Any]],
    ) -> None:
        expected, _ = self.ensure_schema(schema)
        if not rows:
            return
        with self.engine.begin() as conn:
            conn.execute(expected.insert(), rows)

    def record_scan(
        self,
        schema: str,
        row: Dict[str, Any],
    ) -> None:
        _, scans = self.ensure_schema(schema)
        with self.engine.begin() as conn:
            conn.execute(scans.insert().values(**row))

    def fetch_summaries(
        self,
        schema: str,
        outlet_id: Optional[int] = None,
    ) -> List[AuditSummaryItem]:
        expected, scans = self.ensure_schema(schema)

        expected_stmt = select(
            expected.c.barcode,
            expected.c.outlet_id,
            expected.c.article_name,
            expected.c.division,
            expected.c.section,
            expected.c.department,
            expected.c.category_6,
            expected.c.book_qty,
        )
        scanned_stmt = (
            select(
                scans.c.barcode.label("barcode"),
                scans.c.outlet_id.label("outlet_id"),
                func.coalesce(func.sum(scans.c.qty), 0).label("scanned_qty"),
            )
            .group_by(scans.c.barcode, scans.c.outlet_id)
        )

        if outlet_id:
            expected_stmt = expected_stmt.where(expected.c.outlet_id == outlet_id)
            scanned_stmt = scanned_stmt.where(scans.c.outlet_id == outlet_id)

        with self.engine.connect() as conn:
            expected_rows = conn.execute(expected_stmt).all()
            scanned_rows = conn.execute(scanned_stmt).all()

        scanned_map: Dict[tuple, Decimal] = {
            (row.barcode, row.outlet_id): row.scanned_qty for row in scanned_rows
        }

        results: List[AuditSummaryItem] = []
        for row in expected_rows:
            scanned_qty = scanned_map.get((row.barcode, row.outlet_id), Decimal("0"))
            book_qty = Decimal(row.book_qty)
            variance = scanned_qty - book_qty
            remaining = book_qty - scanned_qty
            results.append(
                AuditSummaryItem(
                    barcode=row.barcode,
                    outlet_id=row.outlet_id,
                    article_name=row.article_name,
                    division=row.division,
                    section=row.section,
                    department=row.department,
                    category_6=row.category_6,
                    book_qty=book_qty,
                    scanned_qty=scanned_qty,
                    variance=variance,
                    remaining=remaining,
                )
            )
        return results

    def fetch_user_summaries(
        self,
        schema: str,
        outlet_id: Optional[int] = None,
    ) -> List[AuditUserSummaryItem]:
        _, scans = self.ensure_schema(schema)
        stmt = (
            select(
                scans.c.user_name,
                scans.c.outlet_id,
                func.count(scans.c.scan_id).label("scan_count"),
                func.coalesce(func.sum(scans.c.qty), 0).label("total_qty"),
            )
            .group_by(scans.c.user_name, scans.c.outlet_id)
            .order_by(scans.c.user_name, scans.c.outlet_id)
        )
        if outlet_id:
            stmt = stmt.where(scans.c.outlet_id == outlet_id)

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()

        return [
            AuditUserSummaryItem(
                user_name=row.user_name,
                outlet_id=row.outlet_id,
                scan_count=row.scan_count,
                total_qty=row.total_qty,
            )
            for row in rows
        ]

    def fetch_category_summaries(
        self,
        schema: str,
        outlet_id: Optional[int] = None,
    ) -> List[AuditCategorySummaryItem]:
        expected, scans = self.ensure_schema(schema)

        scanned_stmt = (
            select(
                scans.c.barcode,
                scans.c.outlet_id,
                func.coalesce(func.sum(scans.c.qty), 0).label("scanned_qty"),
            )
            .group_by(scans.c.barcode, scans.c.outlet_id)
        )
        if outlet_id:
            scanned_stmt = scanned_stmt.where(scans.c.outlet_id == outlet_id)

        with self.engine.connect() as conn:
            scanned_rows = conn.execute(scanned_stmt).all()
            scanned_map: Dict[tuple, Decimal] = {
                (row.barcode, row.outlet_id): row.scanned_qty for row in scanned_rows
            }

            expected_stmt = select(
                expected.c.barcode,
                expected.c.outlet_id,
                expected.c.division,
                expected.c.section,
                expected.c.department,
                expected.c.category_6,
                expected.c.book_qty,
            )
            if outlet_id:
                expected_stmt = expected_stmt.where(expected.c.outlet_id == outlet_id)
            expected_rows = conn.execute(expected_stmt).all()

        agg: Dict[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]], Dict[str, Decimal]] = {}
        for row in expected_rows:
            key = (row.division, row.section, row.department, row.category_6)
            scanned_qty = scanned_map.get((row.barcode, row.outlet_id), Decimal("0"))
            book_qty = Decimal(row.book_qty)
            data = agg.setdefault(
                key,
                {"book_qty": Decimal("0"), "scanned_qty": Decimal("0")},
            )
            data["book_qty"] += book_qty
            data["scanned_qty"] += scanned_qty

        results: List[AuditCategorySummaryItem] = []
        for key, data in agg.items():
            book_qty = data["book_qty"]
            scanned_qty = data["scanned_qty"]
            variance = scanned_qty - book_qty
            remaining = book_qty - scanned_qty
            division, section, department, category_6 = key
            results.append(
                AuditCategorySummaryItem(
                    division=division,
                    section=section,
                    department=department,
                    category_6=category_6,
                    book_qty=book_qty,
                    scanned_qty=scanned_qty,
                    variance=variance,
                    remaining=remaining,
                )
            )
        return results


runtime_store = AuditRuntimeStore(engine)


def create_audit(db: Session, payload: AuditCreate) -> Audit:
    audit = Audit(
        name=payload.name,
        start_date=payload.start_date,
        expiry_date=payload.expiry_date,
        status="pending_acceptance",
        created_by=payload.created_by,
    )
    for outlet_id in payload.outlet_ids:
        audit.outlets.append(AuditOutlet(outlet_id=outlet_id))

    db.add(audit)
    db.flush()  # get audit_id

    schema_name = runtime_store._schema_name(audit.audit_id)
    runtime_store.ensure_schema(schema_name)
    audit.runtime_schema = schema_name

    db.commit()
    db.refresh(audit)
    return audit


def ingest_expected_from_df(
    db: Session,
    audit: Audit,
    df: pd.DataFrame,
    uploaded_by: Optional[str] = None,
    filename: str = "upload",
) -> Dict[str, int]:
    if audit.status == "purged":
        raise ValueError("Audit is already purged.")

    schema_name = audit.runtime_schema or runtime_store._schema_name(audit.audit_id)
    expected_table, _ = runtime_store.ensure_schema(schema_name)
    with runtime_store.engine.begin() as conn:
        conn.execute(expected_table.delete())

    required = {"barcode", "book_qty", "outlet"}
    header_aliases = {
        "barcode": "barcode",
        "bar_code": "barcode",
        "article": "article_name",
        "article_name": "article_name",
        "name": "article_name",
        "book_qty": "book_qty",
        "qty": "book_qty",
        "quantity": "book_qty",
        "outlet": "outlet",
        "site": "outlet",
        "site_name": "outlet",
        "outlet_name": "outlet",
    }

    col_map: Dict[int, str] = {}
    for idx, header in enumerate(df.columns):
        norm = _normalize_header(header)
        target = header_aliases.get(norm)
        if target:
            col_map[idx] = target

    missing = required - set(col_map.values())
    if missing:
        raise ValueError(f"Missing required columns for audit upload: {sorted(missing)}")

    rows: List[Dict[str, Any]] = []
    stats = {"inserted": 0, "missing_outlet": 0, "skipped_missing_barcode": 0}
    pkb_map: Dict[str, Optional[PKBProduct]] = {}

    for _, row in df.iterrows():
        row_data: Dict[str, Any] = {}
        for idx, field in col_map.items():
            row_data[field] = row.iloc[idx]

        barcode = normalize_barcode(row_data.get("barcode", ""))
        if not barcode:
            stats["skipped_missing_barcode"] += 1
            continue

        outlet_name = row_data.get("outlet")
        outlet = _find_outlet(db, outlet_name or "")
        if not outlet:
            stats["missing_outlet"] += 1
            continue

        book_qty = _clean_decimal(row_data.get("book_qty")) or Decimal("0")

        product = pkb_map.get(barcode)
        if product is None:
            product = (
                db.query(PKBProduct)
                .filter(PKBProduct.barcode == barcode)
                .order_by(PKBProduct.version.desc())
                .first()
            )
            pkb_map[barcode] = product

        if product:
            article_name = product.article_name or product.item_name or product.product_name
            division = product.division
            section = product.section
            department = product.department
            category_6 = product.category_6
            pkb_id = product.pkb_id
        else:
            article_name = row_data.get("article_name")
            division = None
            section = None
            department = None
            category_6 = None
            pkb_id = None

        rows.append(
            {
                "barcode": barcode,
                "article_name": str(article_name) if article_name else None,
                "division": division,
                "section": section,
                "department": department,
                "category_6": category_6,
                "pkb_id": pkb_id,
                "outlet_id": outlet.outlet_id,
                "book_qty": book_qty,
                "uploaded_by": uploaded_by,
            }
        )
        stats["inserted"] += 1

    runtime_store.ingest_expected_rows(schema_name, rows)

    upload_log = AuditUpload(
        audit_id=audit.audit_id,
        filename=filename,
        rows_ingested=stats["inserted"],
        rows_skipped=stats["missing_outlet"] + stats["skipped_missing_barcode"],
        uploaded_by=uploaded_by,
    )
    db.add(upload_log)
    db.commit()
    db.refresh(upload_log)
    return stats


def mark_outlet_acceptance(db: Session, audit: Audit, payload: AuditAcceptance) -> AuditOutlet:
    if audit.status == "purged":
        raise ValueError("Audit is already purged.")
    outlet_link = (
        db.query(AuditOutlet)
        .filter(AuditOutlet.audit_id == audit.audit_id, AuditOutlet.outlet_id == payload.outlet_id)
        .first()
    )
    if not outlet_link:
        raise ValueError("Outlet not part of this audit.")

    outlet_link.acceptance_status = payload.acceptance_status
    outlet_link.accepted_by = payload.accepted_by
    outlet_link.accepted_at = datetime.utcnow()

    if payload.acceptance_status == "accepted" and audit.status == "pending_acceptance":
        audit.status = "active"
    if payload.acceptance_status == "rejected":
        audit.status = "rejected"

    db.commit()
    db.refresh(outlet_link)
    return outlet_link


def assign_user(db: Session, audit: Audit, payload: AuditAssignmentCreate) -> AuditAssignment:
    if audit.status == "purged":
        raise ValueError("Audit is already purged.")
    outlet_link = (
        db.query(AuditOutlet)
        .filter(AuditOutlet.audit_id == audit.audit_id, AuditOutlet.outlet_id == payload.outlet_id)
        .first()
    )
    if not outlet_link:
        raise ValueError("Outlet not part of this audit.")

    assignment = AuditAssignment(
        audit_id=audit.audit_id,
        audit_outlet_id=outlet_link.audit_outlet_id,
        outlet_id=payload.outlet_id,
        user_name=payload.user_name,
        assigned_by=payload.assigned_by,
        status="assigned",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _get_outlet_link(db: Session, audit: Audit, outlet_id: int) -> AuditOutlet:
    outlet_link = (
        db.query(AuditOutlet)
        .filter(AuditOutlet.audit_id == audit.audit_id, AuditOutlet.outlet_id == outlet_id)
        .first()
    )
    if not outlet_link:
        raise ValueError("Outlet not part of this audit.")
    return outlet_link


def record_scan(db: Session, audit: Audit, payload: AuditScanCreate) -> Dict[str, Any]:
    if audit.status != "active":
        raise ValueError("Audit is not active.")
    normalized_barcode = normalize_barcode(payload.barcode)
    if not normalized_barcode:
        raise ValueError("Barcode is required for scanning.")

    outlet_link = _get_outlet_link(db, audit, payload.outlet_id)
    if outlet_link.submission_status == "submitted":
        raise ValueError("Outlet audit already submitted.")

    assignment_query = db.query(AuditAssignment).filter(
        AuditAssignment.audit_id == audit.audit_id,
        AuditAssignment.outlet_id == payload.outlet_id,
        AuditAssignment.user_name == payload.user_name,
    )
    if payload.assignment_id:
        assignment_query = assignment_query.filter(AuditAssignment.assignment_id == payload.assignment_id)
    assignment: Optional[AuditAssignment] = assignment_query.first()
    if not assignment:
        raise ValueError("User is not assigned to this outlet for the audit.")
    if assignment.status == "submitted":
        raise ValueError("Assignment already submitted.")

    qty = payload.qty if isinstance(payload.qty, Decimal) else Decimal(str(payload.qty))

    runtime_store.record_scan(
        audit.runtime_schema or runtime_store._schema_name(audit.audit_id),
        {
            "barcode": normalized_barcode,
            "outlet_id": payload.outlet_id,
            "qty": qty,
            "user_name": payload.user_name,
            "assignment_id": assignment.assignment_id,
            "device_ref": payload.device_ref,
        },
    )

    if assignment.status == "assigned":
        assignment.status = "active"
        assignment.started_at = datetime.utcnow()
        db.commit()

    return {"status": "ok", "assignment_id": assignment.assignment_id}


def submit_assignment(db: Session, audit: Audit, assignment_id: int, submitted_by: Optional[str] = None) -> AuditAssignment:
    if audit.status != "active":
        raise ValueError("Audit is not active.")
    assignment = (
        db.query(AuditAssignment)
        .filter(AuditAssignment.audit_id == audit.audit_id, AuditAssignment.assignment_id == assignment_id)
        .first()
    )
    if not assignment:
        raise ValueError("Assignment not found.")
    outlet_link = _get_outlet_link(db, audit, assignment.outlet_id)
    if outlet_link.submission_status == "submitted":
        raise ValueError("Outlet audit already submitted.")
    assignment.status = "submitted"
    assignment.submitted_at = datetime.utcnow()
    assignment.completed_at = assignment.completed_at or assignment.submitted_at
    db.commit()
    db.refresh(assignment)
    return assignment


def submit_outlet(db: Session, audit: Audit, outlet_id: int, submitted_by: Optional[str] = None) -> AuditOutlet:
    if audit.status != "active":
        raise ValueError("Audit is not active.")
    outlet_link = _get_outlet_link(db, audit, outlet_id)
    open_assignments = (
        db.query(AuditAssignment)
        .filter(
            AuditAssignment.audit_id == audit.audit_id,
            AuditAssignment.outlet_id == outlet_id,
            AuditAssignment.status != "submitted",
        )
        .count()
    )
    if open_assignments > 0:
        raise ValueError("All assignments must be submitted before outlet submission.")
    outlet_link.submission_status = "submitted"
    outlet_link.submitted_by = submitted_by
    outlet_link.submitted_at = datetime.utcnow()
    db.commit()

    # if all outlets submitted, flag audit
    all_submitted = (
        db.query(AuditOutlet)
        .filter(AuditOutlet.audit_id == audit.audit_id, AuditOutlet.submission_status != "submitted")
        .count()
        == 0
    )
    if all_submitted:
        audit.status = "awaiting_admin"
        db.commit()
    db.refresh(outlet_link)
    return outlet_link


def summarize(audit: Audit, outlet_id: Optional[int] = None) -> List[AuditSummaryItem]:
    return runtime_store.fetch_summaries(audit.runtime_schema or runtime_store._schema_name(audit.audit_id), outlet_id)


def summarize_by_user(audit: Audit, outlet_id: Optional[int] = None) -> List[AuditUserSummaryItem]:
    return runtime_store.fetch_user_summaries(
        audit.runtime_schema or runtime_store._schema_name(audit.audit_id),
        outlet_id,
    )


def summarize_by_category(audit: Audit, outlet_id: Optional[int] = None) -> List[AuditCategorySummaryItem]:
    return runtime_store.fetch_category_summaries(
        audit.runtime_schema or runtime_store._schema_name(audit.audit_id),
        outlet_id,
    )


def purge_audit(db: Session, audit: Audit) -> None:
    if audit.runtime_schema:
        runtime_store.drop_schema(audit.runtime_schema)
    audit.status = "purged"
    audit.purged_at = datetime.utcnow()
    db.commit()
