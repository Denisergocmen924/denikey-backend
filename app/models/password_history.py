from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vault_item_id = Column(UUID(as_uuid=True), ForeignKey("vault_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_old_password = Column(Text, nullable=False)
    encryption_version = Column(Integer, default=1)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    # İlişki
    vault_item = relationship("VaultItem", back_populates="password_history")