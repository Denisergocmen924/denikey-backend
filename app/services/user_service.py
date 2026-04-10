from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import (
    string_to_salt,
    hash_master_password_for_auth,
    create_access_token,
    create_refresh_token,
)
from app.services.audit_log_service import create_audit_log
from app.services.category_service import create_default_categories
from app.services.email_service import send_verification_code, verify_code
from app.services.device_service import is_device_trusted, trust_device
from fastapi import HTTPException
import uuid


async def register_user(db: AsyncSession, data: UserRegister, ip_address: str = None) -> dict:
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="E-posta veya telefon numarası zorunlu")

    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")

    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu telefon numarası zaten kayıtlı")

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
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    if data.email:
        await send_verification_code(db, str(user.id), data.email, "register")

    await create_default_categories(user.id, db)
    await create_audit_log(db=db, user_id=str(user.id), action="register", status="success", ip_address=ip_address)

    payload = {"sub": str(user.id), "username": user.username}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"user": user, "access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def verify_email(db: AsyncSession, user_id: str, code: str, device_id: str = None, device_type: str = None, ip_address: str = None) -> dict:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    is_valid = await verify_code(db, user_id, code, "register")
    if not is_valid:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    user.is_verified = True
    await db.flush()

    if device_id:
        await trust_device(db, user_id, device_id, device_type=device_type, ip_address=ip_address)

    payload = {"sub": str(user.id), "username": user.username}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def verify_device(db: AsyncSession, user_id: str, code: str, device_id: str, device_type: str = None, ip_address: str = None) -> dict:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    is_valid = await verify_code(db, user_id, code, "new_device")
    if not is_valid:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    await trust_device(db, user_id, device_id, device_type=device_type, ip_address=ip_address)
    await create_audit_log(db=db, user_id=user_id, action="device_verified", status="success", ip_address=ip_address)

    payload = {"sub": str(user.id), "username": user.username}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def login_user(db: AsyncSession, username: str, master_password: str, device_id: str = None, device_type: str = None, ip_address: str = None) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

    if user.is_locked:
        raise HTTPException(status_code=403, detail="Hesabınız kilitlenmiştir")

    salt = string_to_salt(user.encryption_key_salt)
    password_hash = hash_master_password_for_auth(master_password, salt)

    if password_hash != user.password_hash:
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.is_locked = True
        await db.flush()
        await create_audit_log(db=db, user_id=str(user.id), action="login_failed", status="failed", ip_address=ip_address, extra_data={"attempts": user.failed_attempts})
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

    user.failed_attempts = 0
    await db.flush()

    # Cihaz kontrolü
    if device_id:
        trusted = await is_device_trusted(db, str(user.id), device_id)
        if not trusted:
            if user.email:
                await send_verification_code(db, str(user.id), user.email, "new_device")
            await create_audit_log(db=db, user_id=str(user.id), action="login_new_device", status="pending", ip_address=ip_address)
            return {
                "user": user,
                "access_token": None,
                "encryption_key_salt": user.encryption_key_salt,
                "needs_device_verification": True,
            }

    await create_audit_log(db=db, user_id=str(user.id), action="login_success", status="success", ip_address=ip_address)
    payload = {"sub": str(user.id), "username": user.username}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {
        "user": user,
        "access_token": token,
        "refresh_token": refresh,
        "encryption_key_salt": user.encryption_key_salt,
        "needs_device_verification": False,
    }


async def forgot_password(db: AsyncSession, email: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        # Güvenlik için aynı mesajı döndür
        return {"user_id": None, "sent": False}

    await send_verification_code(db, str(user.id), email, "forgot_password")
    return {"user_id": str(user.id), "sent": True}


async def reset_password(db: AsyncSession, user_id: str, code: str, new_master_password: str, new_encryption_key_salt: str) -> dict:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    is_valid = await verify_code(db, user_id, code, "forgot_password")
    if not is_valid:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    salt = string_to_salt(new_encryption_key_salt)
    user.password_hash = hash_master_password_for_auth(new_master_password, salt)
    user.encryption_key_salt = new_encryption_key_salt
    user.failed_attempts = 0
    user.is_locked = False
    await db.flush()

    await create_audit_log(db=db, user_id=user_id, action="password_reset", status="success")

    payload = {"sub": str(user.id), "username": user.username}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def change_email_request(db: AsyncSession, user_id: str, new_email: str) -> None:
    # Yeni email başka hesapta var mı?
    result = await db.execute(select(User).where(User.email == new_email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kullanılıyor")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    # Yeni adrese doğrulama kodu gönder
    await send_verification_code(db, user_id, new_email, "email_change")

    # Eski adrese bilgilendirme
    if user.email:
        from app.services.email_service import send_email_change_notification
        await send_email_change_notification(user.email)


async def change_email_confirm(db: AsyncSession, user_id: str, code: str, new_email: str) -> None:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    is_valid = await verify_code(db, user_id, code, "email_change")
    if not is_valid:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    user.email = new_email
    await db.flush()
    await create_audit_log(db=db, user_id=user_id, action="email_changed", status="success")


async def resend_verification(db: AsyncSession, user_id: str):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if user.email:
        await send_verification_code(db, user_id, user.email, "register")
