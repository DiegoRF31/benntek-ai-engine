"""add challenge authoring columns

Revision ID: f6h8j0l2n4p6
Revises: e5g7i9k1m3o5
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision: str = 'f6h8j0l2n4p6'
down_revision: str = 'e5g7i9k1m3o5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend challenges table with authoring metadata
    op.add_column('challenges', sa.Column('instructor_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('challenges', sa.Column('challenge_type', sa.String(100), nullable=False, server_default='prompt_injection'))
    op.add_column('challenges', sa.Column('time_limit_minutes', sa.Integer, nullable=True))

    # Extend challenge_versions table with approval workflow fields
    op.add_column('challenge_versions', sa.Column('approval_status', sa.String(50), nullable=False, server_default='approved'))
    op.add_column('challenge_versions', sa.Column('generation_method', sa.String(50), nullable=False, server_default='manual'))
    op.add_column('challenge_versions', sa.Column('reviewer_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    op.add_column('challenge_versions', sa.Column('reviewer_notes', sa.Text, nullable=True))
    op.add_column('challenge_versions', sa.Column('submitted_at', sa.DateTime, nullable=True))

    op.create_index('ix_challenges_instructor_id', 'challenges', ['instructor_id'])
    op.create_index('ix_challenge_versions_approval_status', 'challenge_versions', ['approval_status'])


def downgrade() -> None:
    op.drop_index('ix_challenge_versions_approval_status', table_name='challenge_versions')
    op.drop_index('ix_challenges_instructor_id', table_name='challenges')

    op.drop_column('challenge_versions', 'submitted_at')
    op.drop_column('challenge_versions', 'reviewer_notes')
    op.drop_column('challenge_versions', 'reviewer_id')
    op.drop_column('challenge_versions', 'generation_method')
    op.drop_column('challenge_versions', 'approval_status')

    op.drop_column('challenges', 'time_limit_minutes')
    op.drop_column('challenges', 'challenge_type')
    op.drop_column('challenges', 'instructor_id')
