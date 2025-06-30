"""Merge heads

Revision ID: 9129d77ff3ad
Revises: add_family_management, d753a005841b
Create Date: 2025-06-30 08:40:24.471832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9129d77ff3ad'
down_revision: Union[str, None] = ('add_family_management', 'd753a005841b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
