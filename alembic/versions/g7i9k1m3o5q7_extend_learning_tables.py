"""extend learning tables with content fields and references

Revision ID: g7i9k1m3o5q7
Revises: f6h8j0l2n4p6
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision: str = 'g7i9k1m3o5q7'
down_revision: str = 'f6h8j0l2n4p6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend modules table with authoring content fields
    op.add_column('modules', sa.Column('prerequisites', sa.Text, nullable=True))
    op.add_column('modules', sa.Column('learning_outcomes', sa.Text, nullable=True))
    op.add_column('modules', sa.Column('safety_note', sa.Text, nullable=True))

    # Extend learning_paths table
    op.add_column('learning_paths', sa.Column('prerequisites', sa.Text, nullable=True))
    op.add_column('learning_paths', sa.Column('learning_goals', sa.Text, nullable=True))

    # New module_references table
    op.create_table(
        'module_references',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('module_id', sa.Integer, sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reference_order', sa.Integer, nullable=False, server_default='1'),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='documentation'),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('url', sa.Text, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
    )
    op.create_index('ix_module_references_module_id', 'module_references', ['module_id'])


def downgrade() -> None:
    op.drop_index('ix_module_references_module_id', table_name='module_references')
    op.drop_table('module_references')

    op.drop_column('learning_paths', 'learning_goals')
    op.drop_column('learning_paths', 'prerequisites')

    op.drop_column('modules', 'safety_note')
    op.drop_column('modules', 'learning_outcomes')
    op.drop_column('modules', 'prerequisites')
