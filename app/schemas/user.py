from pydantic import BaseModel, field_validator
from typing import Optional

class UserRegister(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    master_password: str
    encryption_key_salt: str
    device_id: Optional[str] = None
    device_type: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Kullanıcı adı 3-50 karakter olmalı')
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
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    device_name: Optional[str] = None  # okunabilir isim: "Samsung Galaxy S21"

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None
    preferred_language: str
    preferred_theme: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    gender: Optional[str] = None

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Kullanıcı adı 3-50 karakter olmalı')
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    encryption_key_salt: str
    user: UserResponse
