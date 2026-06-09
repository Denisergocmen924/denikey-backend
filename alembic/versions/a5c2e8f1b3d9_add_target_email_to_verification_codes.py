"""add_target_email_to_verification_codes

Revision ID: a5c2e8f1b3d9
Revises: e7a1c9f4d2b8
Create Date: 2026-06-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a5c2e8f1b3d9'
down_revision: Union[str, Sequence[str], None] = 'e7a1c9f4d2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'verification_codes',
        sa.Column('target_email', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('verification_codes', 'target_email')
