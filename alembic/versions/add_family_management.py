"""Add family management - Adult and AdultBooking models

Revision ID: add_family_management
Revises: enhanced_event_system
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_family_management'
down_revision = 'enhanced_event_system'
branch_labels = None
depends_on = None


def upgrade():
    # Create adults table
    op.create_table('adults',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('relationship_to_family', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('allergies', sa.String(length=255), nullable=True),
        sa.Column('dietary_requirements', sa.Text(), nullable=True),
        sa.Column('medical_conditions', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=100), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
        sa.Column('emergency_contact_relationship', sa.String(length=50), nullable=True),
        sa.Column('accessibility_needs', sa.Text(), nullable=True),
        sa.Column('support_requirements', sa.Text(), nullable=True),
        sa.Column('can_supervise_children', sa.Boolean(), nullable=True, default=False),
        sa.Column('supervision_qualifications', sa.Text(), nullable=True),
        sa.Column('willing_to_volunteer', sa.Boolean(), nullable=True, default=False),
        sa.Column('volunteer_skills', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('other_info', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_adults_id'), 'adults', ['id'], unique=False)

    # Create adult_bookings table
    op.create_table('adult_bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('adult_id', sa.Integer(), nullable=False),
        sa.Column('ticket_type_id', sa.Integer(), nullable=True),
        sa.Column('booking_reference', sa.String(length=20), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True, default=1),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('supervising_children', sa.Text(), nullable=True),
        sa.Column('ticket_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('add_ons_total', sa.Numeric(precision=10, scale=2), nullable=True, default=0),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True, default=0),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('payment_status', sa.Enum('unpaid', 'pending', 'paid', 'refunded', 'failed', name='paymentstatus'), nullable=True),
        sa.Column('stripe_payment_id', sa.String(length=100), nullable=True),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
        sa.Column('custom_field_responses', sa.JSON(), nullable=True),
        sa.Column('booking_status', sa.String(length=20), nullable=True, default='confirmed'),
        sa.Column('checked_in', sa.Boolean(), nullable=True, default=False),
        sa.Column('check_in_time', sa.DateTime(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['adult_id'], ['adults.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_types.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_reference')
    )
    op.create_index(op.f('ix_adult_bookings_id'), 'adult_bookings', ['id'], unique=False)


def downgrade():
    # Drop adult_bookings table
    op.drop_index(op.f('ix_adult_bookings_id'), table_name='adult_bookings')
    op.drop_table('adult_bookings')
    
    # Drop adults table
    op.drop_index(op.f('ix_adults_id'), table_name='adults')
    op.drop_table('adults') 