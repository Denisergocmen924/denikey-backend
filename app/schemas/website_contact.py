from pydantic import BaseModel, Field, EmailStr
from typing import Literal
from datetime import datetime


class WebsiteContactCreate(BaseModel):
    type: Literal["general", "business"]
    name: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=10, max_length=5000)


class WebsiteContactResponse(BaseModel):
    id: str
    type: str
    name: str
    email: str
    subject: str
    message: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
