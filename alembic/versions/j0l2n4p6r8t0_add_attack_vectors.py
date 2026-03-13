"""add attack_vectors table

Revision ID: j0l2n4p6r8t0
Revises: i9k1m3o5q7s9
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'j0l2n4p6r8t0'
down_revision = 'i9k1m3o5q7s9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'attack_vectors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('attack_type', sa.String(100), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effectiveness_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_attack_vectors_tenant_id', 'attack_vectors', ['tenant_id'])
    op.create_index('ix_attack_vectors_category', 'attack_vectors', ['category'])
    op.create_index('ix_attack_vectors_attack_type', 'attack_vectors', ['attack_type'])


def downgrade():
    op.drop_index('ix_attack_vectors_attack_type', 'attack_vectors')
    op.drop_index('ix_attack_vectors_category', 'attack_vectors')
    op.drop_index('ix_attack_vectors_tenant_id', 'attack_vectors')
    op.drop_table('attack_vectors')
