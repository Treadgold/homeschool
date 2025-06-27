"""add_google_oauth_fields

Revision ID: d256eade3774
Revises: 7932e23c212c
Create Date: 2025-06-27 13:44:00.653823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd256eade3774'
down_revision: Union[str, None] = '7932e23c212c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google OAuth field to users table
    op.add_column('users', sa.Column('google_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)
    
    # Update auth_provider field to support Google
    # Note: This assumes the auth_provider field already exists from previous migrations


def downgrade() -> None:
    # Remove Google OAuth fields
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'google_id')
