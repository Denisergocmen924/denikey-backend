from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class VaultItem(Base):
    __tablename__ = "vault_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    encrypted_password = Column(Text, nullable=False)
    iv = Column(String(255), nullable=True)
    encryption_version = Column(Integer, default=1)
    notes = Column(Text, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    item_type_id = Column(UUID(as_uuid=True), ForeignKey("item_types.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(String(2048), nullable=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    is_favorite = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # İlişkiler
    custom_fields = relationship("CustomField", back_populates="vault_item", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistory", back_populates="vault_item", cascade="all, delete-orphan")