from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from fastapi import HTTPException
import uuid


async def create_system_category(user_id: uuid.UUID, db: AsyncSession):
    category = Category(
        id=uuid.uuid4(),
        user_id=user_id,
        name_tr="Kategorisizler",
        name_en="Uncategorized",
        icon="inbox",
        color="#888780",
        is_system=True,
        sort_order=0,
    )
    db.add(category)
    await db.flush()


async def get_categories(user_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Category).where(
            or_(Category.user_id == user_id, Category.is_system == True)
        ).order_by(Category.sort_order)
    )
    return result.scalars().all()


async def create_category(user_id: uuid.UUID, data: CategoryCreate, db: AsyncSession):
    category = Category(user_id=user_id, **data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(user_id: uuid.UUID, category_id: uuid.UUID, data: CategoryUpdate, db: AsyncSession):
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    if category.is_system:
        raise HTTPException(status_code=403, detail="Sistem kategorileri düzenlenemez")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(user_id: uuid.UUID, category_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")
    if category.is_system:
        raise HTTPException(status_code=403, detail="Sistem kategorileri silinemez")
    await db.delete(category)
    await db.commit()
