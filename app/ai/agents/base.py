"""
Base Agent Classes for AI System
Provides common interface and functionality for all AI agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    THINKING = "thinking"
    USING_TOOL = "using_tool"
    PLANNING = "planning"
    WAITING = "waiting"
    ERROR = "error"


class AgentResponse:
    """Standard response format for all agents"""
    
    def __init__(
        self,
        response: str,
        status: AgentStatus = AgentStatus.WAITING,
        agent_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        tool_results: Optional[List[Dict]] = None
    ):
        self.response = response
        self.status = status
        self.agent_data = agent_data or {}
        self.error = error
        self.tool_results = tool_results or []
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "response": self.response,
            "status": self.status.value,
            "agent_data": self.agent_data,
            "error": self.error,
            "tool_results": self.tool_results,
            "timestamp": self.timestamp.isoformat()
        }


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents
    Provides common interface and functionality
    """
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @abstractmethod
    async def process_message(self, message: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a user message and return an agent response
        
        Args:
            message: User's message
            context: Optional context for the conversation
            
        Returns:
            AgentResponse with the agent's response and status
        """
        pass
    
    @abstractmethod
    async def start_conversation(self) -> AgentResponse:
        """
        Start a new conversation with the agent
        
        Returns:
            AgentResponse with initial greeting
        """
        pass
    
    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return self.status
    
    def set_status(self, status: AgentStatus):
        """Set agent status"""
        self.status = status
        self.logger.info(f"Agent status changed to: {status.value}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check agent health and readiness
        
        Returns:
            Dict with health status information
        """
        return {
            "agent_type": self.__class__.__name__,
            "status": self.status.value,
            "user_id": self.user_id,
            "healthy": True,
            "timestamp": datetime.utcnow().isoformat()
        }


class ConversationalAgent(BaseAgent):
    """
    Base class for agents that maintain conversation context
    Provides conversation history management
    """
    
    def __init__(self, db: Session, user_id: int):
        super().__init__(db, user_id)
        self.conversation_history: List[Dict] = []
        self.max_history_length = 50
    
    def add_to_history(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim history if it gets too long
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def get_conversation_context(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history for context"""
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.logger.info("Conversation history cleared")


class ToolCapableAgent(ConversationalAgent):
    """
    Base class for agents that can use tools
    Provides tool management and execution capabilities
    """
    
    def __init__(self, db: Session, user_id: int):
        super().__init__(db, user_id)
        self.available_tools: Dict[str, Any] = {}
        self.tool_usage_history: List[Dict] = []
    
    def register_tool(self, name: str, tool_func: Any, description: str = ""):
        """Register a tool for the agent to use"""
        self.available_tools[name] = {
            "function": tool_func,
            "description": description,
            "registered_at": datetime.utcnow().isoformat()
        }
        self.logger.info(f"Tool registered: {name}")
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of available tools"""
        return {
            name: {
                "description": tool["description"],
                "registered_at": tool["registered_at"]
            }
            for name, tool in self.available_tools.items()
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool and record the usage"""
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not available")
        
        tool_func = self.available_tools[tool_name]["function"]
        
        try:
            self.set_status(AgentStatus.USING_TOOL)
            result = await tool_func(**kwargs)
            
            # Record tool usage
            self.tool_usage_history.append({
                "tool_name": tool_name,
                "kwargs": kwargs,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            })
            
            self.logger.info(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            self.tool_usage_history.append({
                "tool_name": tool_name,
                "kwargs": kwargs,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "success": False
            })
            
            self.logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise
        finally:
            self.set_status(AgentStatus.WAITING)
    
    def get_tool_usage_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get history of tool usage"""
        if limit:
            return self.tool_usage_history[-limit:]
        return self.tool_usage_history 