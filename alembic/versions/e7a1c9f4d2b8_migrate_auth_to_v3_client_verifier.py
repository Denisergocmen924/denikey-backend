"""migrate auth hash to v3 (client-derived verifier)

v2 saklı hash = base64(Argon2_v2(password, auth_salt)) = istemcinin artık yollayacağı
verifier'ın ta kendisi. v3'te sunucu Argon2 yapmaz; gelen verifier'ı SHA-256'layıp
saklı değerle karşılaştırır (saklı değer != tel üstündeki değer -> DB sızıntısında
replay engellenir).

Migration: tüm v2 hash'lerini SHA256'lar (yeni saklı değer), auth_hash_version=3 yapar,
token_version++ ile herkesi yeniden girişe zorlar.

NOT: Yalnızca v2 kullanıcılar için doğrudur. v1 kullanıcılar deploy öncesi silindi
(Argon2 parametreleri farklı olduğu için SHA256 taklidi tutmaz). Kalan tabloda v1 yok.

Revision ID: e7a1c9f4d2b8
Revises: d4b6f8e9c012
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
import hashlib
import base64


revision = 'e7a1c9f4d2b8'
down_revision = 'd4b6f8e9c012'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, password_hash FROM users WHERE auth_hash_version = 2")
    ).fetchall()
    for row in rows:
        # security.hash_auth_verifier ile birebir aynı: base64(SHA256(verifier_string))
        new_hash = base64.b64encode(
            hashlib.sha256(row.password_hash.encode('utf-8')).digest()
        ).decode('utf-8')
        conn.execute(
            sa.text(
                "UPDATE users SET password_hash = :h, auth_hash_version = 3, "
                "token_version = COALESCE(token_version, 0) + 1 WHERE id = :id"
            ),
            {"h": new_hash, "id": row.id},
        )


def downgrade():
    # SHA-256 tek yönlü; eski Argon2 verifier değerine geri dönülemez.
    raise NotImplementedError("v3 auth hash migration geri alınamaz (SHA-256 tek yönlü)")
