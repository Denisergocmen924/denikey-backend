from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class Trash(Base):
    __tablename__ = "trash"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vault_item_id = Column(UUID(as_uuid=True), ForeignKey("vault_items.id", ondelete="CASCADE"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    permanent_delete_at = Column(DateTime(timezone=True), nullable=False)