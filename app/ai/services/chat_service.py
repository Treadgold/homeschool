"""
AI Chat Service

This service handles all AI chat conversation functionality, including:
- Starting new chat sessions
- Processing chat messages with a LangChain agent
- Finalizing event creation from drafts

Refactored to use LangChain agent as the primary processor.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    User, ChatConversation, ChatMessage, AgentSession, AgentStatus
)
# Import the Qwen3-optimized agent service
from .qwen3_optimized_agent import invoke_agent
# Import the new LangGraph agent service
from .langgraph_event_agent import invoke_langgraph_event_agent

# Configuration for which agent to use
AGENT_TYPE = "langgraph"  # Options: "qwen3_optimized", "langgraph"

class ChatService:
    """Service for managing AI chat conversations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def initialize_chat_session(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Finds or creates a chat conversation for a user.
        This is now a simple session initializer.
        """
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required.")

        conversation = db.query(ChatConversation).filter(
            ChatConversation.user_id == user.id, 
            ChatConversation.status != "archived"
        ).first()

        # Ensure agent session exists for existing conversations
        if conversation:
            agent_session = db.query(AgentSession).filter_by(conversation_id=conversation.id).first()
            if not agent_session:
                agent_session = AgentSession(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation.id,
                    agent_type="event_creator",
                    status=AgentStatus.waiting,
                    memory={}
                )
                db.add(agent_session)
                db.commit()

        if not conversation:
            conversation = ChatConversation(user_id=user.id, id=str(uuid.uuid4()))
            db.add(conversation)
            
            # Create agent session for draft storage
            agent_session = AgentSession(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                agent_type="event_creator",
                status=AgentStatus.waiting,
                memory={}
            )
            db.add(agent_session)
            
            # Add an initial welcome message
            initial_message = ChatMessage(
                conversation_id=conversation.id,
                role='assistant',
                content="Welcome! How can I help you create an event today?"
            )
            db.add(initial_message)
            db.commit()
            db.refresh(conversation)
        
        from app.ai_assistant import ai_manager
        current_config = ai_manager.get_current_model_config()

        return {
            "session_id": conversation.id,
            "user_id": conversation.user_id,
            "provider": current_config.provider if current_config else "Ollama",
            "model": current_config.model_name if current_config else "default",
            "conversation_history": [msg.to_dict() for msg in conversation.messages[-20:]]
        }
    
    async def send_chat_message(
        self, 
        session_id: str, 
        message: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Send a message to the AI agent using the new LangChain service."""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        try:
            # Get the current model from the ai_manager
            from app.ai_assistant import ai_manager
            current_config = ai_manager.get_current_model_config()
            model_name = current_config.model_name if current_config else "llama3" # Fallback

            # Choose agent based on configuration
            if AGENT_TYPE == "langgraph":
                agent_response = await invoke_langgraph_event_agent(
                    session_id=session_id,
                    user_prompt=message,
                    model=model_name
                )
            else:  # Default to qwen3_optimized
                agent_response = await invoke_agent(
                    session_id=session_id,
                    user_prompt=message,
                    model=model_name
                )

            # Save user message
            user_message = ChatMessage(conversation_id=session_id, role='user', content=message)
            db.add(user_message)

            # The new agent handles its own state, so we don't need to manually manage it here.
            # We just need to format the response for the frontend.
            ai_response_text = agent_response.get("output", "I'm sorry, I encountered a problem.")
            
            # Save AI response
            ai_message = ChatMessage(conversation_id=session_id, role='assistant', content=ai_response_text)
            db.add(ai_message)
            
            db.commit()

            # Check if tools were used to trigger event preview update
            tools_used = agent_response.get("intermediate_steps", [])
            tool_calls_made = len(tools_used) > 0
            
            return {
                "session_id": session_id,
                "user_message": message,
                "ai_response": ai_response_text,
                "agent_status": "waiting", # The new agent is synchronous, so it's always waiting after a response.
                "thought_chain": [], # LangChain agent handles thoughts internally. We can expose them if needed later.
                "tools_used": tools_used, # Expose tool usage
                "tool_calls_made": tool_calls_made, # Flag for HTMX to update preview
                "event_data_extracted": tool_calls_made, # Also set this flag for compatibility
                "needs_input": True,
                "type": "text",
                "provider": current_config.provider if current_config else "Ollama",
                "model": model_name
            }
            
        except Exception as e:
            self.logger.error(f"LangChain agent failed to process chat message: {e}\n{traceback.format_exc()}")
            # Get model info even in error case
            try:
                from app.ai_assistant import ai_manager
                current_config = ai_manager.get_current_model_config()
                provider = current_config.provider if current_config else "unknown"
                model = current_config.model_name if current_config else "unknown"
            except:
                provider = "unknown"
                model = "unknown"
            
            return {
                "session_id": session_id,
                "user_message": message,
                "ai_response": f"I'm sorry, I encountered an error: {str(e)}",
                "error": str(e),
                "agent_status": "error",
                "needs_input": True,
                "type": "error",
                "provider": provider,
                "model": model
            }
    
    async def create_event_from_chat(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Create an actual event from the AI conversation using the dynamic connection"""
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        try:
            # Use the new dynamic connection system
            from app.event_draft_manager import EventDraftManager
            
            draft_manager = EventDraftManager(db)
            result = draft_manager.create_event_from_draft(session_id, user.id)
            
            if result["success"]:
                # Add success message to conversation
                try:
                    success_message = ChatMessage(
                        conversation_id=session_id,
                        role='assistant',
                        content=f"🎉 Perfect! Your event '{result['event'].title}' has been created successfully! You can view it in the events list."
                    )
                    db.add(success_message)
                    db.commit()
                except Exception as msg_error:
                    self.logger.warning(f"Failed to add success message: {msg_error}")
                
                return {
                    "success": True,
                    "event_id": result["event_id"],
                    "message": result["message"],
                    "redirect_url": f"/event/{result['event_id']}"
                }
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=result.get("error", "Failed to create event")
                )
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Event creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create event. Please try again."
            }
    
    async def start_new_chat(self, user: User, db: Session) -> Dict[str, Any]:
        """Archives the current conversation and starts a new one."""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Archive any active conversations for the user
        active_conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == user.id,
            ChatConversation.status != "archived"
        ).all()
        for conv in active_conversations:
            conv.status = "archived"
            
        # Archive corresponding agent sessions
        for conv in active_conversations:
            agent_session = db.query(AgentSession).filter_by(conversation_id=conv.id).first()
            if agent_session:
                agent_session.status = AgentStatus.idle
        
        # Create a new session
        new_conversation = ChatConversation(id=str(uuid.uuid4()), user_id=user.id)
        db.add(new_conversation)
        
        # Create corresponding agent session (CRITICAL FIX)
        agent_session = AgentSession(
            id=new_conversation.id,  # Use same ID as conversation
            conversation_id=new_conversation.id,
            agent_type="event_creator",
            status=AgentStatus.waiting,
            memory={}
        )
        db.add(agent_session)

        # Add an initial welcome message
        initial_message = ChatMessage(
            conversation_id=new_conversation.id,
            role='assistant',
            content="Welcome! How can I help you create an event today?"
        )
        db.add(initial_message)
        db.commit()
        db.refresh(new_conversation)
        
        return {"session_id": new_conversation.id}
    
    async def get_event_preview(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Get event preview data for HTMX interface - Updated to use EventDraftManager"""
        try:
            # Use the EventDraftManager to get current draft (same as the tools use)
            from app.event_draft_manager import EventDraftManager
            
            draft_manager = EventDraftManager(db)
            current_draft = draft_manager.get_current_draft(session_id)
            
            if not current_draft:
                self.logger.info(f"No event draft found for session {session_id}")
                return {
                    "has_data": False,
                    "message": "No event data available yet"
                }
            
            self.logger.info(f"Found event draft for session {session_id}: {list(current_draft.keys())}")
            
            # Return structured event data
            return {
                "has_data": True,
                "event_data": current_draft,
                "fields": self._format_event_fields(current_draft),
                "can_create": self._can_create_event(current_draft)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event preview: {str(e)}")
            return {
                "has_data": False,
                "error": str(e)
            }
    
    def _format_event_fields(self, event_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Format event data into displayable fields"""
        fields = []
        
        if event_data.get("title"):
            fields.append({
                "label": "📝 Title",
                "value": event_data["title"]
            })
        
        if event_data.get("description"):
            fields.append({
                "label": "📄 Description", 
                "value": event_data["description"]
            })
        
        if event_data.get("location"):
            fields.append({
                "label": "📍 Location",
                "value": event_data["location"]
            })
        
        if event_data.get("date") or event_data.get("date_text"):
            date_text = event_data.get("date_text", event_data.get("date"))
            fields.append({
                "label": "🗓️ Date",
                "value": str(date_text)
            })
        
        if event_data.get("time"):
            fields.append({
                "label": "⏰ Time",
                "value": event_data["time"]
            })
        
        if event_data.get("max_pupils") or event_data.get("max_capacity"):
            capacity = event_data.get("max_pupils") or event_data.get("max_capacity")
            fields.append({
                "label": "👥 Capacity",
                "value": f"{capacity} participants"
            })
        
        if event_data.get("min_age") and event_data.get("max_age"):
            fields.append({
                "label": "🎂 Age Range",
                "value": f"{event_data['min_age']}-{event_data['max_age']} years"
            })
        
        if event_data.get("cost") is not None:
            if event_data["cost"] == 0:
                fields.append({
                    "label": "💰 Pricing",
                    "value": "FREE EVENT"
                })
            else:
                fields.append({
                    "label": "💰 Pricing",
                    "value": f"${event_data['cost']} per participant"
                })
        
        return fields
    
    def _can_create_event(self, event_data: Dict[str, Any]) -> bool:
        """Check if event has enough data to be created"""
        return bool(
            event_data.get("title") and 
            (event_data.get("date") or event_data.get("date_text"))
        ) 