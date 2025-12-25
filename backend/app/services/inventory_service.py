from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Tuple

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.inventory import ClosingStock, Sale, PerpetualClosing, PurchaseReturn
from app.models.outlet import Outlet, OutletAlias
from app.models.purchase import PurchaseProcessed
from app.utils.text_cleaner import normalize_barcode, normalize_name


def _clean_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: Any):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def _find_outlet(db: Session, site_name: str) -> Outlet | None:
    norm = normalize_name(site_name)
    outlet = db.query(Outlet).filter(func.upper(Outlet.outlet_name) == norm).first()
    if outlet:
        return outlet
    alias = db.query(OutletAlias).filter(func.upper(OutletAlias.alias_name) == norm).first()
    return alias.outlet if alias else None


def _normalize_header(header: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(header))
    return "_".join([segment for segment in cleaned.split("_") if segment])


def import_closing_stock_from_excel(
    db: Session,
    df: pd.DataFrame,
    uploaded_by: str | None = None,
) -> Dict[str, int]:
    required = {"barcode", "outlet", "qty"}
    header_aliases = {
        "barcode": "barcode",
        "bar_code": "barcode",
        "site": "outlet",
        "outlet": "outlet",
        "outlet_name": "outlet",
        "site_name": "outlet",
        "qty": "qty",
        "quantity": "qty",
        "closing_qty": "qty",
        "closing": "qty",
        "date": "as_of_date",
        "as_of": "as_of_date",
    }

    col_map: Dict[int, str] = {}
    for idx, header in enumerate(df.columns):
        norm = _normalize_header(header)
        target = header_aliases.get(norm)
        if target:
            col_map[idx] = target

    missing = required - set(col_map.values())
    if missing:
        raise ValueError(f"Missing required columns for closing stock: {sorted(missing)}")

    stats = {"inserted": 0, "missing_outlet": 0, "skipped_missing_barcode": 0}

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

        qty = _clean_decimal(row_data.get("qty")) or Decimal("0")
        as_of_date = _parse_date(row_data.get("as_of_date"))

        rec = ClosingStock(
            outlet_id=outlet.outlet_id,
            barcode=barcode,
            qty=qty,
            as_of_date=as_of_date,
            uploaded_by=uploaded_by,
        )
        db.add(rec)
        stats["inserted"] += 1

    db.commit()
    return stats


def import_sales_from_excel(
    db: Session,
    df: pd.DataFrame,
    uploaded_by: str | None = None,
) -> Dict[str, int]:
    required = {"barcode", "outlet", "qty", "sale_amount", "sale_date"}
    header_aliases = {
        "barcode": "barcode",
        "bar_code": "barcode",
        "site": "outlet",
        "outlet": "outlet",
        "outlet_name": "outlet",
        "site_name": "outlet",
        "qty": "qty",
        "quantity": "qty",
        "sale_qty": "qty",
        "sold_qty": "qty",
        "sale_amount": "sale_amount",
        "amount": "sale_amount",
        "sale_value": "sale_amount",
        "sale": "sale_amount",
        "date": "sale_date",
        "sale_date": "sale_date",
        "invoice_date": "sale_date",
    }

    col_map: Dict[int, str] = {}
    for idx, header in enumerate(df.columns):
        norm = _normalize_header(header)
        target = header_aliases.get(norm)
        if target:
            col_map[idx] = target

    missing = required - set(col_map.values())
    if missing:
        raise ValueError(f"Missing required columns for sales: {sorted(missing)}")

    stats = {"inserted": 0, "missing_outlet": 0, "skipped_missing_barcode": 0, "skipped_bad_date": 0}

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

        sale_date = _parse_date(row_data.get("sale_date"))
        if not sale_date:
            stats["skipped_bad_date"] += 1
            continue

        qty = _clean_decimal(row_data.get("qty")) or Decimal("0")
        amount = _clean_decimal(row_data.get("sale_amount")) or Decimal("0")

        rec = Sale(
            outlet_id=outlet.outlet_id,
            barcode=barcode,
            qty=qty,
            sale_amount=amount,
            sale_date=sale_date,
            uploaded_by=uploaded_by,
        )
        db.add(rec)
        stats["inserted"] += 1

    db.commit()
    return stats


def import_perpetual_from_excel(
    db: Session,
    df: pd.DataFrame,
    uploaded_by: str | None = None,
) -> Dict[str, int]:
    required = {"barcode", "outlet", "qty"}
    header_aliases = {
        "barcode": "barcode",
        "bar_code": "barcode",
        "site": "outlet",
        "outlet": "outlet",
        "outlet_name": "outlet",
        "site_name": "outlet",
        "qty": "qty",
        "quantity": "qty",
        "perpetual_qty": "qty",
        "date": "as_of_date",
        "as_of": "as_of_date",
    }

    col_map: Dict[int, str] = {}
    for idx, header in enumerate(df.columns):
        norm = _normalize_header(header)
        target = header_aliases.get(norm)
        if target:
            col_map[idx] = target

    missing = required - set(col_map.values())
    if missing:
        raise ValueError(f"Missing required columns for perpetual closing: {sorted(missing)}")

    stats = {"inserted": 0, "missing_outlet": 0, "skipped_missing_barcode": 0}

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

        qty = _clean_decimal(row_data.get("qty")) or Decimal("0")
        as_of_date = _parse_date(row_data.get("as_of_date"))

        rec = PerpetualClosing(
            outlet_id=outlet.outlet_id,
            barcode=barcode,
            qty=qty,
            as_of_date=as_of_date,
            uploaded_by=uploaded_by,
        )
        db.add(rec)
        stats["inserted"] += 1

    db.commit()
    return stats


def import_grt_from_excel(
    db: Session,
    df: pd.DataFrame,
    uploaded_by: str | None = None,
) -> Dict[str, int]:
    """
    Ingest purchase returns (GRT):
      Required: barcode, entry_no, entry_date, supplier_name, outlet/site, qty, amount.
    """
    required = {"barcode", "entry_no", "entry_date", "supplier_name", "outlet", "qty", "amount"}
    header_aliases = {
        "goods_return_daas": "barcode",  # specific file header
        "unnamed_1": "article_name",
        "unnamed_2": "invoice_no",
        "unnamed_3": "entry_no",
        "unnamed_4": "entry_date",
        "unnamed_5": "supplier_name",
        "unnamed_6": "outlet",
        "unnamed_7": "category_6",
        "unnamed_8": "qty",
        "unnamed_9": "amount",
        "barcode": "barcode",
        "bar_code": "barcode",
        "qty": "qty",
        "quantity": "qty",
        "return_qty": "qty",
        "return_quantity": "qty",
        "rtn_qty": "qty",
        "amount": "amount",
        "net_amount": "amount",
        "rtn_amt": "amount",
        "return_amount": "amount",
        "invoice_no": "invoice_no",
        "invoice": "invoice_no",
        "inv_no": "invoice_no",
        "entry_no": "entry_no",
        "entry": "entry_no",
        "entry_number": "entry_no",
        "date": "entry_date",
        "entry_date": "entry_date",
        "return_date": "entry_date",
        "supplier_name": "supplier_name",
        "supplier": "supplier_name",
        "suppilier_name": "supplier_name",
        "outlet": "outlet",
        "site": "outlet",
        "site_name": "outlet",
        "owner_site": "outlet",
        "stock_point": "outlet",
        "article_name": "article_name",
        "cat_6": "category_6",
        "category_6": "category_6",
        "cat-6": "category_6",
    }

    col_map: Dict[int, str] = {}
    for idx, header in enumerate(df.columns):
        norm = _normalize_header(header)
        target = header_aliases.get(norm)
        if target:
            col_map[idx] = target

    missing = required - set(col_map.values())
    if missing:
        raise ValueError(f"Missing required columns for purchase return: {sorted(missing)}")

    stats = {
        "inserted": 0,
        "missing_outlet": 0,
        "skipped_missing_barcode": 0,
        "skipped_bad_date": 0,
        "skipped_missing_required": 0,
    }

    for _, row in df.iterrows():
        row_data: Dict[str, Any] = {}
        for idx, field in col_map.items():
            row_data[field] = row.iloc[idx]

        barcode_raw = row_data.get("barcode", "")
        if str(barcode_raw).strip().lower() in {"barcode", "m"}:
            # skip header/meta rows
            continue

        barcode = normalize_barcode(barcode_raw)
        if not barcode:
            stats["skipped_missing_barcode"] += 1
            continue

        outlet = _find_outlet(db, row_data.get("outlet") or "")
        if not outlet:
            stats["missing_outlet"] += 1
            continue

        entry_date = _parse_date(row_data.get("entry_date"))
        if not entry_date:
            stats["skipped_bad_date"] += 1
            continue

        entry_no = str(row_data.get("entry_no") or "").strip()
        supplier_name = str(row_data.get("supplier_name") or "").strip()
        amount = _clean_decimal(row_data.get("amount")) or Decimal("0")
        qty = _clean_decimal(row_data.get("qty")) or Decimal("0")

        if not entry_no or not supplier_name:
            stats["skipped_missing_required"] += 1
            continue

        rec = PurchaseReturn(
            outlet_id=outlet.outlet_id,
            barcode=barcode,
            entry_no=entry_no,
            entry_date=entry_date,
            supplier_name=supplier_name,
            invoice_no=(str(row_data.get("invoice_no") or "").strip() or None),
            article_name=(str(row_data.get("article_name") or "").strip() or None),
            category_6=(str(row_data.get("category_6") or "").strip() or None),
            qty=qty,
            amount=amount,
            uploaded_by=uploaded_by,
        )
        db.add(rec)
        stats["inserted"] += 1

    db.commit()
    return stats


def _latest_closing_by_key(db: Session) -> Dict[Tuple[int, str], ClosingStock]:
    """
    Return the latest closing record per (outlet_id, barcode), preferring most recent
    uploaded_at and falling back to highest primary key.
    """
    results: Dict[Tuple[int, str], ClosingStock] = {}
    closings = db.query(ClosingStock).all()
    for row in closings:
        key = (row.outlet_id, row.barcode)
        existing = results.get(key)
        if not existing:
            results[key] = row
            continue
        # Prefer the row with the latest uploaded_at; if equal/None, use higher id
        if existing.uploaded_at and row.uploaded_at:
            if row.uploaded_at > existing.uploaded_at:
                results[key] = row
        elif row.uploaded_at and not existing.uploaded_at:
            results[key] = row
        elif (not existing.uploaded_at and not row.uploaded_at) and row.closing_id > existing.closing_id:
            results[key] = row
    return results


def recompute_perpetual_closing(
    db: Session,
    uploaded_by: str | None = None,
) -> Dict[str, Any]:
    """
    Derive perpetual closing as:
      opening (latest closing) + purchases - sales
    Sales returns should come in as negative qty; purchase returns will be wired later.
    Stores results into perpetual_closing table (full refresh).
    """
    closing_by_key = _latest_closing_by_key(db)

    purchase_totals: Dict[Tuple[int, str], Decimal] = {}
    for row in (
        db.query(
            PurchaseProcessed.outlet_id,
            PurchaseProcessed.barcode,
            func.sum(PurchaseProcessed.pur_qty).label("qty"),
        )
        .filter(PurchaseProcessed.outlet_id.isnot(None), PurchaseProcessed.barcode.isnot(None))
        .group_by(PurchaseProcessed.outlet_id, PurchaseProcessed.barcode)
        .all()
    ):
        key = (row.outlet_id, row.barcode)
        purchase_totals[key] = Decimal(row.qty or 0)

    purchase_return_totals: Dict[Tuple[int, str], Decimal] = {}
    latest_return_date: Dict[Tuple[int, str], Any] = {}
    for row in (
        db.query(
            PurchaseReturn.outlet_id,
            PurchaseReturn.barcode,
            func.sum(PurchaseReturn.qty).label("qty"),
            func.max(PurchaseReturn.entry_date).label("last_date"),
        )
        .filter(PurchaseReturn.outlet_id.isnot(None), PurchaseReturn.barcode.isnot(None))
        .group_by(PurchaseReturn.outlet_id, PurchaseReturn.barcode)
        .all()
    ):
        key = (row.outlet_id, row.barcode)
        purchase_return_totals[key] = Decimal(row.qty or 0)
        latest_return_date[key] = row.last_date

    sales_totals: Dict[Tuple[int, str], Decimal] = {}
    latest_sale_date: Dict[Tuple[int, str], Any] = {}
    for row in (
        db.query(
            Sale.outlet_id,
            Sale.barcode,
            func.sum(Sale.qty).label("qty"),
            func.max(Sale.sale_date).label("last_date"),
        )
        .filter(Sale.outlet_id.isnot(None), Sale.barcode.isnot(None))
        .group_by(Sale.outlet_id, Sale.barcode)
        .all()
    ):
        key = (row.outlet_id, row.barcode)
        sales_totals[key] = Decimal(row.qty or 0)
        latest_sale_date[key] = row.last_date

    keys = (
        set(closing_by_key.keys())
        | set(purchase_totals.keys())
        | set(sales_totals.keys())
        | set(purchase_return_totals.keys())
    )

    # Reset derived table before inserting fresh values
    db.query(PerpetualClosing).delete(synchronize_session=False)

    inserted = 0
    total_purchase_qty = Decimal("0")
    total_sales_qty = Decimal("0")
    total_purchase_return_qty = Decimal("0")

    for key in keys:
        outlet_id, barcode = key
        closing_row = closing_by_key.get(key)
        opening_qty = Decimal(closing_row.qty or 0) if closing_row else Decimal("0")
        purchase_qty = purchase_totals.get(key, Decimal("0"))
        sales_qty = sales_totals.get(key, Decimal("0"))
        purchase_return_qty = purchase_return_totals.get(key, Decimal("0"))

        perpetual_qty = opening_qty + purchase_qty - purchase_return_qty - sales_qty

        as_of_date = None
        if closing_row and closing_row.as_of_date:
            as_of_date = closing_row.as_of_date
        elif latest_sale_date.get(key):
            as_of_date = latest_sale_date[key]
        elif latest_return_date.get(key):
            as_of_date = latest_return_date[key]

        rec = PerpetualClosing(
            outlet_id=outlet_id,
            barcode=barcode,
            qty=perpetual_qty,
            as_of_date=as_of_date,
            uploaded_by=uploaded_by,
        )
        db.add(rec)
        inserted += 1
        total_purchase_qty += purchase_qty
        total_sales_qty += sales_qty
        total_purchase_return_qty += purchase_return_qty

    db.commit()

    return {
        "computed": inserted,
        "total_purchase_qty": str(total_purchase_qty),
        "total_purchase_return_qty": str(total_purchase_return_qty),
        "total_sales_qty": str(total_sales_qty),
        "opening_records": len(closing_by_key),
        "keys_processed": len(keys),
    }
