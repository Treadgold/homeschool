"""
AI Model Service

This service handles all AI model management functionality, including:
- Model configuration and switching
- Model testing (chat, function calling, dynamic integration)
- Available models listing
- Ollama model refresh
- Queue management and clearing
- Dynamic connection testing

Extracted from main.py as part of Phase 2 AI architecture refactoring.
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, AgentSession, ChatConversation, Event, AgentStatus


class ModelService:
    """Service for AI model management and testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_available_models(self, request, user: User):
        """Get list of available AI models for admin interface"""
        from app.ai_assistant import ai_manager
        from fastapi.templating import Jinja2Templates
        
        # Initialize templates
        templates = Jinja2Templates(directory="app/templates")
        
        available_models = ai_manager.get_available_models()
        current_model = ai_manager.current_config
        
        return templates.TemplateResponse("admin_ai_models.html", {
            "request": request,
            "available_models": available_models,
            "current_model": current_model,
            "current_user": user,
            "csrf_token": self._generate_csrf_token()
        })
    
    async def set_current_model(self, model_key: str, user: User, csrf_token: str) -> Dict[str, Any]:
        """Set the current AI model"""
        if not csrf_token or not self._verify_csrf_token(csrf_token):
            raise HTTPException(status_code=400, detail="Invalid CSRF token")
        
        from app.ai_assistant import ai_manager
        success = ai_manager.set_current_model(model_key)
        
        if success:
            return {"success": True, "message": f"AI model set to {model_key}"}
        else:
            return {"success": False, "message": "Failed to set AI model"}
    
    async def test_model(self, model_key: str, user: User, csrf_token: str) -> Dict[str, Any]:
        """Test an AI model with comprehensive capabilities testing"""
        if not csrf_token or not self._verify_csrf_token(csrf_token):
            raise HTTPException(status_code=400, detail="Invalid CSRF token")
        
        from app.ai_assistant import ai_manager
        
        result = await ai_manager.test_provider(model_key)
        
        # Try comprehensive testing if basic test passes
        if result.get("success"):
            try:
                # Temporarily set this model and test capabilities
                old_model = ai_manager.current_config
                ai_manager.set_current_model(model_key)
                
                provider = ai_manager.get_current_provider()
                
                # Test 1: Basic Chat
                start_time = time.time()
                
                async def run_test(test_func):
                    """Run test function without timeout - user can cancel via UI"""
                    try:
                        return await test_func()
                    except asyncio.CancelledError:
                        elapsed = time.time() - start_time
                        return {
                            "content": None,
                            "error": f"Test was cancelled after {elapsed:.1f} seconds"
                        }
                    except Exception as e:
                        elapsed = time.time() - start_time
                        return {
                            "content": None,
                            "error": f"Test failed after {elapsed:.1f}s: {str(e)}"
                        }
                
                async def chat_test():
                    return await provider.chat_completion([
                        {"role": "user", "content": "Hello, can you help me create events? Please respond briefly."}
                    ])
                
                test_response = await run_test(chat_test)
                elapsed_time = time.time() - start_time
                
                if test_response.get("content"):
                    result["chat_test"] = f"✅ Chat test successful ({elapsed_time:.1f}s)"
                    result["sample_response"] = test_response.get("content")[:100] + "..."
                    result["loading_time"] = f"{elapsed_time:.1f}s"
                else:
                    error_msg = test_response.get("error", "No response received")
                    result["chat_test"] = f"❌ Chat test failed: {error_msg}"
                    result["success"] = False
                    result["error"] = f"Chat test failed: {error_msg}"
                    result["loading_time"] = f"{elapsed_time:.1f}s"
                
                # Test 2: Function Calling (if chat test passed)
                if result.get("success"):
                    test_functions = [
                        {
                            "name": "test_function_call",
                            "description": "A simple test function to verify function calling works",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "A test message to return"
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["success", "error"],
                                        "description": "Status of the test"
                                    }
                                },
                                "required": ["message", "status"]
                            }
                        }
                    ]
                    
                    async def function_test():
                        return await provider.chat_completion(
                            messages=[
                                {"role": "user", "content": "Please call the test_function_call function with message='Function calling works!' and status='success'"}
                            ],
                            tools=test_functions
                        )
                    
                    func_start_time = time.time()
                    function_test_response = await run_test(function_test)
                    func_elapsed = time.time() - func_start_time
                    
                    # Parse function calling response
                    func_call = self._parse_function_call(function_test_response)
                    
                    if func_call and func_call.get("name") == "test_function_call":
                        try:
                            args_str = func_call.get("arguments", "{}")
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                            if args.get("message") and args.get("status") == "success":
                                result["function_test"] = f"✅ Function calling successful ({func_elapsed:.1f}s)"
                                result["function_response"] = f"Called: {func_call['name']}({args})"
                            else:
                                result["function_test"] = f"⚠️ Function called but with incorrect parameters ({func_elapsed:.1f}s)"
                                result["function_response"] = f"Args: {args}"
                        except Exception as e:
                            result["function_test"] = f"⚠️ Function called but args parsing failed: {str(e)} ({func_elapsed:.1f}s)"
                            result["function_response"] = f"Raw args: {func_call.get('arguments')}"
                    elif function_test_response.get("content"):
                        # Some models might not support function calling but respond with text
                        if "test_function_call" in function_test_response["content"].lower():
                            result["function_test"] = f"⚠️ Model acknowledged function but didn't call it ({func_elapsed:.1f}s)"
                        else:
                            result["function_test"] = f"❌ Model doesn't support function calling ({func_elapsed:.1f}s)"
                    else:
                        result["function_test"] = f"❌ Function calling test failed ({func_elapsed:.1f}s)"
                
                # Test 3: Dynamic Event Creation (if function calling passed)
                if result.get("success") and result.get("function_test", "").startswith("✅"):
                    dynamic_start_time = time.time()
                    dynamic_test_response = await self._test_dynamic_event_creation(run_test)
                    dynamic_elapsed = time.time() - dynamic_start_time
                    
                    if dynamic_test_response.get("success"):
                        if dynamic_test_response.get("has_tool_results") and dynamic_test_response.get("draft_created"):
                            result["dynamic_test"] = f"✅ Dynamic event creation successful ({dynamic_elapsed:.1f}s)"
                            result["dynamic_details"] = f"Created draft: '{dynamic_test_response.get('draft_title', 'Event')}'"
                            result["dynamic_response"] = f"AI used tools and created {dynamic_test_response.get('response_length', 0)} char response"
                        elif dynamic_test_response.get("draft_created"):
                            result["dynamic_test"] = f"⚠️ Event draft created but via fallback extraction ({dynamic_elapsed:.1f}s)"
                            result["dynamic_details"] = f"Draft: '{dynamic_test_response.get('draft_title', 'Event')}'"
                        elif dynamic_test_response.get("has_tool_results"):
                            result["dynamic_test"] = f"⚠️ AI used tools but no draft created ({dynamic_elapsed:.1f}s)"
                            result["dynamic_details"] = "Tools executed but draft save may have failed"
                        else:
                            result["dynamic_test"] = f"❌ AI didn't use tools for event creation ({dynamic_elapsed:.1f}s)"
                            result["dynamic_details"] = f"Response type: {dynamic_test_response.get('ai_response_type', 'unknown')}"
                            result["success"] = False
                            result["error"] = f"AI model didn't use function calling tools for event creation"
                    else:
                        result["dynamic_test"] = f"❌ Dynamic test failed: {dynamic_test_response.get('error', 'Unknown error')} ({dynamic_elapsed:.1f}s)"
                        result["success"] = False
                        result["error"] = f"Dynamic event creation test failed: {dynamic_test_response.get('error', 'Unknown error')}"
                else:
                    result["dynamic_test"] = "⏭️ Dynamic test skipped (function calling required)"
                
                # Restore old model
                ai_manager.set_current_model(old_model)
                
            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                result["chat_test"] = f"❌ Test error: {str(e)} ({elapsed:.1f}s)"
                result["function_test"] = "❌ Function test skipped due to chat test failure"
                result["success"] = False
                result["error"] = f"Test failed with exception: {str(e)}"
                # Make sure to restore model even if there's an error
                try:
                    ai_manager.set_current_model(old_model)
                except:
                    pass
        
        return result
    
    def get_available_models_api(self, user: User) -> Dict[str, Any]:
        """Get list of available AI models (API endpoint)"""
        from app.ai_assistant import ai_manager
        
        available_models = ai_manager.get_available_models()
        current_model = ai_manager.current_config
        
        models_list = []
        for key, config in available_models.items():
            models_list.append({
                "key": key,
                "provider": config.provider,
                "model_name": config.model_name,
                "endpoint_url": config.endpoint_url,
                "enabled": config.enabled,
                "is_current": key == current_model
            })
        
        return {
            "models": models_list,
            "current_model": current_model,
            "ollama_endpoint": ai_manager.ollama_endpoint
        }
    
    async def refresh_ollama_models(self, user: User, csrf_token: str) -> Dict[str, Any]:
        """Refresh available Ollama models"""
        if not csrf_token or not self._verify_csrf_token(csrf_token):
            raise HTTPException(status_code=400, detail="Invalid CSRF token")
        
        try:
            from app.ai_assistant import ai_manager
            # Force refresh Ollama models
            ollama_models = ai_manager.refresh_ollama_models()
            
            return {
                "success": True,
                "message": f"Found {len(ollama_models)} Ollama models",
                "models": list(ollama_models.keys())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to refresh Ollama models"
            }
    
    async def clear_request_queue(self, user: User, db: Session) -> Dict[str, Any]:
        """Clear the AI request queue in case of issues"""
        try:
            from app.ai_assistant import ai_manager
            provider = ai_manager.get_current_provider()
            
            if not provider:
                raise HTTPException(status_code=404, detail="No AI provider configured")
            
            # Clear Ollama queue if it exists
            if hasattr(provider, '_request_queue') and provider._request_queue:
                queue_size = provider._request_queue.qsize()
                
                # Clear the queue
                while not provider._request_queue.empty():
                    try:
                        provider._request_queue.get_nowait()
                        provider._request_queue.task_done()
                    except:
                        break
                
                # Reset model loaded status to force reload
                if hasattr(provider, '_model_loaded'):
                    provider._model_loaded = False
                
                return {
                    "success": True,
                    "message": f"Cleared {queue_size} requests from queue",
                    "queue_size_before": queue_size,
                    "queue_size_after": provider._request_queue.qsize(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": True,
                    "message": "No request queue to clear",
                    "provider": provider.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clear queue: {str(e)}")
    
    async def test_dynamic_connection(self, user: User, db: Session) -> Dict[str, Any]:
        """Test the dynamic connection between AI tools and event creation API"""
        try:
            from app.ai_assistant import ThinkingEventAgent
            from app.event_draft_manager import EventDraftManager
            
            # Create test session
            test_session_id = str(uuid.uuid4())
            
            conversation = ChatConversation(
                id=test_session_id,
                user_id=user.id,
                title="Dynamic Connection Test",
                status="active"
            )
            db.add(conversation)
            
            agent_session = AgentSession(
                id=str(uuid.uuid4()),
                conversation_id=test_session_id,
                agent_type="event_creator",
                status=AgentStatus.idle
            )
            db.add(agent_session)
            db.commit()
            
            # Test AI Assistant with Dynamic Integration
            agent = ThinkingEventAgent()
            
            test_message = "Create a coding workshop for teenagers next Saturday from 2-4pm at the community center, $15 per student, max 20 students"
            
            ai_response = await agent.chat(
                user_message=test_message,
                conversation_history=[],
                user_id=user.id,
                db=db,
                session_id=test_session_id
            )
            
            # Check draft creation
            draft_manager = EventDraftManager(db)
            current_draft = draft_manager.get_current_draft(test_session_id)
            
            # Test API connection
            api_result = None
            if current_draft:
                api_result = draft_manager.create_event_from_draft(test_session_id, user.id)
            
            # Clean up test data
            if api_result and api_result.get("success"):
                # Remove test event
                test_event = db.query(Event).filter(Event.id == api_result["event_id"]).first()
                if test_event:
                    db.delete(test_event)
            
            db.delete(agent_session)
            db.delete(conversation)
            db.commit()
            
            return {
                "success": True,
                "results": {
                    "ai_response_type": ai_response.get("type"),
                    "has_tool_results": bool(ai_response.get("tool_results")),
                    "draft_created": bool(current_draft),
                    "draft_title": current_draft.get("title") if current_draft else None,
                    "api_connection": api_result.get("success") if api_result else False,
                    "event_created": bool(api_result and api_result.get("success")),
                    "full_flow_success": bool(current_draft and api_result and api_result.get("success"))
                },
                "message": "Dynamic connection test completed",
                "ai_response": ai_response.get("response", "")[:200] + "..." if len(ai_response.get("response", "")) > 200 else ai_response.get("response", "")
            }
            
        except Exception as e:
            # Clean up on error
            try:
                if 'agent_session' in locals():
                    db.delete(agent_session)
                if 'conversation' in locals():
                    db.delete(conversation)
                db.commit()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e),
                "message": "Dynamic connection test failed"
            }
    
    def _parse_function_call(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse function call from AI response (handles different provider formats)"""
        # Check for function/tool calls in response (different providers use different formats)
        func_call = None
        
        if response.get("function_call"):
            # OpenAI format
            func_call = response["function_call"]
        elif response.get("tool_calls") and len(response["tool_calls"]) > 0:
            # Anthropic/Ollama format - handle different structures
            tool_call = response["tool_calls"][0]
            if isinstance(tool_call, dict):
                # Ollama native format: {"function": {"name": "...", "arguments": {...}}}
                if "function" in tool_call:
                    func_call = tool_call["function"]
                # Alternative format: direct function object
                elif "name" in tool_call:
                    func_call = tool_call
                # Anthropic format
                else:
                    func_call = tool_call.get("function")
        
        return func_call
    
    async def _test_dynamic_event_creation(self, run_test_func) -> Dict[str, Any]:
        """Test dynamic event creation with AI tools"""
        async def dynamic_event_test():
            try:
                from app.ai_assistant import ThinkingEventAgent
                from app.event_draft_manager import EventDraftManager
                from app.database import get_db
                
                # Get database session
                db = next(get_db())
                
                # Create test session for dynamic integration
                test_session_id = str(uuid.uuid4())
                test_user_id = 1  # Admin user
                
                # Create test conversation and agent session
                conversation = ChatConversation(
                    id=test_session_id,
                    user_id=test_user_id,
                    title="Dynamic Connection Test",
                    status="active"
                )
                db.add(conversation)
                
                agent_session = AgentSession(
                    id=str(uuid.uuid4()),
                    conversation_id=test_session_id,
                    agent_type="event_creator",
                    status=AgentStatus.idle
                )
                db.add(agent_session)
                db.commit()
                
                # Test the AI assistant with dynamic integration
                agent = ThinkingEventAgent()
                
                # Use the exact message from the screenshot
                test_message = "I need to set up a zoo visit. It's for up to 50 people. Children from 5 - 15, under 10 they must be accompanied by at least one adult per family. Tickets are $12.50 for kids and $27 per adult"
                
                ai_response = await agent.chat(
                    user_message=test_message,
                    conversation_history=[],
                    user_id=test_user_id,
                    db=db,
                    session_id=test_session_id
                )
                
                # Check if tools were used and drafts created
                draft_manager = EventDraftManager(db)
                current_draft = draft_manager.get_current_draft(test_session_id)
                
                # Clean up test data
                db.delete(agent_session)
                db.delete(conversation)
                db.commit()
                db.close()
                
                return {
                    "ai_response_type": ai_response.get("type"),
                    "has_tool_results": bool(ai_response.get("tool_results")),
                    "has_event_preview": bool(ai_response.get("event_preview")),
                    "draft_created": bool(current_draft),
                    "draft_title": current_draft.get("title") if current_draft else None,
                    "response_length": len(ai_response.get("response", "")),
                    "success": True
                }
                
            except Exception as e:
                # Clean up on error
                try:
                    if 'db' in locals():
                        if 'agent_session' in locals():
                            db.delete(agent_session)
                        if 'conversation' in locals():
                            db.delete(conversation)
                        db.commit()
                        db.close()
                except:
                    pass
                
                return {
                    "success": False,
                    "error": str(e)
                }
        
        return await run_test_func(dynamic_event_test)
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        # Import from main.py or security module
        from app.main import generate_csrf_token
        return generate_csrf_token()
    
    def _verify_csrf_token(self, token: str) -> bool:
        """Verify CSRF token"""
        # Import from main.py or security module
        from app.main import verify_csrf_token
        return verify_csrf_token(token) 