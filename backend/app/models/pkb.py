from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class PKBProduct(Base):
    __tablename__ = "pkb_products"
    __table_args__ = (
        Index("ix_pkb_products_barcode_version", "barcode", "version", unique=True),
    )

    pkb_id = Column(Integer, primary_key=True, index=True)

    # BASE FIELDS
    remarks = Column(String(255), nullable=True)
    category_6 = Column(String(255), nullable=True)
    category_group = Column(String(50), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    barcode = Column(String(50), index=True)

    hsn_code = Column(String(50), nullable=True)

    division = Column(String(150), nullable=True)
    section = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)

    # PRODUCT NAMES
    article_name = Column(String(255), nullable=True)
    item_name = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)   # "NAME" column

    brand_name = Column(String(255), nullable=True)
    size = Column(String(100), nullable=True)
    weight = Column(String(100), nullable=True)

    # PRICING
    rsp = Column(Numeric(10, 2), nullable=True)
    mrp = Column(Numeric(10, 2), nullable=True)

    # TAXES
    cgst = Column(Numeric(10, 2), nullable=True)
    sgst = Column(Numeric(10, 2), nullable=True)
    cess = Column(Numeric(10, 2), nullable=True)
    igst = Column(Numeric(10, 2), nullable=True)
    tax = Column(Numeric(10, 4), nullable=True)         # 5% becomes 0.05

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Reverse relation (optional)
    update_logs = relationship("PKBUpdateLog", back_populates="product", cascade="all, delete-orphan")
