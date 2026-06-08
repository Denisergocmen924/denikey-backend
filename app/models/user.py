from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    encryption_key_salt = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    preferred_language = Column(String(10), default="tr")
    preferred_theme = Column(String(20), default="system")
    is_verified = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    failed_attempts = Column(Integer, default=0)
    token_version = Column(Integer, default=0, nullable=False, server_default="0")
    auth_hash_version = Column(Integer, default=1, nullable=False, server_default="1")
    lock_until = Column(DateTime(timezone=True), nullable=True)
    totp_secret = Column(Text, nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    totp_trust_duration_seconds = Column(Integer, default=0, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())