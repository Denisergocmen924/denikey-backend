from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import (
    string_to_salt,
    hash_master_password_for_auth,
    hash_master_password_for_auth_v1,
    hash_master_password_for_auth_v2,
    create_access_token,
    create_refresh_token,
    create_email_verify_token,
)
from app.services.audit_log_service import create_audit_log
from app.services.category_service import create_system_category
from app.services.email_service import send_verification_code, verify_code
from app.services.device_service import (
    is_device_trusted, trust_device, update_device_last_active,
    get_device_status, is_totp_trust_valid, set_totp_trust,
)
from fastapi import HTTPException
import uuid


async def register_user(db: AsyncSession, data: UserRegister, ip_address: str = None) -> dict:
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="E-posta veya telefon numarası zorunlu")

    result = await db.execute(select(User).where(User.username == data.username))
    existing_username = result.scalar_one_or_none()
    if existing_username and existing_username.is_verified:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
    if existing_username and not existing_username.is_verified:
        await db.delete(existing_username)
        await db.flush()

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_verified:
                raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")
            # Doğrulanmamış hesabı sil — cascade ile tüm bağlı veriler temizlenir
            await db.delete(existing)
            await db.flush()

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
        gender=data.gender,
        password_hash=password_hash,
        encryption_key_salt=data.encryption_key_salt,
        is_verified=False,
        auth_hash_version=2,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    if data.email:
        await send_verification_code(db, str(user.id), data.email, "register")

    await create_system_category(user.id, db)
    await create_audit_log(db=db, user_id=str(user.id), action="register", status="success", ip_address=ip_address)

    payload = {"sub": str(user.id), "username": user.username, "tv": user.token_version}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    email_verify_token = create_email_verify_token(str(user.id), "register")
    return {
        "user": user,
        "access_token": token,
        "refresh_token": refresh,
        "encryption_key_salt": user.encryption_key_salt,
        "email_verify_token": email_verify_token,
    }


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

    payload = {"sub": str(user.id), "username": user.username, "tv": user.token_version, "did": device_id or ""}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def verify_device(db: AsyncSession, user_id: str, code: str, device_id: str, device_type: str = None, display_name: str = None, ip_address: str = None) -> dict:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    is_valid = await verify_code(db, user_id, code, "new_device")
    if not is_valid:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş kod")

    device = await trust_device(db, user_id, device_id, device_type=device_type, display_name=display_name, ip_address=ip_address)
    await create_audit_log(db=db, user_id=user_id, action="device_verified", status="success", ip_address=ip_address)

    # E-posta doğrulaması 2FA yerine geçer — TOTP trust süresini başlat
    if user.totp_enabled and user.totp_trust_duration_seconds > 0:
        await set_totp_trust(db, user_id, device_id, user.totp_trust_duration_seconds)

    payload = {"sub": str(user.id), "username": user.username, "tv": user.token_version, "did": device_id}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {"access_token": token, "refresh_token": refresh, "encryption_key_salt": user.encryption_key_salt}


async def login_user(db: AsyncSession, username: str, master_password: str, device_id: str = None, device_type: str = None, display_name: str = None, ip_address: str = None) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    # Kullanıcı adıyla bulunamazsa e-posta olarak dene
    if not user:
        result = await db.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

    if user.is_locked:
        if user.lock_until and datetime.now(timezone.utc) >= user.lock_until:
            user.is_locked = False
            user.failed_attempts = 0
            user.lock_until = None
            await db.flush()
        else:
            raise HTTPException(status_code=403, detail="Hesabınız kilitlenmiştir")

    salt = string_to_salt(user.encryption_key_salt)
    hash_fn = hash_master_password_for_auth_v1 if (user.auth_hash_version or 1) == 1 else hash_master_password_for_auth_v2
    password_hash = hash_fn(master_password, salt)

    if password_hash != user.password_hash:
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.is_locked = True
            user.lock_until = datetime.now(timezone.utc) + timedelta(minutes=20)
        await db.flush()
        await create_audit_log(db=db, user_id=str(user.id), action="login_failed", status="failed", ip_address=ip_address, extra_data={"attempts": user.failed_attempts})
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")

    user.failed_attempts = 0
    if (user.auth_hash_version or 1) == 1:
        user.password_hash = hash_master_password_for_auth_v2(master_password, salt)
        user.auth_hash_version = 2
    await db.flush()

    if not user.is_verified:
        if user.email:
            await send_verification_code(db, str(user.id), user.email, "register")
        return {
            "user": user,
            "needs_email_verification": True,
            "email_verify_token": create_email_verify_token(str(user.id), "register"),
        }

    # Cihaz kontrolü
    if device_id:
        device_status = await get_device_status(db, str(user.id), device_id)
        if device_status == "banned":
            raise HTTPException(
                status_code=403,
                detail="Bu hesap için bu cihaz kullanılamıyor"
            )
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
                "email_verify_token": create_email_verify_token(str(user.id), "new_device"),
            }
        # Güvenilir cihaz — last_active_at güncelle
        await update_device_last_active(db, str(user.id), device_id)

    # TOTP aktifse cihaz güven süresi dolmamışsa atla, dolmuşsa kod iste
    if user.totp_enabled:
        totp_trusted = device_id and await is_totp_trust_valid(db, str(user.id), device_id)
        if not totp_trusted:
            from app.services.totp_service import create_totp_temp_token
            temp_token = create_totp_temp_token(str(user.id), device_id, device_type, display_name)
            await create_audit_log(db=db, user_id=str(user.id), action="login_totp_pending", status="pending", ip_address=ip_address)
            return {
                "user": user,
                "needs_totp": True,
                "totp_temp_token": temp_token,
                "needs_device_verification": False,
            }

    await create_audit_log(db=db, user_id=str(user.id), action="login_success", status="success", ip_address=ip_address)
    payload = {"sub": str(user.id), "username": user.username, "tv": user.token_version, "did": device_id or ""}
    token = create_access_token(payload)
    refresh = create_refresh_token(payload)
    return {
        "user": user,
        "access_token": token,
        "refresh_token": refresh,
        "encryption_key_salt": user.encryption_key_salt,
        "needs_device_verification": False,
        "needs_totp": False,
    }


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
    user.token_version = (user.token_version or 0) + 1
    await db.flush()
    await create_audit_log(db=db, user_id=user_id, action="email_changed", status="success")


async def update_profile(
    db: AsyncSession,
    user: User,
    username: str = None,
    full_name: str = None,
    gender: str = None,
) -> User:
    if username and username != user.username:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
        user.username = username
    if full_name is not None:
        user.full_name = full_name
    if gender is not None:
        user.gender = gender
    await db.flush()
    await db.refresh(user)
    return user


async def logout_user(db: AsyncSession, user: User) -> None:
    """Token version'ı artırarak mevcut tüm token'ları geçersiz kılar."""
    user.token_version = (user.token_version or 0) + 1
    await db.flush()
    await db.commit()


async def delete_account(db: AsyncSession, user: User, username: str, master_password: str) -> None:
    if username != user.username:
        raise HTTPException(status_code=400, detail="Kullanıcı adı hatalı")

    salt = string_to_salt(user.encryption_key_salt)
    hash_fn = hash_master_password_for_auth_v1 if (user.auth_hash_version or 1) == 1 else hash_master_password_for_auth_v2
    password_hash = hash_fn(master_password, salt)
    if password_hash != user.password_hash:
        raise HTTPException(status_code=400, detail="Şifre hatalı")

    user_email = user.email
    await db.delete(user)
    await db.flush()

    if user_email:
        from app.services.email_service import send_account_deletion_notification
        await send_account_deletion_notification(user_email)


async def resend_verification(db: AsyncSession, user_id: str, purpose: str = "register"):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if user.email:
        await send_verification_code(db, user_id, user.email, purpose)
