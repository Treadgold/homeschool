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
chat_service = ChatService()
health_service = HealthService()
model_service = ModelService()
event_service = EventService()

# Create AI router without prefix (frontend expects direct routes)
ai_router = APIRouter(tags=["AI System"])

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

@ai_router.post("/chat/new")
async def start_new_chat(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user)
):
    """Start a new chat session"""
    return await chat_service.start_new_chat(user, db)


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


# ===== ADMIN ENDPOINTS =====

@ai_router.get("/admin/ai-models", response_class=HTMLResponse)
async def admin_ai_models(request: Request, user: User = Depends(require_admin_user)):
    """Show AI model configuration page"""
    return model_service.get_available_models(request, user)

@ai_router.post("/admin/ai-models/set-current")
async def set_current_ai_model(
    request: Request,
    model_key: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(require_admin_user)
):
    """
    Set the current AI model
    Extracted from main.py set_current_ai_model()
    """
    try:
        return await model_service.set_current_model(model_key, user, csrf_token)
        
    except Exception as e:
        logger.error(f"Failed to set AI model: {e}")
        return {
            "success": False,
            "message": f"Failed to set AI model: {str(e)}"
        }


@ai_router.post("/admin/ai-models/{model_key}/test")
async def test_ai_model(
    model_key: str,
    request: Request,
    csrf_token: str = Form(...),
    user: User = Depends(require_authenticated_user)
):
    """
    Test an AI model with chat and function calling capabilities
    Extracted from main.py test_ai_model()
    """
    try:
        return await model_service.test_model(model_key, user, csrf_token)
        
    except Exception as e:
        logger.error(f"Failed to test AI model: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Model testing failed"
        }


@ai_router.get("/models/available")
async def get_available_ai_models(user: User = Depends(require_authenticated_user)):
    """Get list of available AI models (API endpoint)"""
    return model_service.get_available_models_api(user)


@ai_router.post("/admin/ai-models/refresh-ollama")
async def refresh_ollama_models(
    request: Request,
    csrf_token: str = Form(...),
    user: User = Depends(require_admin_user)
):
    """Refresh available Ollama models"""
    return await model_service.refresh_ollama_models(user, csrf_token)


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

@ai_router.get("/ai-create-event", response_class=HTMLResponse)
async def ai_create_event_page(
    request: Request,
    user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """
    AI event creation page - main interface for AI-powered event creation
    This is the route the frontend expects for AI event creation
    """
    try:
        return await chat_service.initialize_chat_session(user, db)
        
    except Exception as e:
        return f"""
        <div class="alert alert-error">
            <h4>❌ Failed to Initialize AI Event Creation</h4>
            <p>Error: {str(e)}</p>
        </div>
        """


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
        return await chat_service.initialize_chat_session(user, db)
        
    except Exception as e:
        return f"""
        <div class="alert alert-error">
            <h4>❌ Failed to Initialize AI</h4>
            <p>Error: {str(e)}</p>
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
        return await chat_service.process_chat_message(session_id, message, user, db)
        
    except Exception as e:
        return f"""
        <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">❌ Error: {str(e)}</div>
        </div>
        """


@ai_router.post("/event-preview", response_class=HTMLResponse)
async def ai_event_preview_htmx(
    request: Request,
    session_id: str = Form(...),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    """
    HTMX endpoint for event preview from AI conversation
    Extracted from main.py ai_event_preview_htmx()
    """
    return await event_service.get_event_preview_html(session_id, user, db)


# ===== ERROR HANDLERS =====
# Note: Exception handlers are implemented at the service level
# APIRouter doesn't support app-level exception handlers


# ===== PLACEHOLDER ENDPOINTS FOR FUTURE IMPLEMENTATION =====

# These endpoints exist in main.py but will be implemented in later phases
placeholder_endpoints = [
    "/event-preview",
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