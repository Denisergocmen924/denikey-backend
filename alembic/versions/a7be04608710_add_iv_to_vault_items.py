"""add_iv_to_vault_items

Revision ID: a7be04608710
Revises:
Create Date: 2026-04-05 15:09:21.310676

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a7be04608710'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vault_items', sa.Column('iv', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('vault_items', 'iv')
