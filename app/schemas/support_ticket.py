from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SupportTicketCreate(BaseModel):
    category: str        # bug, suggestion, other
    subject: str
    message: str
    priority: str = "normal"  # low, normal, high


class SupportTicketResponse(BaseModel):
    id: str
    user_id: str
    category: str
    subject: str
    message: str
    priority: str
    status: str
    admin_reply: Optional[str] = None
    replied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
