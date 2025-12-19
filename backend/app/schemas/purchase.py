from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PurchaseRawBase(BaseModel):
    site_name: str
    barcode: str
    supplier_name: str
    hsn_code: str
    division: str
    section: str
    department: str
    category_6: Optional[str] = None
    category_group: Optional[str] = None
    article_name_raw: str
    item_name_raw: str
    name_raw: str
    brand_name_raw: str
    size_raw: str
    pur_qty: Decimal
    net_amount: Decimal
    rsp_raw: Decimal
    mrp_raw: Decimal
    cgst_raw: Optional[Decimal] = None
    sgst_raw: Optional[Decimal] = None
    cess_raw: Optional[Decimal] = None
    igst_raw: Optional[Decimal] = None
    tax_raw: Optional[Decimal] = None
    batch_no: Optional[str] = None
    mfg_date: Optional[date] = None
    expiry_date: Optional[date] = None
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseRawCreate(PurchaseRawBase):
    pass


class PurchaseRawOut(PurchaseRawBase):
    raw_id: int
    uploaded_at: Optional[datetime] = None


class PurchaseProcessedOut(BaseModel):
    purchase_id: int
    barcode: str
    article_name: str
    item_name: str
    name: str
    brand_name: str
    size: str
    division: str
    section: str
    department: str
    category_6: Optional[str] = None
    category_group: Optional[str] = None
    pur_qty: Decimal
    net_amount: Decimal
    rsp: Decimal
    mrp: Decimal
    processed_at: datetime

    class Config:
        from_attributes = True
