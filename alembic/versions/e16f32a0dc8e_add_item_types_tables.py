"""add_item_types_tables

Revision ID: e16f32a0dc8e
Revises: fb120d5f99d2
Create Date: 2026-04-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e16f32a0dc8e'
down_revision: Union[str, Sequence[str], None] = 'fb120d5f99d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('item_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name_tr', sa.String(length=100), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('item_type_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name_tr', sa.String(length=100), nullable=False),
        sa.Column('field_name_en', sa.String(length=100), nullable=False),
        sa.Column('field_type', sa.String(length=20), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['item_type_id'], ['item_types.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('item_type_fields')
    op.drop_table('item_types')
