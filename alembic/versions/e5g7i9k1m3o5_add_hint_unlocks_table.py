"""add hint unlocks table

Revision ID: e5g7i9k1m3o5
Revises: d4f6a8c0e2b5
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision: str = 'e5g7i9k1m3o5'
down_revision: str = 'd4f6a8c0e2b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_hint_unlocks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('challenge_version_id', sa.Integer, sa.ForeignKey('challenge_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hint_id', sa.Integer, nullable=False),
        sa.Column('unlocked_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'challenge_version_id', 'hint_id', name='uq_user_hint_unlock'),
    )
    op.create_index('ix_user_hint_unlocks_user_version', 'user_hint_unlocks', ['user_id', 'challenge_version_id'])


def downgrade() -> None:
    op.drop_index('ix_user_hint_unlocks_user_version', table_name='user_hint_unlocks')
    op.drop_table('user_hint_unlocks')
