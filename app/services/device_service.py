from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from app.models.device import Device
import uuid


async def is_device_trusted(db: AsyncSession, user_id: str, device_id: str) -> bool:
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
            Device.is_trusted == True,
            Device.status != "banned",
        )
    )
    return result.scalar_one_or_none() is not None


async def trust_device(
    db: AsyncSession,
    user_id: str,
    device_id: str,
    device_type: str = None,
    display_name: str = None,
    ip_address: str = None,
) -> Device:
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
        )
    )
    device = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if device:
        device.is_trusted = True
        device.status = "active"
        device.last_active_at = now
        if device_type:
            device.device_type = device_type
        if display_name:
            device.display_name = display_name
        if ip_address:
            device.ip_address = ip_address
    else:
        device = Device(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            device_name=device_id,
            display_name=display_name,
            device_type=device_type,
            is_trusted=True,
            status="active",
            ip_address=ip_address,
            last_active_at=now,
        )
        db.add(device)

    await db.flush()
    return device


async def update_device_last_active(db: AsyncSession, user_id: str, device_id: str) -> None:
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
        )
    )
    device = result.scalar_one_or_none()
    if device:
        device.last_active_at = datetime.now(timezone.utc)
        await db.flush()


async def get_device_status(db: AsyncSession, user_id: str, device_id: str) -> str | None:
    """Cihazın mevcut durumunu döndürür. Cihaz bulunamazsa None."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
        )
    )
    device = result.scalar_one_or_none()
    return device.status if device else None


async def check_and_update_device(db: AsyncSession, user_id: str, device_id: str) -> str | None:
    """Tek sorguda cihaz durumunu kontrol eder; aktifse last_active günceller."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return None
    if device.status not in ("revoked", "banned"):
        device.last_active_at = datetime.now(timezone.utc)
        await db.flush()
    return device.status


async def get_user_devices(db: AsyncSession, user_id: str) -> list[Device]:
    result = await db.execute(
        select(Device)
        .where(Device.user_id == uuid.UUID(user_id))
        .order_by(Device.last_active_at.desc().nullslast())
    )
    return list(result.scalars().all())


async def revoke_device(db: AsyncSession, user_id: str, device_id: str) -> bool:
    """Cihazın oturumunu sonlandırır (revoked). Tekrar giriş yapabilir ama doğrulama gerekir."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.id == uuid.UUID(device_id),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    device.status = "revoked"
    device.is_trusted = False
    await db.flush()
    return True


async def ban_device(db: AsyncSession, user_id: str, device_id: str) -> bool:
    """Cihazı yasaklar (banned). Tekrar giriş yapsa bile doğrulama kodu gönderilir."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.id == uuid.UUID(device_id),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    device.status = "banned"
    device.is_trusted = False
    await db.flush()
    return True


async def unban_device(db: AsyncSession, user_id: str, device_id: str) -> bool:
    """Cihaz yasağını kaldırır — durumu active, is_trusted=True yapar."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.id == uuid.UUID(device_id),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    device.status = "active"
    device.is_trusted = True
    await db.flush()
    return True


async def is_totp_trust_valid(db: AsyncSession, user_id: str, device_id: str) -> bool:
    """Cihazın TOTP güven süresi hâlâ geçerliyse True döndürür."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
            Device.status == "active",
        )
    )
    device = result.scalar_one_or_none()
    if not device or not device.totp_trusted_until:
        return False
    return device.totp_trusted_until > datetime.now(timezone.utc)


async def delete_device(db: AsyncSession, user_id: str, device_id: str) -> bool:
    """Cihazı kalıcı olarak siler."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.id == uuid.UUID(device_id),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    await db.delete(device)
    await db.flush()
    return True


async def rename_device(db: AsyncSession, user_id: str, device_id: str, display_name: str) -> bool:
    """Cihaz görünen adını günceller."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.id == uuid.UUID(device_id),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        return False
    device.display_name = display_name.strip()[:100]
    await db.flush()
    return True


async def set_totp_trust(
    db: AsyncSession, user_id: str, device_id: str, duration_seconds: int
) -> None:
    """Başarılı TOTP doğrulamasının ardından cihaza güven süresi atar. duration_seconds=0 ise trust temizlenir."""
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
        )
    )
    device = result.scalar_one_or_none()
    if device:
        if duration_seconds <= 0:
            device.totp_trusted_until = None
        else:
            device.totp_trusted_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        await db.flush()
