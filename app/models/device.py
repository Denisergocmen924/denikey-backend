from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    device_type = Column(String(20), nullable=True)  # android, ios, windows, mac
    jwt_token = Column(String(500), nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(50), nullable=True)
    is_trusted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())