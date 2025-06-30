# 🏗️ AI Architecture Design - Separation and Modularization

## 🎯 Overview

This document outlines the architectural redesign to separate AI functionality from the main web application, creating a clean, maintainable, and scalable AI subsystem.

## 🚨 Current Issues

### Main Problems
1. **Monolithic main.py (3,497 lines)** - AI endpoints mixed with core web app
2. **Scattered AI Logic** - AI functionality spread across multiple concerns
3. **Tight Coupling** - AI system tightly coupled to web application
4. **Hard to Debug** - Mixed responsibilities make troubleshooting difficult
5. **Scalability Issues** - Hard to scale AI independently from web app

### Current AI Endpoints in main.py
```
/api/ai/chat/start                    # 40 lines
/api/ai/chat/{session_id}/message     # 60 lines  
/api/ai/chat/{session_id}/create-event # 50 lines
/api/ai/chat/new                      # 30 lines
/api/ai/chat/{session_id}/status      # 25 lines
/api/ai/health-status                 # 45 lines
/api/ai/chat/init                     # 35 lines
/api/ai/chat/message                  # 50 lines
/api/ai/event-preview                 # 65 lines
/api/ai/health                        # 30 lines
/api/ai/migrate                       # 80 lines
/admin/ai-models                      # 25 lines
/admin/ai-models/set-current          # 20 lines
/admin/ai-models/{model_key}/test     # 150 lines
/api/ai/models/available              # 25 lines
/admin/ai-models/refresh-ollama       # 30 lines
/api/ai/clear-queue                   # 40 lines
/api/ai/test-dynamic-connection       # 70 lines
/ai-create-event                      # 10 lines

Total: ~840 lines of AI code in main.py
```

## 🏗️ Proposed Architecture

### High-Level Structure
```
app/
├── main.py                 # Core web app only (< 2000 lines)
├── ai/                     # AI subsystem
│   ├── __init__.py
│   ├── router.py          # AI-specific FastAPI router
│   ├── agents/            # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py        # Base agent class
│   │   ├── event_creator.py
│   │   └── conversation_manager.py
│   ├── providers/         # AI provider abstractions
│   │   ├── __init__.py
│   │   ├── manager.py     # Provider management
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── ollama.py
│   ├── tools/             # AI tools
│   │   ├── __init__.py
│   │   ├── registry.py    # Tool registry
│   │   ├── event_tools.py
│   │   └── validation_tools.py
│   ├── services/          # Business logic services
│   │   ├── __init__.py
│   │   ├── chat_service.py
│   │   ├── health_service.py
│   │   └── migration_service.py
│   ├── schemas/           # Pydantic models
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── agent.py
│   │   └── events.py
│   └── config.py          # AI-specific configuration
└── api/                   # API layer (new)
    ├── __init__.py
    ├── events.py          # Event-related endpoints
    ├── bookings.py        # Booking-related endpoints
    ├── admin.py           # Admin endpoints
    └── users.py           # User-related endpoints
```

### Core Principles

1. **Separation of Concerns** - AI logic completely isolated
2. **Single Responsibility** - Each module has one clear purpose
3. **Dependency Injection** - Clean interfaces between components
4. **Error Boundaries** - AI failures don't crash main app
5. **Independent Scaling** - AI can be scaled separately
6. **Plugin Architecture** - Easy to add new agents/tools/providers

## 🔧 Component Design

### 1. AI Router (`app/ai/router.py`)
```python
"""
Centralized AI endpoint routing
All AI endpoints moved here from main.py
"""

from fastapi import APIRouter, Depends
from .services.chat_service import ChatService
from .services.health_service import HealthService
from .services.migration_service import MigrationService

ai_router = APIRouter(prefix="/api/ai", tags=["AI"])

# Chat endpoints
@ai_router.post("/chat/start")
async def start_chat(chat_service: ChatService = Depends()):
    return await chat_service.start_session()

@ai_router.post("/chat/{session_id}/message")
async def send_message(session_id: str, message: str, 
                      chat_service: ChatService = Depends()):
    return await chat_service.process_message(session_id, message)

# Health endpoints
@ai_router.get("/health")
async def health_check(health_service: HealthService = Depends()):
    return await health_service.comprehensive_check()

# Admin endpoints
@ai_router.get("/admin/models")
async def list_models(admin_service: AdminService = Depends()):
    return await admin_service.get_available_models()
```

### 2. Chat Service (`app/ai/services/chat_service.py`)
```python
"""
Business logic for AI chat functionality
Extracted from main.py
"""

class ChatService:
    def __init__(self, db: Session, agent_factory: AgentFactory):
        self.db = db
        self.agent_factory = agent_factory
    
    async def start_session(self, user_id: int) -> ChatSessionResponse:
        """Start new chat session with health checks"""
        # Health validation
        if not await self._validate_system_health():
            raise AISystemUnavailableError()
        
        # Create session
        agent = self.agent_factory.create_event_creator(user_id)
        return await agent.start_conversation()
    
    async def process_message(self, session_id: str, message: str) -> ChatResponse:
        """Process user message with error boundaries"""
        try:
            agent = self.agent_factory.get_agent_for_session(session_id)
            return await agent.process_message(session_id, message)
        except AIProviderError as e:
            return self._create_fallback_response(e)
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            raise ChatProcessingError(str(e))
```

### 3. Agent Factory (`app/ai/agents/factory.py`)
```python
"""
Factory for creating and managing agents
Centralized agent lifecycle management
"""

class AgentFactory:
    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.provider_manager = provider_manager
        self._agent_cache = {}
    
    def create_event_creator(self, user_id: int) -> EventCreationAgent:
        """Create event creation agent with dependency injection"""
        return EventCreationAgent(
            db=self.db,
            user_id=user_id,
            provider=self.provider_manager.get_current_provider(),
            tools=self._create_tools(user_id)
        )
    
    async def get_agent_for_session(self, session_id: str) -> BaseAgent:
        """Get or create agent for existing session"""
        if session_id not in self._agent_cache:
            self._agent_cache[session_id] = await self._load_agent(session_id)
        return self._agent_cache[session_id]
```

### 4. Health Service (`app/ai/services/health_service.py`)
```python
"""
Comprehensive AI system health monitoring
Extracted from main.py health check logic
"""

class HealthService:
    def __init__(self, db: Session, provider_manager: ProviderManager):
        self.db = db
        self.provider_manager = provider_manager
    
    async def comprehensive_check(self) -> HealthStatus:
        """Complete system health check"""
        checks = await asyncio.gather(
            self._check_database_health(),
            self._check_ai_provider_health(),
            self._check_migration_status(),
            return_exceptions=True
        )
        
        return HealthStatus(
            overall_status=self._determine_overall_status(checks),
            checks=self._format_check_results(checks),
            timestamp=datetime.utcnow()
        )
    
    async def _check_database_health(self) -> DatabaseHealth:
        """Database connectivity and schema validation"""
        missing_tables = DatabaseHealthChecker.get_missing_tables(self.db)
        return DatabaseHealth(
            status="healthy" if not missing_tables else "requires_migration",
            missing_tables=missing_tables,
            connection_test=await self._test_db_connection()
        )
```

### 5. Error Boundaries and Fallbacks
```python
"""
Error handling and fallback systems
Prevent AI failures from crashing main app
"""

class AISystemUnavailableError(Exception):
    """Raised when AI system is completely unavailable"""
    pass

class AIProviderError(Exception):
    """AI provider specific errors"""
    pass

@ai_router.exception_handler(AISystemUnavailableError)
async def ai_unavailable_handler(request: Request, exc: AISystemUnavailableError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "AI system temporarily unavailable",
            "fallback_message": "Event creation is temporarily limited to manual form entry",
            "retry_after": 300
        }
    )

@ai_router.exception_handler(AIProviderError)
async def ai_provider_handler(request: Request, exc: AIProviderError):
    return JSONResponse(
        status_code=200,  # Don't fail the request
        content={
            "response": "I'm having trouble connecting to my AI service. Let me help you create your event manually.",
            "fallback_mode": True,
            "suggestions": ["Use the manual event creation form", "Try again in a few minutes"]
        }
    )
```

## 🗄️ Database Layer Separation

### AI-Specific Models
```python
# app/ai/models.py - AI-specific database models
class ChatConversation(Base):
    """Moved from app/models.py"""
    __tablename__ = "chat_conversations"
    # ... existing fields

class ChatMessage(Base):
    """Moved from app/models.py"""
    __tablename__ = "chat_messages"
    # ... existing fields

class AgentSession(Base):
    """Moved from app/models.py"""
    __tablename__ = "agent_sessions"
    # ... existing fields
```

### Repository Pattern
```python
# app/ai/repositories/chat_repository.py
class ChatRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_conversation(self, user_id: int, title: str) -> ChatConversation:
        """Create new conversation with transaction safety"""
        try:
            conversation = ChatConversation(user_id=user_id, title=title)
            self.db.add(conversation)
            self.db.commit()
            return conversation
        except SQLAlchemyError as e:
            self.db.rollback()
            raise ChatRepositoryError(f"Failed to create conversation: {e}")
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get conversation messages with pagination"""
        return self.db.query(ChatMessage)\
            .filter(ChatMessage.conversation_id == conversation_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(limit).all()
```

## 🔌 Integration Points

### Main App Integration
```python
# app/main.py - Clean integration
from app.ai.router import ai_router
from app.ai.config import ai_config
from app.ai.middleware import AIHealthMiddleware

app = FastAPI()

# Add AI middleware for health monitoring
app.add_middleware(AIHealthMiddleware)

# Include AI router
app.include_router(ai_router)

# Optional: AI health check endpoint for main app
@app.get("/system/health")
async def system_health():
    return {
        "web_app": "healthy",
        "ai_system": await ai_config.health_service.quick_check(),
        "database": "healthy"
    }
```

### Dependency Injection Setup
```python
# app/ai/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db

def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """Dependency injection for chat service"""
    return ChatService(
        db=db,
        agent_factory=get_agent_factory(db),
        provider_manager=get_provider_manager()
    )

def get_health_service(db: Session = Depends(get_db)) -> HealthService:
    """Dependency injection for health service"""
    return HealthService(
        db=db,
        provider_manager=get_provider_manager()
    )
```

## 📊 Benefits of New Architecture

### 1. **Maintainability**
- AI code isolated in single module
- Clear responsibilities for each component
- Easy to locate and fix AI-specific issues

### 2. **Testability**
- Each service can be unit tested independently
- Mock AI providers for testing
- Isolated test environments

### 3. **Scalability**
- AI system can be scaled independently
- Easy to add new agents or providers
- Plugin architecture for extensions

### 4. **Reliability**
- Error boundaries prevent AI failures from crashing main app
- Circuit breaker pattern for fault tolerance
- Graceful degradation when AI unavailable

### 5. **Development Velocity**
- Team can work on AI features without touching main app
- Clear interfaces reduce integration bugs
- Faster deployment of AI improvements

## 🚀 Migration Plan

### Phase 1: Foundation (Week 1)
1. Create `app/ai/` directory structure
2. Move AI-specific models to `app/ai/models.py`
3. Create base service classes and interfaces
4. Set up dependency injection framework

### Phase 2: Service Extraction (Week 2)
1. Extract chat functionality to `ChatService`
2. Extract health checks to `HealthService`
3. Extract migration logic to `MigrationService`
4. Create AI router with basic endpoints

### Phase 3: Agent Refactoring (Week 3)
1. Refactor existing agents to use new architecture
2. Implement agent factory pattern
3. Create tool registry system
4. Add comprehensive error handling

### Phase 4: Integration & Testing (Week 4)
1. Update main.py to use AI router
2. Add integration tests
3. Performance testing and optimization
4. Documentation and deployment

## 🎯 Success Metrics

- **Line Count**: main.py reduced from 3,497 to < 2,000 lines
- **Separation**: 0% AI code remaining in main.py
- **Test Coverage**: >90% test coverage for AI module
- **Performance**: No degradation in response times
- **Reliability**: AI failures don't crash main app

## 📝 Next Steps

1. **Review and Approve Architecture** - Team review of this design
2. **Create Implementation Issues** - Break down into specific tasks
3. **Setup Development Branch** - Create feature branch for refactoring
4. **Begin Phase 1 Implementation** - Start with foundation setup

---

This architecture provides a clean separation between the AI subsystem and the main web application, making the codebase more maintainable, testable, and scalable while preserving all existing functionality. 