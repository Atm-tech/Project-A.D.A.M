from decimal import Decimal, InvalidOperation
from typing import Any, Dict

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.inventory import ClosingStock, Sale, PerpetualClosing
from app.models.outlet import Outlet, OutletAlias
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
