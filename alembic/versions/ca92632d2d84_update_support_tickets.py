"""update_support_tickets

Revision ID: ca92632d2d84
Revises: a7be04608710
Create Date: 2026-04-05 17:04:42.787760

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'ca92632d2d84'
down_revision: Union[str, Sequence[str], None] = 'a7be04608710'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('support_tickets', sa.Column('subject', sa.String(length=255), nullable=True))
    op.add_column('support_tickets', sa.Column('priority', sa.String(length=20), nullable=True))
    op.add_column('support_tickets', sa.Column('admin_reply', sa.Text(), nullable=True))
    op.add_column('support_tickets', sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('support_tickets', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.drop_column('support_tickets', 'screenshot_url')


def downgrade() -> None:
    op.add_column('support_tickets', sa.Column('screenshot_url', sa.VARCHAR(length=500), nullable=True))
    op.drop_column('support_tickets', 'updated_at')
    op.drop_column('support_tickets', 'replied_at')
    op.drop_column('support_tickets', 'admin_reply')
    op.drop_column('support_tickets', 'priority')
    op.drop_column('support_tickets', 'subject')
