from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.trash_service import (
    get_trash_items,
    restore_trash_item,
    delete_trash_item,
    empty_trash,
)

router = APIRouter(prefix="/trash", tags=["Trash"])


@router.get("/")
async def list_trash(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_trash_items(db, current_user)


@router.post("/{trash_id}/restore")
async def restore_item(
    trash_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await restore_trash_item(db, str(trash_id), current_user)


@router.delete("/{trash_id}")
async def delete_item(
    trash_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await delete_trash_item(db, str(trash_id), current_user)


@router.delete("/")
async def clear_trash(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await empty_trash(db, current_user)
