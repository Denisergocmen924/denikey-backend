from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.trash import Trash
from app.models.vault_item import VaultItem
from app.models.user import User
import uuid


async def get_trash_items(db: AsyncSession, current_user: User) -> list:
    result = await db.execute(
        select(Trash, VaultItem)
        .join(VaultItem, Trash.vault_item_id == VaultItem.id)
        .options(selectinload(VaultItem.custom_fields))
        .where(Trash.user_id == current_user.id)
        .order_by(Trash.deleted_at.desc())
    )
    rows = result.all()
    return [
        {
            "trash_id": str(t.id),
            "deleted_at": t.deleted_at,
            "permanent_delete_at": t.permanent_delete_at,
            "item": {
                "id": str(v.id),
                "title": v.title,
                "encrypted_password": v.encrypted_password,
                "iv": v.iv,
                "category_id": str(v.category_id) if v.category_id else None,
                "item_type_id": str(v.item_type_id) if v.item_type_id else None,
                "icon": v.icon,
                "color": v.color,
                "custom_fields": [
                    {
                        "id": str(f.id),
                        "field_name": f.field_name,
                        "field_type": f.field_type,
                        "encrypted_value": f.encrypted_value,
                        "sort_order": f.sort_order,
                    }
                    for f in v.custom_fields
                ],
            },
        }
        for t, v in rows
    ]


async def restore_trash_item(db: AsyncSession, trash_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(Trash).where(
            Trash.id == uuid.UUID(trash_id),
            Trash.user_id == current_user.id,
        )
    )
    trash = result.scalar_one_or_none()
    if not trash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğe bulunamadı")

    await db.delete(trash)
    await db.flush()
    return {"message": "Öğe geri yüklendi"}


async def delete_trash_item(db: AsyncSession, trash_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(Trash).where(
            Trash.id == uuid.UUID(trash_id),
            Trash.user_id == current_user.id,
        )
    )
    trash = result.scalar_one_or_none()
    if not trash:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğe bulunamadı")

    # Vault item'ı da kalıcı sil
    item_result = await db.execute(
        select(VaultItem).where(VaultItem.id == trash.vault_item_id)
    )
    item = item_result.scalar_one_or_none()
    if item:
        await db.delete(item)

    await db.delete(trash)
    await db.flush()
    return {"message": "Öğe kalıcı olarak silindi"}


async def empty_trash(db: AsyncSession, current_user: User) -> dict:
    result = await db.execute(
        select(Trash).where(Trash.user_id == current_user.id)
    )
    trash_items = result.scalars().all()

    for trash in trash_items:
        item_result = await db.execute(
            select(VaultItem).where(VaultItem.id == trash.vault_item_id)
        )
        item = item_result.scalar_one_or_none()
        if item:
            await db.delete(item)
        await db.delete(trash)

    await db.flush()
    return {"message": f"{len(trash_items)} öğe kalıcı olarak silindi"}
