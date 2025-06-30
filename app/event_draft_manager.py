"""
Dynamic Event Draft Manager
Provides seamless connection between AI tool creation and event creation API
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import re

from app.models import Event, AgentSession, ChatConversation, ChatMessage
from app.ai_tools import DynamicEventTools

logger = logging.getLogger(__name__)

class EventDraftManager:
    """
    Dynamic connection between AI agent tool creation and actual event creation API.
    
    This class provides:
    1. Structured storage of event drafts from AI tools
    2. Reliable retrieval for event creation API
    3. Validation and transformation of draft data
    4. Audit trail of draft evolution
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _make_json_safe(self, obj):
        if isinstance(obj, dict):
            return {k: self._make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(i) for i in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def save_event_draft(
        self, 
        session_id: str, 
        draft_data: Dict[str, Any],
        source: str = "ai_tool"
    ) -> bool:
        """
        Save event draft data to agent session with structured storage.
        
        Args:
            session_id: Chat session ID
            draft_data: Event data from AI tools
            source: Source of the draft (ai_tool, user_input, etc.)
        
        Returns:
            bool: Success status
        """
        try:
            # Get agent session
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not agent_session:
                logger.error(f"No agent session found for session_id: {session_id}")
                return False
            
            # Initialize memory if needed
            if not agent_session.memory:
                agent_session.memory = {}
            
            # Create structured draft storage
            safe_draft_data = self._make_json_safe(draft_data)
            draft_entry = {
                "event_data": safe_draft_data,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "version": self._get_next_version(agent_session.memory)
            }
            
            # Store current draft
            agent_session.memory["current_event_draft"] = draft_entry
            
            # Maintain draft history
            if "draft_history" not in agent_session.memory:
                agent_session.memory["draft_history"] = []
            
            agent_session.memory["draft_history"].append(draft_entry)
            
            # Update agent session
            agent_session.updated_at = datetime.now()
            self.db.commit()
            
            logger.info(f"Saved event draft v{draft_entry['version']} for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save event draft: {e}")
            self.db.rollback()
            return False
    
    def get_current_draft(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most current event draft for a session.
        
        Args:
            session_id: Chat session ID
        
        Returns:
            Dict containing event data or None if not found
        """
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not agent_session or not agent_session.memory:
                return None
            
            current_draft = agent_session.memory.get("current_event_draft")
            if current_draft:
                return current_draft.get("event_data")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current draft: {e}")
            return None
    
    def update_draft(
        self, 
        session_id: str, 
        updates: Dict[str, Any], 
        source: str = "user_modification"
    ) -> bool:
        """
        Update existing draft with new information.
        
        Args:
            session_id: Chat session ID  
            updates: Dictionary of fields to update
            source: Source of the update
        
        Returns:
            bool: Success status
        """
        try:
            current_draft = self.get_current_draft(session_id)
            if not current_draft:
                # No existing draft, create new one
                return self.save_event_draft(session_id, updates, source)
            
            # Merge updates with existing draft
            updated_draft = {**current_draft, **updates}
            
            return self.save_event_draft(session_id, updated_draft, source)
            
        except Exception as e:
            logger.error(f"Failed to update draft: {e}")
            return False
    
    def create_event_from_draft(
        self, 
        session_id: str, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Create actual Event from the current draft.
        This is the dynamic connection point to the API.
        
        Args:
            session_id: Chat session ID
            user_id: User creating the event
        
        Returns:
            Dict with success status and event details
        """
        try:
            # Get current draft
            draft_data = self.get_current_draft(session_id)
            if not draft_data:
                return {
                    "success": False,
                    "error": "No event draft found in conversation",
                    "details": "AI has not created an event draft yet"
                }
            
            # Validate draft data
            validation_result = self._validate_draft_data(draft_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Draft data validation failed",
                    "details": validation_result["issues"]
                }
            
            # Transform draft data to Event model
            event_data = self._transform_draft_to_event(draft_data)
            
            # Create the actual Event
            new_event = Event(**event_data)
            self.db.add(new_event)
            self.db.commit()
            self.db.refresh(new_event)
            
            # Mark draft as used
            self._mark_draft_as_used(session_id, new_event.id)
            
            logger.info(f"Successfully created event {new_event.id} from draft in session {session_id}")
            
            return {
                "success": True,
                "event_id": new_event.id,
                "event": new_event,
                "message": f"Event '{new_event.title}' created successfully!"
            }
            
        except Exception as e:
            logger.error(f"Failed to create event from draft: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Failed to create event: {str(e)}",
                "details": "Database or validation error occurred"
            }
    
    def get_draft_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the evolution history of drafts for this session."""
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not agent_session or not agent_session.memory:
                return []
            
            return agent_session.memory.get("draft_history", [])
            
        except Exception as e:
            logger.error(f"Failed to get draft history: {e}")
            return []
    
    def clear_draft(self, session_id: str) -> bool:
        """Clear the current draft for a session."""
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if agent_session and agent_session.memory:
                agent_session.memory.pop("current_event_draft", None)
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to clear draft: {e}")
            return False
    
    def _get_next_version(self, memory: Dict) -> int:
        """Get next version number for draft history."""
        history = memory.get("draft_history", [])
        if not history:
            return 1
        return max(entry.get("version", 0) for entry in history) + 1
    
    def _validate_draft_data(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate draft data before creating event."""
        issues = []
        
        # Required fields
        if not draft_data.get("title"):
            issues.append("Event title is required")
        
        # Age validation
        min_age = draft_data.get("min_age")
        max_age = draft_data.get("max_age")
        if min_age and max_age and min_age > max_age:
            issues.append("Minimum age cannot be greater than maximum age")
        
        # Capacity validation
        capacity = draft_data.get("max_pupils")
        if capacity and capacity < 1:
            issues.append("Event capacity must be at least 1")
        
        # Cost validation
        cost = draft_data.get("cost")
        if cost and cost < 0:
            issues.append("Event cost cannot be negative")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _transform_draft_to_event(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform AI draft data to Event model format."""
        event_data = {}
        
        # Direct mappings
        direct_fields = [
            "title", "description", "location", "max_pupils", 
            "min_age", "max_age", "cost", "event_type"
        ]
        
        for field in direct_fields:
            if field in draft_data:
                event_data[field] = draft_data[field]
        
        # Handle date field
        if "date" in draft_data:
            date_value = draft_data["date"]
            if isinstance(date_value, str):
                try:
                    event_data["date"] = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except:
                    # Fallback to default date
                    event_data["date"] = datetime.now() + timedelta(days=7)
            elif isinstance(date_value, datetime):
                event_data["date"] = date_value
        else:
            # Default to next week
            event_data["date"] = datetime.now() + timedelta(days=7)
        
        # Set defaults
        if "event_type" not in event_data:
            event_data["event_type"] = "homeschool"
        
        if "max_pupils" not in event_data:
            event_data["max_pupils"] = 20
        
        return event_data
    
    def _mark_draft_as_used(self, session_id: str, event_id: int):
        """Mark the current draft as used to create an event."""
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if agent_session and agent_session.memory:
                current_draft = agent_session.memory.get("current_event_draft")
                if current_draft:
                    current_draft["used_to_create_event"] = event_id
                    current_draft["event_created_at"] = datetime.now().isoformat()
                
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark draft as used: {e}")


class DynamicToolIntegration:
    """
    Integration layer that connects AI tools with the EventDraftManager.
    Provides the dynamic connection the user requested.
    """
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.tools = DynamicEventTools(db, user_id)
        self.draft_manager = EventDraftManager(db)
    
    async def execute_tool_with_draft_integration(
        self, 
        session_id: str,
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute AI tool and automatically integrate results with draft management.
        This creates the dynamic connection between tools and API.
        """
        try:
            # Execute the tool
            tool_result = await self.tools.execute_tool(tool_name, arguments)
            
            # If tool created event data, save it to draft manager
            if tool_name == "create_event_draft" and tool_result.get("success"):
                event_data = tool_result.get("event_data")
                if event_data:
                    saved = self.draft_manager.save_event_draft(
                        session_id, 
                        event_data,
                        source=f"ai_tool_{tool_name}"
                    )
                    tool_result["draft_saved"] = saved
                    tool_result["can_create_event"] = saved

                    # --- NEW LOGIC: Parse and add ticket types if mentioned in arguments ---
                    ticket_types = []
                    # Example: parse arguments['description'] or similar for ticket info
                    desc = arguments.get('description') or arguments.get('notes') or ''
                    # Look for patterns like 'Children are only $17, adult tickets will be $38'
                    child_match = re.search(r'child(?:ren)?[^\d$]*(\$?\d+(?:\.\d{1,2})?)', desc, re.IGNORECASE)
                    adult_match = re.search(r'adult[^\d$]*(\$?\d+(?:\.\d{1,2})?)', desc, re.IGNORECASE)
                    if child_match:
                        price = float(child_match.group(1).replace('$',''))
                        ticket_types.append({"name": "Child", "price": price})
                    if adult_match:
                        price = float(adult_match.group(1).replace('$',''))
                        ticket_types.append({"name": "Adult", "price": price})
                    # Optionally, add more parsing for other ticket types
                    # Add each ticket type using the tool
                    for ticket in ticket_types:
                        await self.tools.execute_tool("add_ticket_type", ticket)
                    tool_result["ticket_types_added"] = ticket_types
            return tool_result
        except Exception as e:
            logger.error(f"Tool integration failed: {e}")
            return {"error": f"Tool integration failed: {str(e)}"}
    
    def create_event_from_current_draft(self, session_id: str) -> Dict[str, Any]:
        """
        Direct API to create event from current draft.
        This is the dynamic connection endpoint.
        """
        return self.draft_manager.create_event_from_draft(session_id, self.user_id) 