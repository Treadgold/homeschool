"""
AI Event Service

This service handles AI-related event management functionality, including:
- Event preview generation from AI conversations
- Event creation from chat conversations
- HTMX event preview interfaces
- Integration with event draft manager

Extracted from main.py as part of Phase 2 AI architecture refactoring.
"""

import logging
import traceback
from typing import Dict, List, Optional, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User


class EventService:
    """Service for AI-driven event management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_event_preview(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Get event preview from AI conversation for display"""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            from app.event_draft_manager import EventDraftManager
            
            draft_manager = EventDraftManager(db)
            current_draft = draft_manager.get_current_draft(session_id)
            
            if not current_draft:
                return {
                    "success": False,
                    "error": "No event draft found for this conversation"
                }
            
            # Format event fields for display
            event_fields = self._format_event_fields(current_draft)
            
            # Check if event can be created (has required fields)
            can_create = self._can_create_event(current_draft)
            
            return {
                "success": True,
                "session_id": session_id,
                "event_preview": {
                    "title": current_draft.get("title", ""),
                    "description": current_draft.get("description", ""),
                    "date": current_draft.get("date", ""),
                    "location": current_draft.get("location", ""),
                    "max_pupils": current_draft.get("max_pupils", ""),
                    "min_age": current_draft.get("min_age", ""),
                    "max_age": current_draft.get("max_age", ""),
                    "cost": current_draft.get("cost", ""),
                    "image_url": current_draft.get("image_url", "")
                },
                "event_fields": event_fields,
                "can_create_event": can_create,
                "draft_status": "ready" if can_create else "incomplete"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event preview: {e}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Failed to get event preview: {str(e)}"
            }
    
    async def get_event_preview_html(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> str:
        """HTMX endpoint for event preview display"""
        try:
            preview_data = await self.get_event_preview(session_id, user, db)
            
            if not preview_data["success"]:
                return f"""
                <div class="alert alert-warning">
                    <h4>⚠️ No Event Preview Available</h4>
                    <p>{preview_data.get("error", "Unable to generate event preview")}</p>
                </div>
                """
                
            event = preview_data["event_preview"]
            fields = preview_data["event_fields"]
            can_create = preview_data["can_create_event"]
            
            # Generate HTML for event preview
            preview_html = f"""
            <div class="event-preview">
                <h3>📅 Event Preview</h3>
                <div class="event-details">
            """
            
            # Add event fields
            for field in fields:
                if field["value"]:
                    preview_html += f"""
                    <div class="event-field">
                        <strong>{field["label"]}:</strong> 
                        <span class="field-value">{field["value"]}</span>
                    </div>
                    """
            
            # Add create button if event is ready
            if can_create:
                preview_html += f"""
                </div>
                <div class="event-actions">
                    <button class="btn btn-success" 
                            hx-post="/api/ai/chat/{session_id}/create-event"
                            hx-target="#event-preview"
                            hx-swap="innerHTML"
                            hx-include="[name='csrf_token']">
                        🎉 Create Event
                    </button>
                    <small class="text-muted">This will create the actual event in your system.</small>
                </div>
                """
            else:
                preview_html += f"""
                </div>
                <div class="event-actions">
                    <p class="text-warning">
                        ⚠️ Event needs more details before it can be created. 
                        Continue the conversation to provide missing information.
                    </p>
                </div>
                """
            
            preview_html += "</div>"
            return preview_html
            
        except Exception as e:
            self.logger.error(f"Failed to generate event preview HTML: {e}")
            return f"""
            <div class="alert alert-error">
                <h4>❌ Preview Error</h4>
                <p>Unable to generate event preview: {str(e)}</p>
            </div>
            """
    
    async def create_event_from_chat(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Create an actual event from the AI conversation using the dynamic connection"""
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        try:
            # Use the dynamic connection system
            from app.event_draft_manager import EventDraftManager
            
            draft_manager = EventDraftManager(db)
            result = draft_manager.create_event_from_draft(session_id, user.id)
            
            if result["success"]:
                # Add success message to conversation
                try:
                    from app.models import ChatMessage
                    success_message = ChatMessage(
                        conversation_id=session_id,
                        role='assistant',
                        content=f"🎉 Perfect! Your event '{result['event'].title}' has been created successfully! You can view it in the events list."
                    )
                    db.add(success_message)
                    db.commit()
                except Exception as msg_error:
                    self.logger.warning(f"Failed to add success message: {msg_error}")
                
                return {
                    "success": True,
                    "event_id": result["event_id"],
                    "message": result["message"],
                    "redirect_url": f"/event/{result['event_id']}"
                }
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=result.get("error", "Failed to create event")
                )
                
        except Exception as e:
            self.logger.error(f"Failed to create event from chat: {e}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create event: {str(e)}"
            )
    
    async def create_event_from_chat_html(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> str:
        """HTMX endpoint for event creation from chat"""
        try:
            result = await self.create_event_from_chat(session_id, user, db)
            
            return f"""
            <div class="alert alert-success">
                <h4>🎉 Event Created Successfully!</h4>
                <p>{result["message"]}</p>
                <a href="{result["redirect_url"]}" class="btn btn-primary">
                    View Event
                </a>
            </div>
            """
            
        except HTTPException as he:
            return f"""
            <div class="alert alert-error">
                <h4>❌ Event Creation Failed</h4>
                <p>{he.detail}</p>
                <button class="btn btn-secondary" onclick="location.reload()">
                    🔄 Try Again
                </button>
            </div>
            """
        except Exception as e:
            self.logger.error(f"Failed to create event HTML response: {e}")
            return f"""
            <div class="alert alert-error">
                <h4>❌ Unexpected Error</h4>
                <p>An unexpected error occurred: {str(e)}</p>
                <button class="btn btn-secondary" onclick="location.reload()">
                    🔄 Reload Page
                </button>
            </div>
            """
    
    def _format_event_fields(self, event_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Format event data into display fields"""
        fields = [
            {"label": "Event Title", "value": event_data.get("title", ""), "required": True},
            {"label": "Description", "value": event_data.get("description", ""), "required": False},
            {"label": "Date & Time", "value": event_data.get("date", ""), "required": True},
            {"label": "Location", "value": event_data.get("location", ""), "required": False},
            {"label": "Max Students", "value": str(event_data.get("max_pupils", "")), "required": False},
            {"label": "Min Age", "value": str(event_data.get("min_age", "")), "required": False},
            {"label": "Max Age", "value": str(event_data.get("max_age", "")), "required": False},
            {"label": "Cost", "value": f"${event_data.get('cost', '')}" if event_data.get("cost") else "", "required": False},
            {"label": "Image URL", "value": event_data.get("image_url", ""), "required": False}
        ]
        
        # Filter out empty fields for display
        return [field for field in fields if field["value"]]
    
    def _can_create_event(self, event_data: Dict[str, Any]) -> bool:
        """Check if event has required fields for creation"""
        required_fields = ["title", "date"]
        return all(event_data.get(field) for field in required_fields)
    
    def get_ai_create_event_page_data(self, user: User) -> Dict[str, Any]:
        """Get data for the AI event creation page"""
        from app.main import generate_csrf_token
        
        return {
            "current_user": user,
            "csrf_token": generate_csrf_token()
        } 