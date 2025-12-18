from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Tuple

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.outlet import Outlet, OutletAlias
from app.models.pkb import PKBProduct
from app.models.purchase import PurchaseProcessed, PurchaseRaw
from app.utils.text_cleaner import normalize_barcode, normalize_name, normalize_whitespace
from app.utils.weight_parser import parse_weight


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


REQUIRED_FIELDS = {
    "site_name",
    "barcode",
    "supplier_name",
    "hsn_code",
    "division",
    "section",
    "department",
    "article_name_raw",
    "item_name_raw",
    "name_raw",
    "brand_name_raw",
    "size_raw",
    "pur_qty",
    "net_amount",
    "rsp_raw",
    "mrp_raw",
}

# Allowed column aliases from Excel -> model field
HEADER_ALIASES = {
    "site_name": "site_name",
    "site": "site_name",
    "sitecode": "site_name",
    "outlet": "site_name",
    "outlet_name": "site_name",
    "barcode": "barcode",
    "supplier_name": "supplier_name",
    "supplier": "supplier_name",
    "hsn_code": "hsn_code",
    "hsn": "hsn_code",
    "division": "division",
    "section": "section",
    "department": "department",
    "article_name": "article_name_raw",
    "article": "article_name_raw",
    "item_name": "item_name_raw",
    "item": "item_name_raw",
    "name": "name_raw",
    "product_name": "name_raw",
    "brand_name": "brand_name_raw",
    "brand": "brand_name_raw",
    "brandname": "brand_name_raw",
    "brand_nm": "brand_name_raw",
    "brand_nm_": "brand_name_raw",
    "size": "size_raw",
    "rsp": "rsp_raw",
    "mrp": "mrp_raw",
    "pur_qty": "pur_qty",
    "pur": "pur_qty",
    "qty": "pur_qty",
    "quantity": "pur_qty",
    "quantity_purchased": "pur_qty",
    "purchase_qty": "pur_qty",
    "purchase_quantity": "pur_qty",
    "purch_qty": "pur_qty",
    "npur": "net_amount",
    "n_pur": "net_amount",
    "netpur": "net_amount",
    "net_pur": "net_amount",
    "net_amount": "net_amount",
    "net_amt": "net_amount",
    "netamt": "net_amount",
    "net_value": "net_amount",
    "tax": "tax_raw",
    "cgst": "cgst_raw",
    "sgst": "sgst_raw",
    "igst": "igst_raw",
    "cess": "cess_raw",
    "batch_no": "batch_no",
    "batch": "batch_no",
    "mfg_date": "mfg_date",
    "expiry_date": "expiry_date",
    "remarks": "remarks",
    "invoice_no": "invoice_no",
    "entry_no": "entry_no",
    "date": "date",
}


def _normalize_header(header: str) -> str:
    """Lowercase, strip, and collapse non-alphanumerics to underscore."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(header))
    return "_".join([segment for segment in cleaned.split("_") if segment])


def _maybe_promote_first_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    If the file has blank/unnamed headers and the real header is in the first row,
    promote that row to headers.
    """
    if not len(df):
        return df
    headers = list(df.columns)
    unnamed = [str(h).lower().startswith("unnamed") or str(h).strip() == "" for h in headers]
    if unnamed.count(True) >= max(1, len(headers) // 2):
        # Treat first row as header
        df = df.copy()
        new_headers = [str(h) for h in df.iloc[0].tolist()]
        df = df.iloc[1:]
        df.columns = new_headers
    return df


def _build_column_map(df: pd.DataFrame) -> Dict[int, str]:
    """
    Build a column index -> model field map using aliases and detect missing required fields.
    """
    col_map: Dict[int, str] = {}
    normalized_seen: list[tuple[int, str, str]] = []  # (index, raw header, normalized)
    for idx, raw_header in enumerate(df.columns):
        normalized = _normalize_header(raw_header)
        normalized_seen.append((idx, str(raw_header), normalized))
        target = HEADER_ALIASES.get(normalized)
        if not target:
            # Heuristics for common variations
            if "brand" in normalized:
                target = "brand_name_raw"
            elif "net" in normalized and ("amt" in normalized or "amount" in normalized or "value" in normalized):
                target = "net_amount"
            elif "pur" in normalized or "qty" in normalized or "quantity" in normalized:
                target = "pur_qty"
        if target:
            col_map[idx] = target

    missing = REQUIRED_FIELDS - set(col_map.values())
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)} "
            f"(headers: {normalized_seen})"
        )

    return col_map


def _ensure_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[int, str]]:
    """
    Build column map; if required columns are missing, attempt to promote the first row
    as headers and retry before failing.
    """
    try:
        return df, _build_column_map(df)
    except ValueError as err:
        if df.empty:
            raise
        # Try promoting the first row as headers
        fallback_headers = [str(h) for h in df.iloc[0].tolist()]
        promoted_df = df.iloc[1:].copy()
        promoted_df.columns = fallback_headers
        try:
            return promoted_df, _build_column_map(promoted_df)
        except ValueError as err2:
            normalized_fallback = [_normalize_header(h) for h in fallback_headers]
            raise ValueError(
                f"{err}; fallback_headers={fallback_headers}; "
                f"fallback_normalized={normalized_fallback}; error={err2}"
            ) from err2


def import_purchase_from_excel(
    db: Session,
    df: pd.DataFrame,
    uploaded_by: str | None = None,
) -> Dict[str, int]:
    """
    Ingest purchase Excel:
    - Store every row into purchase_raw
    - Create purchase_processed when PKB + Outlet are available
    """
    df = _maybe_promote_first_row(df)
    df, col_map = _ensure_columns(df)

    stats = {
        "raw_inserted": 0,
        "processed_inserted": 0,
        "missing_pkb": 0,
        "missing_outlet": 0,
    }

    for _, row in df.iterrows():
        row_data: Dict[str, Any] = {}
        for col_idx, model_field in col_map.items():
            row_data[model_field] = row.iloc[col_idx]

        raw = PurchaseRaw(
            site_name=normalize_name(row_data.get("site_name", "")),
            barcode=normalize_barcode(row_data.get("barcode", "")),
            supplier_name=normalize_whitespace(row_data.get("supplier_name", "")),
            hsn_code=normalize_whitespace(row_data.get("hsn_code", "")),
            division=normalize_whitespace(row_data.get("division", "")),
            section=normalize_whitespace(row_data.get("section", "")),
            department=normalize_whitespace(row_data.get("department", "")),
            article_name_raw=normalize_whitespace(row_data.get("article_name_raw", "")),
            item_name_raw=normalize_whitespace(row_data.get("item_name_raw", "")),
            name_raw=normalize_whitespace(row_data.get("name_raw", "")),
            brand_name_raw=normalize_whitespace(row_data.get("brand_name_raw", "")),
            size_raw=normalize_whitespace(row_data.get("size_raw", "")),
            pur_qty=_clean_decimal(row_data.get("pur_qty")) or Decimal("0"),
            net_amount=_clean_decimal(row_data.get("net_amount")) or Decimal("0"),
            rsp_raw=_clean_decimal(row_data.get("rsp_raw")) or Decimal("0"),
            mrp_raw=_clean_decimal(row_data.get("mrp_raw")) or Decimal("0"),
            cgst_raw=_clean_decimal(row_data.get("cgst_raw")),
            sgst_raw=_clean_decimal(row_data.get("sgst_raw")),
            cess_raw=_clean_decimal(row_data.get("cess_raw")),
            igst_raw=_clean_decimal(row_data.get("igst_raw")),
            tax_raw=_clean_decimal(row_data.get("tax_raw")),
            batch_no=normalize_whitespace(row_data.get("batch_no", "")),
            mfg_date=row_data.get("mfg_date"),
            expiry_date=row_data.get("expiry_date"),
            uploaded_by=uploaded_by,
        )
        db.add(raw)
        db.flush()
        stats["raw_inserted"] += 1

        outlet = _find_outlet(db, raw.site_name)
        if not outlet:
            stats["missing_outlet"] += 1
            continue

        product: PKBProduct | None = (
            db.query(PKBProduct)
            .filter(PKBProduct.barcode == raw.barcode)
            .first()
        )
        if not product:
            stats["missing_pkb"] += 1
            continue

        value, unit = parse_weight(raw.size_raw)
        weight_str = f"{value} {unit}" if value and unit else None

        processed = PurchaseProcessed(
            raw_id=raw.raw_id,
            outlet_id=outlet.outlet_id,
            pkb_id=product.pkb_id,
            barcode=raw.barcode,
            article_name=product.article_name or raw.article_name_raw,
            item_name=product.item_name or raw.item_name_raw,
            name=product.product_name or raw.name_raw,
            brand_name=product.brand_name or raw.brand_name_raw,
            size=weight_str or raw.size_raw,
            division=product.division or raw.division,
            section=product.section or raw.section,
            department=product.department or raw.department,
            pur_qty=raw.pur_qty,
            net_amount=raw.net_amount,
            rsp=product.rsp or raw.rsp_raw,
            mrp=product.mrp or raw.mrp_raw,
            cgst=product.cgst,
            sgst=product.sgst,
            cess=product.cess,
            igst=product.igst,
            tax=product.tax,
            processed_by=uploaded_by,
        )
        db.add(processed)
        stats["processed_inserted"] += 1

    db.commit()
    return stats
