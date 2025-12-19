from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PKBBase(BaseModel):
    barcode: str
    hsn_code: Optional[str] = None
    division: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    article_name: Optional[str] = None
    item_name: Optional[str] = None
    product_name: Optional[str] = None
    brand_name: Optional[str] = None
    size: Optional[str] = None
    weight: Optional[str] = None
    rsp: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    cgst: Optional[Decimal] = None
    sgst: Optional[Decimal] = None
    cess: Optional[Decimal] = None
    igst: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    remarks: Optional[str] = None
    category_6: Optional[str] = None
    category_group: Optional[str] = None
    version: Optional[int] = 1
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True  # Pydantic v2 compatible


class PKBCreate(PKBBase):
    pass


class PKBUpdate(BaseModel):
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
