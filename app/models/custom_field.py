from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_item_id = Column(UUID(as_uuid=True), ForeignKey("vault_items.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(20), nullable=False)  # text, number, date
    encrypted_value = Column(Text, nullable=True)
    encryption_version = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # İlişki
    vault_item = relationship("VaultItem", back_populates="custom_fields")