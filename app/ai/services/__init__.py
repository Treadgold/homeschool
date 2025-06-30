"""
AI Services Package

This package contains service classes that handle the business logic
for AI functionality, extracted from main.py as part of Phase 2
of the AI architecture refactoring.

Services:
- ChatService: Chat conversation management
- HealthService: System health and migration
- ModelService: AI model management  
- EventService: Event creation from AI
"""

from .chat_service import ChatService
from .health_service import HealthService
from .model_service import ModelService
from .event_service import EventService

__all__ = [
    "ChatService",
    "HealthService", 
    "ModelService",
    "EventService"
]
