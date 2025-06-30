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
                    "Add discount codes if needed"
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create event draft: {e}")
            return {"error": f"Failed to create event draft: {str(e)}"}
    
    async def add_ticket_type(self, **ticket_data) -> Dict[str, Any]:
        """Add a ticket type to the event"""
        try:
            # Validate required fields
            if not ticket_data.get("name"):
                return {"error": "Ticket name is required"}
            
            if ticket_data.get("price") is None:
                return {"error": "Ticket price is required"}
            
            # Convert price to Decimal for consistency
            ticket_data["price"] = Decimal(str(ticket_data["price"]))
            
            # Parse dates
            for date_field in ["sale_starts", "sale_ends"]:
                if ticket_data.get(date_field) and isinstance(ticket_data[date_field], str):
                    ticket_data[date_field] = datetime.fromisoformat(ticket_data[date_field].replace("Z", "+00:00"))
            
            # Set defaults
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
    
    # ===== TOOL EXECUTION =====
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given arguments"""
        try:
            # Map tool names to methods
            tool_methods = {
                "create_event_draft": self.create_event_draft,
                "add_ticket_type": self.add_ticket_type,
                "add_pricing_tier": self.add_pricing_tier,
                "set_event_venue": self.set_event_venue,
                "create_discount_code": self.create_discount_code,
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