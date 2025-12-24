from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, UniqueConstraint
from app.models.base import Base


class AppUser(Base):
    __tablename__ = "app_users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_app_users_username"),
        UniqueConstraint("phone", name="uq_app_users_phone"),
    )

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    password = Column(String(150), nullable=False)  # plain text for now (hardcoded demo)
    role = Column(String(50), nullable=False)  # admin/manager/user
    status = Column(String(20), nullable=False, default="active")  # active/pending/rejected
    outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=True)
    requested_outlet_id = Column(Integer, ForeignKey("outlets.outlet_id"), nullable=True)
    approved_by = Column(String(150), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
