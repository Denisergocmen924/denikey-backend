from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class SupportTicketCreate(BaseModel):
    category: Literal["bug", "suggestion", "other"]
    subject: str = Field(..., max_length=200)
    message: str = Field(..., max_length=5000)
    priority: Literal["low", "normal", "high"] = "normal"


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
