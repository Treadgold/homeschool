from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, Float, func, JSON, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime
import enum
from decimal import Decimal

Base = declarative_base()

# ============================================================================
# ENHANCED EVENT SYSTEM - Phase 1: Database Models
# ============================================================================

class EventStatus(enum.Enum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"
    completed = "completed"

class VenueType(enum.Enum):
    physical = "physical"
    online = "online"
    hybrid = "hybrid"

class TicketStatus(enum.Enum):
    active = "active"
    sold_out = "sold_out"
    hidden = "hidden"
    expired = "expired"

class PaymentStatus(enum.Enum):
    unpaid = "unpaid"
    pending = "pending"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Event Information
    title = Column(String(200), nullable=False)
    subtitle = Column(String(300), nullable=True)  # Event subtitle/tagline
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)  # For previews
    
    # Scheduling
    date = Column(DateTime, default=datetime.datetime.utcnow)
    end_date = Column(DateTime, nullable=True)  # For multi-day events
    timezone = Column(String(50), default="Pacific/Auckland")
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(JSON, nullable=True)  # {"type": "weekly", "interval": 1, "days": ["monday"]}
    
    # Venue & Location
    venue_type = Column(Enum(VenueType), default=VenueType.physical)
    event_format = Column(String(50), nullable=True)  # in_person, online, hybrid
    venue_name = Column(String(200), nullable=True)  # Name of the venue
    location = Column(String(200), nullable=True)
    location_details = Column(Text, nullable=True)
    venue_address = Column(Text, nullable=True)
    # Individual address components
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    venue_capacity = Column(Integer, nullable=True)
    
    # Online Meeting Details
    online_meeting_url = Column(String(500), nullable=True)
    online_meeting_details = Column(Text, nullable=True)
    meeting_id = Column(String(100), nullable=True)
    meeting_password = Column(String(100), nullable=True)
    
    # Event Details
    event_type = Column(String(50), default='homeschool')
    category = Column(String(100), nullable=True)  # workshop, festival, class, etc.
    status = Column(Enum(EventStatus), default=EventStatus.draft)
    
    # Additional Event Information
    what_to_bring = Column(Text, nullable=True)
    dress_code = Column(String(200), nullable=True)
    language = Column(String(50), nullable=True, default='english')
    accessibility_info = Column(Text, nullable=True)
    parking_info = Column(Text, nullable=True)
    
    # Capacity & Age Restrictions
    max_pupils = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)  # Alternative to max_pupils
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    recommended_age = Column(Integer, nullable=True)
    age_restrictions_notes = Column(Text, nullable=True)
    
    # Pricing (kept for backward compatibility, but tickets are preferred)
    cost = Column(Float, nullable=True)
    currency = Column(String(3), default="NZD")
    pricing_notes = Column(Text, nullable=True)
    
    # Ticketing Options
    is_free = Column(Boolean, default=False)
    requires_registration = Column(Boolean, default=True)
    early_bird_discount = Column(Float, nullable=True)  # Percentage
    group_discount = Column(Float, nullable=True)  # Percentage
    member_discount = Column(Float, nullable=True)  # Percentage
    registration_deadline = Column(DateTime, nullable=True)
    
    # Branding & Media
    image_url = Column(String(500), nullable=True)
    banner_image_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    brand_colors = Column(JSON, nullable=True)  # {"primary": "#ff0000", "secondary": "#00ff00"}
    gallery_images = Column(JSON, nullable=True)  # ["url1", "url2", ...]
    
    # Rich Content
    event_agenda = Column(Text, nullable=True)
    speaker_info = Column(Text, nullable=True)
    rich_description = Column(Text, nullable=True)
    
    # Requirements & Policies
    requirements = Column(Text, nullable=True)  # What to bring, prerequisites
    cancellation_policy = Column(Text, nullable=True)
    refund_policy = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    
    # External Links
    website_url = Column(String(500), nullable=True)
    booking_url = Column(String(500), nullable=True)
    
    # Social Media Links
    facebook_url = Column(String(500), nullable=True)
    instagram_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    youtube_url = Column(String(500), nullable=True)
    tiktok_url = Column(String(500), nullable=True)
    
    # Partner & Venue Links
    venue_website = Column(String(500), nullable=True)
    partner_url = Column(String(500), nullable=True)
    related_events = Column(Text, nullable=True)  # URLs, one per line
    
    # Contact Information
    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    emergency_contact = Column(String(50), nullable=True)
    
    # Legal & Policy Links
    terms_url = Column(String(500), nullable=True)
    privacy_policy_url = Column(String(500), nullable=True)
    
    # Publishing Settings
    featured_event = Column(Boolean, default=False)
    send_notifications = Column(Boolean, default=True)
    publish_date = Column(DateTime, nullable=True)
    seo_keywords = Column(String(500), nullable=True)
    
    # Admin & Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Legacy fields (kept for backward compatibility)
    is_multi_part = Column(Boolean, default=False)
    part_number = Column(Integer, nullable=True)
    
    # Relationships
    bookings = relationship("Booking", back_populates="event")
    adult_bookings = relationship("AdultBooking", back_populates="event")
    tickets = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")
    sessions = relationship("EventSession", back_populates="event", cascade="all, delete-orphan")
    custom_fields = relationship("EventCustomField", back_populates="event", cascade="all, delete-orphan")
    add_ons = relationship("EventAddOn", back_populates="event", cascade="all, delete-orphan")
    discounts = relationship("EventDiscount", back_populates="event", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

class TicketType(Base):
    __tablename__ = "ticket_types"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Ticket Information
    name = Column(String(100), nullable=False)  # "Adult", "Child", "VIP", "Student"
    description = Column(Text, nullable=True)
    internal_name = Column(String(100), nullable=True)  # For admin reference
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), default="NZD")
    
    # Availability
    quantity_available = Column(Integer, nullable=True)  # None = unlimited
    quantity_sold = Column(Integer, default=0)
    max_per_order = Column(Integer, nullable=True)  # Limit per booking
    min_per_order = Column(Integer, default=1)
    
    # Timing
    sale_starts = Column(DateTime, nullable=True)
    sale_ends = Column(DateTime, nullable=True)
    
    # Status & Visibility
    status = Column(Enum(TicketStatus), default=TicketStatus.active)
    is_hidden = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    
    # Restrictions
    age_restrictions = Column(JSON, nullable=True)  # {"min": 18, "max": 65}
    requires_approval = Column(Boolean, default=False)
    
    # Relationships
    event = relationship("Event", back_populates="tickets")
    bookings = relationship("Booking", back_populates="ticket_type")
    pricing_tiers = relationship("TicketPricingTier", back_populates="ticket_type", cascade="all, delete-orphan")

class TicketPricingTier(Base):
    __tablename__ = "ticket_pricing_tiers"
    id = Column(Integer, primary_key=True, index=True)
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False)
    
    # Tier Information
    name = Column(String(100), nullable=False)  # "Early Bird", "Regular", "Late"
    price = Column(Numeric(10, 2), nullable=False)
    
    # Timing
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=True)
    
    # Quantity limits for this tier
    quantity_available = Column(Integer, nullable=True)
    quantity_sold = Column(Integer, default=0)
    
    # Relationships
    ticket_type = relationship("TicketType", back_populates="pricing_tiers")

class EventSession(Base):
    __tablename__ = "event_sessions"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Session Details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    session_type = Column(String(50), nullable=True)  # workshop, lecture, break, meal
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    
    # Location (can be different from main event)
    location = Column(String(200), nullable=True)
    room = Column(String(100), nullable=True)
    
    # Presenter/Speaker
    presenter_name = Column(String(200), nullable=True)
    presenter_bio = Column(Text, nullable=True)
    presenter_image_url = Column(String(500), nullable=True)
    
    # Capacity
    max_attendees = Column(Integer, nullable=True)
    requires_booking = Column(Boolean, default=False)
    
    # Relationships
    event = relationship("Event", back_populates="sessions")

class EventCustomField(Base):
    __tablename__ = "event_custom_fields"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Field Configuration
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(200), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, textarea, select, checkbox, radio, file, date
    
    # Options and Validation
    options = Column(JSON, nullable=True)  # For select/radio: ["Option 1", "Option 2"]
    validation_rules = Column(JSON, nullable=True)  # {"required": true, "min_length": 5}
    placeholder = Column(String(200), nullable=True)
    help_text = Column(Text, nullable=True)
    
    # Conditional Logic
    conditional_logic = Column(JSON, nullable=True)  # {"show_if": {"field": "age", "operator": "<", "value": 18}}
    
    # Display
    sort_order = Column(Integer, default=0)
    is_required = Column(Boolean, default=False)
    
    # Relationships
    event = relationship("Event", back_populates="custom_fields")

class EventAddOn(Base):
    __tablename__ = "event_add_ons"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Add-on Details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Availability
    quantity_available = Column(Integer, nullable=True)
    quantity_sold = Column(Integer, default=0)
    max_per_order = Column(Integer, nullable=True)
    
    # Type
    addon_type = Column(String(50), nullable=True)  # merchandise, meal, transport, accommodation
    
    # Relationships
    event = relationship("Event", back_populates="add_ons")

class EventDiscount(Base):
    __tablename__ = "event_discounts"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Discount Details
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Discount Type
    discount_type = Column(String(20), nullable=False)  # percentage, fixed_amount, buy_x_get_y
    discount_value = Column(Numeric(10, 2), nullable=False)
    
    # Usage Limits
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, default=0)
    max_uses_per_user = Column(Integer, nullable=True)
    
    # Timing
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Conditions
    minimum_order_amount = Column(Numeric(10, 2), nullable=True)
    applicable_ticket_types = Column(JSON, nullable=True)  # [ticket_type_id1, ticket_type_id2]
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    event = relationship("Event", back_populates="discounts")

# ============================================================================
# ENHANCED BOOKING SYSTEM
# ============================================================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Make nullable for OAuth users
    is_admin = Column(Boolean, default=False)
    email_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # OAuth fields
    facebook_id = Column(String(50), unique=True, nullable=True, index=True)
    google_id = Column(String(50), unique=True, nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    auth_provider = Column(String(20), default='email')  # 'email', 'facebook', 'google'
    
    children = relationship("Child", back_populates="user")
    adults = relationship("Adult", back_populates="user")
    chat_conversations = relationship("ChatConversation", back_populates="user")

class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    
    # Enhanced Child Information
    date_of_birth = Column(DateTime, nullable=True)
    school_year = Column(String(20), nullable=True)
    
    # Health & Safety
    allergies = Column(String(255), nullable=True)
    dietary_requirements = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    
    # Contact & Emergency
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Accessibility
    accessibility_needs = Column(Text, nullable=True)
    needs_assisting_adult = Column(Boolean, default=False)
    support_requirements = Column(Text, nullable=True)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    other_info = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="children")
    bookings = relationship("Booking", back_populates="child")

class Adult(Base):
    __tablename__ = "adults"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    
    # Basic Information
    date_of_birth = Column(DateTime, nullable=True)
    relationship_to_family = Column(String(50), nullable=True)  # parent, guardian, caregiver, volunteer
    
    # Contact Information
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Health & Safety
    allergies = Column(String(255), nullable=True)
    dietary_requirements = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    
    # Emergency Contact (for the adult themselves)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Accessibility
    accessibility_needs = Column(Text, nullable=True)
    support_requirements = Column(Text, nullable=True)
    
    # Supervision & Volunteer Information
    can_supervise_children = Column(Boolean, default=False)
    supervision_qualifications = Column(Text, nullable=True)  # First aid, teaching, etc.
    willing_to_volunteer = Column(Boolean, default=False)
    volunteer_skills = Column(Text, nullable=True)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    other_info = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="adults")
    adult_bookings = relationship("AdultBooking", back_populates="adult")

class AdultBooking(Base):
    __tablename__ = "adult_bookings"
    id = Column(Integer, primary_key=True, index=True)
    
    # Core Booking Information
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    adult_id = Column(Integer, ForeignKey("adults.id"), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=True)
    
    # Booking Details
    booking_reference = Column(String(20), nullable=True, unique=True)
    quantity = Column(Integer, default=1)
    
    # Role in Event
    role = Column(String(50), nullable=True)  # attendee, volunteer, supervisor, helper
    supervising_children = Column(Text, nullable=True)  # JSON list of child IDs they'll supervise
    
    # Pricing
    ticket_price = Column(Numeric(10, 2), nullable=True)
    add_ons_total = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=True)
    
    # Payment
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.unpaid)
    stripe_payment_id = Column(String(100), nullable=True)
    payment_date = Column(DateTime, nullable=True)
    
    # Custom Field Responses
    custom_field_responses = Column(JSON, nullable=True)
    
    # Status & Tracking
    booking_status = Column(String(20), default="confirmed")  # confirmed, cancelled, waitlisted
    checked_in = Column(Boolean, default=False)
    check_in_time = Column(DateTime, nullable=True)
    
    # Cancellation Tracking
    cancellation_requested_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancellation_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_approved_at = Column(DateTime, nullable=True)
    refund_processed = Column(Boolean, default=False)
    refund_amount = Column(Numeric(10, 2), nullable=True)
    refund_processed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="adult_bookings")
    adult = relationship("Adult", back_populates="adult_bookings")
    ticket_type = relationship("TicketType")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    
    # Core Booking Information
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id"), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=True)
    
    # Booking Details
    booking_reference = Column(String(20), nullable=True, unique=True)
    quantity = Column(Integer, default=1)
    
    # Pricing
    ticket_price = Column(Numeric(10, 2), nullable=True)
    add_ons_total = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=True)
    
    # Payment
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.unpaid)
    stripe_payment_id = Column(String(100), nullable=True)
    payment_date = Column(DateTime, nullable=True)
    
    # Custom Field Responses
    custom_field_responses = Column(JSON, nullable=True)  # {"field_name": "response_value"}
    
    # Status & Tracking
    booking_status = Column(String(20), default="confirmed")  # confirmed, cancelled, waitlisted, cancellation_requested
    checked_in = Column(Boolean, default=False)
    check_in_time = Column(DateTime, nullable=True)
    
    # Cancellation Tracking
    cancellation_requested_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    cancellation_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_approved_at = Column(DateTime, nullable=True)
    refund_processed = Column(Boolean, default=False)
    refund_amount = Column(Numeric(10, 2), nullable=True)
    refund_processed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Legacy fields (kept for backward compatibility)
    part_number = Column(Integer, nullable=True)
    volunteer = Column(Boolean, default=False)
    volunteer_role = Column(String(100), nullable=True)
    voucher_used = Column(Boolean, default=False)
    
    # Relationships
    event = relationship("Event", back_populates="bookings")
    child = relationship("Child", back_populates="bookings")
    ticket_type = relationship("TicketType", back_populates="bookings")
    booking_add_ons = relationship("BookingAddOn", back_populates="booking", cascade="all, delete-orphan")

class BookingAddOn(Base):
    __tablename__ = "booking_add_ons"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    add_on_id = Column(Integer, ForeignKey("event_add_ons.id"), nullable=False)
    
    quantity = Column(Integer, default=1)
    price_per_item = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="booking_add_ons")
    add_on = relationship("EventAddOn")

# ============================================================================
# EXISTING MODELS (unchanged)
# ============================================================================

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    upload_date = Column(DateTime, default=func.now())

class AgentStatus(enum.Enum):
    """Agent status enumeration"""
    idle = "idle"
    thinking = "thinking"
    using_tool = "using_tool"
    planning = "planning"
    waiting = "waiting"
    error = "error"

class ChatConversation(Base):
    """Persistent chat conversations"""
    __tablename__ = "chat_conversations"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True)  # Auto-generated from first message
    status = Column(String(20), default="active")  # active, completed, archived
    agent_context = Column(JSON, nullable=True)  # Agent memory and state
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    """Individual messages in conversations"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    msg_metadata = Column(JSON, nullable=True)  # Tool calls, timing, etc.
    agent_status = Column(Enum(AgentStatus, name="agent_status"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "msg_metadata": self.msg_metadata,
            "agent_status": self.agent_status.value if self.agent_status else None,
            "created_at": self.created_at.isoformat()
        }

class AgentSession(Base):
    """Agent session state for complex workflows"""
    __tablename__ = "agent_sessions"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    agent_type = Column(String(50), default="event_creator")  # event_creator, planner, assistant
    current_step = Column(String(100), nullable=True)
    plan = Column(JSON, nullable=True)  # Agent's current plan
    memory = Column(JSON, nullable=True)  # Working memory
    tools_used = Column(JSON, nullable=True)  # History of tool usage
    status = Column(Enum(AgentStatus, name="agent_status"), default=AgentStatus.idle)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation")

# Add these new models after the existing models for dynamic schema extension

class DynamicFieldDefinition(Base):
    """Define custom fields that can be added to any model"""
    __tablename__ = "dynamic_field_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    target_model = Column(String(50), nullable=False)  # "Event", "TicketType", "Child", etc.
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(50), nullable=False)  # "string", "integer", "decimal", "boolean", "json"
    field_label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Field Configuration
    is_required = Column(Boolean, default=False)
    default_value = Column(Text, nullable=True)
    validation_rules = Column(JSON, nullable=True)  # {"min": 0, "max": 100, "pattern": "^[A-Z]+$"}
    options = Column(JSON, nullable=True)  # For select fields
    
    # Admin
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

class DynamicFieldValue(Base):
    """Store values for dynamic fields"""
    __tablename__ = "dynamic_field_values"
    
    id = Column(Integer, primary_key=True, index=True)
    field_definition_id = Column(Integer, ForeignKey("dynamic_field_definitions.id"), nullable=False)
    target_model = Column(String(50), nullable=False)
    target_record_id = Column(Integer, nullable=False)  # ID of the Event, TicketType, etc.
    
    # Value storage (only one will be used based on field_type)
    string_value = Column(Text, nullable=True)
    integer_value = Column(Integer, nullable=True)
    decimal_value = Column(Numeric(15, 4), nullable=True)
    boolean_value = Column(Boolean, nullable=True)
    json_value = Column(JSON, nullable=True)
    date_value = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    field_definition = relationship("DynamicFieldDefinition")
    
    # Composite index for fast lookups
    __table_args__ = (
        Index('idx_dynamic_field_lookup', 'target_model', 'target_record_id'),
    )

# Add dynamic field support to existing models
# This would be added to Event, TicketType, Child, etc.
class EventDynamicFieldMixin:
    """Mixin to add dynamic field support to any model"""
    
    @property
    def dynamic_fields(self):
        """Get all dynamic field values for this record"""
        from sqlalchemy.orm import sessionmaker
        db = sessionmaker()()
        
        values = db.query(DynamicFieldValue).join(DynamicFieldDefinition).filter(
            DynamicFieldValue.target_model == self.__class__.__name__,
            DynamicFieldValue.target_record_id == self.id,
            DynamicFieldDefinition.is_active == True
        ).all()
        
        result = {}
        for value in values:
            field_name = value.field_definition.field_name
            field_type = value.field_definition.field_type
            
            # Extract the appropriate value based on type
            if field_type == "string":
                result[field_name] = value.string_value
            elif field_type == "integer":
                result[field_name] = value.integer_value
            elif field_type == "decimal":
                result[field_name] = float(value.decimal_value) if value.decimal_value else None
            elif field_type == "boolean":
                result[field_name] = value.boolean_value
            elif field_type == "json":
                result[field_name] = value.json_value
            elif field_type == "date":
                result[field_name] = value.date_value
        
        return result
    
    def set_dynamic_field(self, field_name: str, value, field_type: str = None):
        """Set a dynamic field value"""
        from sqlalchemy.orm import sessionmaker
        db = sessionmaker()()
        
        # Get or create field definition
        field_def = db.query(DynamicFieldDefinition).filter(
            DynamicFieldDefinition.target_model == self.__class__.__name__,
            DynamicFieldDefinition.field_name == field_name,
            DynamicFieldDefinition.is_active == True
        ).first()
        
        if not field_def:
            if not field_type:
                # Auto-detect type
                if isinstance(value, bool):
                    field_type = "boolean"
                elif isinstance(value, int):
                    field_type = "integer"
                elif isinstance(value, (float, Decimal)):
                    field_type = "decimal"
                elif isinstance(value, (dict, list)):
                    field_type = "json"
                else:
                    field_type = "string"
            
            # Create new field definition
            field_def = DynamicFieldDefinition(
                target_model=self.__class__.__name__,
                field_name=field_name,
                field_type=field_type,
                field_label=field_name.replace('_', ' ').title()
            )
            db.add(field_def)
            db.commit()
        
        # Get or create field value
        field_value = db.query(DynamicFieldValue).filter(
            DynamicFieldValue.field_definition_id == field_def.id,
            DynamicFieldValue.target_record_id == self.id
        ).first()
        
        if not field_value:
            field_value = DynamicFieldValue(
                field_definition_id=field_def.id,
                target_model=self.__class__.__name__,
                target_record_id=self.id
            )
            db.add(field_value)
        
        # Set the appropriate value field
        if field_def.field_type == "string":
            field_value.string_value = str(value)
        elif field_def.field_type == "integer":
            field_value.integer_value = int(value)
        elif field_def.field_type == "decimal":
            field_value.decimal_value = Decimal(str(value))
        elif field_def.field_type == "boolean":
            field_value.boolean_value = bool(value)
        elif field_def.field_type == "json":
            field_value.json_value = value
        elif field_def.field_type == "date":
            field_value.date_value = value
        
        db.commit()
        return field_value 