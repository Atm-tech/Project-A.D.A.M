from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.outlet import Outlet, OutletAlias
from app.schemas.outlet import OutletCreate, OutletUpdate
from app.utils.text_cleaner import normalize_name


def _find_outlet_by_name_or_alias(db: Session, name: str) -> Optional[Outlet]:
    """Lookup outlet by canonical name or alias."""
    norm = normalize_name(name)
    outlet = (
        db.query(Outlet)
        .filter(func.upper(Outlet.outlet_name) == norm)
        .first()
    )
    if outlet:
        return outlet
    alias = (
        db.query(OutletAlias)
        .filter(func.upper(OutletAlias.alias_name) == norm)
        .first()
    )
    return alias.outlet if alias else None


def upsert_outlet(db: Session, payload: OutletCreate) -> Outlet:
    """
    Create or update an outlet. Aliases are attached if provided.
    """
    outlet = _find_outlet_by_name_or_alias(db, payload.outlet_name)
    if outlet:
        outlet.city = payload.city
        outlet.state = payload.state
        outlet.is_active = payload.is_active
    else:
        outlet = Outlet(
            outlet_name=normalize_name(payload.outlet_name),
            city=payload.city,
            state=payload.state,
            is_active=payload.is_active,
        )
        db.add(outlet)
        db.flush()

    # Attach aliases
    existing_aliases = {normalize_name(a.alias_name) for a in outlet.aliases}
    for alias in payload.aliases:
        norm_alias = normalize_name(alias)
        if norm_alias in existing_aliases:
            continue
        outlet.aliases.append(
            OutletAlias(alias_name=norm_alias, outlet_id=outlet.outlet_id)
        )
        existing_aliases.add(norm_alias)

    db.commit()
    db.refresh(outlet)
    return outlet


def list_outlets(db: Session, limit: int = 50, offset: int = 0) -> List[Outlet]:
    return (
        db.query(Outlet)
        .order_by(Outlet.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_outlet(db: Session, outlet_id: int) -> Outlet:
    outlet = db.query(Outlet).filter(Outlet.outlet_id == outlet_id).first()
    if not outlet:
        raise ValueError("Outlet not found")
    return outlet


def update_outlet(db: Session, outlet_id: int, payload: OutletUpdate) -> Outlet:
    outlet = get_outlet(db, outlet_id)
    outlet.outlet_name = normalize_name(payload.outlet_name)
    outlet.city = payload.city
    outlet.state = payload.state
    outlet.is_active = payload.is_active

    if payload.aliases is not None:
        new_aliases = {normalize_name(a) for a in payload.aliases if a}
        outlet.aliases.clear()
        for alias in new_aliases:
            outlet.aliases.append(OutletAlias(alias_name=alias, outlet_id=outlet.outlet_id))

    db.commit()
    db.refresh(outlet)
    return outlet


def delete_outlet(db: Session, outlet_id: int) -> None:
    outlet = get_outlet(db, outlet_id)
    db.delete(outlet)
    db.commit()


def add_alias(db: Session, outlet_id: int, alias_name: str) -> Outlet:
    outlet = get_outlet(db, outlet_id)
    norm = normalize_name(alias_name)
    existing = {normalize_name(a.alias_name) for a in outlet.aliases}
    if norm not in existing:
        outlet.aliases.append(OutletAlias(alias_name=norm, outlet_id=outlet.outlet_id))
        db.commit()
        db.refresh(outlet)
    return outlet


def delete_alias(db: Session, outlet_id: int, alias_id: int) -> Outlet:
    outlet = get_outlet(db, outlet_id)
    alias = next((a for a in outlet.aliases if a.alias_id == alias_id), None)
    if not alias:
        raise ValueError("Alias not found for outlet")
    db.delete(alias)
    db.commit()
    db.refresh(outlet)
    return outlet
