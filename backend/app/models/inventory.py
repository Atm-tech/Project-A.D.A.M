from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, func
from app.models.base import Base


class ClosingStock(Base):
    __tablename__ = "closing_stock"

    closing_id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)
    barcode = Column(String(50), nullable=False)
    qty = Column(Numeric(12, 3), nullable=False)
    as_of_date = Column(Date, nullable=True)
    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Sale(Base):
    __tablename__ = "sales"

    sale_id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)
    barcode = Column(String(50), nullable=False)
    qty = Column(Numeric(12, 3), nullable=False)
    sale_amount = Column(Numeric(12, 2), nullable=False)
    sale_date = Column(Date, nullable=False)
    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    grt_id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)

    barcode = Column(String(50), nullable=False)
    article_name = Column(String(255), nullable=True)
    invoice_no = Column(String(100), nullable=True)
    entry_no = Column(String(100), nullable=False)
    entry_date = Column(Date, nullable=False)
    supplier_name = Column(String(150), nullable=False)
    category_6 = Column(String(150), nullable=True)

    qty = Column(Numeric(12, 3), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)

    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PerpetualClosing(Base):
    __tablename__ = "perpetual_closing"

    perpetual_id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)
    barcode = Column(String(50), nullable=False)
    qty = Column(Numeric(12, 3), nullable=False)
    as_of_date = Column(Date, nullable=True)
    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
