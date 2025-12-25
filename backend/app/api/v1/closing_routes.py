import logging
from io import BytesIO
from typing import Optional, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.inventory import ClosingStock
from app.schemas.inventory import ClosingStockOut
from app.services.inventory_service import import_closing_stock_from_excel, recompute_perpetual_closing

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_ROWS = 25000
MAX_COLUMNS = 100
ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".xlsm", ".xltx", ".xltm", ".csv")


def _load_df(content: bytes, filename: str) -> pd.DataFrame:
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel/CSV files are allowed.",
        )

    if content is None or len(content) == 0:
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
    except Exception as exc:
        logger.error("Unable to read closing stock file %s: %s", filename, exc, exc_info=True)
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


@router.post(
    "/upload-excel",
    summary="Upload closing stock Excel/CSV",
    tags=["Closing Stock"],
)
async def upload_closing_stock(
    file: UploadFile = File(...),
    uploaded_by: Optional[str] = None,
    db: Session = Depends(get_db),
):
    content = await file.read()
    df = _load_df(content, file.filename)
    try:
        stats = import_closing_stock_from_excel(db, df, uploaded_by=uploaded_by)
        try:
            perpetual_stats = recompute_perpetual_closing(db, uploaded_by=uploaded_by)
        except Exception as exc:
            logger.error("Perpetual recompute after closing upload failed: %s", exc, exc_info=True)
            perpetual_stats = {"error": "Perpetual recompute failed"}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {
        "status": "success",
        "message": "Closing stock ingested.",
        **stats,
        "perpetual": perpetual_stats,
    }


@router.get(
    "/",
    response_model=List[ClosingStockOut],
    summary="List closing stock (paged)",
    tags=["Closing Stock"],
)
def list_closing_stock(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    rows = (
        db.query(ClosingStock)
        .order_by(ClosingStock.closing_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows
