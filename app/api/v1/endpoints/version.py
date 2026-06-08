import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.system_setting import SystemSetting
from app.core.config import settings

router = APIRouter(prefix="/version", tags=["version"])

_cache: dict = {"value": None, "at": 0.0}
_TTL = 300  # 5 dakika


def clear_version_cache() -> None:
    _cache["value"] = None
    _cache["at"] = 0.0


async def _get_min_version(db: AsyncSession) -> str:
    if _cache["value"] and time.time() - _cache["at"] < _TTL:
        return _cache["value"]
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "minimum_app_version")
    )
    setting = result.scalar_one_or_none()
    value = setting.value if setting else settings.MINIMUM_APP_VERSION
    _cache["value"] = value
    _cache["at"] = time.time()
    return value


@router.get("")
async def get_version(db: AsyncSession = Depends(get_db)):
    version = await _get_min_version(db)
    return {"minimum_version": version}
