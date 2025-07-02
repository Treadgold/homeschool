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

from fastapi import HTTPException, status, FastAPI
from sqlalchemy.orm import Session

from app.models import User, AgentSession, ChatConversation, Event, AgentStatus
from app.ai.services.react_agent_service import invoke_agent

# Assuming the FastAPI app is created in main.py
from app.main import app

# In-memory log storage
log_storage = []

# Function to add logs
def add_log(message: str):
    log_storage.append(message)
    if len(log_storage) > 100:  # Limit log size
        log_storage.pop(0)

# Endpoint to get logs
@app.get('/admin/ai-models/logs')
async def get_logs():
    return log_storage

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
        logger = logging.getLogger(__name__)
        add_log("Starting model test")
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
                
                # Test 1: Basic Chat (now uses LangChain agent)
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
                    try:
                        add_log("Starting chat test")
                        # Get the actual model name for the test
                        model_config = ai_manager.get_available_models().get(model_key)
                        model_name_to_test = model_config.model_name if model_config else model_key
                        
                        agent_response = await invoke_agent(
                            session_id="chat-test-session",
                            user_prompt="Hello, can you help me create events? Please respond briefly.",
                            model=model_name_to_test
                        )
                        add_log("Chat test completed")
                        return {"content": agent_response.get("output")}
                    except Exception as e:
                        add_log(f"Chat test failed: {str(e)}")
                        return {"error": str(e)}
                
                test_response = await run_test(chat_test)
                add_log("Chat test response received")
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
                    func_start_time = time.time()
                    add_log("Starting function calling test")
                    
                    # Use the LangChain agent to test for tool-calling capability
                    try:
                        from app.ai_assistant import ai_manager
                        model_config = ai_manager.get_available_models().get(model_key)
                        model_name_to_test = model_config.model_name if model_config else model_key
                        
                        agent_response = await invoke_agent(
                            session_id="test-session",
                            user_prompt="Create an event draft for a 'Science Fair' on August 15, 2025",
                            model=model_name_to_test
                        )
                        
                        func_elapsed = time.time() - func_start_time
                        
                        # The new agent returns 'intermediate_steps' if it called a tool
                        if agent_response.get("intermediate_steps"):
                            tool_calls = agent_response["intermediate_steps"]
                            # Handle different intermediate_steps formats
                            tool_names = []
                            for step in tool_calls:
                                if isinstance(step, tuple) and len(step) >= 2:
                                    # Format: (call_dict, output)
                                    call_info = step[0]
                                    if isinstance(call_info, dict):
                                        # Dict format: {"name": "tool_name", ...}
                                        tool_name = call_info.get("name", "unknown")
                                    elif hasattr(call_info, "tool"):
                                        # Object format: obj.tool
                                        tool_name = call_info.tool
                                    else:
                                        tool_name = str(call_info)
                                    tool_names.append(tool_name)
                                else:
                                    tool_names.append("unknown")
                            
                            if tool_names:
                                result["function_test"] = f"✅ Function calling successful ({func_elapsed:.1f}s)"
                                result["function_response"] = f"Agent called tools: {', '.join(tool_names)}"
                            else:
                                result["function_test"] = f"⚠️ Agent responded but no clear tool usage ({func_elapsed:.1f}s)"
                                result["function_response"] = "Agent response received but tool usage unclear."
                        else:
                            result["function_test"] = f"❌ Model doesn't support function calling ({func_elapsed:.1f}s)"
                            result["function_response"] = "Agent did not call any tools."

                    except Exception as e:
                        func_elapsed = time.time() - func_start_time
                        self.logger.error(f"Function calling test failed: {e}")
                        result["function_test"] = f"❌ Function calling test failed ({func_elapsed:.1f}s): {e}"
                    add_log("Function calling test completed")
                
                # Test 3: Dynamic Event Creation (if function calling passed)
                if result.get("success") and result.get("function_test", "").startswith("✅"):
                    dynamic_start_time = time.time()
                    add_log("Starting dynamic event creation test")
                    
                    try:
                        model_config = ai_manager.get_available_models().get(model_key)
                        model_name_to_test = model_config.model_name if model_config else model_key
                        
                        agent_response = await invoke_agent(
                            session_id="dynamic-test-session",
                            user_prompt="I need to set up a zoo visit for next Friday. It's for up to 50 people. Children from 5 - 15. Tickets are $12.50 for kids and $27 per adult",
                            model=model_name_to_test
                        )

                        dynamic_elapsed = time.time() - dynamic_start_time
                        
                        if agent_response.get("intermediate_steps"):
                            # Check for event draft creation in different formats
                            draft_tool_called = False
                            for step in agent_response.get("intermediate_steps", []):
                                if isinstance(step, tuple) and len(step) >= 2:
                                    call_info = step[0]
                                    if isinstance(call_info, dict):
                                        tool_name = call_info.get("name", "")
                                    elif hasattr(call_info, "tool"):
                                        tool_name = call_info.tool
                                    else:
                                        tool_name = str(call_info)
                                    
                                    if "create_event_draft" in tool_name:
                                        draft_tool_called = True
                                        break
                            if draft_tool_called:
                                result["dynamic_test"] = f"✅ Dynamic event creation successful ({dynamic_elapsed:.1f}s)"
                                result["dynamic_details"] = "Agent correctly used 'create_event_draft' tool."
                            else:
                                result["dynamic_test"] = f"⚠️ Agent used tools, but not for event creation ({dynamic_elapsed:.1f}s)"
                        else:
                            result["dynamic_test"] = f"❌ AI didn't use tools for event creation ({dynamic_elapsed:.1f}s)"
                            result["success"] = False
                            result["error"] = "AI model did not use any tools for the dynamic creation test."

                    except Exception as e:
                        dynamic_elapsed = time.time() - dynamic_start_time
                        result["dynamic_test"] = f"❌ Dynamic test failed: {str(e)} ({dynamic_elapsed:.1f}s)"
                        result["success"] = False
                        result["error"] = f"Dynamic event creation test failed: {str(e)}"
                    add_log("Dynamic event creation test completed")
                else:
                    result["dynamic_test"] = "⏭️ Dynamic test skipped (function calling required)"
                
                # Restore old model
                add_log("Restoring old model")
                ai_manager.set_current_model(old_model)
                add_log("Model test completed")
                
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
        """Test the dynamic connection between AI tools and event creation API using LangChain."""
        try:
            from app.ai_assistant import ai_manager
            
            # Get current model for the test
            current_config = ai_manager.get_current_model_config()
            model_name = current_config.model_name if current_config else "llama3"

            test_message = "Create a coding workshop for teenagers next Saturday from 2-4pm at the community center, $15 per student, max 20 students"
            
            agent_response = await invoke_agent(
                session_id="dynamic-connection-test",
                user_prompt=test_message,
                model=model_name
            )
            
            # Check if the agent used the 'create_event_draft' tool
            tool_used = False
            for step in agent_response.get("intermediate_steps", []):
                if isinstance(step, tuple) and len(step) >= 2:
                    call_info = step[0]
                    if isinstance(call_info, dict):
                        tool_name = call_info.get("name", "")
                    elif hasattr(call_info, "tool"):
                        tool_name = call_info.tool
                    else:
                        tool_name = str(call_info)
                    
                    if "create_event_draft" in tool_name:
                        tool_used = True
                        break

            # In a real test, you might also check if the draft was actually saved to the DB
            # for the test session_id, but for now, checking tool use is sufficient.

            return {
                "success": True,
                "results": {
                    "ai_response_type": "agent_action" if tool_used else "text_response",
                    "has_tool_results": tool_used,
                    "draft_created": tool_used, # Assuming tool call implies draft creation
                    "full_flow_success": tool_used
                },
                "message": "Dynamic connection test completed using LangChain agent.",
                "ai_response": agent_response.get("output", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Dynamic connection test failed: {str(e)}"
            }
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        # Import from auth utils module
        from app.utils.auth_utils import generate_csrf_token
        return generate_csrf_token()
    
    def _verify_csrf_token(self, token: str) -> bool:
        """Verify CSRF token"""
        # Import from auth utils module
        from app.utils.auth_utils import verify_csrf_token
        return verify_csrf_token(token) 