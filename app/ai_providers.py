"""
AI Provider Abstraction Layer
Supports OpenAI, Anthropic, and Ollama with admin-configurable endpoints
"""

import json
import os
import httpx
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from asyncio import Queue, Lock
from datetime import datetime
import logging

@dataclass
class ModelConfig:
    """Configuration for an AI model"""
    provider: str  # "ollama", "openai", "anthropic"
    model_name: str
    endpoint_url: str
    api_key: Optional[str] = None
    max_tokens: int = 1000  # Increased for larger models
    temperature: float = 0.7
    enabled: bool = True

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
    
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion with optional tool calling"""
        pass
    
    @abstractmethod
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> Any:
        """Format tools for specific provider's API"""
        pass

class OllamaProvider(BaseAIProvider):
    """Ollama local model provider with request queuing to prevent memory issues"""
    
    # Class-level queue and lock for all instances
    _request_queue: Optional[Queue] = None
    _processing_lock: Optional[Lock] = None
    _current_model: Optional[str] = None
    _model_loaded: bool = False
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=None)  # No timeout - let user cancel if needed
        self.base_url = config.endpoint_url.rstrip('/')
        self.model = config.model_name
        self.timeout = None  # No artificial timeout limits
        
        # Initialize class-level queue and lock if not exists
        if OllamaProvider._request_queue is None:
            OllamaProvider._request_queue = Queue(maxsize=10)  # Limit queue size
        if OllamaProvider._processing_lock is None:
            OllamaProvider._processing_lock = Lock()
    
    async def _ensure_model_loaded(self) -> bool:
        """Ensure the correct model is loaded, unloading others if necessary"""
        async with OllamaProvider._processing_lock:
            if OllamaProvider._current_model == self.model and OllamaProvider._model_loaded:
                return True
            
            try:
                # If a different model is loaded, we need to be careful about memory
                if OllamaProvider._current_model and OllamaProvider._current_model != self.model:
                    logging.warning(f"Model change requested: {OllamaProvider._current_model} -> {self.model}")
                    # Note: Ollama doesn't have explicit unload, but we track this for monitoring
                
                # Check if model exists
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(f"{self.base_url}/api/tags")
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        available_models = [m["name"] for m in models]
                        
                        if self.model not in available_models:
                            raise Exception(f"Model {self.model} not available. Available: {available_models}")
                        
                        OllamaProvider._current_model = self.model
                        OllamaProvider._model_loaded = True
                        return True
                    else:
                        raise Exception(f"Failed to check available models: {response.status_code}")
                        
            except Exception as e:
                logging.error(f"Failed to ensure model loaded: {e}")
                OllamaProvider._model_loaded = False
                return False
    
    async def _process_request(self, payload: Dict) -> Dict:
        """Process a single request through the queue"""
        # Add request to queue
        request_id = f"req_{datetime.now().timestamp()}"
        await OllamaProvider._request_queue.put((request_id, payload))
        
        # Process requests one by one
        async with OllamaProvider._processing_lock:
            try:
                # Get our request (should be the one we just added)
                current_req_id, current_payload = await asyncio.wait_for(
                    OllamaProvider._request_queue.get(), timeout=1.0
                )
                
                if current_req_id != request_id:
                    # Put it back and wait
                    await OllamaProvider._request_queue.put((current_req_id, current_payload))
                    raise Exception("Request queue ordering issue")
                
                # Ensure model is loaded
                if not await self._ensure_model_loaded():
                    raise Exception("Failed to load model")
                
                # Configure for hybrid CPU/GPU execution (large model support)
                if "options" not in current_payload:
                    current_payload["options"] = {}
                
                # Enable automatic CPU/GPU hybrid execution for large models
                current_payload["options"].update({
                    # Let Ollama automatically determine optimal GPU layers based on VRAM
                    # "num_gpu": -1,  # Auto-detect (default behavior)
                    
                    # Use more CPU threads when GPU VRAM is insufficient  
                    "num_thread": 16,  # Increase for better CPU performance (you have 128GB RAM)
                    
                    # Allow larger context windows (Ollama will manage memory automatically)
                    "num_ctx": 8192,  # Increased from 4096 for larger models
                    
                    # Keep response length reasonable but not overly restrictive
                    "num_predict": min(2000, current_payload["options"].get("num_predict", 1000)),
                })
                
                # Make the actual request using /api/generate (auto-loads models)
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=current_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    else:
                        raise Exception(f"Ollama request failed: {response.status_code} - {response.text}")
                        
            except asyncio.TimeoutError:
                raise Exception("Request timeout in queue")
            except Exception as e:
                logging.error(f"Request processing failed: {e}")
                raise
            finally:
                # Mark task as done
                OllamaProvider._request_queue.task_done()
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion with Ollama using /api/chat (preferred) or /api/generate fallback"""
        
        try:
            # Add debugging
            logging.info(f"Ollama chat_completion called with {len(messages)} messages, tools: {bool(tools)}")
            
            # Try /api/chat first (more reliable and modern)
            chat_result = await self._try_chat_endpoint(messages, tools)
            if chat_result.get("success", False):
                logging.info(f"Chat endpoint succeeded, content length: {len(chat_result.get('content', ''))}")
                return chat_result
            
            # Fallback to /api/generate with prompt conversion
            logging.warning(f"Chat endpoint failed, falling back to generate: {chat_result.get('error')}")
            generate_result = await self._try_generate_endpoint(messages, tools)
            logging.info(f"Generate endpoint result, content length: {len(generate_result.get('content', ''))}")
            return generate_result
            
        except Exception as e:
            logging.error(f"Chat completion failed: {e}", exc_info=True)
            return {
                "content": f"Sorry, I encountered an error: {str(e)}",
                "tool_calls": None,
                "provider": "ollama",
                "error": str(e)
            }
    
    async def _try_chat_endpoint(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Try the modern /api/chat endpoint first"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": 8192,  # Larger context for bigger models
                "num_thread": 16,  # More CPU threads for hybrid execution
            }
        }
        
        # Add tools if provided - use proper Ollama format
        if tools:
            # Format tools for Ollama's native function calling
            formatted_tools = []
            for tool in tools:
                formatted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", "unknown"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                }
                formatted_tools.append(formatted_tool)
            
            payload["tools"] = formatted_tools
        
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", {})
                    content = message.get("content", "")
                    
                    # Parse tool calls from Ollama response
                    tool_calls = None
                    if tools and message.get("tool_calls"):
                        tool_calls = message["tool_calls"]
                    
                    # FIXED: Don't consider empty content as success when tools are available
                    if not content.strip() and tools:
                        return {
                            "success": False,
                            "error": "Empty content returned from chat endpoint with tools available",
                            "fallback_available": True,
                            "should_use_generate": True
                        }
                    
                    return {
                        "success": True,
                        "content": content,
                        "tool_calls": tool_calls,
                        "provider": "ollama",
                        "model": self.model,
                        "endpoint": "/api/chat",
                        "elapsed": f"{elapsed:.1f}s"
                    }
                
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": "/api/chat endpoint not available",
                        "fallback_available": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Chat endpoint returned {response.status_code}",
                        "details": response.text[:200]
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"Chat request timeout after {self.timeout}s",
                "details": "Model may be loading or overloaded"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Chat endpoint error: {str(e)}",
                "details": f"Error type: {type(e).__name__}"
            }
    
    async def _try_generate_endpoint(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fallback to /api/generate with prompt conversion and enhanced tool calling"""
        # Convert messages to a single prompt for /api/generate
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        # Enhanced tool context if provided
        if tools:
            tool_descriptions = []
            tool_examples = []
            
            for tool in tools:
                name = tool.get("name", "unknown")
                description = tool.get("description", "")
                parameters = tool.get("parameters", {})
                
                # Build parameter description
                param_desc = []
                if parameters.get("properties"):
                    for param_name, param_info in parameters["properties"].items():
                        param_type = param_info.get("type", "string")
                        param_desc.append(f"{param_name} ({param_type}): {param_info.get('description', '')}")
                
                tool_descriptions.append(f"- {name}: {description}")
                if param_desc:
                    tool_descriptions.append(f"  Parameters: {', '.join(param_desc)}")
                
                # Add example format
                if name == "create_event_draft":
                    tool_examples.append(f'TOOL_CALL: {name} {{"title": "Event Title", "description": "Event details", "location": "Event location", "date": "2024-12-01", "cost": 25}}')
            
            enhanced_prompt = f"""
Available tools:
{chr(10).join(tool_descriptions)}

When you need to use a tool, respond with exactly this format:
TOOL_CALL: tool_name {{"parameter": "value", "parameter2": "value2"}}

Examples:
{chr(10).join(tool_examples)}

Important: You can use tools to help create, validate, or get suggestions for events. Use them when helpful!
"""
            
            prompt_parts.insert(-1, enhanced_prompt)
        
        prompt = "\n\n".join(prompt_parts)
        if not prompt.endswith("Assistant:"):
            prompt += "\n\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": 8192,  # Larger context for bigger models
                "num_thread": 16,  # More CPU threads for hybrid execution
            }
        }
        
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("response", "")
                    
                    if content:
                        # Enhanced tool call parsing
                        tool_calls = []
                        if tools and "TOOL_CALL:" in content:
                            tool_calls = self._parse_tool_calls_from_text(content, tools)
                            logging.info(f"Parsed {len(tool_calls)} tool calls from response")
                        
                        return {
                            "content": content,
                            "tool_calls": tool_calls if tool_calls else None,
                            "provider": "ollama",
                            "model": self.model,
                            "endpoint": "/api/generate",
                            "elapsed": f"{elapsed:.1f}s"
                        }
                    else:
                        return {
                            "content": "No response generated",
                            "tool_calls": None,
                            "provider": "ollama",
                            "error": "Empty response from generate endpoint",
                            "raw_response": str(result)
                        }
                else:
                    return {
                        "content": f"Generation failed with status {response.status_code}",
                        "tool_calls": None,
                        "provider": "ollama",
                        "error": f"HTTP {response.status_code}",
                        "details": response.text[:200]
                    }
                    
        except httpx.TimeoutException:
            return {
                "content": f"Request timeout after {self.timeout}s - model may be loading",
                "tool_calls": None,
                "provider": "ollama",
                "error": "timeout"
            }
        except Exception as e:
            return {
                "content": f"Generation error: {str(e)}",
                "tool_calls": None,
                "provider": "ollama",
                "error": str(e)
            }
    
    def _parse_tool_calls_from_text(self, content: str, available_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse tool calls from text response for models without native function calling"""
        import re
        import json
        
        tool_calls = []
        tool_names = [tool.get("name", "") for tool in available_tools]
        
        # Add debugging
        logging.info(f"Available tool names: {tool_names}")
        logging.info(f"Content to parse: {content[:200]}...")
        
        # Pattern to match TOOL_CALL: function_name {"param": "value"}
        pattern = r'TOOL_CALL:\s*(\w+)\s*(\{[^}]*\})'
        matches = re.findall(pattern, content)
        
        logging.info(f"Found {len(matches)} potential tool calls")
        
        for function_name, args_str in matches:
            logging.info(f"Checking function: '{function_name}' against available tools: {tool_names}")
            
            if function_name in tool_names:
                try:
                    # Parse the JSON arguments
                    arguments = json.loads(args_str)
                    
                    tool_calls.append({
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(arguments)
                        }
                    })
                    logging.info(f"Successfully parsed tool call: {function_name} with args: {arguments}")
                    
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse tool call arguments: {args_str} - {e}")
                    continue
            else:
                logging.warning(f"Unknown tool function: {function_name} (available: {tool_names})")
        
        return tool_calls
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> Any:
        """Format tools for Ollama's native tool calling API"""
        formatted_tools = []
        for tool in tools:
            formatted_tools.append({
                "type": "function",
                "function": tool
            })
        return formatted_tools

    async def _check_running_models(self) -> Dict[str, Any]:
        """Check which models are currently loaded in Ollama memory/VRAM"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ps")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Find our specific model
                    our_model = None
                    for model in models:
                        if model.get("name") == self.model or model.get("model") == self.model:
                            our_model = model
                            break
                    
                    return {
                        "success": True,
                        "total_models_loaded": len(models),
                        "all_loaded_models": [m.get("name", "unknown") for m in models],
                        "our_model_loaded": our_model is not None,
                        "our_model_info": our_model,
                        "total_vram_used": sum(m.get("size_vram", 0) for m in models),
                        "models_detail": models
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to check running models: {response.status_code}",
                        "details": response.text[:200]
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error checking running models: {str(e)}",
                "details": f"Error type: {type(e).__name__}"
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection with progressive complexity and detailed diagnostics"""
        try:
            # Level 1: Basic connection test
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    logging.info(f"Testing connection to Ollama at {self.base_url}/api/tags")
                    response = await client.get(f"{self.base_url}/api/tags")
                    logging.info(f"Connection response: {response.status_code}")
                    
                    if response.status_code != 200:
                        return {
                            "success": False, 
                            "error": f"Ollama server returned {response.status_code}",
                            "level_failed": "connection",
                            "details": response.text[:200] if response.text else "No response body"
                        }
                except httpx.ConnectError as e:
                    logging.error(f"Connection error to {self.base_url}: {e}")
                    return {
                        "success": False,
                        "error": f"Cannot connect to Ollama at {self.base_url}",
                        "level_failed": "connection",
                        "details": str(e)
                    }
                except httpx.TimeoutException:
                    logging.error(f"Connection timeout to {self.base_url}")
                    return {
                        "success": False,
                        "error": "Connection timeout to Ollama server",
                        "level_failed": "connection",
                        "details": f"Timeout after 10s connecting to {self.base_url}"
                    }
                
                # Check if our model is available
                models_data = response.json()
                models = models_data.get("models", [])
                available_models = [m["name"] for m in models]
                
                logging.info(f"Available models: {available_models}")
                logging.info(f"Looking for model: {self.model}")
                
                if self.model not in available_models:
                    return {
                        "success": False, 
                        "error": f"Model {self.model} not available",
                        "level_failed": "model_availability",
                        "available_models": available_models
                    }
                
                # Level 2: Check model loading status before generation
                logging.info("Checking model loading status")
                model_status = await self._check_running_models()
                
                # Level 2: Test simple generation (bypass queue system)
                logging.info("Starting simple generation test")
                simple_test = await self._test_simple_generation()
                if not simple_test["success"]:
                    logging.error(f"Simple generation test failed: {simple_test}")
                    # Add model status to the error response for debugging
                    simple_test["model_status_before_test"] = model_status
                    return simple_test
                
                # Level 3: Test chat format
                logging.info("Starting chat generation test")
                chat_test = await self._test_chat_generation()
                if not chat_test["success"]:
                    logging.error(f"Chat generation test failed: {chat_test}")
                    return chat_test
                
                logging.info("All tests passed successfully")
                
                # Final model status check
                final_model_status = await self._check_running_models()
                
                return {
                    "success": True,
                    "model": self.model,
                    "available_models": available_models,
                    "queue_size": OllamaProvider._request_queue.qsize() if OllamaProvider._request_queue else 0,
                    "tests_passed": ["connection", "model_availability", "simple_generation", "chat_generation"],
                    "final_model_status": final_model_status
                }
                
        except Exception as e:
            logging.error(f"Unexpected error in test_connection: {e}")
            return {
                "success": False, 
                "error": str(e),
                "level_failed": "unknown",
                "details": f"Unexpected error in test_connection: {type(e).__name__}"
            }
    
    async def _test_simple_generation(self) -> Dict[str, Any]:
        """Test simple generation with minimal payload"""
        payload = {
            "model": self.model,
            "prompt": "Hello",
            "stream": False,
            "options": {
                "num_predict": 5,  # Very short response
                "temperature": 0.1
            }
        }
        
        logging.info(f"Testing simple generation with payload: {payload}")
        
        try:
            # Check model status before the request
            pre_request_status = await self._check_running_models()
            logging.info(f"Model status before generation: {pre_request_status.get('our_model_loaded', False)}")
            
            async with httpx.AsyncClient(timeout=None) as client:  # No timeout for large models
                start_time = time.time()
                logging.info(f"Sending POST request to {self.base_url}/api/generate")
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                elapsed = time.time() - start_time
                
                logging.info(f"Generation response: {response.status_code} (took {elapsed:.1f}s)")
                
                # Check model status after the request
                post_request_status = await self._check_running_models()
                logging.info(f"Model status after generation: {post_request_status.get('our_model_loaded', False)}")
                
                if response.status_code == 200:
                    result = response.json()
                    logging.info(f"Generation result keys: {list(result.keys())}")
                    
                    if result.get("response"):
                        logging.info(f"Generation successful, response: '{result['response'][:100]}'")
                        return {
                            "success": True,
                            "test": "simple_generation",
                            "elapsed": f"{elapsed:.1f}s",
                            "response_preview": result["response"][:50],
                            "model_status_before": pre_request_status,
                            "model_status_after": post_request_status
                        }
                    else:
                        logging.error(f"Empty response from Ollama: {result}")
                        return {
                            "success": False,
                            "error": "Empty response from Ollama",
                            "level_failed": "simple_generation",
                            "elapsed": f"{elapsed:.1f}s",
                            "raw_response": str(result),
                            "model_status_before": pre_request_status,
                            "model_status_after": post_request_status
                        }
                else:
                    logging.error(f"Generation failed with status {response.status_code}: {response.text[:200]}")
                    return {
                        "success": False,
                        "error": f"Generation failed with status {response.status_code}",
                        "level_failed": "simple_generation",
                        "elapsed": f"{elapsed:.1f}s",
                        "details": response.text[:200]
                    }
                    
        except httpx.TimeoutException:
            # This should rarely happen now with no timeout limits
            logging.error("Generation request was cancelled or timed out")
            timeout_status = await self._check_running_models()
            return {
                "success": False,
                "error": "Generation was cancelled or network issue occurred",
                "level_failed": "simple_generation",
                "details": "Check your network connection or try again",
                "model_status_before": pre_request_status if 'pre_request_status' in locals() else None,
                "model_status_at_timeout": timeout_status
            }
        except Exception as e:
            logging.error(f"Generation test exception: {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": f"Generation test failed: {str(e)}",
                "level_failed": "simple_generation",
                "details": f"Error type: {type(e).__name__}"
            }
    
    async def _test_chat_generation(self) -> Dict[str, Any]:
        """Test chat-style generation using /api/chat endpoint if available"""
        # Try new /api/chat endpoint first
        chat_payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Say 'Hello world' and nothing else."}
            ],
            "stream": False,
            "options": {
                "num_predict": 10,
                "temperature": 0.1
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:  # No timeout for large models
                start_time = time.time()
                
                # Try /api/chat first (newer endpoint)
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=chat_payload,
                    headers={"Content-Type": "application/json"}
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("message", {}).get("content"):
                        return {
                            "success": True,
                            "test": "chat_generation",
                            "endpoint_used": "/api/chat",
                            "elapsed": f"{elapsed:.1f}s",
                            "response_preview": result["message"]["content"][:50]
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Empty message content from /api/chat",
                            "level_failed": "chat_generation",
                            "elapsed": f"{elapsed:.1f}s",
                            "raw_response": str(result)
                        }
                        
                elif response.status_code == 404:
                    # /api/chat not available, fallback to /api/generate with chat format
                    return await self._test_generate_with_chat_format()
                    
                else:
                    return {
                        "success": False,
                        "error": f"Chat generation failed with status {response.status_code}",
                        "level_failed": "chat_generation",
                        "elapsed": f"{elapsed:.1f}s",
                        "details": response.text[:200]
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Chat generation was cancelled or network issue",
                "level_failed": "chat_generation",
                "details": "Check your network connection or try again"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Chat generation test failed: {str(e)}",
                "level_failed": "chat_generation",
                "details": f"Error type: {type(e).__name__}"
            }
    
    async def _test_generate_with_chat_format(self) -> Dict[str, Any]:
        """Fallback test using /api/generate with chat-formatted prompt"""
        prompt = "User: Say 'Hello world' and nothing else.\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 10,
                "temperature": 0.1
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:  # No timeout for large models
                start_time = time.time()
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("response"):
                        return {
                            "success": True,
                            "test": "chat_generation",
                            "endpoint_used": "/api/generate (chat format)",
                            "elapsed": f"{elapsed:.1f}s",
                            "response_preview": result["response"][:50]
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Empty response from /api/generate",
                            "level_failed": "chat_generation",
                            "elapsed": f"{elapsed:.1f}s",
                            "raw_response": str(result)
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Generate with chat format failed: {response.status_code}",
                        "level_failed": "chat_generation",
                        "elapsed": f"{elapsed:.1f}s",
                        "details": response.text[:200]
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Generate chat format test failed: {str(e)}",
                "level_failed": "chat_generation",
                "details": f"Error type: {type(e).__name__}"
            }

    async def _check_running_models(self) -> Dict[str, Any]:
        """Check which models are currently loaded in Ollama memory/VRAM"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ps")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Find our specific model
                    our_model = None
                    for model in models:
                        if model.get("name") == self.model or model.get("model") == self.model:
                            our_model = model
                            break
                    
                    return {
                        "success": True,
                        "total_models_loaded": len(models),
                        "all_loaded_models": [m.get("name", "unknown") for m in models],
                        "our_model_loaded": our_model is not None,
                        "our_model_info": our_model,
                        "total_vram_used": sum(m.get("size_vram", 0) for m in models),
                        "models_detail": models
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to check running models: {response.status_code}",
                        "details": response.text[:200]
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error checking running models: {str(e)}",
                "details": f"Error type: {type(e).__name__}"
            }

class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # Import here to make it optional
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=config.api_key)
        except ImportError:
            raise ImportError("openai package required for OpenAI provider")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion with OpenAI"""
        
        try:
            kwargs = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
            
            if tools:
                kwargs["tools"] = [{"type": "function", "function": func} for func in tools]
                kwargs["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            
            return {
                "content": message.content,
                "tool_calls": message.tool_calls,
                "provider": "openai",
                "model": self.config.model_name
            }
            
        except Exception as e:
            return {
                "content": f"Sorry, I encountered an error: {str(e)}",
                "tool_calls": None,
                "provider": "openai",
                "error": str(e)
            }
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> Any:
        """OpenAI expects tools in specific format"""
        return tools

class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # Import here to make it optional
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        except ImportError:
            raise ImportError("anthropic package required for Anthropic provider")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chat completion with Anthropic Claude"""
        
        try:
            # Convert messages format for Anthropic
            system_message = ""
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append(msg)
            
            kwargs = {
                "model": self.config.model_name,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": claude_messages
            }
            
            if system_message:
                kwargs["system"] = system_message
            
            if tools:
                kwargs["tools"] = self.format_tools_for_provider(tools)
            
            response = await self.client.messages.create(**kwargs)
            
            # Extract tool calls if any
            tool_calls = []
            content = ""
            
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input)
                        }
                    })
            
            return {
                "content": content,
                "tool_calls": tool_calls if tool_calls else None,
                "provider": "anthropic",
                "model": self.config.model_name
            }
            
        except Exception as e:
            return {
                "content": f"Sorry, I encountered an error: {str(e)}",
                "tool_calls": None,
                "provider": "anthropic",
                "error": str(e)
            }
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> Any:
        """Format tools for Anthropic's format"""
        formatted_tools = []
        for tool in tools:
            func = tool
            if isinstance(tool, dict) and "function" in tool:
                func = tool["function"]
            
            formatted_tools.append({
                "name": func["name"],
                "description": func["description"],
                "input_schema": func.get("parameters", {})
            })
        return formatted_tools

class MockAIProvider(BaseAIProvider):
    """Minimal mock AI provider - fails fast when no real AI is available"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fail fast with clear error message"""
        
        return {
            "content": "⚠️ No AI model is currently available. Please configure a proper AI model (Ollama, OpenAI, or Anthropic) in Admin > AI Models.",
            "tool_calls": None,
            "provider": "mock",
            "model": self.config.model_name,
            "error": "No real AI provider configured"
        }
    
    def format_tools_for_provider(self, tools: List[Dict[str, Any]]) -> Any:
        """Mock provider can handle any tool format"""
        return tools

class AIProviderManager:
    """Manages different AI providers and configurations"""
    
    def __init__(self):
        self.providers = {}
        self.default_configs = self._get_default_configs()
        self.current_config = self._load_current_config()
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        # Cache for Ollama models to avoid repeated API calls
        self._ollama_models_cache = None
        self._ollama_cache_time = 0
    
    def _get_default_configs(self) -> Dict[str, ModelConfig]:
        """Get default model configurations"""
        return {
            "mock_assistant": ModelConfig(
                provider="mock",
                model_name="test-assistant",
                endpoint_url="local://mock",
                max_tokens=500,
                temperature=0.7,
                enabled=True
            ),
# Ollama models will be discovered dynamically
            "openai_gpt4o_mini": ModelConfig(
                provider="openai",
                model_name="gpt-4o-mini",
                endpoint_url="https://api.openai.com/v1",
                api_key=os.getenv("OPENAI_API_KEY"),
                max_tokens=500,
                temperature=0.7,
                enabled=bool(os.getenv("OPENAI_API_KEY"))
            ),
            "openai_gpt4": ModelConfig(
                provider="openai", 
                model_name="gpt-4",
                endpoint_url="https://api.openai.com/v1",
                api_key=os.getenv("OPENAI_API_KEY"),
                max_tokens=500,
                temperature=0.7,
                enabled=bool(os.getenv("OPENAI_API_KEY"))
            ),
            "anthropic_claude": ModelConfig(
                provider="anthropic",
                model_name="claude-3-sonnet-20240229",
                endpoint_url="https://api.anthropic.com",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                max_tokens=500,
                temperature=0.7,
                enabled=bool(os.getenv("ANTHROPIC_API_KEY"))
            )
        }
    
    def _load_current_config(self) -> str:
        """Load current model config from environment or default"""
        return os.getenv("CURRENT_AI_MODEL", "mock_assistant")
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """Get all available model configurations including dynamic Ollama models"""
        # Start with static configs
        models = {k: v for k, v in self.default_configs.items() if v.enabled}
        
        # Add dynamic Ollama models
        ollama_models = self._get_ollama_models()
        models.update(ollama_models)
        
        return models
    
    def get_current_model_key(self) -> str:
        """Get the current model key"""
        return self.current_config
    
    def get_current_model_config(self) -> ModelConfig:
        """Get the current model configuration"""
        # Check if it's a dynamic Ollama model first
        all_models = self.get_available_models()
        return all_models.get(self.current_config) or self.default_configs.get(self.current_config)
    
    def get_current_provider(self) -> BaseAIProvider:
        """Get the currently configured AI provider"""
        # Get all available models (including dynamic Ollama ones)
        all_models = self.get_available_models()
        config = all_models.get(self.current_config)
        
        if not config or not config.enabled:
            # Fallback to first available
            if not all_models:
                raise ValueError("No AI models configured or available")
            config = list(all_models.values())[0]
            self.current_config = list(all_models.keys())[0]
        
        return self._create_provider(config)
    
    def _create_provider(self, config: ModelConfig) -> BaseAIProvider:
        """Create provider instance for given config"""
        if config.provider == "mock":
            return MockAIProvider(config)
        elif config.provider == "ollama":
            return OllamaProvider(config)
        elif config.provider == "openai":
            return OpenAIProvider(config)
        elif config.provider == "anthropic":
            return AnthropicProvider(config)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")
    
    def set_current_model(self, model_key: str) -> bool:
        """Set the current model"""
        all_models = self.get_available_models()
        if model_key in all_models and all_models[model_key].enabled:
            self.current_config = model_key
            return True
        return False
    
    async def test_provider(self, model_key: str) -> Dict[str, Any]:
        """Test if a provider is working with progressive testing and detailed diagnostics"""
        all_models = self.get_available_models()
        if model_key not in all_models:
            return {"success": False, "error": "Model not found"}
        
        config = all_models[model_key]
        if not config.enabled:
            return {"success": False, "error": "Model not enabled"}
        
        try:
            provider = self._create_provider(config)
            
            # For Ollama, use the new progressive testing system
            if config.provider == "ollama":
                # Use the provider's own progressive test_connection method
                logging.info(f"Starting progressive test for Ollama model: {model_key}")
                result = await provider.test_connection()
                logging.info(f"Progressive test completed for {model_key}: {result.get('success')}")
                return result
            
            # For other providers, use simplified validation
            else:
                if config.provider == "openai":
                    # Validate OpenAI configuration
                    if not config.api_key:
                        return {
                            "success": False,
                            "error": "OpenAI API key not configured",
                            "details": "Set OPENAI_API_KEY environment variable"
                        }
                    
                elif config.provider == "anthropic":
                    # Validate Anthropic configuration
                    if not config.api_key:
                        return {
                            "success": False,
                            "error": "Anthropic API key not configured",
                            "details": "Set ANTHROPIC_API_KEY environment variable"
                        }
                
                return {
                    "success": True, 
                    "provider": config.provider,
                    "model": config.model_name,
                    "endpoint": config.endpoint_url,
                    "tests_passed": ["configuration_valid"]
                }
                
        except Exception as e:
            logging.error(f"Provider creation failed for {model_key}: {e}")
            return {
                "success": False, 
                "error": str(e),
                "details": f"Provider creation failed: {type(e).__name__}"
            }

    def _get_ollama_models(self) -> Dict[str, ModelConfig]:
        """Discover available Ollama models dynamically"""
        current_time = time.time()
        
        # Use cache if it's less than 30 seconds old
        if (self._ollama_models_cache is not None and 
            current_time - self._ollama_cache_time < 30):
            return self._ollama_models_cache
        
        models = {}
        
        try:
            # Query Ollama API for available models
            response = httpx.get(f"{self.ollama_endpoint}/api/tags", timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                
                for model_info in data.get("models", []):
                    model_name = model_info.get("name", "")
                    if model_name:
                        # Create a safe key for the model
                        safe_key = f"ollama_{model_name.replace(':', '_').replace('/', '_')}"
                        
                        # Determine temperature based on model type
                        temperature = 0.3 if "code" in model_name.lower() else 0.7
                        
                        models[safe_key] = ModelConfig(
                            provider="ollama",
                            model_name=model_name,
                            endpoint_url=self.ollama_endpoint,
                            max_tokens=500,
                            temperature=temperature,
                            enabled=True
                        )
                        
                # Update cache
                self._ollama_models_cache = models
                self._ollama_cache_time = current_time
                
        except Exception as e:
            # If Ollama is not available, just return empty dict
            # Don't raise an error as other providers might still work
            print(f"Could not connect to Ollama at {self.ollama_endpoint}: {e}")
            models = {}
        
        return models
    
    def refresh_ollama_models(self) -> Dict[str, ModelConfig]:
        """Force refresh of Ollama models cache"""
        self._ollama_models_cache = None
        self._ollama_cache_time = 0
        return self._get_ollama_models()

# Global manager instance
ai_manager = AIProviderManager() 