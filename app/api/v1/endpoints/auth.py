from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse, UserProfileUpdate
from app.services.user_service import (
    register_user, login_user, verify_email, verify_device,
    resend_verification, forgot_password, reset_password,
    change_email_request, change_email_confirm, update_profile,
)
from app.core.dependencies import get_current_user
from app.core.security import verify_refresh_token, create_access_token, create_refresh_token
from app.models.user import User
from app.db.database import get_db
from sqlalchemy import select
import uuid
import os
import shutil
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


class VerifyEmailRequest(BaseModel):
    user_id: str
    code: str
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class ResendVerificationRequest(BaseModel):
    user_id: str

class VerifyDeviceRequest(BaseModel):
    user_id: str
    code: str
    device_id: str
    device_type: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    user_id: str
    code: str
    new_master_password: str
    new_encryption_key_salt: str

class ChangeEmailRequest(BaseModel):
    new_email: str

class ConfirmEmailChangeRequest(BaseModel):
    code: str
    new_email: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str


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
        "user": {
            "id": str(result["user"].id),
            "username": result["user"].username,
            "email": result["user"].email,
            "phone": result["user"].phone,
            "full_name": result["user"].full_name,
            "avatar_url": result["user"].avatar_url,
            "preferred_language": result["user"].preferred_language,
            "preferred_theme": result["user"].preferred_theme,
        }
    }


@router.post("/login")
@limiter.limit("10/minute")
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await login_user(
        db,
        data.username,
        data.master_password,
        device_id=data.device_id,
        device_type=data.device_type,
        ip_address=ip,
    )
    if result.get("needs_device_verification"):
        return {
            "needs_device_verification": True,
            "user_id": str(result["user"].id),
            "email": result["user"].email,
        }
    return {
        "needs_device_verification": False,
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "encryption_key_salt": result["encryption_key_salt"],
        "user": {
            "id": str(result["user"].id),
            "username": result["user"].username,
            "email": result["user"].email,
            "phone": result["user"].phone,
            "full_name": result["user"].full_name,
            "avatar_url": result["user"].avatar_url,
            "preferred_language": result["user"].preferred_language,
            "preferred_theme": result["user"].preferred_theme,
        }
    }


@router.post("/verify-email")
async def verify_email_endpoint(data: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await verify_email(db, data.user_id, data.code, device_id=data.device_id, device_type=data.device_type, ip_address=ip)
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "encryption_key_salt": result["encryption_key_salt"],
    }


@router.post("/verify-device")
async def verify_device_endpoint(data: VerifyDeviceRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await verify_device(db, data.user_id, data.code, data.device_id, device_type=data.device_type, ip_address=ip)
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
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya hesap kilitli",
        )

    token_payload = {"sub": str(user.id), "username": user.username}
    new_access = create_access_token(token_payload)
    new_refresh = create_refresh_token(token_payload)
    return {"access_token": new_access, "refresh_token": new_refresh}


@router.post("/resend-verification")
async def resend_verification_endpoint(data: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    await resend_verification(db, data.user_id)
    return {"message": "Doğrulama kodu tekrar gönderildi"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password_endpoint(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await forgot_password(db, data.email)
    return {"message": "E-posta adresiniz kayıtlıysa kod gönderildi", "user_id": result.get("user_id")}


@router.post("/reset-password")
async def reset_password_endpoint(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    return await reset_password(db, data.user_id, data.code, data.new_master_password, data.new_encryption_key_salt)


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
    user = await update_profile(db, current_user, username=data.username, full_name=data.full_name, gender=data.gender)
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "gender": user.gender,
    }


@router.post("/profile/avatar")
async def upload_avatar_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Desteklenmeyen dosya türü. JPEG, PNG veya WebP yükleyin.")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{current_user.id}.{ext}"
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "avatars")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    avatar_url = f"/uploads/avatars/{filename}"
    user = await update_profile(db, current_user, avatar_url=avatar_url)
    return {"avatar_url": user.avatar_url}


@router.get("/profile")
async def get_profile_endpoint(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "gender": current_user.gender,
    }


@router.delete("/profile/avatar")
async def delete_avatar_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.avatar_url:
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "avatars")
        file_path = os.path.join(uploads_dir, os.path.basename(current_user.avatar_url))
        if os.path.exists(file_path):
            os.remove(file_path)
        current_user.avatar_url = None
        await db.flush()
    return {"message": "Profil fotoğrafı silindi"}
