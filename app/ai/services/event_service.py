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
            
            # Proof and enhance the draft before preview
            current_draft = self.proof_event_description(current_draft)
            
            # Format event fields for display
            event_fields = self._format_event_fields(current_draft)
            
            # Check if event can be created (has required fields)
            can_create = self._can_create_event(current_draft)
            
            # Optionally, get previous draft (not implemented here, so pass None)
            critical_status = self.get_critical_field_status(current_draft, previous=None)
            
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
                "draft_status": "ready" if can_create else "incomplete",
                "critical_field_status": critical_status
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
        try:
            if cost is not None and float(cost) > 0:
                price_display = f"${float(cost):.2f}"
            elif event.get("is_free"):
                price_display = "FREE"
        except Exception:
            price_display = str(cost) if cost is not None else ""
        
        # Generate highlights
        highlights = []
        try:
            min_age_val = int(min_age) if min_age not in (None, "") else None
        except Exception:
            min_age_val = None
        try:
            max_age_val = int(max_age) if max_age not in (None, "") else None
        except Exception:
            max_age_val = None
        try:
            max_participants_val = int(max_participants) if max_participants not in (None, "") else None
        except Exception:
            max_participants_val = None

        if venue_type and venue_type != "physical":
            highlights.append(f"🌐 {venue_type.title()}")
        if min_age_val and max_age_val:
            highlights.append(f"👶 Ages {min_age_val}-{max_age_val}")
        elif min_age_val:
            highlights.append(f"👶 Ages {min_age_val}+")
        if max_participants_val:
            highlights.append(f"👥 Max {max_participants_val}")
        if price_display:
            highlights.append(f"�� {price_display}")
        
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
    
    def proof_event_description(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Proof and enhance the event description and key fields for preview."""
        # Copy to avoid mutating input
        draft = dict(draft)
        description = draft.get("description", "")
        title = draft.get("title", "Untitled Event")
        date = draft.get("date", None)
        location = draft.get("location", None)
        cost = draft.get("cost", None)
        min_age = draft.get("min_age", None)
        max_age = draft.get("max_age", None)
        max_pupils = draft.get("max_pupils", None)

        # Build a list of missing details to add to the description
        details = []
        if date and str(date) not in description:
            details.append(f"Date: {date}")
        if location and location not in description:
            details.append(f"Location: {location}")
        if cost not in (None, "") and (str(cost) not in description and "$" not in description):
            try:
                cost_val = float(cost)
                if cost_val > 0:
                    details.append(f"Cost: ${cost_val:.2f}")
                else:
                    details.append("Cost: Free")
            except Exception:
                details.append(f"Cost: {cost}")
        if min_age and (f"Ages {min_age}" not in description):
            if max_age:
                details.append(f"Ages: {min_age}-{max_age}")
            else:
                details.append(f"Ages: {min_age}+")
        if max_pupils and (str(max_pupils) not in description):
            details.append(f"Max participants: {max_pupils}")

        # Add missing details to the description
        if details:
            if description:
                description = description.strip()
                if not description.endswith("."):
                    description += "."
                description += " " + " ".join(details)
            else:
                description = " ".join(details)
        # Optionally, rephrase for clarity (simple version)
        description = description.replace("..", ".")
        draft["description"] = description.strip()
        return draft 

    def get_critical_field_status(self, current: dict, previous: dict = None) -> dict:
        """Check which critical fields are present, missing, or newly added."""
        # Determine event format/type
        event_format = (current.get("event_format") or "").lower()
        is_in_person = event_format == "in_person"
        is_online = event_format == "online"
        is_hybrid = event_format == "hybrid"

        # Define required fields
        required_fields = [
            ("title", "Event Title"),
            ("event_type", "Event Type"),
            ("short_description", "Short Description"),
            ("start_date", "Start Date & Time"),
            ("event_format", "Event Format"),
        ]
        # Pricing: at least one of these must be present
        pricing_fields = ["is_free", "cost", "ticket_price"]
        # Location required for in-person/hybrid
        if is_in_person or is_hybrid:
            required_fields.append(("location", "Location"))
        # Online meeting link required for online/hybrid
        if is_online or is_hybrid:
            required_fields.append(("online_meeting_link", "Online Meeting Link"))

        # Check which are present
        present = set()
        for key, _ in required_fields:
            val = current.get(key)
            if val not in (None, ""):
                present.add(key)
        # Pricing logic
        has_pricing = False
        if current.get("is_free") or (current.get("cost") and float(current.get("cost") or 0) > 0):
            has_pricing = True
        elif current.get("ticket_price"):
            try:
                if float(current["ticket_price"]) > 0:
                    has_pricing = True
            except Exception:
                pass
        if has_pricing:
            present.add("pricing")
        else:
            # Add a pseudo-field for missing pricing
            required_fields.append(("pricing", "Pricing (Cost, Ticket, or Free)"))

        # Determine missing fields
        missing = [label for key, label in required_fields if key not in present]

        # Determine added fields (if previous provided)
        added = []
        if previous:
            for key, label in required_fields:
                prev_val = previous.get(key) if previous else None
                curr_val = current.get(key)
                if (curr_val not in (None, "")) and (prev_val in (None, "")):
                    added.append(label)
            # Pricing
            prev_pricing = previous.get("is_free") or (previous.get("cost") and float(previous.get("cost") or 0) > 0) or (previous.get("ticket_price") and float(previous["ticket_price"]) > 0)
            curr_pricing = has_pricing
            if curr_pricing and not prev_pricing:
                added.append("Pricing (Cost, Ticket, or Free)")
        else:
            # If no previous, all present fields are 'added'
            added = [label for key, label in required_fields if key in present]
            if has_pricing:
                added.append("Pricing (Cost, Ticket, or Free)")

        all_present = len(missing) == 0
        return {"added": added, "missing": missing, "all_present": all_present} 