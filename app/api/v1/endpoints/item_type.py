from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.item_type_service import get_item_types

router = APIRouter(prefix="/item-types", tags=["Item Types"])

@router.get("/")
async def list_item_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_item_types(current_user.id, db)
