import hashlib
import base64
import pyotp
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import (
    encrypt_data,
    decrypt_data,
    verify_auth_verifier,
)
from app.models.user import User


def _totp_app_key() -> bytes:
    """TOTP_SECRET_KEY'den TOTP şifreleme anahtarı türetir (AES-256)."""
    return hashlib.sha256(
        (settings.TOTP_SECRET_KEY + ":totp-secret-v1").encode()
    ).digest()


def generate_totp_setup(username: str) -> dict:
    """
    Yeni TOTP secret üretir.
    Döndürür: {secret, otpauth_uri}
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=username, issuer_name="DeniKey")
    return {"secret": secret, "otpauth_uri": uri}


def verify_totp_code(encrypted_secret: str, code: str) -> bool:
    """DB'deki şifreli secret ile TOTP kodunu doğrular."""
    try:
        secret = decrypt_data(encrypted_secret, _totp_app_key())
        totp = pyotp.TOTP(secret)
        # valid_window=1 → ±30 saniyelik tolerans
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


def verify_totp_code_raw(secret: str, code: str) -> bool:
    """Ham (şifrelenmemiş) secret ile TOTP kodunu doğrular (kurulum sırasında)."""
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
    except Exception:
        return False


async def enable_totp(db: AsyncSession, user: User, secret: str, code: str) -> None:
    """TOTP'u etkinleştirir: kodu doğrular, şifreli secret'ı kaydeder."""
    if not verify_totp_code_raw(secret, code):
        raise HTTPException(status_code=400, detail="Geçersiz doğrulama kodu")

    encrypted = encrypt_data(secret, _totp_app_key())
    user.totp_secret = encrypted
    user.totp_enabled = True
    await db.flush()


async def disable_totp(db: AsyncSession, user: User, auth_verifier: str) -> None:
    """TOTP'u devre dışı bırakır: verifier doğrulaması gerekir."""
    if not verify_auth_verifier(auth_verifier, user.password_hash):
        raise HTTPException(status_code=401, detail="Master password hatalı")

    user.totp_secret = None
    user.totp_enabled = False
    await db.flush()


def create_totp_temp_token(
    user_id: str,
    device_id: Optional[str],
    device_type: Optional[str],
    display_name: Optional[str],
) -> str:
    """
    Şifre doğrulandı ama TOTP henüz girilmedi.
    5 dakika geçerli, yalnızca /auth/totp/verify-login'de kabul edilir.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": user_id,
        "type": "totp_pending",
        "did": device_id or "",
        "dtype": device_type or "",
        "dname": display_name or "",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_totp_temp_token(token: str) -> Optional[dict]:
    """Temp token'ı doğrular, payload döndürür."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "totp_pending":
            return None
        return payload
    except JWTError:
        return None
