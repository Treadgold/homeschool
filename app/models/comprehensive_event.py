"""
Comprehensive Event Management System
====================================

This module provides a complete event management framework designed for educational
organizations, homeschool communities, and multi-age group activities.

Architecture Overview:
- Event: Core event entity with comprehensive metadata
- EventTicket: Flexible ticketing system supporting multiple pricing tiers
- EventSession: Multi-session support for courses and recurring events
- EventRequirement: Detailed requirements and policies
- EventStaff: Staff assignments and supervision tracking
- EventCheckIn: Real-time attendance and head count management
- EventPolicy: Configurable policies and restrictions

Designed for extensibility to support:
- Complex age-based pricing and supervision requirements
- Multi-part courses and event series
- Real-time head count and safety tracking
- Staff scheduling and supervision ratios
- Custom event templates and categories
- Advanced booking and payment workflows
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Dict, List, Optional, Any, Union
import uuid

# Import Base from existing models
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import Base


class EventStatus(PyEnum):
    """Event lifecycle status enumeration."""
    DRAFT = "draft"                    # Event created but not published
    PUBLISHED = "published"            # Event live and accepting registrations
    REGISTRATION_CLOSED = "reg_closed" # Event published but registration closed
    IN_PROGRESS = "in_progress"        # Event currently happening
    COMPLETED = "completed"            # Event finished successfully
    CANCELLED = "cancelled"            # Event cancelled
    POSTPONED = "postponed"            # Event postponed to new date


class EventType(PyEnum):
    """Event category enumeration for different event types."""
    WORKSHOP = "workshop"              # Hands-on learning experience
    FIELD_TRIP = "field_trip"         # Off-site educational visit
    SOCIAL_EVENT = "social_event"      # Community gathering or party
    SPORTS = "sports"                  # Physical activities and games
    ARTS_CRAFTS = "arts_crafts"        # Creative and artistic activities
    SCIENCE = "science"                # STEM and science activities
    ACADEMIC = "academic"              # Educational lectures or classes
    LIFE_SKILLS = "life_skills"        # Practical life skills training
    COURSE_SERIES = "course_series"    # Multi-session course
    CAMP = "camp"                      # Day or overnight camps
    PERFORMANCE = "performance"        # Shows, concerts, presentations
    VOLUNTEER = "volunteer"            # Community service activities


class SupervisionLevel(PyEnum):
    """Supervision requirement levels."""
    NONE = "none"                      # No special supervision required
    BASIC = "basic"                    # Standard adult presence
    ENHANCED = "enhanced"              # Higher adult-to-child ratio
    ONE_ON_ONE = "one_on_one"         # Individual supervision required
    SPECIALIZED = "specialized"        # Specialized staff required


class ComprehensiveEvent(Base):
    """
    Enhanced Event Model for Complex Educational Events
    
    This model supports sophisticated event management including:
    - Multi-tier pricing and ticketing
    - Complex age and supervision requirements  
    - Multi-session courses and series
    - Real-time capacity and head count tracking
    - Staff scheduling and supervision ratios
    - Custom policies and requirements
    
    Design Principles:
    - Extensible: Easy to add new fields and relationships
    - Flexible: Supports diverse event types and requirements
    - Scalable: Efficient for large numbers of events and participants
    - Safe: Built-in safety and supervision tracking
    - User-friendly: Clear data structure for UI development
    """
    
    __tablename__ = "comprehensive_events"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # === Basic Information ===
    title = Column(String(200), nullable=False, index=True)
    """Event title displayed to users"""
    
    subtitle = Column(String(300), nullable=True)
    """Optional subtitle for additional context"""
    
    description = Column(Text, nullable=True)
    """Detailed event description with rich text support"""
    
    short_description = Column(String(500), nullable=True)
    """Brief description for cards and previews"""
    
    event_type = Column(Enum(EventType), nullable=False, index=True)
    """Primary event category"""
    
    status = Column(Enum(EventStatus), default=EventStatus.DRAFT, index=True)
    """Current event status"""
    
    # === Scheduling ===
    start_datetime = Column(DateTime, nullable=False, index=True)
    """Event start date and time"""
    
    end_datetime = Column(DateTime, nullable=True, index=True)
    """Event end date and time (optional for open-ended events)"""
    
    duration_minutes = Column(Integer, nullable=True)
    """Expected duration in minutes (calculated or manual)"""
    
    timezone = Column(String(50), default="Pacific/Auckland")
    """Event timezone for international support"""
    
    is_recurring = Column(Boolean, default=False)
    """Whether this is part of a recurring series"""
    
    recurrence_pattern = Column(JSON, nullable=True)
    """Recurrence configuration (weekly, monthly, etc.)"""
    
    # === Location ===
    location_name = Column(String(200), nullable=True)
    """Venue or location name"""
    
    location_address = Column(Text, nullable=True)
    """Full address including street, city, postal code"""
    
    location_coordinates = Column(JSON, nullable=True)
    """Latitude/longitude for mapping: {"lat": -36.8485, "lng": 174.7633}"""
    
    location_details = Column(Text, nullable=True)
    """Additional venue information (parking, entrance, etc.)"""
    
    is_virtual = Column(Boolean, default=False)
    """Whether event is held online"""
    
    virtual_platform = Column(String(100), nullable=True)
    """Online platform (Zoom, Teams, etc.)"""
    
    virtual_access_details = Column(JSON, nullable=True)
    """Meeting links, passwords, etc. (encrypted)"""
    
    # === Capacity Management ===
    max_participants = Column(Integer, nullable=True)
    """Maximum total participants"""
    
    min_participants = Column(Integer, nullable=True)
    """Minimum participants needed to run event"""
    
    current_registrations = Column(Integer, default=0)
    """Current number of confirmed registrations"""
    
    waitlist_enabled = Column(Boolean, default=True)
    """Whether to enable waitlist when full"""
    
    max_waitlist = Column(Integer, nullable=True)
    """Maximum waitlist size"""
    
    # === Age Groups & Supervision ===
    min_age_years = Column(Integer, nullable=True)
    """Minimum age in years"""
    
    max_age_years = Column(Integer, nullable=True)
    """Maximum age in years"""
    
    primary_age_group = Column(String(50), nullable=True)
    """Target age group description (e.g., "Primary School", "Teens")"""
    
    supervision_level = Column(Enum(SupervisionLevel), default=SupervisionLevel.BASIC)
    """Required supervision level"""
    
    supervision_ratio = Column(JSON, nullable=True)
    """Adult-to-child ratios by age: {"under_5": 4, "5_to_10": 8, "over_10": 12}"""
    
    requires_guardian = Column(Boolean, default=False)
    """Whether children must be accompanied by parent/guardian"""
    
    guardian_age_threshold = Column(Integer, nullable=True)
    """Age below which guardian is required"""
    
    # === Pricing & Ticketing ===
    base_price_nzd = Column(Float, nullable=True)
    """Base price in New Zealand dollars"""
    
    is_free = Column(Boolean, default=False)
    """Whether event is completely free"""
    
    pricing_structure = Column(JSON, nullable=True)
    """Complex pricing: {"child": 10, "adult": 22, "family_4": 35, "concession": 8}"""
    
    early_bird_pricing = Column(JSON, nullable=True)
    """Early bird discounts with cutoff dates"""
    
    late_fee_pricing = Column(JSON, nullable=True)
    """Late registration fees"""
    
    # === Requirements & Policies ===
    health_requirements = Column(JSON, nullable=True)
    """Health and safety requirements"""
    
    equipment_provided = Column(JSON, nullable=True)
    """List of equipment/materials provided"""
    
    equipment_required = Column(JSON, nullable=True)
    """List of equipment participants must bring"""
    
    dietary_accommodations = Column(Boolean, default=False)
    """Whether dietary restrictions can be accommodated"""
    
    accessibility_features = Column(JSON, nullable=True)
    """Accessibility features and accommodations"""
    
    cancellation_policy = Column(Text, nullable=True)
    """Event cancellation and refund policy"""
    
    weather_policy = Column(Text, nullable=True)
    """Policy for weather-related changes"""
    
    # === Staff & Supervision ===
    facilitator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    """Primary event facilitator/organizer"""
    
    required_staff_count = Column(Integer, default=1)
    """Number of staff members required"""
    
    assigned_staff = Column(JSON, nullable=True)
    """List of assigned staff member IDs and roles"""
    
    volunteer_spots = Column(Integer, default=0)
    """Number of volunteer positions available"""
    
    # === Media & Marketing ===
    featured_image_url = Column(String(500), nullable=True)
    """Main event image URL"""
    
    gallery_images = Column(JSON, nullable=True)
    """Additional event images"""
    
    video_url = Column(String(500), nullable=True)
    """Promotional or instructional video"""
    
    marketing_tags = Column(JSON, nullable=True)
    """Tags for searchability and categorization"""
    
    social_media_hashtags = Column(JSON, nullable=True)
    """Suggested hashtags for social sharing"""
    
    # === Registration Management ===
    registration_opens = Column(DateTime, nullable=True)
    """When registration becomes available"""
    
    registration_closes = Column(DateTime, nullable=True)
    """Registration deadline"""
    
    late_registration_allowed = Column(Boolean, default=False)
    """Whether to allow registration after deadline"""
    
    registration_questions = Column(JSON, nullable=True)
    """Custom questions for registration form"""
    
    requires_approval = Column(Boolean, default=False)
    """Whether registrations need manual approval"""
    
    # === Communication ===
    contact_email = Column(String(255), nullable=True)
    """Contact email for event questions"""
    
    contact_phone = Column(String(50), nullable=True)
    """Contact phone number"""
    
    communication_preferences = Column(JSON, nullable=True)
    """How to communicate with participants"""
    
    # === Analytics & Tracking ===
    view_count = Column(Integer, default=0)
    """Number of times event page was viewed"""
    
    inquiry_count = Column(Integer, default=0)
    """Number of inquiries received"""
    
    conversion_rate = Column(Float, nullable=True)
    """Registration conversion rate (inquiries to bookings)"""
    
    # === System Fields ===
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # === Metadata ===
    custom_fields = Column(JSON, nullable=True)
    """Extensible custom fields for future features"""
    
    integration_data = Column(JSON, nullable=True)
    """Data for third-party integrations"""
    
    ai_metadata = Column(JSON, nullable=True)
    """AI-generated insights and suggestions"""
    
    # === Relationships ===
    # tickets = relationship("EventTicket", back_populates="event", cascade="all, delete-orphan")
    # sessions = relationship("EventSession", back_populates="event", cascade="all, delete-orphan")
    # requirements = relationship("EventRequirement", back_populates="event", cascade="all, delete-orphan")
    # staff_assignments = relationship("EventStaffAssignment", back_populates="event", cascade="all, delete-orphan")
    # check_ins = relationship("EventCheckIn", back_populates="event", cascade="all, delete-orphan")
    # bookings = relationship("EventBooking", back_populates="event")
    
    def __repr__(self) -> str:
        return f"<ComprehensiveEvent(id={self.id}, title='{self.title}', status='{self.status.value}')>"
    
    # === Business Logic Methods ===
    
    def is_registration_open(self) -> bool:
        """Check if registration is currently open."""
        now = datetime.utcnow()
        
        if self.status != EventStatus.PUBLISHED:
            return False
            
        if self.registration_opens and now < self.registration_opens:
            return False
            
        if self.registration_closes and now > self.registration_closes:
            return self.late_registration_allowed
            
        return True
    
    def has_capacity(self, requested_spots: int = 1) -> bool:
        """Check if event has capacity for requested number of spots."""
        if not self.max_participants:
            return True
            
        return (self.current_registrations + requested_spots) <= self.max_participants
    
    def get_pricing_for_age(self, age: int, is_early_bird: bool = False) -> Optional[float]:
        """Get price for specific age, considering early bird discounts."""
        if self.is_free:
            return 0.0
            
        pricing = self.early_bird_pricing if is_early_bird and self.early_bird_pricing else self.pricing_structure
        
        if not pricing:
            return self.base_price_nzd
            
        # Age-based pricing logic
        if age < 18:
            return pricing.get("child", pricing.get("default", self.base_price_nzd))
        else:
            return pricing.get("adult", pricing.get("default", self.base_price_nzd))
    
    def get_supervision_requirements(self) -> Dict[str, Any]:
        """Get detailed supervision requirements."""
        return {
            "level": self.supervision_level.value,
            "ratio": self.supervision_ratio or {},
            "requires_guardian": self.requires_guardian,
            "guardian_age_threshold": self.guardian_age_threshold,
            "staff_count": self.required_staff_count
        }
    
    def calculate_duration(self) -> Optional[int]:
        """Calculate event duration in minutes."""
        if self.duration_minutes:
            return self.duration_minutes
            
        if self.start_datetime and self.end_datetime:
            delta = self.end_datetime - self.start_datetime
            return int(delta.total_seconds() / 60)
            
        return None
    
    def is_suitable_for_age(self, age: int) -> bool:
        """Check if event is suitable for given age."""
        if self.min_age_years and age < self.min_age_years:
            return False
            
        if self.max_age_years and age > self.max_age_years:
            return False
            
        return True
    
    def get_cancellation_deadline(self) -> Optional[datetime]:
        """Get the deadline for free cancellation."""
        if not self.start_datetime:
            return None
            
        # Default: 24 hours before event
        return self.start_datetime - timedelta(hours=24)
    
    def to_preview_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event preview display."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.short_description or self.description,
            "event_type": self.event_type.value,
            "status": self.status.value,
            "start_datetime": self.start_datetime.isoformat() if self.start_datetime else None,
            "end_datetime": self.end_datetime.isoformat() if self.end_datetime else None,
            "duration": self.calculate_duration(),
            "location": {
                "name": self.location_name,
                "address": self.location_address,
                "is_virtual": self.is_virtual
            },
            "capacity": {
                "max_participants": self.max_participants,
                "current_registrations": self.current_registrations,
                "has_capacity": self.has_capacity(),
                "is_full": not self.has_capacity()
            },
            "age_requirements": {
                "min_age": self.min_age_years,
                "max_age": self.max_age_years,
                "primary_age_group": self.primary_age_group
            },
            "pricing": {
                "is_free": self.is_free,
                "base_price": self.base_price_nzd,
                "pricing_structure": self.pricing_structure
            },
            "supervision": self.get_supervision_requirements(),
            "registration": {
                "is_open": self.is_registration_open(),
                "requires_approval": self.requires_approval
            },
            "media": {
                "featured_image": self.featured_image_url,
                "video": self.video_url
            }
        }


class EventTicket(Base):
    """
    Flexible Ticketing System
    
    Supports multiple ticket types per event with different pricing,
    capacity limits, and restrictions.
    """
    
    __tablename__ = "event_tickets"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("comprehensive_events.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    price_nzd = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=True)
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    
    sale_starts = Column(DateTime, nullable=True)
    sale_ends = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    
    # Relationships
    # event = relationship("ComprehensiveEvent", back_populates="tickets")


class EventSession(Base):
    """
    Multi-Session Support for Courses and Series
    
    Enables complex events that span multiple dates or times.
    """
    
    __tablename__ = "event_sessions"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("comprehensive_events.id"), nullable=False)
    
    session_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=True)
    
    location_override = Column(String(200), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    is_mandatory = Column(Boolean, default=True)
    materials_needed = Column(JSON, nullable=True)
    
    # Relationships
    # event = relationship("ComprehensiveEvent", back_populates="sessions")


class EventCheckIn(Base):
    """
    Real-time Attendance and Head Count Management
    
    Critical for safety and supervision in educational settings.
    """
    
    __tablename__ = "event_check_ins"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("comprehensive_events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    guardian_present = Column(Boolean, default=False)
    guardian_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    emergency_contact_verified = Column(Boolean, default=False)
    health_notes = Column(Text, nullable=True)
    
    status = Column(String(50), default="registered")  # registered, checked_in, checked_out, no_show
    
    # Relationships
    # event = relationship("ComprehensiveEvent", back_populates="check_ins")


# === Factory Functions for AI Agent ===

def create_event_from_ai_data(ai_extracted_data: Dict[str, Any], user_id: int) -> ComprehensiveEvent:
    """
    Factory function to create ComprehensiveEvent from AI-extracted data.
    
    Args:
        ai_extracted_data: Dictionary containing extracted event information
        user_id: ID of user creating the event
        
    Returns:
        ComprehensiveEvent instance ready for database insertion
    """
    
    # Parse AI data with sensible defaults
    event_data = {
        "title": ai_extracted_data.get("title", "New Event"),
        "description": ai_extracted_data.get("description"),
        "event_type": _parse_event_type(ai_extracted_data.get("event_type", "workshop")),
        "location_name": ai_extracted_data.get("location"),
        "location_details": ai_extracted_data.get("location_details"),
        "max_participants": ai_extracted_data.get("max_capacity") or ai_extracted_data.get("max_pupils"),
        "min_age_years": ai_extracted_data.get("min_age"),
        "max_age_years": ai_extracted_data.get("max_age"),
        "created_by_id": user_id,
        "status": EventStatus.DRAFT
    }
    
    # Handle pricing
    if ai_extracted_data.get("pricing_info"):
        pricing = ai_extracted_data["pricing_info"]
        if "child_cost" in pricing:
            event_data["base_price_nzd"] = pricing["child_cost"]
            event_data["pricing_structure"] = {
                "child": pricing["child_cost"],
                "adult": pricing.get("adult_cost", pricing["child_cost"])
            }
    elif ai_extracted_data.get("cost") is not None:
        if ai_extracted_data["cost"] == 0:
            event_data["is_free"] = True
        else:
            event_data["base_price_nzd"] = ai_extracted_data["cost"]
    
    # Handle supervision requirements
    if ai_extracted_data.get("supervision_required"):
        event_data["supervision_level"] = SupervisionLevel.ENHANCED
        event_data["requires_guardian"] = True
        event_data["guardian_age_threshold"] = 11  # Based on "children under 11 must have adult"
    
    # Handle date and time
    if ai_extracted_data.get("date_text"):
        try:
            import dateutil.parser
            parsed_date = dateutil.parser.parse(ai_extracted_data["date_text"])
            
            # Add time if provided
            if ai_extracted_data.get("time"):
                time_str = ai_extracted_data["time"]
                # Parse time and combine with date
                # This is simplified - you'd want more robust time parsing
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    from datetime import datetime
                    time_obj = datetime.strptime(time_str, "%I%p" if ":" not in time_str else "%I:%M%p")
                    parsed_date = parsed_date.replace(hour=time_obj.hour, minute=time_obj.minute)
            
            event_data["start_datetime"] = parsed_date
            
        except Exception as e:
            # Handle date parsing errors gracefully
            print(f"Date parsing error: {e}")
    
    # Create and return event
    return ComprehensiveEvent(**{k: v for k, v in event_data.items() if v is not None})


def _parse_event_type(event_type_str: str) -> EventType:
    """Parse event type string to EventType enum."""
    type_mapping = {
        "workshop": EventType.WORKSHOP,
        "field-trip": EventType.FIELD_TRIP,
        "field trip": EventType.FIELD_TRIP,
        "trip": EventType.FIELD_TRIP,
        "social": EventType.SOCIAL_EVENT,
        "sports": EventType.SPORTS,
        "arts": EventType.ARTS_CRAFTS,
        "science": EventType.SCIENCE,
        "academic": EventType.ACADEMIC,
        "course": EventType.COURSE_SERIES,
        "camp": EventType.CAMP
    }
    
    return type_mapping.get(event_type_str.lower(), EventType.WORKSHOP)


# === Documentation for Future Development ===

"""
FUTURE EXTENSION ROADMAP
=======================

1. REAL-TIME HEAD COUNT SYSTEM
   - Live dashboard showing current attendance
   - QR code check-in/check-out
   - Emergency evacuation procedures
   - Guardian notification system

2. ADVANCED SUPERVISION TRACKING
   - Staff scheduling with qualifications
   - Real-time supervision ratio monitoring
   - Automatic alerts for ratio violations
   - Volunteer management system

3. SMART PRICING ENGINE
   - Dynamic pricing based on demand
   - Sibling discounts and family packages
   - Loyalty program integration
   - Scholarship and subsidy management

4. EVENT TEMPLATE SYSTEM
   - Pre-configured event templates
   - Recurring event automation
   - Curriculum integration
   - Resource planning

5. ANALYTICS AND INSIGHTS
   - Event performance metrics
   - Participant behavior analysis
   - Revenue optimization
   - Safety incident tracking

6. INTEGRATION ECOSYSTEM
   - Payment gateway integration
   - Calendar synchronization
   - Email marketing automation
   - Learning management systems

7. MOBILE APPLICATIONS
   - Staff check-in app
   - Parent communication app
   - Event discovery mobile
   - Emergency response tools

IMPLEMENTATION NOTES:
- All new features should extend existing models rather than replace
- Maintain backward compatibility with current booking system
- Consider performance implications for real-time features
- Prioritize safety and child protection in all developments
""" 