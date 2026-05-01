from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CustomFieldCreate(BaseModel):
    field_name: str
    field_type: str
    encrypted_value: Optional[str] = None
    sort_order: int = 0

class CustomFieldResponse(BaseModel):
    id: str
    field_name: str
    field_type: str
    encrypted_value: Optional[str] = None
    sort_order: int
    model_config = {"from_attributes": True}

class CustomFieldData(BaseModel):
    field_name: str
    value: str
    field_type: str = "text"

class VaultItemCreate(BaseModel):
    title: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    encrypted_password: str
    iv: Optional[str] = None
    notes: Optional[str] = None
    url: Optional[str] = None
    category_id: Optional[str] = None
    item_type_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_favorite: bool = False
    sort_order: int = 0
    custom_fields: Optional[List[CustomFieldCreate]] = []
    custom_fields_data: Optional[List[CustomFieldData]] = []

class VaultItemUpdate(BaseModel):
    title: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    encrypted_password: Optional[str] = None
    iv: Optional[str] = None
    notes: Optional[str] = None
    url: Optional[str] = None
    category_id: Optional[str] = None
    item_type_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_favorite: Optional[bool] = None
    sort_order: Optional[int] = None
    custom_fields_data: Optional[List[CustomFieldData]] = None

class VaultItemResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    encrypted_password: str
    iv: Optional[str] = None
    encryption_version: int
    notes: Optional[str] = None
    url: Optional[str] = None
    category_id: Optional[str] = None
    item_type_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_favorite: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    custom_fields: List[CustomFieldResponse] = []
    model_config = {"from_attributes": True}
