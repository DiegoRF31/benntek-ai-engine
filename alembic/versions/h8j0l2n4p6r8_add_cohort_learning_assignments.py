"""add cohort_learning_assignments table

Revision ID: h8j0l2n4p6r8
Revises: g7i9k1m3o5q7
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision = 'h8j0l2n4p6r8'
down_revision = 'g7i9k1m3o5q7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cohort_learning_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cohort_id', sa.Integer(), nullable=False),
        sa.Column('learning_path_id', sa.Integer(), nullable=True),
        sa.Column('module_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['cohort_id'], ['cohorts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cohort_id', 'learning_path_id', name='uq_cohort_path_assignment'),
        sa.UniqueConstraint('cohort_id', 'module_id', name='uq_cohort_module_assignment'),
    )
    op.create_index('ix_cohort_learning_assignments_cohort_id', 'cohort_learning_assignments', ['cohort_id'])


def downgrade():
    op.drop_index('ix_cohort_learning_assignments_cohort_id', table_name='cohort_learning_assignments')
    op.drop_table('cohort_learning_assignments')
