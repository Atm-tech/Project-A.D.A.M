from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PKBBase(BaseModel):
    barcode: str
    supplier_name: str
    hsn_code: str
    division: str
    section: str
    department: str
    size: str
    rsp: Decimal
    mrp: Decimal

    class Config:
        from_attributes = True  # Pydantic v2 compatible


class PKBCreate(PKBBase):
    pass


class PKBUpdate(BaseModel):
    supplier_name: Optional[str] = None
    hsn_code: Optional[str] = None
    division: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    size: Optional[str] = None
    rsp: Optional[Decimal] = None
    mrp: Optional[Decimal] = None


class PKBOut(PKBBase):
    pkb_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
