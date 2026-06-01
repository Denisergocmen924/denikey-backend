"""add_failed_attempts_to_verification_codes

Revision ID: d4b6f8e9c012
Revises: c7d9e2f3a4b5, a3f8c1d2e456
Create Date: 2026-06-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4b6f8e9c012'
down_revision: Union[str, Sequence[str], None] = ('c7d9e2f3a4b5', 'a3f8c1d2e456')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'verification_codes',
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('verification_codes', 'failed_attempts')
