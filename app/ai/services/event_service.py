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
                    "success": True,
                    "message": "No event draft created yet. Start describing your event to see it appear here!",
                    "empty_state": True
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
            
            # Handle empty state (no draft yet)
            if preview_data.get("empty_state"):
                return f"""
                <div class="empty-state">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📅</div>
                    <h4>No Event Data Yet</h4>
                    <p>Start describing your event in the chat, and watch it appear here!</p>
                </div>
                """
                
            event = preview_data["event_preview"]
            fields = preview_data["event_fields"]
            can_create = preview_data["can_create_event"]
            
            # Generate enhanced event card HTML
            preview_html = self._generate_event_card_html(event, fields, can_create, session_id)
            return preview_html
            
        except Exception as e:
            self.logger.error(f"Failed to generate event preview HTML: {e}")
            return f"""
            <div class="alert alert-error">
                <h4>❌ Preview Error</h4>
                <p>Unable to generate event preview: {str(e)}</p>
            </div>
            """
    
    def _generate_event_card_html(self, event: Dict[str, Any], fields: List[Dict], can_create: bool, session_id: str) -> str:
        """Generate a beautiful event card preview"""
        
        # Extract key event data
        title = event.get("title", "Untitled Event")
        subtitle = event.get("subtitle", "")
        description = event.get("description") or event.get("short_description", "")
        date_str = event.get("date", "")
        location = event.get("location") or event.get("venue_name", "")
        event_type = event.get("event_type", "homeschool")
        cost = event.get("cost")
        max_participants = event.get("max_pupils") or event.get("max_participants")
        min_age = event.get("min_age")
        max_age = event.get("max_age")
        venue_type = event.get("venue_type", "physical")
        
        # Format date
        formatted_date = ""
        if date_str:
            try:
                if isinstance(date_str, str):
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
                else:
                    formatted_date = date_str.strftime("%A, %B %d, %Y at %I:%M %p")
            except:
                formatted_date = str(date_str)
        
        # Format price
        price_display = ""
        if cost is not None and cost > 0:
            price_display = f"${float(cost):.2f}"
        elif event.get("is_free"):
            price_display = "FREE"
        
        # Generate highlights
        highlights = []
        if venue_type and venue_type != "physical":
            highlights.append(f"🌐 {venue_type.title()}")
        if min_age and max_age:
            highlights.append(f"👶 Ages {min_age}-{max_age}")
        elif min_age:
            highlights.append(f"👶 Ages {min_age}+")
        if max_participants:
            highlights.append(f"👥 Max {max_participants}")
        if price_display:
            highlights.append(f"💰 {price_display}")
        
        # Event type badge
        event_type_display = event_type.replace("_", " ").title()
        
        return f"""
        <div class="event-preview-card">
            <!-- Event Header -->
            <div class="event-header">
                <h3 class="event-title">{title}</h3>
                <span class="event-badge">{event_type_display}</span>
            </div>
            
            {f'<div class="event-subtitle">{subtitle}</div>' if subtitle else ''}
            
            <!-- Event Meta -->
            <div class="event-meta">
                {f'<div class="event-meta-item"><span>📅</span><span>{formatted_date}</span></div>' if formatted_date else ''}
                {f'<div class="event-meta-item"><span>📍</span><span>{location}</span></div>' if location else ''}
            </div>
            
            <!-- Event Highlights -->
            {f'<div class="event-highlights">{"".join([f"<span class=\"event-highlight\">{highlight}</span>" for highlight in highlights])}</div>' if highlights else ''}
            
            <!-- Event Description -->
            {f'<div class="event-description">{description}</div>' if description else ''}
            
            <!-- Event Details Grid -->
            <div class="event-details-grid">
                {self._generate_details_grid(fields)}
            </div>
            
            <!-- Action Buttons -->
            <div class="event-actions">
                {self._generate_action_buttons(can_create, session_id)}
            </div>
        </div>
        """
    
    def _generate_details_grid(self, fields: List[Dict]) -> str:
        """Generate event details grid"""
        detail_items = []
        
        # Map field labels to icons
        icon_map = {
            "Event Title": "📝",
            "Description": "📄", 
            "Date & Time": "🕐",
            "Location": "📍",
            "Max Students": "👥",
            "Min Age": "👶",
            "Max Age": "👴",
            "Cost": "💰",
            "Image URL": "🖼️",
            "Venue Type": "🏢",
            "Event Format": "🎯",
            "Category": "🏷️",
            "Timezone": "🌍",
            "Contact Name": "👤",
            "Contact Email": "📧",
            "Contact Phone": "📞"
        }
        
        for field in fields:
            if field["value"] and field["label"] not in ["Event Title", "Description"]:  # Skip main fields
                icon = icon_map.get(field["label"], "ℹ️")
                detail_items.append(f"""
                <div class="event-detail-item">
                    <span class="event-detail-icon">{icon}</span>
                    <span class="event-detail-label">{field["label"]}:</span>
                    <span class="event-detail-value">{field["value"]}</span>
                </div>
                """)
        
        return "".join(detail_items)
    
    def _generate_action_buttons(self, can_create: bool, session_id: str) -> str:
        """Generate action buttons based on event readiness"""
        if can_create:
            return f"""
            <button class="btn btn-success" 
                    hx-post="/api/ai/chat/{session_id}/create-event"
                    hx-target="#event-preview"
                    hx-swap="innerHTML"
                    hx-include="[name='csrf_token']">
                🎉 Create Event
            </button>
            <small class="text-muted">This will create the actual event in your system.</small>
            """
        else:
            return f"""
            <div class="event-status">
                <p class="text-warning">
                    ⚠️ Event needs more details before it can be created. 
                    Continue the conversation to provide missing information.
                </p>
                <div class="completion-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 60%;"></div>
                    </div>
                    <small>60% Complete</small>
                </div>
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