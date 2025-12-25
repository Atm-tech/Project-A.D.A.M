from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ClosingStockBase(BaseModel):
    barcode: str
    outlet_id: int
    qty: Decimal
    as_of_date: Optional[date] = None
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class ClosingStockOut(ClosingStockBase):
    closing_id: int
    uploaded_at: Optional[datetime] = None


class SaleBase(BaseModel):
    barcode: str
    outlet_id: int
    qty: Decimal
    sale_amount: Decimal
    sale_date: date
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class SaleOut(SaleBase):
    sale_id: int
    uploaded_at: Optional[datetime] = None


class PurchaseReturnBase(BaseModel):
    barcode: str
    article_name: Optional[str] = None
    invoice_no: Optional[str] = None
    entry_no: str
    entry_date: date
    supplier_name: str
    category_6: Optional[str] = None

    outlet_id: int
    qty: Decimal
    amount: Decimal
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseReturnOut(PurchaseReturnBase):
    grt_id: int
    uploaded_at: Optional[datetime] = None


class PerpetualClosingBase(BaseModel):
    barcode: str
    outlet_id: int
    qty: Decimal
    as_of_date: Optional[date] = None
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class PerpetualClosingOut(PerpetualClosingBase):
    perpetual_id: int
    uploaded_at: Optional[datetime] = None
