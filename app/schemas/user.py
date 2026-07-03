from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)          # User.full_name = String(100)
    auth_verifier: str  # istemci tarafı türetilen verifier — ham parola sunucuya gelmez
    encryption_key_salt: str
    device_id: Optional[str] = Field(None, max_length=255)          # Device.device_name = String(255)
    device_type: Optional[str] = Field(None, max_length=20)         # Device.device_type = String(20)

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Kullanıcı adı 3-50 karakter olmalı')
        return v

    # Parola uzunluğu (min 10) artık istemcide doğrulanır — sunucu ham parolayı görmez

class UserLogin(BaseModel):
    username: str
    auth_verifier: str  # ham parola değil; istemcide türetilen verifier
    device_id: Optional[str] = Field(None, max_length=255)          # Device.device_name = String(255)
    device_type: Optional[str] = Field(None, max_length=20)         # Device.device_type = String(20)
    device_name: Optional[str] = Field(None, max_length=100)        # Device.display_name = String(100)

class LoginSaltRequest(BaseModel):
    username: str

class LoginSaltResponse(BaseModel):
    # Var olmayan kullanıcıda sahte-ama-tutarlı salt döner (enumeration'ı engeller)
    encryption_key_salt: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    preferred_language: str
    preferred_theme: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = Field(None, max_length=100)          # User.full_name = String(100)

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
