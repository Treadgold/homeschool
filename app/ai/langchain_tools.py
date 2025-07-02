"""
LangChain-compatible tools for event creation.
These tools are now session-aware and do not contain global state.
"""
from typing import Optional
from langchain_core.tools import tool
from datetime import datetime
from decimal import Decimal
import json

@tool
def create_event_draft(session_id: str, title: str, date: Optional[str] = None, description: Optional[str] = None, end_date: Optional[str] = None, timezone: str = "Pacific/Auckland") -> str:
    """
    Create or update a basic event draft with core information for a specific session.
    Args:
        session_id: The ID of the current user's session.
        title: The title of the event.
        date: The start date and time for the event in ISO format (optional - will use a default if not provided).
        description: A detailed description of the event.
        end_date: The end date and time for multi-day events in ISO format.
        timezone: The timezone for the event, e.g., 'Pacific/Auckland'.
    """
    # Import inside function to avoid circular imports
    from app.database import get_db
    from app.event_draft_manager import EventDraftManager
    
    db_session = next(get_db())
    try:
        draft_manager = EventDraftManager(db_session)
        
        # Set default date if none provided (next Saturday)
        if not date:
            from datetime import datetime, timedelta
            next_saturday = datetime.now() + timedelta(days=(5 - datetime.now().weekday()) % 7 + 1)
            date = next_saturday.strftime("%Y-%m-%d")
        
        draft_data = {
            "title": title,
            "date": date,
            "description": description or f"Details for {title}",
            "end_date": end_date,
            "timezone": timezone
        }
        draft_manager.save_event_draft(session_id, draft_data, source="langchain_agent")
        return f"Event draft '{title}' created successfully for {date} in session {session_id}. You can now add tickets or other details."
    finally:
        db_session.close()

@tool
def add_ticket_type(session_id: str, name: str, price: float, description: Optional[str] = None, quantity_available: Optional[int] = None, max_per_order: Optional[int] = None) -> str:
    """
    Add a ticket type to the event draft for a specific session.
    Args:
        session_id: The ID of the current user's session.
        name: The name of the ticket type (e.g., 'Adult', 'Child').
        price: The price of the ticket.
        description: A description of what the ticket includes.
        quantity_available: The total number of this ticket type available.
        max_per_order: The maximum number of this ticket type that can be bought in a single order.
    """
    # Import inside function to avoid circular imports
    from app.database import get_db
    from app.event_draft_manager import EventDraftManager
    
    db_session = next(get_db())
    try:
        draft_manager = EventDraftManager(db_session)
        current_draft = draft_manager.get_current_draft(session_id)
        if not current_draft:
            return "Error: No event draft found for this session. Please create an event draft first."

        if "tickets" not in current_draft:
            current_draft["tickets"] = []
        
        ticket_data = {
            "name": name,
            "price": price,
            "description": description,
            "quantity_available": quantity_available,
            "max_per_order": max_per_order
        }
        
        current_draft["tickets"].append(ticket_data)
        draft_manager.save_event_draft(session_id, current_draft, source="langchain_agent_add_ticket")

        return f"Ticket type '{name}' with price ${price} added to the draft for '{current_draft.get('title')}' in session {session_id}."
    finally:
        db_session.close()

def get_tools_definition() -> str:
    """Returns a JSON string describing the available tools."""
    tools = [create_event_draft, add_ticket_type]
    tool_defs = []
    for t in tools:
        tool_defs.append(t.get_input_schema().schema())
    return json.dumps(tool_defs, indent=2) 