"""
AI Module - Modular AI System for Event Creation
Provides clean separation of AI functionality from main web application

This module contains:
- AI chat endpoints and services
- Agent management system  
- Health monitoring and diagnostics
- AI provider abstractions
- Tool registry and execution
"""

from .router import ai_router
from .dependencies import (
    get_ai_model_info,
    check_ai_system_health,
    require_authenticated_user,
    require_admin_user
)

# Version and metadata
__version__ = "1.0.0-phase1"
__description__ = "Modular AI system for event creation"

# Export main components
__all__ = [
    # Router
    "ai_router",
    
    # Dependencies  
    "get_ai_model_info",
    "check_ai_system_health", 
    "require_authenticated_user",
    "require_admin_user",
    
    # Metadata
    "__version__",
    "__description__"
]

# Module configuration
AI_MODULE_CONFIG = {
    "phase": "1",
    "status": "foundation",
    "features": {
        "chat_endpoints": "placeholder",
        "health_checks": "implemented", 
        "admin_endpoints": "placeholder",
        "services": "pending_phase2",
        "agents": "pending_phase2"
    },
    "next_phase": {
        "phase": "2", 
        "features": [
            "service_layer_implementation",
            "agent_refactoring",
            "chat_functionality",
            "event_creation_integration"
        ]
    }
}
