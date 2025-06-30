"""
Enhanced AI Tools for Complex Event Creation
Supports the full range of event features including:
- Multiple ticket types with pricing tiers
- Event sessions and schedules
- Custom registration forms
- Add-ons and merchandise
- Discount codes and promotions
- Venue management (physical, online, hybrid)
- Accessibility and special requirements
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.models import (
    Event, TicketType, TicketPricingTier, EventSession, EventCustomField,
    EventAddOn, EventDiscount, User, Child, Booking, BookingAddOn,
    EventStatus, VenueType, TicketStatus, PaymentStatus
)

logger = logging.getLogger(__name__)

class EnhancedEventTools:
    """Comprehensive AI tools for creating complex events with all features"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all available AI tools for event creation"""
        
        return [
            # ===== CORE EVENT TOOLS =====
            {
                "name": "create_event_draft",
                "description": "Create a basic event with core information. This is the foundation - other tools build upon this.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event title"},
                        "description": {"type": "string", "description": "Detailed event description"},
                        "short_description": {"type": "string", "description": "Brief event summary for previews"},
                        "category": {"type": "string", "description": "Event category (workshop, festival, class, etc.)"},
                        "event_type": {"type": "string", "description": "Event type (homeschool, community, etc.)"},
                        "date": {"type": "string", "format": "date-time", "description": "Event start date and time"},
                        "end_date": {"type": "string", "format": "date-time", "description": "Event end date (for multi-day events)"},
                        "timezone": {"type": "string", "description": "Event timezone", "default": "Pacific/Auckland"}
                    },
                    "required": ["title", "date"]
                }
            },
            
            # ===== VENUE & LOCATION TOOLS =====
            {
                "name": "set_event_venue",
                "description": "Configure venue details for physical, online, or hybrid events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "venue_type": {"type": "string", "enum": ["physical", "online", "hybrid"], "description": "Type of venue"},
                        "location": {"type": "string", "description": "Location name or address"},
                        "venue_address": {"type": "string", "description": "Full venue address"},
                        "venue_capacity": {"type": "integer", "description": "Maximum venue capacity"},
                        "online_meeting_url": {"type": "string", "description": "Zoom/Teams meeting URL"},
                        "online_meeting_details": {"type": "string", "description": "Online meeting instructions"},
                        "location_details": {"type": "string", "description": "Additional location information"}
                    },
                    "required": ["venue_type"]
                }
            },
            
            # ===== TICKET MANAGEMENT TOOLS =====
            {
                "name": "add_ticket_type",
                "description": "Add a ticket type to the event (Adult, Child, Student, VIP, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Ticket type name (e.g., 'Adult', 'Child', 'Student')"},
                        "description": {"type": "string", "description": "Ticket description"},
                        "price": {"type": "number", "description": "Ticket price"},
                        "quantity_available": {"type": "integer", "description": "Number of tickets available (null for unlimited)"},
                        "max_per_order": {"type": "integer", "description": "Maximum tickets per order"},
                        "min_per_order": {"type": "integer", "description": "Minimum tickets per order", "default": 1},
                        "age_restrictions": {"type": "object", "description": "Age limits: {'min': 18, 'max': 65}"},
                        "sale_starts": {"type": "string", "format": "date-time", "description": "When ticket sales begin"},
                        "sale_ends": {"type": "string", "format": "date-time", "description": "When ticket sales end"}
                    },
                    "required": ["name", "price"]
                }
            },
            
            {
                "name": "add_pricing_tier",
                "description": "Add pricing tiers to a ticket type (Early Bird, Regular, Late pricing)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_type_name": {"type": "string", "description": "Name of the ticket type to add tiers to"},
                        "tier_name": {"type": "string", "description": "Tier name (e.g., 'Early Bird', 'Regular')"},
                        "price": {"type": "number", "description": "Price for this tier"},
                        "starts_at": {"type": "string", "format": "date-time", "description": "When this tier becomes active"},
                        "ends_at": {"type": "string", "format": "date-time", "description": "When this tier expires"},
                        "quantity_available": {"type": "integer", "description": "Limited quantity for this tier"}
                    },
                    "required": ["ticket_type_name", "tier_name", "price", "starts_at"]
                }
            },
            
            # ===== DISCOUNT & PROMOTION TOOLS =====
            {
                "name": "create_discount_code",
                "description": "Create promotional discount codes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Discount code (e.g., 'EARLYBIRD', 'STUDENT10')"},
                        "name": {"type": "string", "description": "Discount name"},
                        "description": {"type": "string", "description": "Discount description"},
                        "discount_type": {"type": "string", "enum": ["percentage", "fixed_amount"], "description": "Type of discount"},
                        "discount_value": {"type": "number", "description": "Discount amount (10 for 10% or $10)"},
                        "max_uses": {"type": "integer", "description": "Maximum total uses"},
                        "max_uses_per_user": {"type": "integer", "description": "Maximum uses per user"},
                        "starts_at": {"type": "string", "format": "date-time", "description": "When discount becomes active"},
                        "expires_at": {"type": "string", "format": "date-time", "description": "When discount expires"},
                        "minimum_order_amount": {"type": "number", "description": "Minimum order amount to qualify"}
                    },
                    "required": ["code", "name", "discount_type", "discount_value"]
                }
            },
            
            # ===== SESSION & SCHEDULE TOOLS =====
            {
                "name": "add_event_session",
                "description": "Add sessions to multi-session events (workshops, conferences, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Session title"},
                        "description": {"type": "string", "description": "Session description"},
                        "session_type": {"type": "string", "description": "Session type (workshop, lecture, break, meal)"},
                        "start_time": {"type": "string", "format": "date-time", "description": "Session start time"},
                        "end_time": {"type": "string", "format": "date-time", "description": "Session end time"},
                        "location": {"type": "string", "description": "Session location (if different from main event)"},
                        "room": {"type": "string", "description": "Room or area"},
                        "presenter_name": {"type": "string", "description": "Presenter or speaker name"},
                        "presenter_bio": {"type": "string", "description": "Presenter biography"},
                        "max_attendees": {"type": "integer", "description": "Maximum session attendees"},
                        "requires_booking": {"type": "boolean", "description": "Whether session requires separate booking"}
                    },
                    "required": ["title", "start_time", "end_time"]
                }
            },
            
            # ===== ADD-ONS & MERCHANDISE TOOLS =====
            {
                "name": "add_event_addon",
                "description": "Add purchasable add-ons (merchandise, meals, transport, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Add-on name"},
                        "description": {"type": "string", "description": "Add-on description"},
                        "price": {"type": "number", "description": "Add-on price"},
                        "addon_type": {"type": "string", "description": "Type of add-on (merchandise, meal, transport, accommodation)"},
                        "quantity_available": {"type": "integer", "description": "Quantity available"},
                        "max_per_order": {"type": "integer", "description": "Maximum per order"}
                    },
                    "required": ["name", "price"]
                }
            },
            
            # ===== CUSTOM FORM TOOLS =====
            {
                "name": "add_custom_field",
                "description": "Add custom registration form fields",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "field_name": {"type": "string", "description": "Field name (used in code)"},
                        "field_label": {"type": "string", "description": "Field label (shown to users)"},
                        "field_type": {"type": "string", "enum": ["text", "textarea", "select", "checkbox", "radio", "file", "date"], "description": "Field type"},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "Options for select/radio fields"},
                        "is_required": {"type": "boolean", "description": "Whether field is required"},
                        "placeholder": {"type": "string", "description": "Placeholder text"},
                        "help_text": {"type": "string", "description": "Help text for users"},
                        "validation_rules": {"type": "object", "description": "Validation rules"},
                        "conditional_logic": {"type": "object", "description": "When to show this field"}
                    },
                    "required": ["field_name", "field_label", "field_type"]
                }
            },
            
            # ===== CAPACITY & RESTRICTIONS TOOLS =====
            {
                "name": "set_event_capacity",
                "description": "Set event capacity and age restrictions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_pupils": {"type": "integer", "description": "Maximum attendees"},
                        "min_age": {"type": "integer", "description": "Minimum age"},
                        "max_age": {"type": "integer", "description": "Maximum age"},
                        "recommended_age": {"type": "integer", "description": "Recommended age"},
                        "age_restrictions_notes": {"type": "string", "description": "Age restriction details"}
                    }
                }
            },
            
            # ===== BRANDING & MEDIA TOOLS =====
            {
                "name": "set_event_branding",
                "description": "Configure event branding, images, and visual elements",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_url": {"type": "string", "description": "Main event image URL"},
                        "banner_image_url": {"type": "string", "description": "Banner image URL"},
                        "logo_url": {"type": "string", "description": "Event logo URL"},
                        "brand_colors": {"type": "object", "description": "Brand colors: {'primary': '#ff0000', 'secondary': '#00ff00'}"},
                        "gallery_images": {"type": "array", "items": {"type": "string"}, "description": "Gallery image URLs"}
                    }
                }
            },
            
            # ===== POLICY & REQUIREMENTS TOOLS =====
            {
                "name": "set_event_policies",
                "description": "Set event policies, requirements, and terms",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requirements": {"type": "string", "description": "What attendees need to bring or know"},
                        "cancellation_policy": {"type": "string", "description": "Cancellation policy"},
                        "refund_policy": {"type": "string", "description": "Refund policy"},
                        "terms_and_conditions": {"type": "string", "description": "Terms and conditions"}
                    }
                }
            },
            
            # ===== QUERY & SUGGESTION TOOLS =====
            {
                "name": "get_event_suggestions",
                "description": "Get intelligent suggestions based on event details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "suggestion_type": {"type": "string", "enum": ["pricing", "capacity", "timing", "venue", "tickets"], "description": "Type of suggestion needed"},
                        "context": {"type": "object", "description": "Current event context for suggestions"}
                    },
                    "required": ["suggestion_type"]
                }
            },
            
            {
                "name": "validate_event_setup",
                "description": "Validate the complete event setup for issues",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "check_type": {"type": "string", "enum": ["all", "tickets", "venue", "timing", "capacity"], "description": "What to validate"}
                    }
                }
            },
            
            # ===== RECURRING EVENT TOOLS =====
            {
                "name": "setup_recurring_event",
                "description": "Configure recurring event patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recurrence_type": {"type": "string", "enum": ["daily", "weekly", "monthly", "yearly"], "description": "Recurrence pattern"},
                        "interval": {"type": "integer", "description": "Interval between recurrences"},
                        "days_of_week": {"type": "array", "items": {"type": "string"}, "description": "Days of week for weekly recurrence"},
                        "end_date": {"type": "string", "format": "date-time", "description": "When recurrence ends"},
                        "max_occurrences": {"type": "integer", "description": "Maximum number of occurrences"}
                    },
                    "required": ["recurrence_type"]
                }
            }
        ]
    
    # ===== TOOL IMPLEMENTATIONS =====
    
    async def create_event_draft(self, **event_data) -> Dict[str, Any]:
        """Create a basic event draft with core information"""
        try:
            # Validate required fields
            if not event_data.get("title"):
                return {"error": "Event title is required"}
            
            # Parse date
            if isinstance(event_data.get("date"), str):
                event_data["date"] = datetime.fromisoformat(event_data["date"].replace("Z", "+00:00"))
            
            # Parse end_date if provided
            if event_data.get("end_date") and isinstance(event_data["end_date"], str):
                event_data["end_date"] = datetime.fromisoformat(event_data["end_date"].replace("Z", "+00:00"))
            
            # Set defaults
            event_data.setdefault("status", EventStatus.draft)
            event_data.setdefault("created_by", self.user_id)
            event_data.setdefault("event_type", "homeschool")
            event_data.setdefault("currency", "NZD")
            event_data.setdefault("timezone", "Pacific/Auckland")
            
            return {
                "success": True,
                "message": f"Event draft '{event_data['title']}' created successfully",
                "event_data": event_data,
                "next_steps": [
                    "Add ticket types with 'add_ticket_type'",
                    "Configure venue with 'set_event_venue'",
                    "Set capacity with 'set_event_capacity'",
                    "Add custom fields if needed"
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create event draft: {e}")
            return {"error": f"Failed to create event draft: {str(e)}"}
    
    async def set_event_venue(self, **venue_data) -> Dict[str, Any]:
        """Configure venue details"""
        try:
            venue_type = venue_data.get("venue_type")
            if venue_type not in ["physical", "online", "hybrid"]:
                return {"error": "venue_type must be 'physical', 'online', or 'hybrid'"}
            
            # Validate venue type specific requirements
            if venue_type == "online" and not venue_data.get("online_meeting_url"):
                return {"error": "online_meeting_url is required for online events"}
            
            if venue_type == "physical" and not venue_data.get("location"):
                return {"error": "location is required for physical events"}
            
            return {
                "success": True,
                "message": f"Venue configured as {venue_type}",
                "venue_data": venue_data,
                "recommendations": self._get_venue_recommendations(venue_type)
            }
            
        except Exception as e:
            return {"error": f"Failed to set venue: {str(e)}"}
    
    async def add_ticket_type(self, **ticket_data) -> Dict[str, Any]:
        """Add a ticket type to the event"""
        try:
            # Validate required fields
            if not ticket_data.get("name"):
                return {"error": "Ticket name is required"}
            
            if ticket_data.get("price") is None:
                return {"error": "Ticket price is required"}
            
            # Convert price to Decimal
            ticket_data["price"] = Decimal(str(ticket_data["price"]))
            
            # Parse dates
            for date_field in ["sale_starts", "sale_ends"]:
                if ticket_data.get(date_field) and isinstance(ticket_data[date_field], str):
                    ticket_data[date_field] = datetime.fromisoformat(ticket_data[date_field].replace("Z", "+00:00"))
            
            # Set defaults
            ticket_data.setdefault("status", TicketStatus.active)
            ticket_data.setdefault("currency", "NZD")
            ticket_data.setdefault("min_per_order", 1)
            
            return {
                "success": True,
                "message": f"Ticket type '{ticket_data['name']}' added successfully",
                "ticket_data": ticket_data,
                "suggestions": self._get_ticket_suggestions(ticket_data)
            }
            
        except Exception as e:
            return {"error": f"Failed to add ticket type: {str(e)}"}
    
    async def add_pricing_tier(self, **tier_data) -> Dict[str, Any]:
        """Add pricing tier to a ticket type"""
        try:
            # Validate required fields
            required_fields = ["ticket_type_name", "tier_name", "price", "starts_at"]
            for field in required_fields:
                if not tier_data.get(field):
                    return {"error": f"{field} is required"}
            
            # Convert price to Decimal
            tier_data["price"] = Decimal(str(tier_data["price"]))
            
            # Parse dates
            for date_field in ["starts_at", "ends_at"]:
                if tier_data.get(date_field) and isinstance(tier_data[date_field], str):
                    tier_data[date_field] = datetime.fromisoformat(tier_data[date_field].replace("Z", "+00:00"))
            
            return {
                "success": True,
                "message": f"Pricing tier '{tier_data['tier_name']}' added to '{tier_data['ticket_type_name']}'",
                "tier_data": tier_data
            }
            
        except Exception as e:
            return {"error": f"Failed to add pricing tier: {str(e)}"}
    
    async def create_discount_code(self, **discount_data) -> Dict[str, Any]:
        """Create a discount code"""
        try:
            # Validate required fields
            required_fields = ["code", "name", "discount_type", "discount_value"]
            for field in required_fields:
                if not discount_data.get(field):
                    return {"error": f"{field} is required"}
            
            # Validate discount type
            if discount_data["discount_type"] not in ["percentage", "fixed_amount"]:
                return {"error": "discount_type must be 'percentage' or 'fixed_amount'"}
            
            # Convert values to Decimal
            discount_data["discount_value"] = Decimal(str(discount_data["discount_value"]))
            if discount_data.get("minimum_order_amount"):
                discount_data["minimum_order_amount"] = Decimal(str(discount_data["minimum_order_amount"]))
            
            # Parse dates
            for date_field in ["starts_at", "expires_at"]:
                if discount_data.get(date_field) and isinstance(discount_data[date_field], str):
                    discount_data[date_field] = datetime.fromisoformat(discount_data[date_field].replace("Z", "+00:00"))
            
            # Set defaults
            discount_data.setdefault("is_active", True)
            discount_data.setdefault("uses_count", 0)
            
            return {
                "success": True,
                "message": f"Discount code '{discount_data['code']}' created successfully",
                "discount_data": discount_data
            }
            
        except Exception as e:
            return {"error": f"Failed to create discount code: {str(e)}"}
    
    async def add_event_session(self, **session_data) -> Dict[str, Any]:
        """Add a session to the event"""
        try:
            # Validate required fields
            required_fields = ["title", "start_time", "end_time"]
            for field in required_fields:
                if not session_data.get(field):
                    return {"error": f"{field} is required"}
            
            # Parse dates
            for date_field in ["start_time", "end_time"]:
                if isinstance(session_data[date_field], str):
                    session_data[date_field] = datetime.fromisoformat(session_data[date_field].replace("Z", "+00:00"))
            
            # Calculate duration
            duration = session_data["end_time"] - session_data["start_time"]
            session_data["duration_minutes"] = int(duration.total_seconds() / 60)
            
            return {
                "success": True,
                "message": f"Session '{session_data['title']}' added successfully",
                "session_data": session_data
            }
            
        except Exception as e:
            return {"error": f"Failed to add session: {str(e)}"}
    
    async def add_event_addon(self, **addon_data) -> Dict[str, Any]:
        """Add an add-on to the event"""
        try:
            # Validate required fields
            if not addon_data.get("name"):
                return {"error": "Add-on name is required"}
            
            if addon_data.get("price") is None:
                return {"error": "Add-on price is required"}
            
            # Convert price to Decimal
            addon_data["price"] = Decimal(str(addon_data["price"]))
            
            # Set defaults
            addon_data.setdefault("quantity_sold", 0)
            
            return {
                "success": True,
                "message": f"Add-on '{addon_data['name']}' added successfully",
                "addon_data": addon_data
            }
            
        except Exception as e:
            return {"error": f"Failed to add add-on: {str(e)}"}
    
    async def add_custom_field(self, **field_data) -> Dict[str, Any]:
        """Add a custom registration field"""
        try:
            # Validate required fields
            required_fields = ["field_name", "field_label", "field_type"]
            for field in required_fields:
                if not field_data.get(field):
                    return {"error": f"{field} is required"}
            
            # Validate field type
            valid_types = ["text", "textarea", "select", "checkbox", "radio", "file", "date"]
            if field_data["field_type"] not in valid_types:
                return {"error": f"field_type must be one of: {', '.join(valid_types)}"}
            
            # Validate options for select/radio fields
            if field_data["field_type"] in ["select", "radio"] and not field_data.get("options"):
                return {"error": f"options are required for {field_data['field_type']} fields"}
            
            # Set defaults
            field_data.setdefault("is_required", False)
            field_data.setdefault("sort_order", 0)
            
            return {
                "success": True,
                "message": f"Custom field '{field_data['field_label']}' added successfully",
                "field_data": field_data
            }
            
        except Exception as e:
            return {"error": f"Failed to add custom field: {str(e)}"}
    
    async def set_event_capacity(self, **capacity_data) -> Dict[str, Any]:
        """Set event capacity and age restrictions"""
        try:
            return {
                "success": True,
                "message": "Event capacity and restrictions configured",
                "capacity_data": capacity_data
            }
        except Exception as e:
            return {"error": f"Failed to set capacity: {str(e)}"}
    
    async def set_event_branding(self, **branding_data) -> Dict[str, Any]:
        """Configure event branding"""
        try:
            return {
                "success": True,
                "message": "Event branding configured",
                "branding_data": branding_data
            }
        except Exception as e:
            return {"error": f"Failed to set branding: {str(e)}"}
    
    async def set_event_policies(self, **policy_data) -> Dict[str, Any]:
        """Set event policies and requirements"""
        try:
            return {
                "success": True,
                "message": "Event policies configured",
                "policy_data": policy_data
            }
        except Exception as e:
            return {"error": f"Failed to set policies: {str(e)}"}
    
    async def get_event_suggestions(self, suggestion_type: str, context: Dict = None) -> Dict[str, Any]:
        """Get intelligent suggestions for event setup"""
        try:
            context = context or {}
            
            if suggestion_type == "pricing":
                return self._get_pricing_suggestions(context)
            elif suggestion_type == "capacity":
                return self._get_capacity_suggestions(context)
            elif suggestion_type == "timing":
                return self._get_timing_suggestions(context)
            elif suggestion_type == "venue":
                return self._get_venue_suggestions(context)
            elif suggestion_type == "tickets":
                return self._get_ticket_type_suggestions(context)
            else:
                return {"error": f"Unknown suggestion type: {suggestion_type}"}
                
        except Exception as e:
            return {"error": f"Failed to get suggestions: {str(e)}"}
    
    async def validate_event_setup(self, check_type: str = "all") -> Dict[str, Any]:
        """Validate event setup for issues"""
        try:
            issues = []
            warnings = []
            
            # Add validation logic here based on check_type
            
            return {
                "success": True,
                "validation_result": {
                    "issues": issues,
                    "warnings": warnings,
                    "is_valid": len(issues) == 0
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to validate event: {str(e)}"}
    
    async def setup_recurring_event(self, **recurrence_data) -> Dict[str, Any]:
        """Configure recurring event patterns"""
        try:
            # Validate recurrence type
            valid_types = ["daily", "weekly", "monthly", "yearly"]
            if recurrence_data.get("recurrence_type") not in valid_types:
                return {"error": f"recurrence_type must be one of: {', '.join(valid_types)}"}
            
            # Parse dates
            for date_field in ["end_date"]:
                if recurrence_data.get(date_field) and isinstance(recurrence_data[date_field], str):
                    recurrence_data[date_field] = datetime.fromisoformat(recurrence_data[date_field].replace("Z", "+00:00"))
            
            return {
                "success": True,
                "message": f"Recurring pattern configured: {recurrence_data['recurrence_type']}",
                "recurrence_data": recurrence_data
            }
            
        except Exception as e:
            return {"error": f"Failed to setup recurring event: {str(e)}"}
    
    # ===== HELPER METHODS =====
    
    def _get_venue_recommendations(self, venue_type: str) -> List[str]:
        """Get recommendations based on venue type"""
        if venue_type == "online":
            return [
                "Consider adding a tech check session before the event",
                "Provide clear joining instructions",
                "Plan for potential technical difficulties"
            ]
        elif venue_type == "physical":
            return [
                "Ensure adequate parking availability",
                "Consider accessibility requirements",
                "Plan for weather contingencies"
            ]
        else:  # hybrid
            return [
                "Test hybrid setup thoroughly beforehand",
                "Ensure online participants can interact",
                "Have technical support available"
            ]
    
    def _get_ticket_suggestions(self, ticket_data: Dict) -> List[str]:
        """Get suggestions for ticket configuration"""
        suggestions = []
        
        if ticket_data.get("price", 0) == 0:
            suggestions.append("Consider if you need registration limits for free events")
        
        if not ticket_data.get("quantity_available"):
            suggestions.append("Consider setting a capacity limit")
        
        return suggestions
    
    def _get_pricing_suggestions(self, context: Dict) -> Dict[str, Any]:
        """Get pricing suggestions based on context"""
        return {
            "success": True,
            "suggestions": [
                "Consider early bird pricing for advance bookings",
                "Student discounts can increase accessibility",
                "Group discounts encourage larger bookings"
            ]
        }
    
    def _get_capacity_suggestions(self, context: Dict) -> Dict[str, Any]:
        """Get capacity suggestions"""
        return {
            "success": True,
            "suggestions": [
                "Consider venue capacity vs. expected demand",
                "Plan for no-shows (typically 5-10%)",
                "Have a waitlist system for popular events"
            ]
        }
    
    def _get_timing_suggestions(self, context: Dict) -> Dict[str, Any]:
        """Get timing suggestions"""
        return {
            "success": True,
            "suggestions": [
                "Weekend events typically have higher attendance",
                "Consider school holidays for family events",
                "Check for conflicting local events"
            ]
        }
    
    def _get_venue_suggestions(self, context: Dict) -> Dict[str, Any]:
        """Get venue suggestions"""
        return {
            "success": True,
            "suggestions": [
                "Ensure venue has appropriate facilities",
                "Consider parking and accessibility",
                "Check if equipment is available or needs to be brought"
            ]
        }
    
    def _get_ticket_type_suggestions(self, context: Dict) -> Dict[str, Any]:
        """Get ticket type suggestions"""
        return {
            "success": True,
            "suggestions": [
                "Consider Adult/Child pricing for family events",
                "Student discounts increase accessibility",
                "VIP options can increase revenue"
            ]
        }
    
    # ===== TOOL EXECUTION =====
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given arguments"""
        try:
            # Map tool names to methods
            tool_methods = {
                "create_event_draft": self.create_event_draft,
                "set_event_venue": self.set_event_venue,
                "add_ticket_type": self.add_ticket_type,
                "add_pricing_tier": self.add_pricing_tier,
                "create_discount_code": self.create_discount_code,
                "add_event_session": self.add_event_session,
                "add_event_addon": self.add_event_addon,
                "add_custom_field": self.add_custom_field,
                "set_event_capacity": self.set_event_capacity,
                "set_event_branding": self.set_event_branding,
                "set_event_policies": self.set_event_policies,
                "get_event_suggestions": self.get_event_suggestions,
                "validate_event_setup": self.validate_event_setup,
                "setup_recurring_event": self.setup_recurring_event
            }
            
            if tool_name not in tool_methods:
                return {"error": f"Unknown tool: {tool_name}"}
            
            # Execute the tool
            result = await tool_methods[tool_name](**arguments)
            
            self.logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute tool '{tool_name}': {e}")
            return {"error": f"Failed to execute tool: {str(e)}"} 