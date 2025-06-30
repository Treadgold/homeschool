"""Add enhanced event system with tickets, pricing tiers, sessions, add-ons, and discounts

Revision ID: enhanced_event_system
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhanced_event_system'
down_revision = "b02384085cc1"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to events table
    op.add_column('events', sa.Column('short_description', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('end_date', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('timezone', sa.String(length=50), nullable=True, default='Pacific/Auckland'))
    op.add_column('events', sa.Column('is_recurring', sa.Boolean(), nullable=True, default=False))
    op.add_column('events', sa.Column('recurrence_pattern', sa.JSON(), nullable=True))
    op.add_column('events', sa.Column('venue_type', sa.Enum('physical', 'online', 'hybrid', name='venuetype'), nullable=True, default='physical'))
    op.add_column('events', sa.Column('venue_address', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('venue_capacity', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('online_meeting_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('online_meeting_details', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('events', sa.Column('status', sa.Enum('draft', 'published', 'cancelled', 'completed', name='eventstatus'), nullable=True, default='draft'))
    op.add_column('events', sa.Column('age_restrictions_notes', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('currency', sa.String(length=3), nullable=True, default='NZD'))
    op.add_column('events', sa.Column('pricing_notes', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('banner_image_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('brand_colors', sa.JSON(), nullable=True))
    op.add_column('events', sa.Column('gallery_images', sa.JSON(), nullable=True))
    op.add_column('events', sa.Column('requirements', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('cancellation_policy', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('refund_policy', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('terms_and_conditions', sa.Text(), nullable=True))
    op.add_column('events', sa.Column('created_by', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()))
    op.add_column('events', sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now()))
    
    # Add foreign key for created_by
    op.create_foreign_key('fk_events_created_by', 'events', 'users', ['created_by'], ['id'])

    # Create ticket_types table
    op.create_table('ticket_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('internal_name', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        sa.Column('currency', sa.String(length=3), nullable=True, default='NZD'),
        sa.Column('quantity_available', sa.Integer(), nullable=True),
        sa.Column('quantity_sold', sa.Integer(), nullable=True, default=0),
        sa.Column('max_per_order', sa.Integer(), nullable=True),
        sa.Column('min_per_order', sa.Integer(), nullable=True, default=1),
        sa.Column('sale_starts', sa.DateTime(), nullable=True),
        sa.Column('sale_ends', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('active', 'sold_out', 'hidden', 'expired', name='ticketstatus'), nullable=True, default='active'),
        sa.Column('is_hidden', sa.Boolean(), nullable=True, default=False),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('age_restrictions', sa.JSON(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_types_id'), 'ticket_types', ['id'], unique=False)

    # Create ticket_pricing_tiers table
    op.create_table('ticket_pricing_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_type_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=True),
        sa.Column('quantity_available', sa.Integer(), nullable=True),
        sa.Column('quantity_sold', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_types.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ticket_pricing_tiers_id'), 'ticket_pricing_tiers', ['id'], unique=False)

    # Create event_sessions table
    op.create_table('event_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('session_type', sa.String(length=50), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('room', sa.String(length=100), nullable=True),
        sa.Column('presenter_name', sa.String(length=200), nullable=True),
        sa.Column('presenter_bio', sa.Text(), nullable=True),
        sa.Column('presenter_image_url', sa.String(length=500), nullable=True),
        sa.Column('max_attendees', sa.Integer(), nullable=True),
        sa.Column('requires_booking', sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_sessions_id'), 'event_sessions', ['id'], unique=False)

    # Create event_custom_fields table
    op.create_table('event_custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('field_label', sa.String(length=200), nullable=False),
        sa.Column('field_type', sa.String(length=50), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('placeholder', sa.String(length=200), nullable=True),
        sa.Column('help_text', sa.Text(), nullable=True),
        sa.Column('conditional_logic', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),
        sa.Column('is_required', sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_custom_fields_id'), 'event_custom_fields', ['id'], unique=False)

    # Create event_add_ons table
    op.create_table('event_add_ons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        sa.Column('quantity_available', sa.Integer(), nullable=True),
        sa.Column('quantity_sold', sa.Integer(), nullable=True, default=0),
        sa.Column('max_per_order', sa.Integer(), nullable=True),
        sa.Column('addon_type', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_add_ons_id'), 'event_add_ons', ['id'], unique=False)

    # Create event_discounts table
    op.create_table('event_discounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_type', sa.String(length=20), nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('uses_count', sa.Integer(), nullable=True, default=0),
        sa.Column('max_uses_per_user', sa.Integer(), nullable=True),
        sa.Column('starts_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('minimum_order_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('applicable_ticket_types', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_event_discounts_id'), 'event_discounts', ['id'], unique=False)

    # Add new columns to children table
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

    # Add new columns to bookings table
    op.add_column('bookings', sa.Column('ticket_type_id', sa.Integer(), nullable=True))
    op.add_column('bookings', sa.Column('booking_reference', sa.String(length=20), nullable=True))
    op.add_column('bookings', sa.Column('quantity', sa.Integer(), nullable=True, default=1))
    op.add_column('bookings', sa.Column('ticket_price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('add_ons_total', sa.Numeric(precision=10, scale=2), nullable=True, default=0))
    op.add_column('bookings', sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True, default=0))
    op.add_column('bookings', sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('bookings', sa.Column('payment_date', sa.DateTime(), nullable=True))
    op.add_column('bookings', sa.Column('custom_field_responses', sa.JSON(), nullable=True))
    op.add_column('bookings', sa.Column('booking_status', sa.String(length=20), nullable=True, default='confirmed'))
    op.add_column('bookings', sa.Column('checked_in', sa.Boolean(), nullable=True, default=False))
    op.add_column('bookings', sa.Column('check_in_time', sa.DateTime(), nullable=True))
    op.add_column('bookings', sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now()))
    
    # Update payment_status column to use enum
    op.alter_column('bookings', 'payment_status',
                    type_=sa.Enum('unpaid', 'pending', 'paid', 'refunded', 'failed', name='paymentstatus'),
                    existing_type=sa.String(30))
    
    # Add foreign keys
    op.create_foreign_key('fk_bookings_ticket_type', 'bookings', 'ticket_types', ['ticket_type_id'], ['id'])
    op.create_unique_constraint('uq_bookings_reference', 'bookings', ['booking_reference'])

    # Create booking_add_ons table
    op.create_table('booking_add_ons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('add_on_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True, default=1),
        sa.Column('price_per_item', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['add_on_id'], ['event_add_ons.id'], ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_add_ons_id'), 'booking_add_ons', ['id'], unique=False)


def downgrade():
    # Drop new tables
    op.drop_table('booking_add_ons')
    op.drop_table('event_discounts')
    op.drop_table('event_add_ons')
    op.drop_table('event_custom_fields')
    op.drop_table('event_sessions')
    op.drop_table('ticket_pricing_tiers')
    op.drop_table('ticket_types')
    
    # Drop new columns from bookings
    op.drop_constraint('fk_bookings_ticket_type', 'bookings', type_='foreignkey')
    op.drop_constraint('uq_bookings_reference', 'bookings', type_='unique')
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
    
    # Revert payment_status column
    op.alter_column('bookings', 'payment_status',
                    type_=sa.String(30),
                    existing_type=sa.Enum('unpaid', 'pending', 'paid', 'refunded', 'failed', name='paymentstatus'))
    
    # Drop new columns from children
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
    
    # Drop new columns from events
    op.drop_constraint('fk_events_created_by', 'events', type_='foreignkey')
    op.drop_column('events', 'updated_at')
    op.drop_column('events', 'created_at')
    op.drop_column('events', 'created_by')
    op.drop_column('events', 'terms_and_conditions')
    op.drop_column('events', 'refund_policy')
    op.drop_column('events', 'cancellation_policy')
    op.drop_column('events', 'requirements')
    op.drop_column('events', 'gallery_images')
    op.drop_column('events', 'brand_colors')
    op.drop_column('events', 'logo_url')
    op.drop_column('events', 'banner_image_url')
    op.drop_column('events', 'pricing_notes')
    op.drop_column('events', 'currency')
    op.drop_column('events', 'age_restrictions_notes')
    op.drop_column('events', 'status')
    op.drop_column('events', 'category')
    op.drop_column('events', 'online_meeting_details')
    op.drop_column('events', 'online_meeting_url')
    op.drop_column('events', 'venue_capacity')
    op.drop_column('events', 'venue_address')
    op.drop_column('events', 'venue_type')
    op.drop_column('events', 'recurrence_pattern')
    op.drop_column('events', 'is_recurring')
    op.drop_column('events', 'timezone')
    op.drop_column('events', 'end_date')
    op.drop_column('events', 'short_description')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS ticketstatus')
    op.execute('DROP TYPE IF EXISTS venuetype')
    op.execute('DROP TYPE IF EXISTS eventstatus') 