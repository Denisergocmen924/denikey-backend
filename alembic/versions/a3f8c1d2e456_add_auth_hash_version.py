"""add_auth_hash_version

Revision ID: a3f8c1d2e456
Revises: fb120d5f99d2
Create Date: 2026-05-30

"""
from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = 'a3f8c1d2e456'
down_revision: Union[str, Sequence[str], None] = 'fb120d5f99d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column(
        'auth_hash_version',
        sa.Integer(),
        nullable=False,
        server_default='1',
    ))
    # Tüm aktif oturumları geçersiz kıl — kullanıcılar yeniden giriş yaparken hash güçlü parametrelerle yeniden yazılır
    op.execute("UPDATE users SET token_version = token_version + 1")


def downgrade() -> None:
    op.drop_column('users', 'auth_hash_version')
