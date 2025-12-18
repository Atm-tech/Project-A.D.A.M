from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.outlet import Outlet, OutletAlias
from app.schemas.outlet import OutletCreate
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
