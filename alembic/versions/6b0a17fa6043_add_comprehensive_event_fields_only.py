"""Add comprehensive event fields only

Revision ID: 6b0a17fa6043
Revises: 9fc4372be0a3
Create Date: 2025-06-30 06:18:52.131787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b0a17fa6043'
down_revision: Union[str, None] = '9fc4372be0a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
