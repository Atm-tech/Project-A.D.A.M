from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.outlet import Outlet
from app.schemas.outlet import OutletCreate, OutletOut, OutletUpdate
from app.services.outlet_service import (
    add_alias,
    delete_alias,
    delete_outlet,
    get_outlet,
    list_outlets,
    update_outlet,
    upsert_outlet,
)

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


@router.put(
    "/{outlet_id}",
    response_model=OutletOut,
    summary="Update outlet and aliases",
)
def update_outlet_api(
    outlet_id: int,
    payload: OutletUpdate,
    db: Session = Depends(get_db),
) -> OutletOut:
    try:
        return update_outlet(db, outlet_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{outlet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete outlet",
)
def delete_outlet_api(
    outlet_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_outlet(db, outlet_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return None


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


@router.post(
    "/{outlet_id}/aliases",
    response_model=OutletOut,
    summary="Add an alias to outlet",
)
def add_alias_api(
    outlet_id: int,
    alias_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> OutletOut:
    try:
        return add_alias(db, outlet_id, alias_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/{outlet_id}/aliases/{alias_id}",
    response_model=OutletOut,
    summary="Delete an alias from outlet",
)
def delete_alias_api(
    outlet_id: int,
    alias_id: int,
    db: Session = Depends(get_db),
) -> OutletOut:
    try:
        return delete_alias(db, outlet_id, alias_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
