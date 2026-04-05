from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services.user_service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await register_user(db, data)
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

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await login_user(db, data.username, data.master_password)
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
