"""add_totp_trust_fields

Revision ID: c7d9e2f3a4b5
Revises: a1b2c3d4e5f6
Create Date: 2026-05-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c7d9e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('totp_trusted_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('totp_trust_duration_seconds', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'totp_trust_duration_seconds')
    op.drop_column('devices', 'totp_trusted_until')
