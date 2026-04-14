from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # Uygulama
    APP_NAME: str = "DeniKey"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS — production'da sadece izinli origin'ler
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
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

    # Admin paneli
    ADMIN_SECRET_KEY: str = "denikey-admin-2024"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
