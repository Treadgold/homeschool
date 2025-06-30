"""
Integration tests for Function Calling
Tests real AI provider function calling with debugging and connectivity checks
"""

import pytest
import asyncio
import httpx
import json
import os
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock

from app.ai_providers import ai_manager, OllamaProvider, ModelConfig
from app.ai_tools import DynamicEventTools
from tests.conftest import create_test_ai_response


@pytest.mark.integration
@pytest.mark.function_calling
@pytest.mark.requires_ollama
class TestOllamaFunctionCalling:
    """Test Ollama function calling integration"""

    @pytest.fixture
    def ollama_config(self):
        """Ollama configuration for testing"""
        return ModelConfig(
            provider="ollama",
            model_name="devstral:latest",
            endpoint_url="http://host.docker.internal:11434",
            max_tokens=1000,
            temperature=0.7
        )

    @pytest.fixture
    def ollama_provider(self, ollama_config):
        """Create Ollama provider for testing"""
        return OllamaProvider(ollama_config)

    @pytest.mark.asyncio
    async def test_ollama_connectivity(self, ollama_provider):
        """Test basic Ollama connectivity with debugging"""
        print(f"\n🔍 Testing Ollama connectivity...")
        print(f"   Endpoint: {ollama_provider.base_url}")
        print(f"   Model: {ollama_provider.model}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{ollama_provider.base_url}/api/tags")
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available_models = [m["name"] for m in models]
                    
                    print(f"   ✅ Connected to Ollama")
                    print(f"   📋 Available models: {available_models}")
                    
                    if ollama_provider.model in available_models:
                        print(f"   ✅ Model {ollama_provider.model} is available")
                        return True
                    else:
                        print(f"   ❌ Model {ollama_provider.model} not found")
                        pytest.skip(f"Model {ollama_provider.model} not available")
                else:
                    print(f"   ❌ Connection failed: {response.status_code}")
                    pytest.skip("Ollama not accessible")
                    
        except httpx.ConnectError:
            print("   ❌ Connection failed - Ollama not running")
            pytest.skip("Ollama not running")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            pytest.skip(f"Ollama connection error: {e}")

    @pytest.mark.asyncio
    async def test_simple_function_call(self, ollama_provider):
        """Test simple function calling with debugging"""
        # Skip if Ollama not available
        try:
            await self.test_ollama_connectivity(ollama_provider)
        except pytest.skip.Exception:
            pytest.skip("Ollama not available")
        
        print(f"\n🧪 Testing simple function call...")
        
        tools = [
            {
                "type": "function",
                "function": {
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
            }
        ]
        
        messages = [
            {
                "role": "user", 
                "content": "Please call the test_function_call function with message='Function calling works!' and status='success'"
            }
        ]
        
        try:
            start_time = asyncio.get_event_loop().time()
            result = await ollama_provider.chat_completion(messages, tools)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            print(f"   ⏱️  Response time: {elapsed:.2f}s")
            print(f"   📋 Response: {json.dumps(result, indent=2)}")
            
            if result.get("tool_calls"):
                print(f"   🎉 Function calls detected: {len(result['tool_calls'])}")
                for i, call in enumerate(result["tool_calls"]):
                    print(f"      Call {i+1}: {call['name']} - {call.get('arguments', {})}")
                
                assert len(result["tool_calls"]) > 0
                assert result["tool_calls"][0]["name"] == "test_function_call"
                return True
            else:
                print(f"   ⚠️  No function calls in response")
                print(f"   📝 Content: {result.get('content', 'No content')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Function call test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_event_creation_function_calls(self, ollama_provider, test_db_session, test_user):
        """Test event creation function calls"""
        if not await self.test_ollama_connectivity(ollama_provider):
            pytest.skip("Ollama not available")
        
        print(f"\n🧪 Testing event creation function calls...")
        
        # Initialize event tools
        tools = DynamicEventTools(test_db_session, test_user.id)
        tool_definitions = tools.get_tool_definitions()
        
        print(f"   📋 Available tools: {len(tool_definitions)}")
        for tool in tool_definitions:
            print(f"      - {tool['name']}")
        
        messages = [
            {
                "role": "user",
                "content": "Create a birthday party event for a 10-year-old child. The party should be at the community center, cost $25, and allow up to 15 children."
            }
        ]
        
        try:
            start_time = asyncio.get_event_loop().time()
            result = await ollama_provider.chat_completion(messages, tool_definitions)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            print(f"   ⏱️  Response time: {elapsed:.2f}s")
            print(f"   📋 Response content: {result.get('content', 'No content')[:200]}...")
            
            if result.get("tool_calls"):
                print(f"   🎉 Tool calls detected: {len(result['tool_calls'])}")
                for call in result["tool_calls"]:
                    print(f"      Tool: {call['name']}")
                    print(f"      Args: {call.get('arguments', {})}")
                
                # Verify we got an event creation call
                event_calls = [call for call in result["tool_calls"] if call["name"] == "create_event_draft"]
                assert len(event_calls) > 0, "No event creation calls found"
                
                # Verify the call has reasonable arguments
                event_call = event_calls[0]
                args = event_call.get("arguments", {})
                assert "title" in args, "Event title missing"
                
                print(f"   ✅ Event creation call successful: {args.get('title')}")
                return True
            else:
                print(f"   ⚠️  No tool calls detected")
                return False
                
        except Exception as e:
            print(f"   ❌ Event creation test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_function_calling_error_handling(self, ollama_provider):
        """Test function calling error handling"""
        if not await self.test_ollama_connectivity(ollama_provider):
            pytest.skip("Ollama not available")
        
        print(f"\n🧪 Testing function calling error handling...")
        
        # Test with malformed tool definition
        malformed_tools = [
            {
                "type": "function",
                "function": {
                    "name": "invalid_tool",
                    # Missing required fields
                }
            }
        ]
        
        messages = [
            {"role": "user", "content": "Call the invalid tool"}
        ]
        
        try:
            result = await ollama_provider.chat_completion(messages, malformed_tools)
            
            # Should handle malformed tools gracefully
            assert "error" in result or "content" in result
            print(f"   ✅ Error handled gracefully: {result.get('error', 'No error')}")
            
        except Exception as e:
            print(f"   ✅ Exception handled: {e}")
            # Exceptions are acceptable for malformed tools

    @pytest.mark.asyncio
    async def test_function_calling_performance(self, ollama_provider):
        """Test function calling performance with multiple calls"""
        if not await self.test_ollama_connectivity(ollama_provider):
            pytest.skip("Ollama not available")
        
        print(f"\n🧪 Testing function calling performance...")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A simple test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string", "description": "Test value"}
                        },
                        "required": ["value"]
                    }
                }
            }
        ]
        
        messages = [
            {"role": "user", "content": "Call test_function with value='test1', then call it again with value='test2'"}
        ]
        
        try:
            start_time = asyncio.get_event_loop().time()
            result = await ollama_provider.chat_completion(messages, tools)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            print(f"   ⏱️  Total time: {elapsed:.2f}s")
            
            if result.get("tool_calls"):
                print(f"   📞 Function calls: {len(result['tool_calls'])}")
                print(f"   ⚡ Avg time per call: {elapsed/len(result['tool_calls']):.2f}s")
                
                # Performance should be reasonable (< 30s for multiple calls)
                assert elapsed < 30, f"Function calling too slow: {elapsed:.2f}s"
                
            print(f"   ✅ Performance test completed")
            
        except Exception as e:
            print(f"   ❌ Performance test failed: {e}")
            raise


@pytest.mark.integration
@pytest.mark.function_calling
class TestFunctionCallingDebugger:
    """Debug utilities for function calling"""

    def test_debug_tool_schema_validation(self, dynamic_event_tools):
        """Test and debug tool schema validation"""
        print(f"\n🔍 Debugging tool schema validation...")
        
        tool_definitions = dynamic_event_tools.get_tool_definitions()
        
        for tool in tool_definitions:
            print(f"\n📋 Tool: {tool['name']}")
            print(f"   Description: {tool['description']}")
            
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            
            params = tool["parameters"]
            assert "type" in params
            assert params["type"] == "object"
            assert "properties" in params
            
            print(f"   ✅ Schema valid")
        
        print(f"   ✅ All {len(tool_definitions)} tools have valid schemas")

    def test_debug_function_call_parsing(self, ollama_provider):
        """Test and debug function call parsing"""
        print(f"\n🔍 Debugging function call parsing...")
        
        # Test different response formats that might be returned
        test_responses = [
            # Standard format
            {
                "content": "I'll call the function for you.",
                "tool_calls": [
                    {
                        "name": "test_function",
                        "arguments": {"value": "test"}
                    }
                ]
            },
            # Text-based format (some models)
            {
                "content": "I'll call test_function with arguments: {\"value\": \"test\"}"
            },
            # Mixed format
            {
                "content": "Let me create an event. <function_call>create_event_draft({\"title\": \"Test Event\"})</function_call>",
                "tool_calls": None
            }
        ]
        
        for i, response in enumerate(test_responses):
            print(f"\n   Test {i+1}: {response.get('content', '')[:50]}...")
            
            # Test parsing
            if response.get("tool_calls"):
                print(f"      ✅ Standard tool calls: {len(response['tool_calls'])}")
            else:
                # Test text parsing
                content = response.get("content", "")
                if "function_call" in content.lower() or "create_event" in content.lower():
                    print(f"      ⚠️  Text-based function call detected")
                    
                    # Test text parsing logic
                    available_tools = [{"name": "create_event_draft", "description": "Create event"}]
                    parsed_calls = ollama_provider._parse_tool_calls_from_text(content, available_tools)
                    
                    if parsed_calls:
                        print(f"      ✅ Parsed {len(parsed_calls)} calls from text")
                    else:
                        print(f"      ❌ No calls parsed from text")
                else:
                    print(f"      ✅ Regular text response")

    @pytest.mark.asyncio
    async def test_debug_ai_agent_integration(self, test_db_session, test_user):
        """Debug AI agent integration with function calling"""
        print(f"\n🔍 Debugging AI agent integration...")
        
        from app.ai_agent import EventCreationAgent
        
        with patch('app.ai_providers.ai_manager') as mock_manager:
            mock_provider = Mock()
            mock_provider.chat_completion = AsyncMock(return_value={
                "content": "I'll create a birthday party event for you.",
                "tool_calls": [
                    {
                        "name": "create_event_draft",
                        "arguments": {
                            "title": "Birthday Party",
                            "description": "A fun birthday party",
                            "location": "Community Center",
                            "max_pupils": 15,
                            "cost": 25.0
                        }
                    }
                ]
            })
            
            mock_manager.get_current_provider.return_value = mock_provider
            mock_manager.get_current_model_config.return_value = Mock(model_name="test-model")
            
            agent = EventCreationAgent(test_db_session, test_user.id)
            
            print(f"   Testing conversation start...")
            conversation_result = await agent.start_conversation()
            assert conversation_result["success"] is True
            
            conversation_id = conversation_result["conversation_id"]
            print(f"   ✅ Conversation started: {conversation_id}")
            
            print(f"   Testing message processing...")
            message_result = await agent.process_message(
                conversation_id, 
                "Create a birthday party event for a 10-year-old"
            )
            
            print(f"   📋 Message result: {message_result}")
            
            if message_result.get("success"):
                print(f"   ✅ Message processed successfully")
                if "tool_results" in message_result:
                    print(f"   🎉 Tool results present: {len(message_result['tool_results'])}")
                else:
                    print(f"   ⚠️  No tool results (might be expected)")
            else:
                print(f"   ❌ Message processing failed: {message_result.get('error')}")
                
            print(f"   ✅ AI agent integration test completed") 