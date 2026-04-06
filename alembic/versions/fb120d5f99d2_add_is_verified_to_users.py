"""add_is_verified_to_users

Revision ID: fb120d5f99d2
Revises: b5aeeab2c177
Create Date: 2026-04-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'fb120d5f99d2'
down_revision: Union[str, Sequence[str], None] = 'b5aeeab2c177'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_verified')
