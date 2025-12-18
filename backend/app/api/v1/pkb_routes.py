# app/api/v1/pkb_routes.py

import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from io import BytesIO

import pandas as pd

from app.deps import get_db
from app.services.pkb_service import import_pkb_from_excel
from app.schemas.pkb import PKBOut
from app.models.pkb import PKBProduct

router = APIRouter()
logger = logging.getLogger(__name__)

# Thresholds to keep ingestion predictable and prevent abuse.
MAX_ROWS = 20000
MAX_COLUMNS = 200
ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xltx", ".xltm")


def validate_dataframe(df: pd.DataFrame) -> None:
    """Deterministic validation of uploaded Excel contents."""
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded Excel has no data rows.",
        )

    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded Excel exceeds row limit ({MAX_ROWS}).",
        )

    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded Excel exceeds column limit ({MAX_COLUMNS}).",
        )

    if df.columns.duplicated().any():
        dupes = [str(col) for col, dup in zip(df.columns, df.columns.duplicated()) if dup]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate column names detected: {dupes}",
        )

    unnamed = [str(col) for col in df.columns if str(col).strip() == "" or str(col).startswith("Unnamed")]
    if unnamed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column headers missing or unnamed: {unnamed}",
        )


@router.post(
    "/upload-excel",
    summary="Upload PKB master Excel",
    tags=["PKB"],
)
async def upload_pkb_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a PKB Excel file.

    Flow:
    - Validate file extension
    - Read into memory
    - Load into pandas DataFrame (all columns as string)
    - Run PKB import engine
    - Return stats
    """

    # 1) Validate extension (not super strict but enough)
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        logger.warning("Rejected upload due to invalid extension: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx / .xls / .xlsm / .xltx / .xltm) are allowed.",
        )

    # 2) Read file content
    content = await file.read()
    if not content:
        logger.warning("Rejected upload due to empty file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 3) Load into pandas as all-string to protect barcodes, HSN, etc.
    try:
        df = pd.read_excel(BytesIO(content), dtype=str)
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        validate_dataframe(df)
    except HTTPException as http_exc:
        logger.warning(
            "Validation failed for uploaded Excel %s: %s", file.filename, http_exc.detail
        )
        raise
    except Exception as e:
        logger.error("Failed to read Excel %s: %s", file.filename, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read Excel file: {e}",
        )

    # 4) Call service
    try:
        stats = import_pkb_from_excel(db, df)
    except Exception as e:
        logger.error("Error while processing PKB Excel %s: %s", file.filename, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while processing PKB Excel: {e}",
        )

    logger.info(
        "Processed PKB Excel %s with %d rows and %d columns", file.filename, len(df), len(df.columns)
    )

    return {
        "status": "success",
        "message": "PKB Excel processed successfully.",
        **stats,
    }


@router.get(
    "/products",
    response_model=list[PKBOut],
    summary="List PKB products (paged)",
    tags=["PKB"],
)
def list_pkb_products(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    items = (
        db.query(PKBProduct)
        .order_by(PKBProduct.pkb_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items
