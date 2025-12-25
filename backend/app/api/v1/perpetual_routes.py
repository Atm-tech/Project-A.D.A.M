import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.inventory import PerpetualClosing
from app.schemas.inventory import PerpetualClosingOut
from app.services.inventory_service import recompute_perpetual_closing

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/recompute",
    summary="Recompute perpetual closing from opening + purchases - sales",
    tags=["Perpetual Closing"],
    status_code=status.HTTP_200_OK,
)
def recompute_perpetual(
    uploaded_by: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Rebuild perpetual closing table using latest closing (opening) + purchase processed - sales.
    Sales returns should be negative qty. Purchase returns to be integrated separately.
    """
    try:
        stats = recompute_perpetual_closing(db, uploaded_by=uploaded_by)
    except Exception as exc:
        logger.exception("Perpetual recompute failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Perpetual recompute failed.",
        )
    return {"status": "success", **stats}


@router.get(
    "/",
    response_model=List[PerpetualClosingOut],
    summary="List perpetual closing (paged)",
    tags=["Perpetual Closing"],
)
def list_perpetual(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    rows = (
        db.query(PerpetualClosing)
        .order_by(PerpetualClosing.perpetual_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows
