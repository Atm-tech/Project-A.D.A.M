# app/services/pkb_service.py

from typing import Any, Dict
import re

import pandas as pd
from sqlalchemy.orm import Session

from app.models.pkb import PKBProduct


# -------------------------------------------------
# HEADER NORMALIZATION + MAPPING
# -------------------------------------------------

def _normalize_header(h: str) -> str:
    """
    Normalize Excel header into a stable snake_case key:
    'CAT-6' -> 'cat_6'
    """
    return (
        str(h)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


HEADER_MAP: Dict[str, str] = {
    # Remarks / categories
    "remarks": "remarks",
    "cat_6": "category_6",
    "cat6": "category_6",
    "category_6": "category_6",
    "category6": "category_6",

    # Barcode
    "barcode": "barcode",
    "bar_code": "barcode",

    # HSN
    "hsn_code": "hsn_code",
    "hsn": "hsn_code",

    # Hierarchy
    "division": "division",
    "section": "section",
    "department": "department",

    # Names
    "article_name": "article_name",
    "article": "article_name",

    "item_name": "item_name",
    "item name": "item_name",

    "brand": "brand_name",
    "brand_name": "brand_name",

    "name": "product_name",
    "product_name": "product_name",

    # Size / weight
    "size": "size",
    "weight": "weight",

    # Pricing
    "rsp": "rsp",
    "mrp": "mrp",

    # Tax
    "tax": "tax",
}

PKB_COMPARE_FIELDS = [
    "barcode",
    "category_6",
    "category_group",
    "hsn_code",
    "division",
    "section",
    "department",
    "article_name",
    "item_name",
    "product_name",
    "brand_name",
    "size",
    "weight",
    "rsp",
    "mrp",
    "cgst",
    "sgst",
    "cess",
    "igst",
    "tax",
]


# -------------------------------------------------
# VALUE CLEANERS
# -------------------------------------------------

def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def clean_value(v: Any) -> Any:
    """
    Convert NA / blanks / junk to None.
    Trim strings.
    """
    if _is_empty(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        if s.lower() in {"na", "n/a", "-", "--", "null", "none"}:
            return None
        return s
    return v


def parse_tax(value: Any):
    """
    Excel gives:
    - '5%'  -> 0.05
    - '5 %' -> 0.05
    - 5     -> 0.05
    - 0.05  -> 0.05
    """
    value = clean_value(value)
    if value is None:
        return None

    if isinstance(value, str):
        s = value.strip().replace(" ", "")
        if s.endswith("%"):
            s = s[:-1]
        try:
            return round(float(s) / 100.0, 4)
        except ValueError:
            return None

    try:
        f = float(value)
        if f > 1:
            return round(f / 100.0, 4)
        return round(f, 4)
    except Exception:
        return None


_WEIGHT_RE = re.compile(
    r"(\d+(\.\d+)?)\s*(ml|ltr|lt|l|kg|g|gm|pcs|pc|packet|pkt)",
    re.IGNORECASE,
)


def resolve_category_group(category_6: Any) -> str | None:
    """
    Map raw category text to one of the three buckets:
    - FMCG
    - Packing
    - Hyper
    """
    if category_6 is None:
        return None
    text = str(category_6).strip().lower()
    if not text:
        return None
    if "fmcg" in text:
        return "fmcg"
    if "pack" in text:
        return "packing"
    if "hyper" in text:
        return "hyper"
    return None


def _latest_by_barcode(db: Session, barcode: str) -> PKBProduct | None:
    return (
        db.query(PKBProduct)
        .filter(PKBProduct.barcode == barcode)
        .order_by(PKBProduct.version.desc(), PKBProduct.pkb_id.desc())
        .first()
    )


def _rows_differ(existing: PKBProduct, incoming: Dict[str, Any]) -> bool:
    for field in PKB_COMPARE_FIELDS:
        existing_val = getattr(existing, field, None)
        incoming_val = incoming.get(field)
        if existing_val != incoming_val:
            return True
    return False


def _deactivate_versions(db: Session, barcode: str) -> None:
    (
        db.query(PKBProduct)
        .filter(PKBProduct.barcode == barcode, PKBProduct.is_active.is_(True))
        .update({PKBProduct.is_active: False}, synchronize_session=False)
    )


def extract_weight_from_text(text: str) -> str | None:
    """
    Simple weight parser:
    'BANSAL OIL 900ML' -> '900 ML'
    'SUGAR 1KG'        -> '1 KG'
    """
    if not text:
        return None
    match = _WEIGHT_RE.search(text)
    if not match:
        return None
    num = match.group(1)
    unit = match.group(3).upper()

    # normalize units a bit
    if unit in {"LTR", "LT"}:
        unit = "L"
    if unit == "GM":
        unit = "G"
    if unit == "PKT":
        unit = "PKT"

    return f"{num} {unit}"


# -------------------------------------------------
# MAIN IMPORT FUNCTION
# -------------------------------------------------

def import_pkb_from_excel(db: Session, df: pd.DataFrame) -> Dict[str, int]:
    """
    Core PKB import engine.

    - df: pandas DataFrame created from uploaded Excel
    - Returns stats dict:
        {
            "total_rows": ...,
            "inserted": ...,
            "version_bumped": ...,
            "skipped_missing_barcode": ...,
        }
    """

    total_rows = 0
    inserted = 0
    version_bumped = 0
    skipped_missing_barcode = 0

    # Normalize headers once
    normalized_headers = [_normalize_header(col) for col in df.columns]

    # Map each col index -> model field name
    index_to_field: Dict[int, str] = {}
    for idx, norm in enumerate(normalized_headers):
        target = HEADER_MAP.get(norm)
        if target:
            index_to_field[idx] = target

    if not index_to_field:
        # No usable columns found
        return {
            "total_rows": 0,
            "inserted": 0,
            "updated": 0,
            "skipped_missing_barcode": 0,
        }

    for _, row in df.iterrows():
        total_rows += 1
        row_data: Dict[str, Any] = {}

        # Build row_data from Excel row
        for col_idx, raw_value in enumerate(row):
            target_field = index_to_field.get(col_idx)
            if not target_field:
                continue

            value = clean_value(raw_value)

            if target_field == "tax":
                value = parse_tax(value)

            row_data[target_field] = value

        # Enforce barcode as string
        barcode = row_data.get("barcode")
        if _is_empty(barcode):
            skipped_missing_barcode += 1
            continue

        barcode_str = str(barcode).strip()
        if not barcode_str or barcode_str.lower() == "nan":
            skipped_missing_barcode += 1
            continue

        row_data["barcode"] = barcode_str
        row_data["category_group"] = resolve_category_group(row_data.get("category_6"))

        # Auto weight if missing
        if not row_data.get("weight"):
            weight = None
            if row_data.get("size"):
                weight = extract_weight_from_text(row_data["size"])
            if not weight and row_data.get("article_name"):
                weight = extract_weight_from_text(row_data["article_name"])
            if weight:
                row_data["weight"] = weight

        existing = _latest_by_barcode(db, barcode_str)

        if existing:
            if _rows_differ(existing, row_data):
                _deactivate_versions(db, barcode_str)
                new_version = (existing.version or 1) + 1
                product = PKBProduct(**row_data, version=new_version, is_active=True)
                db.add(product)
                inserted += 1
                version_bumped += 1
            else:
                # Keep the latest as active
                if not existing.is_active:
                    existing.is_active = True
        else:
            product = PKBProduct(**row_data, version=1, is_active=True)
            db.add(product)
            inserted += 1

    db.commit()

    return {
        "total_rows": total_rows,
        "inserted": inserted,
        "version_bumped": version_bumped,
        "skipped_missing_barcode": skipped_missing_barcode,
    }
