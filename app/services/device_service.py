from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.device import Device
import uuid


async def is_device_trusted(db: AsyncSession, user_id: str, device_id: str) -> bool:
    result = await db.execute(
        select(Device).where(
            Device.user_id == uuid.UUID(user_id),
            Device.device_name == device_id,
            Device.is_trusted == True,
        )
    )
    return result.scalar_one_or_none() is not None


async def trust_device(db: AsyncSession, user_id: str, device_id: str, device_type: str = None, ip_address: str = None):
    device = Device(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        device_name=device_id,
        device_type=device_type,
        is_trusted=True,
        ip_address=ip_address,
    )
    db.add(device)
    await db.flush()
