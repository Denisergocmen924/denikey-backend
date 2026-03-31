from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Uygulama
    APP_NAME: str = "DeniKey"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Veritabanı
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Şifreleme
    ENCRYPTION_VERSION: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
