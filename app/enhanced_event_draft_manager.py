"""
Enhanced Event Draft Manager
Handles complex event creation with tickets, pricing tiers, sessions, add-ons, and more.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models import Event, TicketType, AgentSession
from app.ai.tools.enhanced_event_tools import EnhancedEventTools

logger = logging.getLogger(__name__)

class EnhancedEventDraftManager:
    """Enhanced draft manager for complex events"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def save_event_draft(self, session_id: str, draft_data: Dict[str, Any], source: str = "ai_tool") -> bool:
        """Save complex event draft data"""
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not agent_session:
                return False
            
            if not agent_session.memory:
                agent_session.memory = {}
            
            draft_entry = {
                "event_data": draft_data.get("event_data", {}),
                "tickets": draft_data.get("tickets", []),
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "version": 1
            }
            
            agent_session.memory["current_event_draft"] = draft_entry
            agent_session.updated_at = datetime.now()
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save enhanced event draft: {e}")
            return False
    
    def get_current_draft(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current event draft"""
        try:
            agent_session = self.db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not agent_session or not agent_session.memory:
                return None
            
            return agent_session.memory.get("current_event_draft")
            
        except Exception as e:
            self.logger.error(f"Failed to get current draft: {e}")
            return None
    
    def create_event_from_draft(self, session_id: str, user_id: int) -> Dict[str, Any]:
        """Create actual Event from draft"""
        try:
            draft_data = self.get_current_draft(session_id)
            if not draft_data:
                return {
                    "success": False,
                    "error": "No event draft found"
                }
            
            # Create basic event for now
            event_data = draft_data.get("event_data", {})
            event_data["created_by"] = user_id
            
            # Parse dates
            if event_data.get("date") and isinstance(event_data["date"], str):
                event_data["date"] = datetime.fromisoformat(event_data["date"].replace("Z", "+00:00"))
            
            # Create event
            event = Event(**self._clean_event_data(event_data))
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            
            return {
                "success": True,
                "event": event,
                "message": f"Event '{event.title}' created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create event: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Failed to create event: {str(e)}"
            }
    
    def _clean_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean event data for Event model"""
        valid_fields = {col.name for col in Event.__table__.columns}
        return {k: v for k, v in event_data.items() if k in valid_fields} 