from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/version", tags=["version"])


@router.get("")
async def get_version():
    return {"minimum_version": settings.MINIMUM_APP_VERSION}
