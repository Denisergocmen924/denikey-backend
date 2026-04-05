from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.vault_item import VaultItem
from app.models.custom_field import CustomField
from app.models.trash import Trash
from app.schemas.vault_item import VaultItemCreate, VaultItemUpdate
from app.models.user import User
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import uuid


async def create_vault_item(db: AsyncSession, data: VaultItemCreate, current_user: User) -> VaultItem:
    if data.custom_fields and len(data.custom_fields) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bir kayıt için maksimum 3 özel alan eklenebilir"
        )

    item_id = uuid.uuid4()
    vault_item = VaultItem(
        id=item_id,
        user_id=current_user.id,
        title=data.title,
        username=data.username,
        email=data.email,
        phone=data.phone,
        encrypted_password=data.encrypted_password,
        iv=data.iv,
        notes=data.notes,
        category_id=uuid.UUID(data.category_id) if data.category_id else None,
        color=data.color,
        icon=data.icon,
        is_favorite=data.is_favorite,
        sort_order=data.sort_order,
    )
    db.add(vault_item)
    await db.flush()

    if data.custom_fields:
        for field in data.custom_fields:
            custom_field = CustomField(
                id=uuid.uuid4(),
                vault_item_id=item_id,
                field_name=field.field_name,
                field_type=field.field_type,
                encrypted_value=field.encrypted_value,
                sort_order=field.sort_order,
            )
            db.add(custom_field)
        await db.flush()

    result = await db.execute(
        select(VaultItem)
        .options(selectinload(VaultItem.custom_fields))
        .where(VaultItem.id == item_id)
    )
    item = result.scalar_one()
    return _serialize_item(item)


async def get_vault_items(db: AsyncSession, current_user: User) -> list:
    # Trash'tekileri filtrele
    trash_subquery = select(Trash.vault_item_id)

    result = await db.execute(
        select(VaultItem)
        .options(selectinload(VaultItem.custom_fields))
        .where(
            VaultItem.user_id == current_user.id,
            VaultItem.id.not_in(trash_subquery)
        )
        .order_by(VaultItem.sort_order, VaultItem.created_at.desc())
    )
    items = result.scalars().all()
    return [_serialize_item(i) for i in items]


async def get_vault_item(db: AsyncSession, item_id: str, current_user: User) -> VaultItem:
    result = await db.execute(
        select(VaultItem)
        .options(selectinload(VaultItem.custom_fields))
        .where(
            VaultItem.id == uuid.UUID(item_id),
            VaultItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")
    return _serialize_item(item)


async def update_vault_item(db: AsyncSession, item_id: str, data: VaultItemUpdate, current_user: User):
    result = await db.execute(
        select(VaultItem)
        .options(selectinload(VaultItem.custom_fields))
        .where(
            VaultItem.id == uuid.UUID(item_id),
            VaultItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await db.flush()
    await db.refresh(item)
    return _serialize_item(item)


async def delete_vault_item(db: AsyncSession, item_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(VaultItem)
        .where(
            VaultItem.id == uuid.UUID(item_id),
            VaultItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")

    trash = Trash(
        id=uuid.uuid4(),
        user_id=current_user.id,
        vault_item_id=item.id,
        permanent_delete_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(trash)
    await db.flush()
    return {"message": "Kayıt çöp kutusuna taşındı"}


def _serialize_item(item: VaultItem) -> dict:
    return {
        "id": str(item.id),
        "user_id": str(item.user_id),
        "title": item.title,
        "username": item.username,
        "email": item.email,
        "phone": item.phone,
        "encrypted_password": item.encrypted_password,
        "iv": item.iv,
        "encryption_version": item.encryption_version,
        "notes": item.notes,
        "category_id": str(item.category_id) if item.category_id else None,
        "color": item.color,
        "icon": item.icon,
        "is_favorite": item.is_favorite,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "custom_fields": [
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "field_type": f.field_type,
                "encrypted_value": f.encrypted_value,
                "sort_order": f.sort_order,
            }
            for f in item.custom_fields
        ],
    }
