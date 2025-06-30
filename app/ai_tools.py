"""
Dynamic AI Tools for Event Creation Agent
Provides introspective function calling interface between AI and booking system
"""

from typing import Dict, List, Optional, Any, Type
from datetime import datetime, date, timedelta
from app.models import Event, User, Child, Booking
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import json

class DynamicEventTools:
    """Dynamic tools that introspect the database schema and system capabilities"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.event_schema = self._introspect_event_schema()
    
    def _introspect_event_schema(self) -> Dict[str, Any]:
        """Dynamically discover what fields are available for events"""
        inspector = inspect(Event)
        schema = {}
        
        for column in inspector.columns:
            column_info = {
                "type": str(column.type),
                "nullable": column.nullable,
                "default": column.default.arg if column.default else None
            }
            
            # Add field descriptions based on column names
            if column.name == "title":
                column_info["description"] = "Event title/name"
            elif column.name == "description":
                column_info["description"] = "Detailed event description"
            elif column.name == "date":
                column_info["description"] = "Event date and time"
            elif column.name == "location":
                column_info["description"] = "Event location/venue"
            elif column.name == "max_pupils":
                column_info["description"] = "Maximum number of participants"
            elif column.name == "min_age":
                column_info["description"] = "Minimum age for participants"
            elif column.name == "max_age":
                column_info["description"] = "Maximum age for participants"
            elif column.name == "cost":
                column_info["description"] = "Event cost in NZD"
            elif column.name == "event_type":
                column_info["description"] = "Type of event (homeschool, offsite, etc.)"
            
            schema[column.name] = column_info
        
        return schema
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Dynamically generate tool definitions based on current system capabilities"""
        
        # Generate create_event_draft parameters from schema
        event_properties = {}
        required_fields = []
        
        for field_name, field_info in self.event_schema.items():
            if field_name in ["id", "created_at", "updated_at"]:
                continue  # Skip auto-generated fields
                
            property_def = {"description": field_info.get("description", f"Event {field_name}")}
            
            # Determine type
            if "Integer" in field_info["type"]:
                property_def["type"] = "integer"
            elif "Float" in field_info["type"]:
                property_def["type"] = "number"
            elif "Boolean" in field_info["type"]:
                property_def["type"] = "boolean"
            elif "DateTime" in field_info["type"]:
                property_def["type"] = "string"
                property_def["format"] = "date-time"
            else:
                property_def["type"] = "string"
            
            # Add to required if not nullable
            if not field_info["nullable"] and field_name != "date":  # date is auto-set
                required_fields.append(field_name)
            
            event_properties[field_name] = property_def
        
        return [
            {
                "name": "create_event_draft",
                "description": "Create a draft event with the provided details. This is the main tool for creating events.",
                "parameters": {
                    "type": "object",
                    "properties": event_properties,
                    "required": ["title"]  # Only title is truly required
                }
            },
            {
                "name": "query_database",
                "description": "Query the database for information about existing events, users, or bookings",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string", 
                            "enum": ["similar_events", "user_history", "date_conflicts", "venue_usage"],
                            "description": "Type of query to perform"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Query filters (e.g., date range, event type, age range)"
                        }
                    },
                    "required": ["query_type"]
                }
            },
            {
                "name": "suggest_event_details",
                "description": "Get intelligent suggestions for event details based on partial information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "partial_event": {"type": "object", "description": "Partial event information"},
                        "suggestion_type": {
                            "type": "string",
                            "enum": ["pricing", "timing", "capacity", "venue", "duration"],
                            "description": "What type of suggestion to generate"
                        }
                    },
                    "required": ["suggestion_type"]
                }
            },
            {
                "name": "validate_event_data",
                "description": "Validate event data for potential issues or conflicts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_data": {"type": "object", "description": "Event data to validate"}
                    },
                    "required": ["event_data"]
                }
            }
        ]
    
    async def create_event_draft(self, **kwargs) -> Dict[str, Any]:
        """Create a draft event using the dynamic schema"""
        try:
            # Filter kwargs to only include valid schema fields
            event_data = {}
            for key, value in kwargs.items():
                if key in self.event_schema and value is not None:
                    event_data[key] = value
            
            # Ensure required fields
            if not event_data.get("title"):
                return {"error": "Event title is required"}
            
            # Set defaults for missing fields
            if "event_type" not in event_data:
                event_data["event_type"] = "homeschool"
            
            if "date" not in event_data:
                event_data["date"] = datetime.now() + timedelta(days=7)  # Default to next week
            
            return {
                "success": True,
                "message": "Event draft created successfully",
                "event_data": event_data,
                "schema_used": self.event_schema
            }
            
        except Exception as e:
            return {"error": f"Failed to create event draft: {str(e)}"}
    
    async def query_database(self, query_type: str, filters: Dict = None) -> Dict[str, Any]:
        """Query the database for relevant information"""
        try:
            filters = filters or {}
            
            if query_type == "similar_events":
                # Find similar events based on filters
                query = self.db.query(Event)
                
                if "event_type" in filters:
                    query = query.filter(Event.event_type == filters["event_type"])
                if "age_range" in filters:
                    min_age, max_age = filters["age_range"]
                    query = query.filter(Event.min_age >= min_age, Event.max_age <= max_age)
                
                events = query.limit(5).all()
                return {
                    "similar_events": [
                        {
                            "title": event.title,
                            "cost": event.cost,
                            "max_pupils": event.max_pupils,
                            "location": event.location,
                            "event_type": event.event_type
                        }
                        for event in events
                    ]
                }
            
            elif query_type == "user_history":
                # Get user's event creation history
                user_events = self.db.query(Event).limit(10).all()  # In real system, filter by creator
                return {
                    "user_events": [
                        {
                            "title": event.title,
                            "date": event.date.isoformat() if event.date else None,
                            "event_type": event.event_type,
                            "cost": event.cost
                        }
                        for event in user_events
                    ]
                }
            
            elif query_type == "date_conflicts":
                # Check for date conflicts
                target_date = filters.get("date")
                if target_date:
                    conflicts = self.db.query(Event).filter(Event.date == target_date).all()
                    return {
                        "conflicts": len(conflicts),
                        "conflicting_events": [event.title for event in conflicts]
                    }
            
            return {"error": f"Unknown query type: {query_type}"}
            
        except Exception as e:
            return {"error": f"Database query failed: {str(e)}"}
    
    async def suggest_event_details(self, suggestion_type: str, partial_event: Dict = None) -> Dict[str, Any]:
        """Generate intelligent suggestions based on partial event data"""
        try:
            partial_event = partial_event or {}
            
            if suggestion_type == "pricing":
                # Suggest pricing based on similar events
                similar_events = await self.query_database("similar_events", {
                    "event_type": partial_event.get("event_type", "homeschool")
                })
                
                if similar_events.get("similar_events"):
                    costs = [e["cost"] for e in similar_events["similar_events"] if e["cost"]]
                    if costs:
                        avg_cost = sum(costs) / len(costs)
                        return {
                            "suggested_price": round(avg_cost, 2),
                            "price_range": {"min": min(costs), "max": max(costs)},
                            "reasoning": f"Based on {len(costs)} similar events"
                        }
                
                return {"suggested_price": 25.0, "reasoning": "Default pricing for homeschool events"}
            
            elif suggestion_type == "capacity":
                event_type = partial_event.get("event_type", "homeschool")
                if event_type == "homeschool":
                    return {"suggested_capacity": 20, "reasoning": "Typical homeschool group size"}
                else:
                    return {"suggested_capacity": 30, "reasoning": "Standard event capacity"}
            
            elif suggestion_type == "timing":
                return {
                    "suggested_times": [
                        {"day": "Saturday", "time": "10:00 AM", "reasoning": "Popular weekend morning slot"},
                        {"day": "Sunday", "time": "2:00 PM", "reasoning": "Family-friendly afternoon time"}
                    ]
                }
            
            return {"error": f"Unknown suggestion type: {suggestion_type}"}
            
        except Exception as e:
            return {"error": f"Suggestion generation failed: {str(e)}"}
    
    async def validate_event_data(self, event_data: Dict) -> Dict[str, Any]:
        """Validate event data for potential issues"""
        try:
            issues = []
            warnings = []
            
            # Check required fields
            if not event_data.get("title"):
                issues.append("Event title is required")
            
            # Check age constraints
            min_age = event_data.get("min_age")
            max_age = event_data.get("max_age")
            if min_age and max_age and min_age > max_age:
                issues.append("Minimum age cannot be greater than maximum age")
            
            # Check capacity
            capacity = event_data.get("max_pupils")
            if capacity and capacity < 1:
                issues.append("Event capacity must be at least 1")
            elif capacity and capacity > 100:
                warnings.append("Large event capacity - consider logistics")
            
            # Check cost
            cost = event_data.get("cost")
            if cost and cost < 0:
                issues.append("Event cost cannot be negative")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "validated_data": event_data
            }
            
        except Exception as e:
            return {"error": f"Validation failed: {str(e)}"}

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with arguments"""
        try:
            if tool_name == "create_event_draft":
                return await self.create_event_draft(**arguments)
            elif tool_name == "query_database":
                return await self.query_database(**arguments)
            elif tool_name == "suggest_event_details":
                return await self.suggest_event_details(**arguments)
            elif tool_name == "validate_event_data":
                return await self.validate_event_data(**arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

# Backward compatibility - keep the old class name as an alias
EventCreationTools = DynamicEventTools

# Function router for the AI to call tools
async def execute_tool_call(
    tool_name: str, 
    arguments: Dict[str, Any], 
    tools: DynamicEventTools
) -> Dict[str, Any]:
    """Execute a tool call from the AI"""
    
    try:
        if tool_name == "create_event_draft":
            return await tools.create_event_draft(**arguments)
        elif tool_name == "query_database":
            return await tools.query_database(**arguments)
        elif tool_name == "suggest_event_details":
            return await tools.suggest_event_details(**arguments)
        elif tool_name == "validate_event_data":
            return await tools.validate_event_data(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"} 