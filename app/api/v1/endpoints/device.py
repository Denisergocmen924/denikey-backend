from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.device_service import (
    get_user_devices, revoke_device, ban_device, unban_device,
    delete_device, rename_device,
)


class DeviceRenameRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("")
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    devices = await get_user_devices(db, str(current_user.id))
    return [
        {
            "id": str(d.id),
            "device_name": d.device_name,
            "display_name": d.display_name,
            "device_type": d.device_type,
            "status": d.status,
            "last_active_at": d.last_active_at.isoformat() if d.last_active_at else None,
            "ip_address": d.ip_address,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in devices
    ]


@router.delete("/{device_id}")
async def revoke_device_endpoint(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await revoke_device(db, str(current_user.id), device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await db.commit()
    return {"message": "Cihaz oturumu sonlandırıldı"}


@router.patch("/{device_id}/ban")
async def ban_device_endpoint(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await ban_device(db, str(current_user.id), device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await db.commit()
    return {"message": "Cihaz yasaklandı"}


@router.patch("/{device_id}/unban")
async def unban_device_endpoint(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await unban_device(db, str(current_user.id), device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await db.commit()
    return {"message": "Cihaz yasağı kaldırıldı"}


@router.delete("/{device_id}/permanent")
async def delete_device_endpoint(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await delete_device(db, str(current_user.id), device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await db.commit()
    return {"message": "Cihaz silindi"}


@router.patch("/{device_id}/rename")
async def rename_device_endpoint(
    device_id: str,
    body: DeviceRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await rename_device(db, str(current_user.id), device_id, body.display_name)
    if not success:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
    await db.commit()
    return {"message": "Cihaz adı güncellendi"}
