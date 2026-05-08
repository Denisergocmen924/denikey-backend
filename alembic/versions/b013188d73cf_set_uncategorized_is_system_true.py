"""set_uncategorized_is_system_true

Revision ID: b013188d73cf
Revises: 0f10bde0bcbd
Create Date: 2026-05-08 20:24:27.570542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b013188d73cf'
down_revision: Union[str, Sequence[str], None] = '0f10bde0bcbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE categories SET is_system = TRUE WHERE name_en = 'Uncategorized'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE categories SET is_system = FALSE WHERE name_en = 'Uncategorized'"
    )
