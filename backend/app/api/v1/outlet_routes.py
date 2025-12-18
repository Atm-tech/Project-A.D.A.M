from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.outlet import Outlet
from app.schemas.outlet import OutletCreate, OutletOut
from app.services.outlet_service import list_outlets, upsert_outlet

router = APIRouter()


@router.post(
    "",
    response_model=OutletOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an outlet with optional aliases",
)
def create_outlet(payload: OutletCreate, db: Session = Depends(get_db)) -> OutletOut:
    outlet = upsert_outlet(db, payload)
    return outlet


@router.get(
    "",
    response_model=List[OutletOut],
    summary="List outlets",
)
def list_outlets_api(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[OutletOut]:
    return list_outlets(db, limit=limit, offset=offset)


@router.get(
    "/search",
    response_model=List[OutletOut],
    summary="Search outlets by name or alias",
)
def search_outlets(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
) -> List[OutletOut]:
    query = (
        db.query(Outlet)
        .filter(func.upper(Outlet.outlet_name).like(f"%{q.upper()}%"))
        .order_by(Outlet.created_at.desc())
    )
    results = query.all()
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No outlets found")
    return results
