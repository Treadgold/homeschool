"""
Dependency Injection for AI Module
Manages service dependencies and provides clean dependency resolution
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.database import get_db
from app.models import User


logger = logging.getLogger(__name__)


# Core Dependencies - Use auth utils to avoid circular imports
from app.utils.auth_utils import get_current_user, require_admin

def require_authenticated_user(user=Depends(get_current_user)) -> User:
    """Require an authenticated user for AI endpoints"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for AI features"
        )
    return user


def require_admin_user(user=Depends(require_admin)) -> User:
    """Require an admin user for AI admin endpoints - uses main.py require_admin"""
    return user


# Service Dependencies (to be created in Phase 2)
class ServiceContainer:
    """Container for all AI services - will be implemented in Phase 2"""
    
    def __init__(self, db: Session):
        self.db = db
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize all services - placeholder for Phase 2"""
        if self._initialized:
            return
        
        logger.info("Initializing AI service container...")
        # Services will be initialized here in Phase 2
        self._initialized = True
    
    def get_service(self, service_name: str):
        """Get a service by name - placeholder for Phase 2"""
        if not self._initialized:
            self.initialize()
        
        return self._services.get(service_name)


def get_service_container(db: Session = Depends(get_db)) -> ServiceContainer:
    """Get initialized service container"""
    container = ServiceContainer(db)
    container.initialize()
    return container


# AI Provider Dependencies
def get_ai_provider():
    """Get current AI provider - will be implemented in Phase 2"""
    try:
        from app.ai_providers import ai_manager
        return ai_manager.get_current_provider()
    except Exception as e:
        logger.error(f"Failed to get AI provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider unavailable"
        )


def get_ai_model_info() -> Dict[str, str]:
    """Get current AI model information"""
    try:
        from app.ai_providers import ai_manager
        config = ai_manager.get_current_model_config()
        return {
            "provider": config.provider if config else "unknown",
            "model": config.model_name if config else "unknown",
            "endpoint": getattr(config, 'endpoint_url', None) if config else None
        }
    except Exception as e:
        logger.warning(f"Could not get AI model info: {e}")
        return {
            "provider": "unknown",
            "model": "unknown",
            "endpoint": None
        }


# Health Check Dependencies
def check_ai_system_health() -> Dict[str, Any]:
    """Quick health check for AI system dependencies"""
    health = {
        "ai_available": False,
        "database_available": False,
        "migration_required": False,
        "issues": []
    }
    
    # Check AI provider
    try:
        provider = get_ai_provider()
        health["ai_available"] = provider is not None
    except Exception as e:
        health["issues"].append(f"AI provider unavailable: {str(e)}")
    
    # Check database (basic check)
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health["database_available"] = True
    except Exception as e:
        health["issues"].append(f"Database unavailable: {str(e)}")
    
    # Check for missing tables (basic check)
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        
        required_tables = ['chat_conversations', 'chat_messages', 'agent_sessions']
        missing_tables = []
        
        for table in required_tables:
            result = db.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :table_name"
            ), {"table_name": table}).fetchone()
            
            if not result:
                missing_tables.append(table)
        
        if missing_tables:
            health["migration_required"] = True
            health["issues"].append(f"Missing tables: {', '.join(missing_tables)}")
        
        db.close()
        
    except Exception as e:
        health["issues"].append(f"Could not check database schema: {str(e)}")
    
    return health


# Validation Dependencies
def validate_chat_message(message: str) -> str:
    """Validate chat message input"""
    if not message or not message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty"
        )
    
    if len(message) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message too long (max 4000 characters)"
        )
    
    return message.strip()


def validate_session_id(session_id: str) -> str:
    """Validate session ID format"""
    if not session_id or len(session_id) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
    
    return session_id


# Error Handling Dependencies
class AISystemError(Exception):
    """Base exception for AI system errors"""
    pass


class AIProviderError(AISystemError):
    """AI provider related errors"""
    pass


class ChatSessionError(AISystemError):
    """Chat session related errors"""
    pass


class HealthCheckError(AISystemError):
    """Health check related errors"""
    pass


def handle_ai_errors(func):
    """Decorator to handle AI-specific errors and convert to HTTP responses"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AIProviderError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI provider error: {str(e)}"
            )
        except ChatSessionError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chat session error: {str(e)}"
            )
        except HealthCheckError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Health check error: {str(e)}"
            )
        except AISystemError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI system error: {str(e)}"
            )
    
    return wrapper


# Configuration Dependencies
def get_ai_config() -> Dict[str, Any]:
    """Get AI system configuration"""
    return {
        "max_message_length": 4000,
        "max_history_length": 50,
        "session_timeout": 3600,
        "tools_enabled": True,
        "debug_mode": False,
        "circuit_breaker_enabled": True,
        "health_check_interval": 300  # 5 minutes
    }


# Logging Dependencies
def get_ai_logger(component: str) -> logging.Logger:
    """Get logger for AI component"""
    return logging.getLogger(f"ai.{component}")


# Rate Limiting Dependencies (placeholder for future implementation)
def check_rate_limit(user: User) -> bool:
    """Check if user is within rate limits for AI requests"""
    # Placeholder - will implement proper rate limiting in Phase 3
    return True


def apply_rate_limit(user: User = Depends(require_authenticated_user)):
    """Apply rate limiting to AI endpoints"""
    if not check_rate_limit(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for AI requests"
        )
    return user


# Phase 2 Placeholders - These will be implemented when services are created
def get_chat_service():
    """Get chat service - will be implemented in Phase 2"""
    pass


def get_health_service():
    """Get health service - will be implemented in Phase 2"""
    pass


def get_migration_service():
    """Get migration service - will be implemented in Phase 2"""
    pass


def get_agent_factory():
    """Get agent factory - will be implemented in Phase 2"""
    pass 