"""add learner_module_progress table

Revision ID: i9k1m3o5q7s9
Revises: h8j0l2n4p6r8
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

revision = 'i9k1m3o5q7s9'
down_revision = 'h8j0l2n4p6r8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'learner_module_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['module_sections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'module_id', 'section_id', name='uq_learner_section_progress'),
    )
    op.create_index('ix_learner_module_progress_user_id', 'learner_module_progress', ['user_id'])
    op.create_index('ix_learner_module_progress_module_id', 'learner_module_progress', ['module_id'])


def downgrade():
    op.drop_index('ix_learner_module_progress_module_id', table_name='learner_module_progress')
    op.drop_index('ix_learner_module_progress_user_id', table_name='learner_module_progress')
    op.drop_table('learner_module_progress')
