"""add_missing_bookings_columns

Revision ID: fix_bookings_columns
Revises: simple_children_fix
Create Date: 2025-06-30 05:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fix_bookings_columns'
down_revision: Union[str, None] = 'simple_children_fix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to bookings table
    op.add_column('bookings', sa.Column('ticket_type_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('booking_reference', sa.String(length=20), nullable=True))
    op.add_column('bookings', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('ticket_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('add_ons_total', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('payment_date', sa.DateTime(), nullable=True))
    op.add_column('bookings', sa.Column('custom_field_responses', sa.JSON(), nullable=True))
    op.add_column('bookings', sa.Column('booking_status', sa.String(length=20), nullable=True))
    op.add_column('bookings', sa.Column('checked_in', sa.Boolean(), nullable=True))
    op.add_column('bookings', sa.Column('check_in_time', sa.DateTime(), nullable=True))
    op.add_column('bookings', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Add unique constraint on booking_reference
    op.create_unique_constraint('uq_bookings_booking_reference', 'bookings', ['booking_reference'])
    
    # Add foreign key constraint for ticket_type_id if ticket_types table exists
    # Note: We'll skip this FK constraint for now since ticket_types table might not exist yet
    # op.create_foreign_key('fk_bookings_ticket_type_id', 'bookings', 'ticket_types', ['ticket_type_id'], ['id'])
    
    # Set default values for existing records
    op.execute("UPDATE bookings SET quantity = 1 WHERE quantity IS NULL")
    op.execute("UPDATE bookings SET add_ons_total = 0 WHERE add_ons_total IS NULL")
    op.execute("UPDATE bookings SET discount_amount = 0 WHERE discount_amount IS NULL")
    op.execute("UPDATE bookings SET booking_status = 'confirmed' WHERE booking_status IS NULL")
    op.execute("UPDATE bookings SET checked_in = false WHERE checked_in IS NULL")


def downgrade() -> None:
    # Remove the added columns
    op.drop_constraint('uq_bookings_booking_reference', 'bookings', type_='unique')
    op.drop_column('bookings', 'updated_at')
    op.drop_column('bookings', 'check_in_time')
    op.drop_column('bookings', 'checked_in')
    op.drop_column('bookings', 'booking_status')
    op.drop_column('bookings', 'custom_field_responses')
    op.drop_column('bookings', 'payment_date')
    op.drop_column('bookings', 'total_amount')
    op.drop_column('bookings', 'discount_amount')
    op.drop_column('bookings', 'add_ons_total')
    op.drop_column('bookings', 'ticket_price')
    op.drop_column('bookings', 'quantity')
    op.drop_column('bookings', 'booking_reference')
    op.drop_column('bookings', 'ticket_type_id') 