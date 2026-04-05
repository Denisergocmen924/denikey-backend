from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import (
    string_to_salt,
    hash_master_password_for_auth,
    create_access_token
)
from fastapi import HTTPException, status
import uuid

async def register_user(db: AsyncSession, data: UserRegister) -> dict:
    if not data.email and not data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-posta veya telefon numarası zorunlu"
        )

    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kullanılıyor"
        )

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta zaten kayıtlı"
            )

    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu telefon numarası zaten kayıtlı"
            )

    # Flutter'dan gelen salt kullanılıyor
    salt = string_to_salt(data.encryption_key_salt)
    password_hash = hash_master_password_for_auth(data.master_password, salt)

    user = User(
        id=uuid.uuid4(),
        username=data.username,
        email=data.email,
        phone=data.phone,
        full_name=data.full_name,
        password_hash=password_hash,
        encryption_key_salt=data.encryption_key_salt,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return {"user": user, "access_token": token, "encryption_key_salt": user.encryption_key_salt}

async def login_user(db: AsyncSession, username: str, master_password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı"
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız kilitlenmiştir"
        )

    salt = string_to_salt(user.encryption_key_salt)
    password_hash = hash_master_password_for_auth(master_password, salt)

    if password_hash != user.password_hash:
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.is_locked = True
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı"
        )

    user.failed_attempts = 0
    await db.flush()

    token = create_access_token({"sub": str(user.id), "username": user.username})
    return {"user": user, "access_token": token, "encryption_key_salt": user.encryption_key_salt}
