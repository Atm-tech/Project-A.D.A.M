from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, func
from app.models.base import Base
from sqlalchemy.orm import relationship

class PurchaseRaw(Base):
    __tablename__ = "purchase_raw"

    raw_id = Column(Integer, primary_key=True, index=True)

    site_name = Column(String(150), nullable=False)
    barcode = Column(String(50), nullable=False)
    supplier_name = Column(String(150), nullable=False)
    hsn_code = Column(String(20), nullable=False)

    division = Column(String(100), nullable=False)
    section = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)

    article_name_raw = Column(String(255), nullable=False)
    item_name_raw = Column(String(255), nullable=False)
    name_raw = Column(String(255), nullable=False)

    brand_name_raw = Column(String(150), nullable=False)
    size_raw = Column(String(100), nullable=False)

    pur_qty = Column(Numeric(10, 3), nullable=False)
    net_amount = Column(Numeric(10, 2), nullable=False)
    rsp_raw = Column(Numeric(10, 2), nullable=False)
    mrp_raw = Column(Numeric(10, 2), nullable=False)

    cgst_raw = Column(Numeric(10, 2))
    sgst_raw = Column(Numeric(10, 2))
    cess_raw = Column(Numeric(10, 2))
    igst_raw = Column(Numeric(10, 2))
    tax_raw = Column(Numeric(10, 2))

    batch_no = Column(String(100))
    mfg_date = Column(Date)
    expiry_date = Column(Date)

    uploaded_by = Column(String(150))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PurchaseProcessed(Base):
    __tablename__ = "purchase_processed"

    purchase_id = Column(Integer, primary_key=True, index=True)
    raw_id = Column(Integer, ForeignKey("purchase_raw.raw_id"))

    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)
    pkb_id = Column(Integer, ForeignKey("pkb_products.pkb_id"), nullable=False)

    barcode = Column(String(50), nullable=False)

    article_name = Column(String(255), nullable=False)
    item_name = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    brand_name = Column(String(150), nullable=False)
    size = Column(String(100), nullable=False)

    division = Column(String(100), nullable=False)
    section = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)

    pur_qty = Column(Numeric(10, 3), nullable=False)
    net_amount = Column(Numeric(10, 2), nullable=False)
    rsp = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2), nullable=False)

    cgst = Column(Numeric(10, 2))
    sgst = Column(Numeric(10, 2))
    cess = Column(Numeric(10, 2))
    igst = Column(Numeric(10, 2))
    tax = Column(Numeric(10, 2))

    batch_no = Column(String(100))
    mfg_date = Column(Date)
    expiry_date = Column(Date)

    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_by = Column(String(150))


class PKBUpdateLog(Base):
    __tablename__ = "pkb_update_log"

    log_id = Column(Integer, primary_key=True, index=True)
    pkb_id = Column(Integer, ForeignKey("pkb_products.pkb_id"), nullable=False)

    field_name = Column(String(100), nullable=False)
    old_value = Column(String(255))
    new_value = Column(String(255))
    reason = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_by = Column(String(150))

    # Link back to the PKB product for auditability
    product = relationship("PKBProduct", back_populates="update_logs")
