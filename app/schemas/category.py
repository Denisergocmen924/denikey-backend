from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CategoryCreate(BaseModel):
    name_tr: str = Field(..., max_length=100)
    name_en: str = Field(..., max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name_tr: Optional[str] = Field(None, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    name_tr: str
    name_en: str
    color: Optional[str]
    icon: Optional[str]
    is_system: bool
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True