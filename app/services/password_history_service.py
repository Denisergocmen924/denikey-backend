from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.password_history import PasswordHistory
from app.models.vault_item import VaultItem
from app.models.user import User
from fastapi import HTTPException, status
import uuid

# Bir vault item için saklanacak maksimum geçmiş sayısı
MAX_HISTORY = 10


async def record_password_change(
    db: AsyncSession,
    vault_item: VaultItem,
    old_encrypted_password: str,
) -> None:
    """Şifre güncellendiğinde eski şifreyi geçmişe kaydet."""
    if not old_encrypted_password:
        return

    history = PasswordHistory(
        id=uuid.uuid4(),
        vault_item_id=vault_item.id,
        user_id=vault_item.user_id,
        encrypted_old_password=old_encrypted_password,
        encryption_version=vault_item.encryption_version,
    )
    db.add(history)

    # En eski kayıtları temizle (MAX_HISTORY aşıldıysa)
    result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.vault_item_id == vault_item.id)
        .order_by(PasswordHistory.changed_at.asc())
    )
    all_history = result.scalars().all()
    if len(all_history) >= MAX_HISTORY:
        for old in all_history[: len(all_history) - MAX_HISTORY + 1]:
            await db.delete(old)

    await db.flush()


async def get_password_history(
    db: AsyncSession, item_id: str, current_user: User
) -> list:
    # Vault item kullanıcıya ait mi kontrol et
    item_result = await db.execute(
        select(VaultItem).where(
            VaultItem.id == uuid.UUID(item_id),
            VaultItem.user_id == current_user.id,
        )
    )
    if not item_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")

    result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.vault_item_id == uuid.UUID(item_id))
        .order_by(PasswordHistory.changed_at.desc())
    )
    history = result.scalars().all()
    return [
        {
            "id": str(h.id),
            "encrypted_old_password": h.encrypted_old_password,
            "encryption_version": h.encryption_version,
            "changed_at": h.changed_at,
        }
        for h in history
    ]


async def clear_password_history(
    db: AsyncSession, item_id: str, current_user: User
) -> dict:
    item_result = await db.execute(
        select(VaultItem).where(
            VaultItem.id == uuid.UUID(item_id),
            VaultItem.user_id == current_user.id,
        )
    )
    if not item_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıt bulunamadı")

    result = await db.execute(
        select(PasswordHistory).where(
            PasswordHistory.vault_item_id == uuid.UUID(item_id)
        )
    )
    for h in result.scalars().all():
        await db.delete(h)
    await db.flush()
    return {"message": "Şifre geçmişi temizlendi"}
