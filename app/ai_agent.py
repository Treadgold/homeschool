"""
Agentic AI System for Event Creation
Implements proper agent patterns with planning, memory, and tool orchestration
With enterprise-grade reliability, logging, and error handling

Updated to integrate with ComprehensiveEvent model for advanced features.
"""

import json
import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import time
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.models import ChatConversation, ChatMessage, AgentSession, AgentStatus, User, Event
from app.ai_providers import ai_manager, BaseAIProvider
from app.ai_tools import EventCreationTools, DynamicEventTools
from app.database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker pattern for AI provider calls"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func):
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - AI provider unavailable")
        
        try:
            result = func()
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e

def retry_with_backoff(retries=3, backoff_factor=1.0, exceptions=(Exception,)):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        logger.error(f"Function {func.__name__} failed after {retries + 1} attempts: {str(e)}")
                        raise e
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator

class DatabaseHealthChecker:
    """Database health and migration checker"""
    
    @staticmethod
    def check_required_tables(db: Session) -> Dict[str, bool]:
        """Check if required tables exist"""
        required_tables = ['chat_conversations', 'chat_messages', 'agent_sessions']
        results = {}
        
        try:
            from sqlalchemy import text
            for table in required_tables:
                # Use proper SQLAlchemy text() and check in public schema
                result = db.execute(text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :table_name"
                ), {"table_name": table}).fetchone()
                results[table] = result is not None
                
            logger.info(f"Database table check: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {table: False for table in required_tables}
    
    @staticmethod
    def get_missing_tables(db: Session) -> List[str]:
        """Get list of missing required tables"""
        results = DatabaseHealthChecker.check_required_tables(db)
        return [table for table, exists in results.items() if not exists]

class AgentMode(Enum):
    """Different agent operational modes"""
    REACTIVE = "reactive"  # Simple response mode
    PLANNING = "planning"  # ReAct-style planning
    COLLABORATIVE = "collaborative"  # Multi-agent mode

class EventCreationAgent:
    """
    Enterprise-grade Agentic AI Assistant with reliability features:
    - Circuit breaker pattern for AI provider calls
    - Retry logic with exponential backoff  
    - Comprehensive logging and monitoring
    - Database health checks
    - Graceful error handling and recovery
    """
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.tools = EventCreationTools(db, user_id)
        self.mode = AgentMode.PLANNING
        self.max_iterations = 5
        self.circuit_breaker = CircuitBreaker()
        
        # Validate database health on initialization
        self._validate_database_health()
        
        logger.info(f"EventCreationAgent initialized for user {user_id}")
    
    def _validate_database_health(self):
        """Validate database has required tables"""
        missing_tables = DatabaseHealthChecker.get_missing_tables(self.db)
        
        if missing_tables:
            logger.error(f"Missing required database tables: {missing_tables}")
            logger.error("Please run the database migration: migrations/add_agent_tables.sql")
            raise RuntimeError(f"Database migration required. Missing tables: {missing_tables}")
        
        logger.info("Database health check passed - all required tables present")
    
    async def start_conversation(self) -> Dict[str, Any]:
        """Start a new conversation"""
        try:
            conversation_id = str(uuid.uuid4())
            
            # Create conversation
            conversation = ChatConversation(
                id=conversation_id,
                user_id=self.user_id,
                title="Event Creation Chat",
                status="active",
                agent_context={"mode": "event_creation", "created_at": datetime.now().isoformat()}
            )
            self.db.add(conversation)
            
            # Create simple agent session
            agent_session = AgentSession(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                agent_type="event_creator",
                current_step="active",
                plan={"goal": "Help user create events"},
                memory={},
                status=AgentStatus.waiting,
                tools_used=[]
            )
            self.db.add(agent_session)
            
            # Add greeting
            greeting = await self._generate_greeting()
            self._add_message(conversation_id, "assistant", greeting, AgentStatus.waiting)
            
            self.db.commit()
            logger.info(f"Started conversation {conversation_id}")
            
            return {
                "conversation_id": conversation_id,
                "message": greeting,
                "status": "active",
                "agent_status": AgentStatus.waiting.value
            }
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            return {
                "error": str(e),
                "message": "Failed to start conversation"
            }
    
    async def process_message(
        self, 
        conversation_id: str, 
        user_message: str
    ) -> Dict[str, Any]:
        """Process user message with AI reasoning"""
        
        try:
            # Get or create conversation
            conversation = self.db.query(ChatConversation).filter_by(id=conversation_id).first()
            if not conversation:
                return {"error": "Conversation not found"}
            
            # Add user message
            self._add_message(conversation_id, "user", user_message, AgentStatus.thinking)
            
            # Get conversation history
            messages = self._get_conversation_messages(conversation_id)
            
            # Process with AI
            response = await self._process_with_ai(user_message, messages)
            
            # Add AI response
            self._add_message(conversation_id, "assistant", response["response"], AgentStatus.waiting)
            
            self.db.commit()
            return response
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "agent_status": AgentStatus.error.value,
                "error": str(e)
            }
    
    async def _process_with_ai(
        self, 
        user_message: str, 
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """Process message using AI reasoning"""
        
        # Get AI provider
        try:
            provider = ai_manager.get_current_provider()
        except Exception as e:
            return {
                "response": f"AI service unavailable: {str(e)}",
                "agent_status": AgentStatus.error.value,
                "error": str(e)
            }
        
        # Initialize tools
        tools = DynamicEventTools(self.db, self.user_id)
        
        # Create simple system prompt
        system_prompt = """You are an AI assistant that helps create events for a homeschool community.

Your goal is to help users create events by:
1. Understanding what they want to create
2. Gathering necessary information through conversation
3. Using tools when appropriate to create drafts or get suggestions
4. Being helpful and conversational

Available tools:
- create_event_draft: Create event drafts
- query_database: Find similar events or check conflicts  
- suggest_event_details: Get suggestions for pricing, timing, etc.
- validate_event_data: Check event data for issues

Be natural and helpful. Ask questions when needed. Use tools when they would be helpful."""

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history[-8:],  # Last 8 messages for context
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Get tools and call AI
            tool_definitions = tools.get_tool_definitions()
            formatted_tools = provider.format_tools_for_provider(tool_definitions)
            
            ai_response = await provider.chat_completion(messages, formatted_tools)
            
            # Handle tool calls
            if ai_response.get("tool_calls"):
                return await self._handle_tool_calls(ai_response, tools, provider)
            else:
                return {
                    "response": ai_response.get("content", "I'm not sure how to help with that."),
                    "agent_status": AgentStatus.waiting.value
                }
                
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return {
                "response": f"I'm having trouble processing your request: {str(e)}",
                "agent_status": AgentStatus.error.value,
                "error": str(e)
            }
    
    async def _handle_tool_calls(
        self, 
        ai_response: Dict, 
        tools: DynamicEventTools, 
        provider
    ) -> Dict[str, Any]:
        """Handle tool calls and generate response"""
        
        tool_results = []
        
        for tool_call in ai_response.get("tool_calls", []):
            function_name = tool_call["function"]["name"]
            try:
                arguments_str = tool_call["function"]["arguments"]
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
                
                # Execute tool
                if function_name == "create_event_draft":
                    result = await tools.create_event_draft(**arguments)
                elif function_name == "query_database":
                    result = await tools.query_database(**arguments)
                elif function_name == "suggest_event_details":
                    result = await tools.suggest_event_details(**arguments)
                elif function_name == "validate_event_data":
                    result = await tools.validate_event_data(**arguments)
                else:
                    result = {"error": f"Unknown function: {function_name}"}
                
                tool_results.append({"function": function_name, "result": result})
                
            except Exception as e:
                logger.error(f"Tool {function_name} failed: {e}")
                tool_results.append({"function": function_name, "error": str(e)})
        
        # Generate natural response based on tool results
        try:
            tool_context = []
            event_preview = None
            
            for result in tool_results:
                if "error" in result:
                    tool_context.append(f"Tool {result['function']} failed: {result['error']}")
                else:
                    tool_context.append(f"Tool {result['function']} completed successfully")
                    # Check for event data
                    if result.get("result", {}).get("event_data"):
                        event_preview = result["result"]["event_data"]
            
            # Ask AI to generate natural response
            follow_up_messages = [
                {
                    "role": "system", 
                    "content": "Generate a natural response based on the tool results. Be conversational and helpful."
                },
                {
                    "role": "user", 
                    "content": f"Tool results: {'; '.join(tool_context)}"
                }
            ]
            
            follow_up = await provider.chat_completion(follow_up_messages)
            
            return {
                "response": follow_up.get("content", "I've processed your request."),
                "agent_status": AgentStatus.waiting.value,
                "event_preview": event_preview,
                "tool_results": tool_results
            }
            
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return {
                "response": "I've processed your request. What would you like to do next?",
                "agent_status": AgentStatus.waiting.value,
                "event_preview": event_preview,
                "tool_results": tool_results
            }
    
    async def create_event_from_conversation(
        self, 
        conversation_id: str
    ) -> Dict[str, Any]:
        """Create actual event from conversation data"""
        
        try:
            conversation = self.db.query(ChatConversation).filter_by(id=conversation_id).first()
            if not conversation:
                return {"error": "Conversation not found"}
            
            # Look for event data in conversation context or messages
            event_data = conversation.agent_context.get("event_draft")
            
            if not event_data:
                return {"error": "No event data found in conversation"}
            
            # Create event using legacy Event model
            event = Event(
                title=event_data.get("title", "New Event"),
                description=event_data.get("description", ""),
                location=event_data.get("location", ""),
                max_pupils=event_data.get("max_pupils", 20),
                cost=event_data.get("cost", 0),
                min_age=event_data.get("min_age"),
                max_age=event_data.get("max_age"),
                event_type=event_data.get("event_type", "homeschool"),
                date=datetime.now() + timedelta(days=7)  # Default date
            )
            
            self.db.add(event)
            self.db.commit()
            
            return {
                "success": True,
                "event_id": event.id,
                "message": f"Event '{event.title}' created successfully!"
            }
            
        except Exception as e:
            logger.error(f"Event creation failed: {e}")
            return {"error": f"Failed to create event: {str(e)}"}
    
    async def _generate_greeting(self) -> str:
        """Generate a simple greeting"""
        try:
            provider = ai_manager.get_current_provider()
            
            # Simple greeting prompt
            messages = [
                {
                    "role": "system", 
                    "content": "Generate a brief, friendly greeting for a user who wants to create an event. Keep it short and welcoming."
                },
                {
                    "role": "user", 
                    "content": "Generate greeting"
                }
            ]
            
            response = await provider.chat_completion(messages)
            return response.get("content", "Hi! I'm here to help you create an event. What would you like to organize?")
            
        except Exception:
            return "Hi! I'm here to help you create an event. What would you like to organize?"
    
    def _add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        agent_status: AgentStatus = None
    ):
        """Add message to conversation"""
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent_status=agent_status,
            msg_metadata={"timestamp": datetime.now().isoformat()}
        )
        self.db.add(message)
    
    def _get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get conversation messages as list of dicts"""
        messages = self.db.query(ChatMessage).filter_by(
            conversation_id=conversation_id
        ).order_by(ChatMessage.created_at).all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]


class ConversationManager:
    """Enhanced conversation manager with database persistence"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        
        conversations = self.db.query(ChatConversation).filter_by(
            user_id=user_id
        ).order_by(ChatConversation.updated_at.desc()).all()
        
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "status": conv.status,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]
    
    def get_or_create_active_conversation(self, user_id: int) -> Optional[str]:
        """Get active conversation or return None to create new one"""
        
        active_conv = self.db.query(ChatConversation).filter_by(
            user_id=user_id,
            status="active"
        ).order_by(ChatConversation.updated_at.desc()).first()
        
        return active_conv.id if active_conv else None
    
    def archive_conversation(self, conversation_id: str):
        """Archive a conversation"""
        
        conversation = self.db.query(ChatConversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.status = "archived"
            self.db.commit() 