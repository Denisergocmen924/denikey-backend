from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.item_type_service import get_item_types, create_item_type, delete_item_type, update_item_type
from pydantic import BaseModel, Field
from typing import Optional
import uuid

router = APIRouter(prefix="/item-types", tags=["Item Types"])


class ItemTypeFieldCreate(BaseModel):
    field_name: str = Field(..., max_length=100)
    field_type: str = Field("text", max_length=20)   # text | secret | number | date | boolean
    is_required: bool = False


class ItemTypeCreate(BaseModel):
    name_tr: str = Field(..., max_length=100)
    icon: Optional[str] = Field("category", max_length=50)
    color: Optional[str] = Field("#534AB7", max_length=20)
    fields: Optional[list[ItemTypeFieldCreate]] = None


@router.get("/")
async def list_item_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_item_types(current_user.id, db)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_item_type(
    data: ItemTypeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await create_item_type(current_user.id, data.model_dump(), db)
    await db.commit()
    return result


class FieldNameUpdate(BaseModel):
    id: str
    field_name: str = Field(..., max_length=100)


class NewFieldCreate(BaseModel):
    field_name: str = Field(..., max_length=100)
    field_type: str = Field("text", max_length=20)


class ItemTypeUpdate(BaseModel):
    name_tr: Optional[str] = Field(None, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    fields: Optional[list[FieldNameUpdate]] = None
    new_fields: Optional[list[NewFieldCreate]] = None


@router.patch("/{item_type_id}")
async def edit_item_type(
    item_type_id: uuid.UUID,
    data: ItemTypeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await update_item_type(current_user.id, str(item_type_id), data.model_dump(exclude_none=True), db)
    await db.commit()
    return result


@router.delete("/{item_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_type(
    item_type_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_item_type(current_user.id, str(item_type_id), db)
    await db.commit()
