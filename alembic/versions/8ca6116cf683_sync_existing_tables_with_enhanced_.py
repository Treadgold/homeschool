"""sync_existing_tables_with_enhanced_models

Revision ID: 8ca6116cf683
Revises: add_dynamic_fields
Create Date: 2025-06-30 05:05:12.149303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ca6116cf683'
down_revision: Union[str, None] = 'add_dynamic_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
