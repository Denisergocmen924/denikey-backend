from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.password_generator import generate_password
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/password", tags=["password"])
limiter = Limiter(key_func=get_remote_address)


class PasswordGenerateRequest(BaseModel):
    length: int = 16
    uppercase: bool = True
    lowercase: bool = True
    numbers: bool = True
    symbols: bool = True


class PasswordGenerateResponse(BaseModel):
    password: str


@router.post("/generate", response_model=PasswordGenerateResponse)
@limiter.limit("60/minute")
async def generate(
    request: Request,
    data: PasswordGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    password = generate_password(
        length=data.length,
        uppercase=data.uppercase,
        lowercase=data.lowercase,
        numbers=data.numbers,
        symbols=data.symbols
    )
    return {"password": password}