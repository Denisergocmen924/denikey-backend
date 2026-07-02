from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.database import get_db
from app.schemas.user import (
    UserRegister, UserLogin, UserResponse, TokenResponse, UserProfileUpdate,
    LoginSaltRequest, LoginSaltResponse,
)
from app.services.user_service import (
    register_user, login_user, verify_email, verify_device,
    resend_verification,
    change_email_request, change_email_confirm, update_profile, logout_user,
    delete_account, get_login_salt,
)
from app.core.dependencies import get_current_user, get_current_device_id
from app.core.security import verify_refresh_token, create_access_token, create_refresh_token
from app.models.user import User
from app.db.database import get_db
from sqlalchemy import select
import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


class VerifyEmailRequest(BaseModel):
    user_id: uuid.UUID
    code: str
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class ResendVerificationRequest(BaseModel):
    temp_token: str

class VerifyDeviceRequest(BaseModel):
    user_id: uuid.UUID
    code: str
    device_id: str
    device_type: Optional[str] = None
    device_name: Optional[str] = None

class ChangeEmailRequest(BaseModel):
    new_email: str

class ConfirmEmailChangeRequest(BaseModel):
    code: str
    new_email: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class DeleteAccountRequest(BaseModel):
    username: str
    auth_verifier: str

class TotpEnableRequest(BaseModel):
    secret: str
    code: str

class TotpDisableRequest(BaseModel):
    auth_verifier: str
    totp_code: str

class TotpVerifyLoginRequest(BaseModel):
    temp_token: str
    code: str

class TotpTrustDurationRequest(BaseModel):
    duration_seconds: int

class TotpVerifyUnlockRequest(BaseModel):
    code: str


@router.post("/register")
@limiter.limit("5/minute")
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await register_user(db, data, ip_address=ip)
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": "bearer",
        "encryption_key_salt": result["encryption_key_salt"],
        "email_verify_token": result["email_verify_token"],
        "user": {
            "id": str(result["user"].id),
            "username": result["user"].username,
            "email": result["user"].email,
            "full_name": result["user"].full_name,
            "preferred_language": result["user"].preferred_language,
            "preferred_theme": result["user"].preferred_theme,
        }
    }


@router.post("/login-salt", response_model=LoginSaltResponse)
@limiter.limit("10/minute")
async def login_salt(data: LoginSaltRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Login'in 1. adımı: istemci verifier'ı türetebilsin diye salt döner.
    Var olmayan kullanıcıda sahte-tutarlı salt → username enumeration engellenir."""
    salt = await get_login_salt(db, data.username)
    return {"encryption_key_salt": salt}


@router.post("/login")
@limiter.limit("10/minute")
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await login_user(
        db,
        data.username,
        data.auth_verifier,
        device_id=data.device_id,
        device_type=data.device_type,
        display_name=data.device_name,
        ip_address=ip,
    )
    if result.get("needs_email_verification"):
        return {
            "needs_email_verification": True,
            "user_id": str(result["user"].id),
            "email": result["user"].email,
            "email_verify_token": result["email_verify_token"],
        }
    if result.get("needs_device_verification"):
        return {
            "needs_device_verification": True,
            "needs_totp": False,
            "user_id": str(result["user"].id),
            "email": result["user"].email,
            "email_verify_token": result["email_verify_token"],
        }
    if result.get("needs_totp"):
        return {
            "needs_device_verification": False,
            "needs_totp": True,
            "totp_temp_token": result["totp_temp_token"],
        }
    return {
        "needs_device_verification": False,
        "needs_totp": False,
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "encryption_key_salt": result["encryption_key_salt"],
        "user": {
            "id": str(result["user"].id),
            "username": result["user"].username,
            "email": result["user"].email,
            "full_name": result["user"].full_name,
            "preferred_language": result["user"].preferred_language,
            "preferred_theme": result["user"].preferred_theme,
        }
    }


@router.post("/verify-email")
@limiter.limit("5/minute")
async def verify_email_endpoint(data: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await verify_email(db, str(data.user_id), data.code, device_id=data.device_id, device_type=data.device_type, ip_address=ip)
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "encryption_key_salt": result["encryption_key_salt"],
    }


@router.post("/verify-device")
@limiter.limit("5/minute")
async def verify_device_endpoint(data: VerifyDeviceRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await verify_device(db, str(data.user_id), data.code, data.device_id, device_type=data.device_type, display_name=data.device_name, ip_address=ip)
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "encryption_key_salt": result["encryption_key_salt"],
    }


@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh_token(request: Request, data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException, status
    payload = verify_refresh_token(data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş refresh token",
        )

    user_id = payload.get("sub")
    token_version = payload.get("tv")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya hesap kilitli",
        )

    # Logout sonrası refresh token geçersizleştirme kontrolü
    if token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum sonlandırılmış, lütfen tekrar giriş yapın",
        )

    device_id = payload.get("did", "")
    if device_id:
        from app.services.device_service import get_device_status
        device_status = await get_device_status(db, user_id, device_id)
        # None = cihaz kalıcı silinmiş; refresh'i reddet (süresiz token yenilemeyi engeller)
        if device_status is None or device_status in ("revoked", "banned"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bu cihazın oturumu sonlandırılmış, lütfen tekrar giriş yapın",
            )

    token_payload = {"sub": str(user.id), "username": user.username, "tv": user.token_version, "did": device_id}
    new_access = create_access_token(token_payload)
    new_refresh = create_refresh_token(token_payload)
    return {"access_token": new_access, "refresh_token": new_refresh}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification_endpoint(request: Request, data: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    from app.core.security import verify_email_verify_token
    payload = verify_email_verify_token(data.temp_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")
    user_id = payload["sub"]
    purpose = payload.get("purpose", "register")
    await resend_verification(db, user_id, purpose)
    return {"message": "Doğrulama kodu tekrar gönderildi"}


@router.post("/change-email")
async def change_email_endpoint(
    data: ChangeEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await change_email_request(db, str(current_user.id), data.new_email)
    return {"message": "Doğrulama kodu yeni e-posta adresinize gönderildi"}


@router.post("/confirm-email-change")
async def confirm_email_change_endpoint(
    data: ConfirmEmailChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await change_email_confirm(db, str(current_user.id), data.code, data.new_email)
    return {"message": "E-posta adresiniz başarıyla güncellendi"}


@router.put("/profile")
async def update_profile_endpoint(
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await update_profile(db, current_user, username=data.username, full_name=data.full_name)
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
    }


@router.get("/profile")
async def get_profile_endpoint(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }


@router.delete("/delete-account")
async def delete_account_endpoint(
    data: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await delete_account(db, current_user, data.username, data.auth_verifier)
    return {"message": "Hesabınız kalıcı olarak silindi"}


@router.post("/logout")
async def logout_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mevcut tüm access ve refresh token'ları geçersiz kılar."""
    await logout_user(db, current_user)
    return {"message": "Başarıyla çıkış yapıldı"}


# ── TOTP Endpoint'leri ─────────────────────────────────────────────────────────

@router.get("/totp/status")
async def totp_status(current_user: User = Depends(get_current_user)):
    return {
        "totp_enabled": current_user.totp_enabled,
        "totp_trust_duration_seconds": current_user.totp_trust_duration_seconds,
    }


@router.put("/totp/trust-duration")
@limiter.limit("10/minute")
async def totp_set_trust_duration(
    data: TotpTrustDurationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    allowed = {0, 43200, 86400, 604800, 2592000, 5184000}
    if data.duration_seconds not in allowed:
        raise HTTPException(status_code=400, detail="Geçersiz süre değeri")
    current_user.totp_trust_duration_seconds = data.duration_seconds
    # "Her seferinde" seçilince mevcut cihazın TOTP trust'ını hemen temizle
    if data.duration_seconds == 0 and device_id:
        from app.services.device_service import set_totp_trust
        await set_totp_trust(db, str(current_user.id), device_id, 0)
    await db.flush()
    return {"totp_trust_duration_seconds": current_user.totp_trust_duration_seconds}


@router.get("/totp/trust-check")
async def totp_trust_check(
    current_user: User = Depends(get_current_user),
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    """Mevcut cihazın TOTP trust durumunu döndürür."""
    if not current_user.totp_enabled:
        return {"totp_enabled": False, "trust_valid": True}
    from app.services.device_service import is_totp_trust_valid
    trust_valid = bool(device_id and await is_totp_trust_valid(db, str(current_user.id), device_id))
    return {"totp_enabled": True, "trust_valid": trust_valid}


@router.post("/totp/verify-unlock")
@limiter.limit("10/minute")
async def totp_verify_unlock(
    data: TotpVerifyUnlockRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    device_id: str = Depends(get_current_device_id),
    db: AsyncSession = Depends(get_db),
):
    """Uygulama açılışında TOTP doğrular ve trust set eder."""
    from app.services.totp_service import verify_totp_code
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP etkin değil")
    if not verify_totp_code(current_user.totp_secret, data.code):
        raise HTTPException(status_code=400, detail="Geçersiz TOTP kodu")
    if device_id:
        from app.services.device_service import set_totp_trust
        await set_totp_trust(db, str(current_user.id), device_id, current_user.totp_trust_duration_seconds)
    return {"success": True}


@router.get("/totp/setup")
async def totp_setup(current_user: User = Depends(get_current_user)):
    from app.services.totp_service import generate_totp_setup
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Authenticator Koruması zaten aktif")
    return generate_totp_setup(current_user.username)


@router.post("/totp/enable")
async def totp_enable(
    data: TotpEnableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.totp_service import enable_totp
    await enable_totp(db, current_user, data.secret, data.code)
    await db.commit()
    return {"message": "Authenticator Koruması etkinleştirildi"}


@router.post("/totp/disable")
async def totp_disable(
    data: TotpDisableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.totp_service import disable_totp
    await disable_totp(db, current_user, data.auth_verifier, data.totp_code)
    await db.commit()
    return {"message": "Authenticator Koruması devre dışı bırakıldı"}


@router.post("/totp/verify-login")
@limiter.limit("10/minute")
async def totp_verify_login(
    data: TotpVerifyLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.services.totp_service import verify_totp_temp_token, verify_totp_code
    from app.services.device_service import (
        is_device_trusted, get_device_status,
        trust_device, update_device_last_active, set_totp_trust,
    )
    from app.services.audit_log_service import create_audit_log

    payload = verify_totp_temp_token(data.temp_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş oturum")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="Geçersiz istek")

    if user.is_locked:
        if user.lock_until and datetime.now(timezone.utc) >= user.lock_until:
            user.is_locked = False
            user.failed_attempts = 0
            user.lock_until = None
            await db.commit()
        else:
            raise HTTPException(status_code=403, detail="Hesap geçici olarak kilitlendi")

    if not verify_totp_code(user.totp_secret, data.code):
        await create_audit_log(
            db=db, user_id=user_id,
            action="login_totp_failed", status="failed",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=400, detail="Geçersiz doğrulama kodu")

    device_id = payload.get("did") or None
    device_type = payload.get("dtype") or None
    display_name = payload.get("dname") or None

    if device_id:
        device_status = await get_device_status(db, user_id, device_id)
        if device_status == "banned":
            raise HTTPException(status_code=403, detail="Bu hesap için bu cihaz kullanılamıyor")
        trusted = await is_device_trusted(db, user_id, device_id)
        if not trusted:
            if user.email:
                from app.services.email_service import send_verification_code
                await send_verification_code(db, user_id, user.email, "new_device")
            await create_audit_log(
                db=db, user_id=user_id,
                action="login_new_device", status="pending",
                ip_address=request.client.host if request.client else None,
            )
            return {
                "needs_device_verification": True,
                "needs_totp": False,
                "user_id": user_id,
                "email": user.email,
            }
        await update_device_last_active(db, user_id, device_id)
        if user.totp_trust_duration_seconds > 0:
            await set_totp_trust(db, user_id, device_id, user.totp_trust_duration_seconds)

    ip = request.client.host if request.client else None
    await create_audit_log(db=db, user_id=user_id, action="login_success", status="success", ip_address=ip)
    token_payload = {"sub": user_id, "username": user.username, "tv": user.token_version, "did": device_id or ""}
    return {
        "needs_device_verification": False,
        "needs_totp": False,
        "access_token": create_access_token(token_payload),
        "refresh_token": create_refresh_token(token_payload),
        "encryption_key_salt": user.encryption_key_salt,
        "user": {
            "id": user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "preferred_language": user.preferred_language,
            "preferred_theme": user.preferred_theme,
        },
    }
