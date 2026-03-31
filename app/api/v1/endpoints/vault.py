from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.vault_item import VaultItemCreate, VaultItemUpdate, VaultItemResponse
from app.services.vault_service import (
    create_vault_item,
    get_vault_items,
    get_vault_item,
    update_vault_item,
    delete_vault_item
)

router = APIRouter(prefix="/vault", tags=["Vault"])


@router.post("/items", response_model=VaultItemResponse)
async def create_item(
    data: VaultItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await create_vault_item(db, data, current_user)


@router.get("/items", response_model=List[VaultItemResponse])
async def list_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_vault_items(db, current_user)


@router.get("/items/{item_id}", response_model=VaultItemResponse)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await get_vault_item(db, item_id, current_user)


@router.put("/items/{item_id}", response_model=VaultItemResponse)
async def update_item(
    item_id: str,
    data: VaultItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await update_vault_item(db, item_id, data, current_user)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await delete_vault_item(db, item_id, current_user)