"""
AI Router - All AI-related FastAPI endpoints
This router contains all AI functionality extracted from main.py
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging

from app.database import get_db
from app.models import User
from .dependencies import (
    require_authenticated_user,
    require_admin_user,
    get_ai_model_info,
    check_ai_system_health,
    validate_chat_message,
    validate_session_id,
    get_ai_config,
    AISystemError,
    AIProviderError,
    ChatSessionError
)
from .schemas.chat import (
    StartChatRequest,
    SendMessageRequest,
    CreateEventRequest,
    StartChatResponse,
    ChatResponse,
    CreateEventResponse,
    ChatError
)
from .schemas.health import (
    SystemHealth,
    HealthSummary,
    MigrationResult
)
from .services import ChatService, HealthService, ModelService, EventService

logger = logging.getLogger(__name__)

# Initialize service instances
print("🤖 Initializing AI services...")
chat_service = ChatService()
health_service = HealthService()
model_service = ModelService()
event_service = EventService()
print("✅ AI services initialized")

# Create AI router without prefix (frontend expects direct routes)
ai_router = APIRouter(tags=["AI System"])
print("🚦 AI router created with 16+ endpoints")

# Log when AI module is fully loaded
logger.info("AI Router module loaded with services: Chat, Health, Model, Event")

# ===== CHAT ENDPOINTS =====

@ai_router.post("/chat/start")
async def start_ai_chat(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user)
):
    """
    Start a new AI chat session
    Extracted from main.py start_ai_chat()
    """
    try:
        return await chat_service.start_chat_session(user, db)
        
    except AISystemError:
        raise
    except Exception as e:
        logger.error(f"Failed to start AI chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start AI chat session"
        )


@ai_router.post("/chat/{session_id}/message")
async def send_chat_message(
    session_id: str,
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user)
):
    """
    Send a message to the AI agent
    Extracted from main.py send_chat_message()
    """
    try:
        # Validate inputs
        session_id = validate_session_id(session_id)
        message = validate_chat_message(message)
        
        return await chat_service.send_chat_message(session_id, message, user, db)
        
    except AISystemError:
        raise
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@ai_router.post("/chat/{session_id}/create-event")
async def create_event_from_chat(
    session_id: str, 
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_user)
):
    """Create an event from AI chat conversation"""
    return await event_service.create_event_from_chat(session_id, user, db)

@ai_router.get("/chat/{session_id}/status") 
async def get_chat_status(
    session_id: str, 
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user)
):
    """Get chat session status"""
    return await chat_service.get_chat_status(session_id, user, db)

@ai_router.post("/chat/new", response_class=HTMLResponse)
async def start_new_chat(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user)
):
    """Start a new chat session and return HTML for HTMX"""
    try:
        # Get the new session data
        session_data = await chat_service.start_new_chat(user, db)
        session_id = session_data.get('session_id', '')
        
        # Return proper HTML for the chat container with preview refresh trigger
        return f"""
        <div class="chat-container" id="chat-container">
            <input type="hidden" name="session_id" value="{session_id}">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">Welcome! How can I help you create an event today?</div>
                </div>
            </div>
            
            <div class="chat-input">
                <form hx-post="/chat/message" 
                      hx-target="#chatMessages" 
                      hx-swap="beforeend"
                      hx-on::after-request="this.reset(); document.getElementById('messageInput').focus()">
                    <input type="hidden" name="session_id" value="{session_id}">
                    <textarea name="message" 
                             id="messageInput"
                             class="chat-textarea"
                             placeholder="Describe your event..."
                             required></textarea>
                    <button type="submit" class="btn btn-primary">Send</button>
                </form>
            </div>
            
            <!-- Trigger preview refresh for new session -->
            <div hx-get="/event-preview?session_id={session_id}"
                 hx-target="#event-preview"
                 hx-trigger="load"
                 hx-swap="innerHTML"
                 style="display: none;">
            </div>
        </div>
        """
    except Exception as e:
        logger.error(f"Failed to start new chat: {e}")
        return f"""
        <div class="alert alert-danger">
            <strong>❌ Error:</strong> Failed to start new chat session. Please try refreshing the page.
            <br><small>Error: {str(e)}</small>
        </div>
        """


# ===== HEALTH ENDPOINTS =====

@ai_router.get("/health")
async def ai_health_check(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    Comprehensive AI system health check
    Extracted from main.py ai_health_check()
    """
    try:
        return await health_service.get_health_check_response(db)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@ai_router.get("/health-status", response_class=HTMLResponse)
async def ai_health_status_htmx(
    request: Request,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX endpoint for health status display
    Extracted from main.py ai_health_status_htmx()
    """
    try:
        return await health_service.get_health_status_html(user, db)
        
    except Exception as e:
        logger.error(f"Health status check failed: {e}")
        return f"""
        <div class="alert alert-error">
            <h4>❌ Health Check Failed</h4>
            <p>Unable to check system status: {str(e)}</p>
        </div>
        """


# ===== ADMIN ENDPOINTS MOVED TO MAIN ROUTER =====
# Admin endpoints are now in main.py at root level for consistency with other admin routes

@ai_router.get("/models/available")
async def get_available_ai_models(user: User = Depends(require_authenticated_user)):
    """Get list of available AI models (API endpoint)"""
    return model_service.get_available_models_api(user)


@ai_router.get("/models/current")
async def get_current_model_info(user: User = Depends(require_authenticated_user)):
    """Get information about the currently active AI model"""
    try:
        from app.ai_assistant import ai_manager
        current_model = ai_manager.current_config
        model_config = ai_manager.get_current_model_config()
        
        return {
            "current_model": current_model,
            "provider": model_config.provider if model_config else "unknown",
            "model_name": model_config.model_name if model_config else "unknown",
            "max_tokens": model_config.max_tokens if model_config else 1000,
            "temperature": model_config.temperature if model_config else 0.7
        }
    except Exception as e:
        logger.error(f"Failed to get current model info: {e}")
        return {
            "current_model": "unknown",
            "provider": "unknown", 
            "model_name": "unknown",
            "max_tokens": 1000,
            "temperature": 0.7
        }

@ai_router.post("/clear-queue")
async def clear_ai_request_queue(
    user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Clear the AI request queue in case of issues"""
    return await model_service.clear_request_queue(user, db)


@ai_router.post("/test-dynamic-connection")
async def test_dynamic_connection(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """Test the dynamic connection between AI tools and event creation API"""
    return await model_service.test_dynamic_connection(user, db)


# ===== MIGRATION ENDPOINTS =====

@ai_router.post("/migrate", response_class=HTMLResponse)
async def run_migration(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_user)
):
    """Run database migration for AI agent tables"""
    return await health_service.run_database_migration(user, db)


@ai_router.get("/migrate/debug")
async def debug_migration_info(
    request: Request,
    user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Debug migration info - shows what would happen without running"""
    return health_service.get_migration_debug_info(user, db)


# ===== HTMX ENDPOINTS =====

# Main AI create event page is now handled at root level in main.py
# This keeps the API endpoints separate from the main page route


@ai_router.get("/chat/init", response_class=HTMLResponse)
async def ai_chat_init_htmx(
    request: Request,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX endpoint to initialize chat interface
    Extracted from main.py ai_chat_init_htmx()
    """
    try:
        # Get the session data from the service
        session_data = await chat_service.initialize_chat_session(user, db)
        
        # Return proper HTML instead of JSON
        session_id = session_data.get('session_id', '')
        return f"""
        <div class="chat-container" id="chat-container">
            <input type="hidden" name="session_id" value="{session_id}">
            <div class="chat-messages" id="chatMessages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">{session_data.get('conversation_history', [{'content': 'Hello! How can I help you create an event?'}])[0]['content']}</div>
                </div>
            </div>
            
            <div class="chat-input">
                <form hx-post="/chat/message" 
                      hx-target="#chatMessages" 
                      hx-swap="beforeend"
                      hx-on::after-request="this.reset(); document.getElementById('messageInput').focus()">
                    <input type="hidden" name="session_id" value="{session_id}">
                    <textarea name="message" 
                             id="messageInput"
                             class="chat-textarea"
                             placeholder="Describe your event..."
                             required></textarea>
                    <button type="submit" class="btn btn-primary">Send</button>
                </form>
            </div>
        </div>
        """
    except Exception as e:
        logger.error(f"Failed to initialize chat: {e}")
        return f"""
        <div class="alert alert-danger">
            <strong>❌ Error:</strong> Failed to initialize chat session. Please try refreshing the page.
            <br><small>Error: {str(e)}</small>
        </div>
        """


@ai_router.post("/chat/message", response_class=HTMLResponse)
async def ai_chat_message_htmx(
    request: Request,
    session_id: str = Form(...),
    message: str = Form(...),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX endpoint for sending chat messages
    Extracted from main.py ai_chat_message_htmx()
    """
    try:
        # First add the user message to the chat
        user_message_html = f"""
        <div class="message user">
            <div class="message-avatar">👤</div>
            <div class="message-content">{message}</div>
        </div>
        """
        
        # Process the message through the chat service
        result = await chat_service.send_chat_message(session_id, message, user, db)
        
        # Get the AI response and format as HTML
        ai_response = result.get('ai_response', 'I apologize, but I encountered an error processing your message.')
        
        # Create the assistant response HTML
        assistant_message_html = f"""
        <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">{ai_response}</div>
        </div>
        """
        
        # Update event preview if we have extracted info OR if tools were called
        event_preview_html = ""
        if result.get('event_preview') or result.get('tool_calls_made'):
            event_preview_html = f"""
            <div hx-get="/event-preview?session_id={session_id}"
                 hx-target="#event-preview" 
                 hx-swap="innerHTML"
                 hx-trigger="load"></div>
            """
        
        # Return both user and assistant messages with preview trigger
        response_html = user_message_html + assistant_message_html + event_preview_html
        
        # Add HTMX trigger to update event preview
        if result.get('tool_calls_made') or result.get('event_data_extracted'):
            response_html += """
            <div hx-trigger="load" 
                 hx-get="/event-preview" 
                 hx-vals='{"session_id": "%s"}'
                 hx-target="#event-preview" 
                 hx-swap="innerHTML"></div>
            """ % session_id
        
        return response_html
        
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}")
        return f"""
        <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">❌ Sorry, I encountered an error: {str(e)}</div>
        </div>
        """


@ai_router.get("/event-preview", response_class=HTMLResponse)  
async def ai_event_preview_get_htmx(
    request: Request,
    session_id: Optional[str] = Query(None),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX GET endpoint for event preview from AI conversation
    """
    try:
        # If session_id is provided, use it; otherwise find active conversation
        if session_id:
            target_session_id = session_id
        else:
            # Find the user's ACTIVE chat conversation (not just most recent)
            from app.models import ChatConversation
            active_conversation = db.query(ChatConversation)\
                .filter(ChatConversation.user_id == user.id)\
                .filter(ChatConversation.status == "active")\
                .order_by(ChatConversation.updated_at.desc())\
                .first()
            
            if not active_conversation:
                return """
                <div class="empty-state">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📅</div>
                    <h4>No Event Data Yet</h4>
                    <p>Start describing your event in the chat, and watch it appear here!</p>
                </div>
                """
            
            target_session_id = str(active_conversation.id)
        
        logger.debug(f"Event preview for user {user.id}, session_id: {target_session_id}")
        
        return await event_service.get_event_preview_html(target_session_id, user, db)
        
    except Exception as e:
        logger.error(f"Error getting event preview: {e}")
        return f"""
            <div class="alert alert-error">
                <strong>Preview Error:</strong> {str(e)}
            </div>
        """


@ai_router.post("/event-preview", response_class=HTMLResponse)
async def ai_event_preview_htmx(
    request: Request,
    session_id: Optional[str] = Form(None),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX endpoint for event preview from AI conversation
    Extracted from main.py ai_event_preview_htmx()
    """
    if not session_id:
        return """
        <div class="empty-state">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📅</div>
            <h4>No Event Data Yet</h4>
            <p>Start describing your event in the chat, and watch it appear here!</p>
        </div>
        """
        
    return await event_service.get_event_preview_html(session_id, user, db)


# ===== ERROR HANDLERS =====
# Note: Exception handlers are implemented at the service level
# APIRouter doesn't support app-level exception handlers


# ===== PLACEHOLDER ENDPOINTS FOR FUTURE IMPLEMENTATION =====

# These endpoints exist in main.py but will be implemented in later phases
placeholder_endpoints = [
    "/models/available", 
    "/models/refresh-ollama",
    "/clear-queue",
    "/test-dynamic-connection"
]

for endpoint in placeholder_endpoints:
    @ai_router.get(endpoint)
    async def placeholder_endpoint(request: Request):
        return {
            "message": f"Endpoint {endpoint} will be implemented in a future phase",
            "status": "placeholder"
        }

@ai_router.get("/test-ticket-tools", response_class=HTMLResponse)
async def test_ticket_tools(
    user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Admin test endpoint to verify ticket tools work without cost averaging"""
    try:
        from app.ai.langchain_tools import create_event_draft, add_ticket_type
        from app.event_draft_manager import EventDraftManager
        
        # Find user's most recent conversation
        from app.models import ChatConversation
        recent_conversation = db.query(ChatConversation)\
            .filter(ChatConversation.user_id == user.id)\
            .order_by(ChatConversation.created_at.desc())\
            .first()
        
        if not recent_conversation:
            return "<div class='alert alert-error'>No conversation found</div>"
        
        session_id = str(recent_conversation.id)
        
        # Test 1: Create event (should NOT create cost field)
        result1 = create_event_draft.invoke({
            'session_id': session_id,
            'title': 'Test Cooking Class',
            'date': '2024-08-25T15:00:00', 
            'description': 'Admin test for ticket tools'
        })
        
        # Test 2: Add multiple tickets with different prices
        result2 = add_ticket_type.invoke({
            'session_id': session_id,
            'name': 'Child Ticket',
            'price': 20.0,
            'description': 'Ages 8-16'
        })
        
        result3 = add_ticket_type.invoke({
            'session_id': session_id,
            'name': 'Adult Ticket',
            'price': 35.0,
            'description': 'Ages 17+'
        })
        
        # Test 3: Check final draft
        draft_manager = EventDraftManager(db)
        final_draft = draft_manager.get_current_draft(session_id)
        
        # Generate results HTML
        has_cost_field = 'cost' in final_draft if final_draft else False
        ticket_count = len(final_draft.get('tickets', [])) if final_draft else 0
        
        status_class = "alert-error" if has_cost_field else "alert-success"
        status_icon = "❌" if has_cost_field else "✅"
        
        ticket_details = ""
        if final_draft and final_draft.get('tickets'):
            for i, ticket in enumerate(final_draft['tickets']):
                name = ticket.get('name', 'Unknown')
                price = ticket.get('price', 0)
                desc = ticket.get('description', '')
                ticket_details += f"<li><strong>{name}</strong>: ${price} - {desc}</li>"
        
        return f"""
        <div class="alert {status_class}">
            <h4>{status_icon} Ticket Tools Test Results</h4>
            <p><strong>Cost field averaging:</strong> {'FAILED - Cost field still present!' if has_cost_field else 'SUCCESS - Cost field removed!'}</p>
            <p><strong>Individual tickets:</strong> {ticket_count} tickets created</p>
            <p><strong>Session ID:</strong> {session_id}</p>
            
            {f'<p><strong>⚠️ Problem:</strong> Cost field = ${final_draft["cost"]}</p>' if has_cost_field else ''}
            
            <h5>📝 Tool Results:</h5>
            <ul>
                <li>Event creation: {len(result1)} characters</li>
                <li>Child ticket: {len(result2)} characters</li>  
                <li>Adult ticket: {len(result3)} characters</li>
            </ul>
            
            <h5>🎫 Tickets Created:</h5>
            <ul>{ticket_details}</ul>
            
            <button onclick="location.reload()" class="btn btn-primary">🔄 Run Test Again</button>
        </div>
        """
        
    except Exception as e:
        return f"""
        <div class="alert alert-error">
            <h4>❌ Test Failed</h4>
            <p>Error: {str(e)}</p>
        </div>
        """ 