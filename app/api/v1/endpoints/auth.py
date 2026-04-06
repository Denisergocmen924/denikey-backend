from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services.user_service import register_user, login_user, verify_email
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class VerifyEmailRequest(BaseModel):
    user_id: str
    code: str


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await register_user(db, data, ip_address=ip)
    return TokenResponse(
        access_token=result["access_token"],
        encryption_key_salt=result["encryption_key_salt"],
        user=UserResponse(
            id=str(result["user"].id),
            username=result["user"].username,
            email=result["user"].email,
            phone=result["user"].phone,
            full_name=result["user"].full_name,
            avatar_url=result["user"].avatar_url,
            preferred_language=result["user"].preferred_language,
            preferred_theme=result["user"].preferred_theme,
        )
    )


@router.post("/verify-email")
async def verify_email_endpoint(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    await verify_email(db, data.user_id, data.code)
    return {"message": "E-posta doğrulandı"}


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await login_user(db, data.username, data.master_password, ip_address=ip)
    return TokenResponse(
        access_token=result["access_token"],
        encryption_key_salt=result["encryption_key_salt"],
        user=UserResponse(
            id=str(result["user"].id),
            username=result["user"].username,
            email=result["user"].email,
            phone=result["user"].phone,
            full_name=result["user"].full_name,
            avatar_url=result["user"].avatar_url,
            preferred_language=result["user"].preferred_language,
            preferred_theme=result["user"].preferred_theme,
        )
    )
