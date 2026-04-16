from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Uygulama
    APP_NAME: str = "DeniKey"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Production'da kesinlikle False; geliştirme için .env'de DEBUG=True yap

    # CORS — mobil istemciler Origin göndermez; web/admin için bilinen domain'ler listelenir
    ALLOWED_ORIGINS: List[str] = [
        "https://denikey.website",
        "https://www.denikey.website",
        "https://denikey-backend-production.up.railway.app",
    ]

    # Veritabanı
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Şifreleme
    ENCRYPTION_VERSION: int = 1

    # Resend (e-posta)
    RESEND_API_KEY: str

    # Admin paneli — default YOK; .env'de ADMIN_SECRET_KEY tanımlanmazsa uygulama başlamaz
    ADMIN_SECRET_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
