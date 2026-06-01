import os
import base64
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings


# ============================================================
# ARGON2 — Master Password'den Şifreleme Anahtarı Türetme
# ============================================================

def derive_encryption_key(master_password: str, salt: bytes) -> bytes:
    """
    Master password + salt kullanarak AES-256 anahtarı türetir.
    Argon2id algoritması kullanılır.
    """
    key = hash_secret_raw(
        secret=master_password.encode('utf-8'),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=Type.ID
    )
    return key


def generate_salt() -> bytes:
    """Yeni bir rastgele salt üretir."""
    return os.urandom(16)


def salt_to_string(salt: bytes) -> str:
    """Salt'ı veritabanında saklamak için string'e çevirir."""
    return base64.b64encode(salt).decode('utf-8')


def string_to_salt(salt_str: str) -> bytes:
    """String salt'ı bytes'a çevirir."""
    return base64.b64decode(salt_str.encode('utf-8'))


# ============================================================
# AES-256-GCM — Şifreleme ve Çözme
# ============================================================

def encrypt_data(data: str, key: bytes) -> str:
    """
    Veriyi AES-256-GCM ile şifreler.
    Döndürülen format: base64(nonce + ciphertext)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """
    AES-256-GCM ile şifrelenmiş veriyi çözer.
    """
    encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]
    aesgcm = AESGCM(key)
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted.decode('utf-8')


# ============================================================
# JWT — Token Üretme ve Doğrulama
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT access token üretir.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return token


def create_refresh_token(data: dict) -> str:
    """
    JWT refresh token üretir. Süresi access token'dan çok daha uzundur.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """
    JWT access token'ı doğrular ve payload'ı döndürür.
    Geçersiz token veya refresh token gönderilirse None döner.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        # Refresh token'ın access token gibi kullanılmasını engelle
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """
    Refresh token'ı doğrular. type == 'refresh' kontrolü yapar.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def create_email_verify_token(user_id: str, purpose: str = "register") -> str:
    """
    Kayıt ve doğrulanmamış giriş sonrası kısa ömürlü token.
    Yalnızca /auth/resend-verification endpoint'inde geçerlidir (15 dk).
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload = {
        "sub": user_id,
        "type": "email_verify",
        "purpose": purpose,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_email_verify_token(token: str) -> Optional[dict]:
    """email_verify token'ını doğrular, payload döndürür."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "email_verify":
            return None
        return payload
    except JWTError:
        return None



# ============================================================
# DOĞRULAMA HASH — Master Password Sunucu Tarafı Doğrulama
# ============================================================

def _auth_salt(salt: bytes) -> bytes:
    import hashlib
    return hashlib.sha256(salt + b"denikey-auth-v1").digest()


def hash_master_password_for_auth_v1(master_password: str, salt: bytes) -> str:
    """Eski zayıf parametreler — yalnızca mevcut hash'leri doğrulamak için kullanılır."""
    auth_hash = hash_secret_raw(
        secret=master_password.encode('utf-8'),
        salt=_auth_salt(salt),
        time_cost=1,
        memory_cost=32768,
        parallelism=1,
        hash_len=32,
        type=Type.ID
    )
    return base64.b64encode(auth_hash).decode('utf-8')


def hash_master_password_for_auth_v2(master_password: str, salt: bytes) -> str:
    """Güçlü parametreler — Flutter şifreleme ile aynı güç."""
    auth_hash = hash_secret_raw(
        secret=master_password.encode('utf-8'),
        salt=_auth_salt(salt),
        time_cost=3,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=Type.ID
    )
    return base64.b64encode(auth_hash).decode('utf-8')


def hash_master_password_for_auth(master_password: str, salt: bytes) -> str:
    """Yeni kayıt ve şifre sıfırlama için her zaman v2 kullanılır."""
    return hash_master_password_for_auth_v2(master_password, salt)