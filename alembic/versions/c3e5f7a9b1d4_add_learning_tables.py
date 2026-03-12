"""add learning tables

Revision ID: c3e5f7a9b1d4
Revises: a1c3e5f7b9d2
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

revision: str = 'c3e5f7a9b1d4'
down_revision: str = 'a1c3e5f7b9d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'modules',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('level', sa.String(50), nullable=False),
        sa.Column('estimated_minutes', sa.Integer, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'module_frameworks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('module_id', sa.Integer, sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('framework_type', sa.String(100), nullable=False),
        sa.Column('framework_label', sa.String(255), nullable=False),
    )

    op.create_table(
        'module_sections',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('module_id', sa.Integer, sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section_order', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False, server_default='text'),
        sa.Column('content', sa.Text, nullable=True),
    )

    op.create_table(
        'learning_paths',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('level', sa.String(50), nullable=False),
        sa.Column('estimated_hours', sa.Float, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'path_modules',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('path_id', sa.Integer, sa.ForeignKey('learning_paths.id', ondelete='CASCADE'), nullable=False),
        sa.Column('module_id', sa.Integer, sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('module_order', sa.Integer, nullable=False),
        sa.Column('is_required', sa.Boolean, nullable=False, server_default='true'),
    )


def downgrade() -> None:
    op.drop_table('path_modules')
    op.drop_table('learning_paths')
    op.drop_table('module_sections')
    op.drop_table('module_frameworks')
    op.drop_table('modules')
