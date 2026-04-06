from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from fastapi import HTTPException
import uuid

SYSTEM_CATEGORIES = [
    {"name_tr": "Kategorisizler", "name_en": "Uncategorized", "icon": "inbox", "color": "#888780", "sort_order": 0},
    {"name_tr": "Sosyal Medya", "name_en": "Social Media", "icon": "people", "color": "#534AB7", "sort_order": 1},
    {"name_tr": "Oyunlar", "name_en": "Games", "icon": "games", "color": "#993C1D", "sort_order": 2},
    {"name_tr": "Bankacılık", "name_en": "Banking", "icon": "account_balance", "color": "#185FA5", "sort_order": 3},
    {"name_tr": "E-posta", "name_en": "Email", "icon": "email", "color": "#0F6E56", "sort_order": 4},
    {"name_tr": "İş", "name_en": "Work", "icon": "work", "color": "#854F0B", "sort_order": 5},
    {"name_tr": "Alışveriş", "name_en": "Shopping", "icon": "shopping_cart", "color": "#993556", "sort_order": 6},
]


async def create_default_categories(user_id: uuid.UUID, db: AsyncSession):
    for cat in SYSTEM_CATEGORIES:
        category = Category(
            id=uuid.uuid4(),
            user_id=user_id,
            name_tr=cat["name_tr"],
            name_en=cat["name_en"],
            icon=cat["icon"],
            color=cat["color"],
            is_system=False,
            sort_order=cat["sort_order"],
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
        raise HTTPException(status_code=404, detail="Category not found")
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
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(category)
    await db.commit()
