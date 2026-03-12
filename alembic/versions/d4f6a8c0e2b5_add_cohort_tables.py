"""add cohort tables

Revision ID: d4f6a8c0e2b5
Revises: c3e5f7a9b1d4
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision: str = 'd4f6a8c0e2b5'
down_revision: str = 'c3e5f7a9b1d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cohorts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('instructor_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('start_date', sa.Date, nullable=True),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'cohort_enrollments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('cohort_id', sa.Integer, sa.ForeignKey('cohorts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('enrolled_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('cohort_id', 'user_id', name='uq_cohort_enrollment'),
    )

    op.create_table(
        'cohort_challenges',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('cohort_id', sa.Integer, sa.ForeignKey('cohorts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('challenge_id', sa.Integer, sa.ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('assigned_at', sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint('cohort_id', 'challenge_id', name='uq_cohort_challenge'),
    )


def downgrade() -> None:
    op.drop_table('cohort_challenges')
    op.drop_table('cohort_enrollments')
    op.drop_table('cohorts')
