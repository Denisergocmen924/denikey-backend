from sqlalchemy import Column, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.database import Base


class WebsiteContact(Base):
    __tablename__ = "website_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(20), nullable=False)   # general, business
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="new", nullable=False)  # new, read, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
