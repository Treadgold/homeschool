"""add_missing_children_columns

Revision ID: simple_children_fix
Revises: 8ca6116cf683
Create Date: 2025-06-30 05:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'simple_children_fix'
down_revision: Union[str, None] = '8ca6116cf683'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to children table
    op.add_column('children', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('children', sa.Column('school_year', sa.String(length=20), nullable=True))
    op.add_column('children', sa.Column('dietary_requirements', sa.Text(), nullable=True))
    op.add_column('children', sa.Column('medical_conditions', sa.Text(), nullable=True))
    op.add_column('children', sa.Column('medications', sa.Text(), nullable=True))
    op.add_column('children', sa.Column('emergency_contact_name', sa.String(length=100), nullable=True))
    op.add_column('children', sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True))
    op.add_column('children', sa.Column('emergency_contact_relationship', sa.String(length=50), nullable=True))
    op.add_column('children', sa.Column('accessibility_needs', sa.Text(), nullable=True))
    op.add_column('children', sa.Column('support_requirements', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('children', 'support_requirements')
    op.drop_column('children', 'accessibility_needs')
    op.drop_column('children', 'emergency_contact_relationship')
    op.drop_column('children', 'emergency_contact_phone')
    op.drop_column('children', 'emergency_contact_name')
    op.drop_column('children', 'medications')
    op.drop_column('children', 'medical_conditions')
    op.drop_column('children', 'dietary_requirements')
    op.drop_column('children', 'school_year')
    op.drop_column('children', 'date_of_birth') 