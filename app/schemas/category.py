from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class CategoryCreate(BaseModel):
    name_tr: str
    name_en: str
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name_tr: Optional[str] = None
    name_en: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
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