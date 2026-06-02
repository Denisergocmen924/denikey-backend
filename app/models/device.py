from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(255), nullable=True, index=True)  # istemci UUID'si (benzersiz tanımlayıcı)
    display_name = Column(String(100), nullable=True)             # okunabilir isim: "Samsung Galaxy S21"
    device_type = Column(String(20), nullable=True)               # android, ios, windows, macos, linux
    status = Column(String(20), nullable=False, default="active") # active | revoked | banned
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(50), nullable=True)
    is_trusted = Column(Boolean, default=False)
    totp_trusted_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())