"""
Pydantic schemas for AI Chat API
Defines request/response models for chat endpoints
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ChatSessionStatus(str, Enum):
    """Chat session status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    PAUSED = "paused"
    ERROR = "error"


class AgentStatusEnum(str, Enum):
    """Agent status for API responses"""
    IDLE = "idle"
    THINKING = "thinking"
    USING_TOOL = "using_tool"
    PLANNING = "planning"
    WAITING = "waiting"
    ERROR = "error"


class MessageRole(str, Enum):
    """Message role types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Request Models
class StartChatRequest(BaseModel):
    """Request to start a new chat session"""
    title: Optional[str] = Field(None, description="Optional chat title")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional initial context")


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session"""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional message context")


class CreateEventRequest(BaseModel):
    """Request to create an event from chat conversation"""
    force_create: bool = Field(False, description="Force creation even if validation fails")


# Response Models
class ToolResult(BaseModel):
    """Result from tool execution"""
    tool_name: str = Field(..., description="Name of the tool executed")
    success: bool = Field(..., description="Whether tool execution was successful")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if tool failed")
    timestamp: datetime = Field(..., description="When the tool was executed")


class ChatMessage(BaseModel):
    """Individual chat message"""
    id: Optional[str] = Field(None, description="Message ID")
    role: MessageRole = Field(..., description="Who sent the message")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="When message was sent")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")


class AgentData(BaseModel):
    """Agent-specific data in responses"""
    extracted_info: Optional[Dict[str, Any]] = Field(None, description="Information extracted by agent")
    event_preview: Optional[Dict[str, Any]] = Field(None, description="Preview of event being created")
    thought_chain: Optional[List[str]] = Field(None, description="Agent's reasoning process")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Agent confidence level")


class ChatResponse(BaseModel):
    """Standard chat response"""
    session_id: str = Field(..., description="Chat session ID")
    response: str = Field(..., description="Agent's response message")
    status: AgentStatusEnum = Field(..., description="Current agent status")
    agent_data: Optional[AgentData] = Field(None, description="Agent-specific data")
    tool_results: Optional[List[ToolResult]] = Field(None, description="Results from any tools used")
    error: Optional[str] = Field(None, description="Error message if something went wrong")
    timestamp: datetime = Field(..., description="Response timestamp")


class ChatSessionInfo(BaseModel):
    """Information about a chat session"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: int = Field(..., description="User who owns this session")
    title: str = Field(..., description="Session title")
    status: ChatSessionStatus = Field(..., description="Current session status")
    agent_type: str = Field(..., description="Type of agent handling this session")
    created_at: datetime = Field(..., description="When session was created")
    updated_at: datetime = Field(..., description="When session was last updated")
    message_count: int = Field(..., description="Number of messages in session")


class StartChatResponse(BaseModel):
    """Response when starting a new chat session"""
    session_id: str = Field(..., description="New session ID")
    message: str = Field(..., description="Initial greeting message")
    status: ChatSessionStatus = Field(..., description="Session status")
    agent_status: AgentStatusEnum = Field(..., description="Agent status")
    agent_type: str = Field(..., description="Type of agent")
    provider: Optional[str] = Field(None, description="AI provider being used")
    model: Optional[str] = Field(None, description="AI model being used")


class ConversationHistory(BaseModel):
    """Full conversation history"""
    session_id: str = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(..., description="All messages in conversation")
    session_info: ChatSessionInfo = Field(..., description="Session metadata")
    agent_summary: Optional[Dict[str, Any]] = Field(None, description="Agent's summary of conversation")


class CreateEventResponse(BaseModel):
    """Response when creating an event from chat"""
    success: bool = Field(..., description="Whether event was created successfully")
    event_id: Optional[int] = Field(None, description="ID of created event")
    event_title: Optional[str] = Field(None, description="Title of created event")
    message: str = Field(..., description="Success or error message")
    redirect_url: Optional[str] = Field(None, description="URL to redirect to after creation")
    errors: Optional[List[str]] = Field(None, description="List of validation errors")


# Error Models
class ChatError(BaseModel):
    """Chat-specific error response"""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="When error occurred")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")


class ValidationError(BaseModel):
    """Input validation error"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value that was provided")


# Status Models
class ChatHealthStatus(BaseModel):
    """Health status for chat system"""
    healthy: bool = Field(..., description="Whether chat system is healthy")
    active_sessions: int = Field(..., description="Number of active chat sessions")
    agent_status: Dict[str, Any] = Field(..., description="Status of AI agents")
    provider_status: Dict[str, Any] = Field(..., description="Status of AI providers")
    last_check: datetime = Field(..., description="When health was last checked")


# Configuration Models
class ChatConfiguration(BaseModel):
    """Chat system configuration"""
    max_message_length: int = Field(4000, description="Maximum message length")
    max_history_length: int = Field(50, description="Maximum conversation history length")
    session_timeout: int = Field(3600, description="Session timeout in seconds")
    ai_provider: str = Field(..., description="Current AI provider")
    ai_model: str = Field(..., description="Current AI model")
    tools_enabled: bool = Field(True, description="Whether tools are enabled")
    debug_mode: bool = Field(False, description="Whether debug mode is enabled") 