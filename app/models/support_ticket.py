from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # bug, suggestion, other
    message = Column(Text, nullable=False)
    screenshot_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")  # pending, reviewing, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())