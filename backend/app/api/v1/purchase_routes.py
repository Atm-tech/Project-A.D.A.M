import logging
from io import BytesIO
from typing import Optional, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.purchase import PurchaseRaw
from app.services.purchase_service import import_purchase_from_excel
from app.schemas.purchase import PurchaseRawOut

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_ROWS = 25000
MAX_COLUMNS = 150
ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xltx", ".xltm", ".csv")


def _validate_df(df: pd.DataFrame) -> None:
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


@router.post(
    "/upload-excel",
    summary="Upload purchase data Excel/CSV",
)
async def upload_purchase_excel(
    file: UploadFile = File(...),
    uploaded_by: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel/CSV files are allowed.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(content), dtype=str)
        else:
            df = pd.read_excel(BytesIO(content), dtype=str)
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        _validate_df(df)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unable to read purchase file %s: %s", file.filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read file: {exc}",
        )

    try:
        stats = import_purchase_from_excel(db, df, uploaded_by=uploaded_by)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Error processing purchase file %s: %s", file.filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while processing purchase file: {exc}",
        )

    return {
        "status": "success",
        "message": "Purchase file processed.",
        **stats,
    }


@router.get(
    "/raw",
    response_model=List[PurchaseRawOut],
    summary="List purchase raw rows (paged)",
)
def list_purchase_raw(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    rows = (
        db.query(PurchaseRaw)
        .order_by(PurchaseRaw.raw_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows
