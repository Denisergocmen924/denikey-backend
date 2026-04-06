from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class ItemType(Base):
    __tablename__ = "item_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name_tr = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fields = relationship("ItemTypeField", back_populates="item_type", cascade="all, delete-orphan")


class ItemTypeField(Base):
    __tablename__ = "item_type_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_type_id = Column(UUID(as_uuid=True), ForeignKey("item_types.id", ondelete="CASCADE"), nullable=False)
    field_name_tr = Column(String(100), nullable=False)
    field_name_en = Column(String(100), nullable=False)
    field_type = Column(String(20), nullable=False)  # text, number, date, boolean, secret
    is_required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    item_type = relationship("ItemType", back_populates="fields")
