from pydantic import BaseModel, field_validator
from typing import Optional
import re

class UserRegister(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    master_password: str
    encryption_key_salt: str

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Kullanıcı adı 3-50 karakter olmalı')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Kullanıcı adı sadece harf, rakam ve _ içerebilir')
        return v

    @field_validator('master_password')
    @classmethod
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError('Master password en az 6 karakter olmalı')
        return v

    def validate_email_or_phone(self):
        if not self.email and not self.phone:
            raise ValueError('E-posta veya telefon numarası zorunlu')

class UserLogin(BaseModel):
    username: str
    master_password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: str
    preferred_theme: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    encryption_key_salt: str
    user: UserResponse
