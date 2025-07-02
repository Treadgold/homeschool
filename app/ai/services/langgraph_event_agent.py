"""
LangGraph-based Event Creation Agent
Provides explicit workflow control and guaranteed tool execution
"""
import json
import re
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from typing_extensions import Literal

from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END, add_messages

from app.ai.langchain_tools import create_event_draft, add_ticket_type
from app.database import get_db
from app.event_draft_manager import EventDraftManager


class EventCreationState(TypedDict):
    """State for the event creation workflow"""
    # Input
    user_input: str
    session_id: str
    
    # Conversation
    messages: Annotated[List[Any], add_messages]
    
    # Extracted information
    extracted_details: Dict[str, Any]
    
    # Created resources
    event_draft: Optional[Dict[str, Any]]
    tickets: List[Dict[str, Any]]
    
    # Workflow control
    current_step: str
    needs_tickets: bool
    needs_more_tickets: bool
    user_response: str


class LangGraphEventAgent:
    """Event creation agent using LangGraph for explicit workflow control"""
    
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.llm = ChatOllama(
            model=model,
            base_url="http://host.docker.internal:11434",
            temperature=0.7,
            timeout=60
        )
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(EventCreationState)
        
        # Add nodes
        workflow.add_node("extract_details", self._extract_event_details)
        workflow.add_node("create_event", self._create_event_draft)
        workflow.add_node("check_tickets", self._check_for_tickets)
        workflow.add_node("add_ticket", self._add_ticket_type)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.add_edge(START, "extract_details")
        workflow.add_edge("extract_details", "create_event")
        workflow.add_edge("create_event", "check_tickets")
        
        # Conditional routing for tickets
        workflow.add_conditional_edges(
            "check_tickets",
            self._should_add_tickets,
            {
                "add_ticket": "add_ticket",
                "finish": "generate_response"
            }
        )
        
        workflow.add_conditional_edges(
            "add_ticket", 
            self._should_add_more_tickets,
            {
                "add_more": "add_ticket",
                "finish": "generate_response"
            }
        )
        
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _extract_event_details(self, state: EventCreationState) -> Dict[str, Any]:
        """Extract event details from user input using LLM"""
        
        # First, get any existing draft to preserve information across messages
        try:
            db = next(get_db())
            draft_manager = EventDraftManager(db)
            existing_draft = draft_manager.get_current_draft(state['session_id']) or {}
        except:
            existing_draft = {}
        
        prompt = f"""
Extract event details from this user request: "{state['user_input']}"

Current existing event information: {existing_draft}

Extract the following information if available:
- title: Event title/name
- description: Event description  
- date: Event date (YYYY-MM-DD format if possible)
- location: Event location
- ticket_info: Any ticket pricing or types mentioned (preserve existing tickets and add new ones)

For ticket_info, look for:
- Prices mentioned with $ symbol
- Age groups (kids, children, adults)
- Ticket types (general admission, VIP, etc.)

If this message is about tickets/pricing, add to existing ticket_info rather than replacing it.

Respond with a JSON object containing the extracted details.
If information is missing, use reasonable defaults or indicate "not_specified".

Example:
{{"title": "Science Fair", "description": "Kids science fair", "date": "2025-08-15", "location": "Zoo", "ticket_info": {{"kids": 10, "adults": 25}}}}
"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
            else:
                # Fallback extraction
                extracted = self._fallback_extraction(state['user_input'])
        except:
            extracted = self._fallback_extraction(state['user_input'])
        
        # Merge with existing draft to preserve accumulated information
        if existing_draft:
            # Preserve existing data, but allow updates
            for key, value in existing_draft.items():
                if key not in extracted and value:
                    extracted[key] = value
            
            # Special handling for ticket_info - merge instead of replace
            if 'ticket_info' in existing_draft and 'ticket_info' in extracted:
                merged_tickets = existing_draft['ticket_info'].copy()
                merged_tickets.update(extracted['ticket_info'])
                extracted['ticket_info'] = merged_tickets
            elif 'ticket_info' in existing_draft and 'ticket_info' not in extracted:
                extracted['ticket_info'] = existing_draft['ticket_info']
        
        return {
            "extracted_details": extracted,
            "current_step": "details_extracted",
            "messages": [HumanMessage(content=state['user_input'])]
        }
    
    def _create_event_draft(self, state: EventCreationState) -> Dict[str, Any]:
        """Create event draft - GUARANTEED EXECUTION"""
        details = state['extracted_details']
        
        # This WILL execute regardless of LLM behavior
        try:
            result = create_event_draft.invoke({
                "session_id": state['session_id'],
                "title": details.get('title', 'New Event'),
                "description": details.get('description', f"Event: {details.get('title', 'New Event')}"),
                "date": details.get('date'),
                "timezone": "Pacific/Auckland"
            })
            
            return {
                "event_draft": {"success": True, "details": details, "result": result},
                "current_step": "event_created"
            }
        except Exception as e:
            return {
                "event_draft": {"success": False, "error": str(e)},
                "current_step": "event_creation_failed"
            }
    
    def _check_for_tickets(self, state: EventCreationState) -> Dict[str, Any]:
        """Enhanced check if we need to add tickets"""
        details = state['extracted_details']
        ticket_info = details.get('ticket_info', {})
        requesting_tickets = details.get('requesting_tickets', False)
        
        # Check for tickets in multiple ways
        needs_tickets = (
            bool(ticket_info) or  # Ticket info extracted
            requesting_tickets or  # User explicitly asking for tickets
            any(word in state['user_input'].lower() for word in [
                'ticket', 'price', 'cost', '$', 'admission', 'entry',
                'kids', 'adults', 'children', 'child', 'under'
            ])
        )
        
        # Also check existing draft for ticket info
        if not needs_tickets:
            from app.event_draft_manager import EventDraftManager
            from app.database import get_db
            try:
                db = next(get_db())
                draft_manager = EventDraftManager(db)
                existing_draft = draft_manager.get_current_draft(state['session_id']) or {}
                if existing_draft.get('ticket_info'):
                    needs_tickets = True
            except:
                pass
        
        return {
            "needs_tickets": needs_tickets,
            "current_step": "checked_tickets"
        }
    
    def _add_ticket_type(self, state: EventCreationState) -> Dict[str, Any]:
        """Enhanced ticket type addition - GUARANTEED EXECUTION"""
        details = state['extracted_details']
        ticket_info = details.get('ticket_info', {})
        existing_tickets = state.get('tickets', [])
        
        print(f"DEBUG: Adding ticket type. ticket_info: {ticket_info}")
        
        # Determine what tickets to add
        if isinstance(ticket_info, dict) and ticket_info:
            for ticket_name, price in ticket_info.items():
                # Check if this ticket type already exists
                existing_names = [t.get('name', '').lower() for t in existing_tickets]
                if ticket_name.lower() not in existing_names:
                    try:
                        print(f"DEBUG: Calling add_ticket_type for {ticket_name} at ${price}")
                        
                        result = add_ticket_type.invoke({
                            "session_id": state['session_id'],
                            "name": ticket_name.title(),
                            "price": float(price),
                            "description": f"{ticket_name.title()} ticket",
                            "quantity_available": 100
                        })
                        
                        print(f"DEBUG: add_ticket_type result: {result}")
                        
                        new_ticket = {
                            "name": ticket_name.title(),
                            "price": price,
                            "result": result
                        }
                        
                        existing_tickets.append(new_ticket)
                        
                    except Exception as e:
                        print(f"DEBUG: Error adding ticket {ticket_name}: {e}")
                        return {
                            "tickets": existing_tickets,
                            "needs_more_tickets": False,
                            "current_step": "ticket_add_failed",
                            "error": str(e)
                        }
        
        # Check if more tickets needed (for workflow continuation)
        remaining_tickets = []
        if isinstance(ticket_info, dict):
            existing_names = [t.get('name', '').lower() for t in existing_tickets]
            remaining_tickets = [
                name for name in ticket_info.keys() 
                if name.lower() not in existing_names
            ]
        
        return {
            "tickets": existing_tickets,
            "needs_more_tickets": len(remaining_tickets) > 0,
            "current_step": "ticket_added" if existing_tickets else "no_tickets_added"
        }
    
    def _generate_response(self, state: EventCreationState) -> Dict[str, Any]:
        """Generate final user response"""
        event_draft = state.get('event_draft', {})
        tickets = state.get('tickets', [])
        
        if event_draft.get('success'):
            title = state['extracted_details'].get('title', 'Your event')
            response = f"Perfect! I've created your '{title}' event draft."
            
            if tickets:
                ticket_summary = ", ".join([f"{t['name']} (${t['price']})" for t in tickets])
                response += f" Added tickets: {ticket_summary}."
            
            response += " You can view the details in the preview panel."
        else:
            response = "I encountered an issue creating your event. Please try again or provide more details."
        
        return {
            "user_response": response,
            "current_step": "completed",
            "messages": [AIMessage(content=response)]
        }
    
    def _should_add_tickets(self, state: EventCreationState) -> Literal["add_ticket", "finish"]:
        """Conditional routing: should we add tickets?"""
        return "add_ticket" if state.get('needs_tickets', False) else "finish"
    
    def _should_add_more_tickets(self, state: EventCreationState) -> Literal["add_more", "finish"]:
        """Conditional routing: should we add more tickets?"""
        return "add_more" if state.get('needs_more_tickets', False) else "finish"
    
    def _fallback_extraction(self, user_input: str) -> Dict[str, Any]:
        """Enhanced fallback extraction when JSON parsing fails"""
        import re
        
        extracted = {}
        
        # Extract title (first meaningful phrase)
        words = user_input.split()
        if len(words) >= 2:
            # Look for event-like phrases
            if any(word in user_input.lower() for word in ['event', 'trip', 'class', 'workshop', 'party']):
                extracted['title'] = ' '.join(words[:6]).title()
        
        # Enhanced price extraction
        prices = re.findall(r'\$(\d+)', user_input)
        if prices:
            ticket_info = {}
            
            # Check for specific age/type mentions
            if any(word in user_input.lower() for word in ['kid', 'child', 'children', 'under']):
                if 'adult' in user_input.lower() and len(prices) >= 2:
                    # Both kids and adults mentioned
                    ticket_info['kids'] = int(prices[0])
                    ticket_info['adults'] = int(prices[1])
                else:
                    ticket_info['kids'] = int(prices[0])
            elif 'adult' in user_input.lower():
                ticket_info['adults'] = int(prices[0])
            else:
                # General ticket
                ticket_info['general'] = int(prices[0])
            
            extracted['ticket_info'] = ticket_info
        
        # Check for ticket-related keywords even without prices
        elif any(word in user_input.lower() for word in ['ticket', 'create ticket', 'add ticket']):
            # User is asking about tickets, set a flag
            extracted['requesting_tickets'] = True
        
        return extracted
    
    async def process_message(self, user_input: str) -> Dict[str, Any]:
        """Process user message through the LangGraph workflow"""
        try:
            # Initialize state
            initial_state = {
                "user_input": user_input,
                "session_id": self.session_id,
                "messages": [],
                "tickets": [],
                "current_step": "started",
                "needs_tickets": False,
                "needs_more_tickets": False
            }
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Count tools that were executed
            tools_executed = []
            if final_state.get('event_draft', {}).get('success'):
                tools_executed.append("create_event_draft")
            
            tools_executed.extend([f"add_ticket_type_{t['name']}" for t in final_state.get('tickets', [])])
            
            return {
                "output": final_state.get('user_response', 'Event processing completed.'),
                "intermediate_steps": [({"name": tool, "type": "function_call"}, "executed") for tool in tools_executed],
                "agent_type": "langgraph_event_agent",
                "success": final_state.get('event_draft', {}).get('success', False),
                "final_state": final_state
            }
            
        except Exception as e:
            return {
                "output": f"I encountered an error processing your event request: {str(e)}",
                "intermediate_steps": [],
                "agent_type": "langgraph_event_agent", 
                "success": False,
                "error": str(e)
            }


# Entry point function
async def invoke_langgraph_event_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """Main entry point for LangGraph event agent"""
    agent = LangGraphEventAgent(model, session_id)
    return await agent.process_message(user_prompt) 