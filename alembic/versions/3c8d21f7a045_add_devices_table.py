"""add_devices_table

Revision ID: 3c8d21f7a045
Revises: e16f32a0dc8e
Create Date: 2026-04-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3c8d21f7a045'
down_revision: Union[str, Sequence[str], None] = 'e16f32a0dc8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if not conn.dialect.has_table(conn, 'devices'):
        op.create_table(
            'devices',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('device_name', sa.String(length=100), nullable=True),
            sa.Column('device_type', sa.String(length=20), nullable=True),
            sa.Column('jwt_token', sa.String(length=500), nullable=True),
            sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ip_address', sa.String(length=50), nullable=True),
            sa.Column('is_trusted', sa.Boolean(), nullable=True, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_devices_user_id'), 'devices', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_devices_user_id'), table_name='devices')
    op.drop_table('devices')
