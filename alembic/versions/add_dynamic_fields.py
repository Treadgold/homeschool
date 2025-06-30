"""Add dynamic field system for truly extensible schemas

Revision ID: add_dynamic_fields
Revises: enhanced_event_system
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_dynamic_fields'
down_revision = 'enhanced_event_system'
branch_labels = None
depends_on = None

def upgrade():
    # Create dynamic field definitions table
    op.create_table('dynamic_field_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_model', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('field_type', sa.String(length=50), nullable=False),
        sa.Column('field_label', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=True),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_model', 'field_name', name='unique_dynamic_field_per_model')
    )
    op.create_index(op.f('ix_dynamic_field_definitions_id'), 'dynamic_field_definitions', ['id'], unique=False)

    # Create dynamic field values table
    op.create_table('dynamic_field_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_definition_id', sa.Integer(), nullable=False),
        sa.Column('target_model', sa.String(length=50), nullable=False),
        sa.Column('target_record_id', sa.Integer(), nullable=False),
        sa.Column('string_value', sa.Text(), nullable=True),
        sa.Column('integer_value', sa.Integer(), nullable=True),
        sa.Column('decimal_value', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('boolean_value', sa.Boolean(), nullable=True),
        sa.Column('json_value', sa.JSON(), nullable=True),
        sa.Column('date_value', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['field_definition_id'], ['dynamic_field_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dynamic_field_values_id'), 'dynamic_field_values', ['id'], unique=False)
    op.create_index('idx_dynamic_field_lookup', 'dynamic_field_values', ['target_model', 'target_record_id'], unique=False)

def downgrade():
    # Drop dynamic field system
    op.drop_index('idx_dynamic_field_lookup', table_name='dynamic_field_values')
    op.drop_index(op.f('ix_dynamic_field_values_id'), table_name='dynamic_field_values')
    op.drop_table('dynamic_field_values')
    op.drop_index(op.f('ix_dynamic_field_definitions_id'), table_name='dynamic_field_definitions')
    op.drop_table('dynamic_field_definitions') 