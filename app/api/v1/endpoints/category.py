from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.category_service import get_categories, create_category, update_category, delete_category
from typing import List
import uuid

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_categories(current_user.id, db)


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create(data: CategoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_category(current_user.id, data, db)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update(category_id: uuid.UUID, data: CategoryUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await update_category(current_user.id, category_id, data, db)


@router.delete("/{category_id}", status_code=204)
async def delete(category_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await delete_category(current_user.id, category_id, db)