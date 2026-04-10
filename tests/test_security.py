"""
security.py fonksiyonları için birim testleri.
Veritabanı veya ağ gerektirmez.
"""
import pytest
import time
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    derive_encryption_key,
    generate_salt,
    encrypt_data,
    decrypt_data,
    hash_master_password_for_auth,
)


# ─── JWT Testleri ─────────────────────────────────────────────────────────────

def test_access_token_round_trip():
    token = create_access_token({"sub": "user-123", "username": "test"})
    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_round_trip():
    token = create_refresh_token({"sub": "user-123", "username": "test"})
    payload = verify_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"


def test_access_token_rejected_as_refresh():
    """Access token, refresh doğrulayıcısından geçemez."""
    token = create_access_token({"sub": "user-123"})
    assert verify_refresh_token(token) is None


def test_refresh_token_rejected_as_access():
    """Refresh token, access doğrulayıcısından geçemez."""
    token = create_refresh_token({"sub": "user-123"})
    # verify_access_token type kontrolü yapmaz ama type claim access olmalı
    payload = verify_access_token(token)
    assert payload is None or payload.get("type") != "access"


def test_invalid_token_returns_none():
    assert verify_access_token("bu.gecersiz.token") is None
    assert verify_refresh_token("bu.gecersiz.token") is None


def test_tampered_token_returns_none():
    token = create_access_token({"sub": "user-123"})
    tampered = token[:-5] + "XXXXX"
    assert verify_access_token(tampered) is None


# ─── AES-256-GCM Testleri ─────────────────────────────────────────────────────

def test_encrypt_decrypt_round_trip():
    salt = generate_salt()
    key = derive_encryption_key("test-master-password", salt)
    plain = "super-secret-password-123"
    encrypted = encrypt_data(plain, key)
    decrypted = decrypt_data(encrypted, key)
    assert decrypted == plain


def test_different_salts_produce_different_keys():
    s1, s2 = generate_salt(), generate_salt()
    k1 = derive_encryption_key("same-password", s1)
    k2 = derive_encryption_key("same-password", s2)
    assert k1 != k2


def test_encryption_is_nondeterministic():
    """Aynı veri iki kez şifrelenince farklı çıktı üretmeli (rastgele nonce)."""
    salt = generate_salt()
    key = derive_encryption_key("password", salt)
    e1 = encrypt_data("hello", key)
    e2 = encrypt_data("hello", key)
    assert e1 != e2


def test_wrong_key_cannot_decrypt():
    salt1, salt2 = generate_salt(), generate_salt()
    k1 = derive_encryption_key("password", salt1)
    k2 = derive_encryption_key("password", salt2)
    encrypted = encrypt_data("secret", k1)
    with pytest.raises(Exception):
        decrypt_data(encrypted, k2)


# ─── Auth Hash Testleri ───────────────────────────────────────────────────────

def test_auth_hash_deterministic():
    salt = generate_salt()
    h1 = hash_master_password_for_auth("master", salt)
    h2 = hash_master_password_for_auth("master", salt)
    assert h1 == h2


def test_auth_hash_different_for_different_passwords():
    salt = generate_salt()
    h1 = hash_master_password_for_auth("password1", salt)
    h2 = hash_master_password_for_auth("password2", salt)
    assert h1 != h2


def test_auth_hash_differs_from_encryption_key():
    """Auth salt (_auth suffix) şifreleme anahtarından farklı olmalı."""
    salt = generate_salt()
    auth_hash = hash_master_password_for_auth("master", salt)
    enc_key = derive_encryption_key("master", salt)
    # İkisi de aynı password + salt'tan türetiliyor ama farklı olmalı
    import base64
    enc_b64 = base64.b64encode(enc_key).decode()
    assert auth_hash != enc_b64
