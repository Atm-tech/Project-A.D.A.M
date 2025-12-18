from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Outlet(Base):
    __tablename__ = "outlets"

    outlet_id = Column(Integer, primary_key=True, index=True)
    outlet_name = Column(String(150), unique=True, nullable=False)
    city = Column(String(100))
    state = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    aliases = relationship("OutletAlias", back_populates="outlet")


class OutletAlias(Base):
    __tablename__ = "outlet_aliases"

    alias_id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=False)
    alias_name = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    outlet = relationship("Outlet", back_populates="aliases")
