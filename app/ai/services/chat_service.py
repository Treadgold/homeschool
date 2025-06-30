"""
AI Chat Service

This service handles all AI chat conversation functionality, including:
- Starting new chat sessions
- Processing chat messages
- Managing conversation history
- Event creation from chat
- HTMX chat interface support

Extracted from main.py as part of Phase 2 AI architecture refactoring.
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


class ChatService:
    """Service for managing AI chat conversations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def start_chat_session(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Start a new AI chat conversation.
        This version correctly handles session and agent creation.
        """
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required to start a chat.")

        try:
            from app.ai_agent import EventCreationAgent
            from app.ai_assistant import ai_manager # This is for getting model info
            
            # This part is simplified, assuming one conversation per user for now.
            # A more robust implementation would handle multiple conversations.
            conversation = db.query(ChatConversation).filter(ChatConversation.user_id == user.id).first()

            if not conversation:
                conversation = ChatConversation(user_id=user.id)
                db.add(conversation)
                db.commit()
                db.refresh(conversation)

            # Get model info for display
            try:
                current_model_key = ai_manager.get_current_model_key()
                current_config = ai_manager.get_current_model_config()
                provider = current_config.provider if current_config else "unknown"
                model = current_config.model_name if current_config else "unknown"
            except Exception:
                provider = "fallback"
                model = "not_available"

            agent = EventCreationAgent(db=db, user_id=user.id)
            initial_message = "Welcome! How can I help you create an event today?"
            
            # Check if conversation has messages to determine if it's new
            if conversation.messages:
                 initial_message = "Welcome back! How can I continue helping you with your event?"

            return {
                "session_id": conversation.id,
                "user_id": conversation.user_id,
                "message": initial_message,
                "provider": provider,
                "model": model,
                "agent_status": "idle",
                "conversation_history": [msg.to_dict() for msg in conversation.messages[-10:]]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start AI chat session: {e}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize AI chat session."
            )
    
    async def send_chat_message(
        self, 
        session_id: str, 
        message: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Send a message to the AI agent with real-time status updates"""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        try:
            # Create agent instance
            from app.ai_agent import EventCreationAgent
            from app.ai_assistant import ai_manager
            
            agent = EventCreationAgent(db, user.id)
            
            # Get AI agent response
            ai_response = await agent.continue_conversation(session_id, message)
            
            # Get model info for display
            try:
                current_config = ai_manager.get_current_model_config()
                provider = current_config.provider if current_config else "unknown"
                model = current_config.model_name if current_config else "unknown"
            except:
                provider = "unknown"
                model = "unknown"
            
            return {
                "session_id": session_id,
                "user_message": message,
                "ai_response": ai_response["response"],
                "agent_status": ai_response.get("agent_status", "waiting"),
                "thought_chain": ai_response.get("thought_chain", []),
                "tools_used": ai_response.get("tools_used", []),
                "needs_input": ai_response.get("needs_input", True),
                "type": "text",
                "provider": provider,
                "model": model
            }
            
        except Exception as e:
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
                "ai_response": "Sorry, I encountered an error. Could you try rephrasing that?",
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
        """Start a brand new conversation (archive current active one)"""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Archive any active conversations
        from app.ai_agent import ConversationManager
        from app.ai_assistant import ai_manager
        
        conv_manager = ConversationManager(db)
        active_conv_id = conv_manager.get_or_create_active_conversation(user.id)
        if active_conv_id:
            conv_manager.archive_conversation(active_conv_id)
        
        # Create new conversation
        from app.ai_agent import EventCreationAgent
        agent = EventCreationAgent(db, user.id)
        result = await agent.start_conversation()
        
        # Get model info
        try:
            current_config = ai_manager.get_current_model_config()
            provider = current_config.provider if current_config else "unknown"
            model = current_config.model_name if current_config else "unknown"
        except:
            provider = "unknown"
            model = "unknown"
        
        return {
            "session_id": result["conversation_id"],
            "message": result["message"],
            "status": result["status"],
            "agent_status": result["agent_status"],
            "provider": provider,
            "model": model
        }
    
    async def get_chat_status(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Get current agent status for real-time updates"""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        try:
            from app.ai_agent import EventCreationAgent
            agent = EventCreationAgent(db, user.id)
            conversation_data = agent.get_conversation_history(session_id)
            
            if not conversation_data:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            return {
                "agent_status": conversation_data["agent_state"]["status"] if conversation_data["agent_state"] else "idle",
                "current_step": conversation_data["agent_state"]["current_step"] if conversation_data["agent_state"] else None
            }
        except RuntimeError as e:
            if "migration" in str(e).lower():
                raise HTTPException(status_code=503, detail="Database migration required")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def initialize_chat_session(self, user: User, db: Session) -> Dict[str, Any]:
        """Start a new AI chat session for HTMX interface"""
        try:
            # Create new session
            session_id = str(uuid.uuid4())
            
            # Initialize AI provider
            from app.ai_assistant import ai_manager
            ai_provider = ai_manager.get_current_provider()
            
            # Create conversation first
            conversation = ChatConversation(
                id=session_id,
                user_id=user.id,
                title="AI Event Creator",
                status="active"
            )
            db.add(conversation)
            db.commit()
            
            # Create agent session record
            agent_session_id = str(uuid.uuid4())
            session = AgentSession(
                id=agent_session_id,
                conversation_id=session_id,
                agent_type="event_creator",
                status=AgentStatus.idle
            )
            db.add(session)
            db.commit()
            
            # Generate initial message
            initial_message = """👋 Hello! I'm your AI Event Assistant. I'll help you create amazing events for your homeschool community.

Just describe your event naturally, like:
• "Science workshop for kids 8-12 next Saturday 10am-2pm at the community center, $15 per child"
• "Free nature walk for families this Sunday morning at the botanical gardens"

What event would you like to create?"""
            
            # Save initial message
            message = ChatMessage(
                conversation_id=conversation.id,
                role='assistant',
                content=initial_message,
                created_at=datetime.utcnow()
            )
            db.add(message)
            db.commit()
            
            return {
                "session_id": session_id,
                "message": initial_message,
                "provider": ai_provider.__class__.__name__,
                "model": getattr(ai_provider, 'model_name', 'unknown')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start AI chat session: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start chat session: {str(e)}")
    
    async def process_chat_message(
        self, 
        session_id: str, 
        message: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Process a chat message and return AI response for HTMX interface"""
        try:
            from app.ai_assistant import ai_manager
            
            # Get conversation
            conversation = db.query(ChatConversation).filter(
                ChatConversation.id == session_id
            ).first()
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Get agent session
            agent_session = db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            # Save user message
            user_message = ChatMessage(
                conversation_id=conversation.id,
                role='user',
                content=message
            )
            db.add(user_message)
            db.commit()
            
            # Get AI provider
            ai_provider = ai_manager.get_current_provider()
            
            # Get conversation history
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation.id
            ).order_by(ChatMessage.created_at).all()
            
            # Build conversation context
            conversation_history = []
            for msg in messages:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Process with AI provider
            try:
                # Use the EventCreationAssistant from ai_assistant.py
                from app.ai_assistant import EventCreationAssistant
                assistant = EventCreationAssistant()
                
                self.logger.info(f"Processing message with EventCreationAssistant: {message[:50]}...")
                
                ai_response = await assistant.chat(
                    user_message=message,
                    conversation_history=conversation_history[:-1],  # Exclude the current message we just added
                    user_id=user.id,
                    db=db,
                    session_id=session_id  # Pass session_id for dynamic integration
                )
                
                self.logger.info(f"AI response received: type={ai_response.get('type')}, has_response={bool(ai_response.get('response'))}, has_tool_results={bool(ai_response.get('tool_results'))}")
                
                # Extract info if available - Use correct key structure
                extracted_info = None
                if ai_response.get("type") == "tool_result" and ai_response.get("tool_results"):
                    # Look for event creation tools in the results
                    for tool_result in ai_response["tool_results"]:
                        # Use "function" key instead of "tool"
                        if tool_result.get("function") == "create_event_draft":
                            extracted_info = tool_result.get("result", {})
                            self.logger.info(f"Extracted event info: {extracted_info}")
                            break
                elif ai_response.get("event_preview"):
                    # Alternative extraction path
                    extracted_info = ai_response.get("event_preview")
                    self.logger.info(f"Extracted event preview: {extracted_info}")
                
                # Get the response text with better fallback handling
                response_text = ai_response.get("response", "").strip()
                
                # Better handling of empty responses
                if not response_text:
                    self.logger.warning("AI returned empty response, using fallback")
                    response_text = f"I understand you mentioned: '{message}'. Let me help you create an event. Could you tell me more about what type of event you'd like to organize?"
                
                # Reformat for consistency with existing code
                ai_response = {
                    "response": response_text,
                    "extracted_info": extracted_info
                }
                
                self.logger.info(f"Final response prepared: {len(response_text)} chars, has_extracted_info={bool(extracted_info)}")
                
            except Exception as e:
                self.logger.error(f"AI processing failed: {e}", exc_info=True)
                # Fallback to a basic response that acknowledges the user's input
                ai_response = {
                    "response": f"I understand you mentioned: '{message}'. Let me help you create an event. Could you tell me more about what type of event you'd like to organize?",
                    "extracted_info": None
                }
            
            # Save AI response
            assistant_message = ChatMessage(
                conversation_id=conversation.id,
                role='assistant',
                content=ai_response.get('response', 'I apologize, but I encountered an error processing your message.')
            )
            db.add(assistant_message)
            
            # Update agent session with extracted info
            if agent_session and ai_response.get('extracted_info'):
                # Merge with existing memory
                current_memory = agent_session.memory or {}
                current_memory.update(ai_response['extracted_info'])
                agent_session.memory = current_memory
                self.logger.info(f"Updated agent memory with extracted info")
            
            db.commit()
            
            # Return the response with tracking info
            return {
                "ai_response": ai_response.get('response', 'I apologize, but I encountered an error processing your message.'),
                "extracted_info": ai_response.get('extracted_info'),
                "event_preview": ai_response.get('extracted_info') is not None,
                "tool_calls_made": bool(ai_response.get('tool_calls')),
                "event_data_extracted": bool(ai_response.get('extracted_info')),
                "provider": ai_provider.__class__.__name__,
                "model": getattr(ai_provider, 'model_name', 'unknown'),
                "agent_status": "completed"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process chat message: {e}", exc_info=True)
            return {
                "ai_response": f"❌ Sorry, I encountered an error: {str(e)}",
                "extracted_info": None,
                "event_preview": None,
                "tool_calls_made": False,
                "event_data_extracted": False,
                "provider": "error",
                "model": "error",
                "agent_status": "error"
            }
    
    async def get_event_preview(
        self, 
        session_id: str, 
        user: User, 
        db: Session
    ) -> Dict[str, Any]:
        """Get event preview data for HTMX interface"""
        try:
            # Get the latest event data from the session
            session = db.query(AgentSession).filter(
                AgentSession.conversation_id == session_id
            ).first()
            
            if not session or not session.memory:
                return {
                    "has_data": False,
                    "message": "No event data available yet"
                }
            
            event_data = session.memory
            
            # Return structured event data
            return {
                "has_data": True,
                "event_data": event_data,
                "fields": self._format_event_fields(event_data),
                "can_create": self._can_create_event(event_data)
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