#!/usr/bin/env python3
"""
AI Agent Debug Utility
Comprehensive debugging and testing tool for the AI Agent system
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.database import get_db
from app.ai_providers import ai_manager, ModelConfig, OllamaProvider
from app.ai_tools import DynamicEventTools
from app.ai_agent import EventCreationAgent, DatabaseHealthChecker
from app.ai_assistant import ThinkingEventAgent
from app.models import User, Event, ChatConversation

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_ai_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class AIAgentDebugger:
    """Comprehensive AI Agent debugging utility"""
    
    def __init__(self):
        self.db = next(get_db())
        self.test_user_id = None
        self.debug_results = {}
    
    async def run_full_diagnostic(self):
        """Run complete diagnostic suite"""
        print("🔬 AI Agent Debug Suite")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Phase 1: Database Health
        await self._check_database_health()
        
        # Phase 2: AI Provider Health
        await self._check_ai_provider_health()
        
        # Phase 3: Tool System Health
        await self._check_tool_system_health()
        
        # Phase 4: Agent Integration Health
        await self._check_agent_integration_health()
        
        # Phase 5: Function Calling Health
        await self._check_function_calling_health()
        
        # Phase 6: End-to-End Testing
        await self._run_end_to_end_tests()
        
        # Generate Report
        self._generate_debug_report()
    
    async def _check_database_health(self):
        """Check database connectivity and schema"""
        print("\n📊 Phase 1: Database Health Check")
        print("-" * 40)
        
        try:
            # Test basic connection
            from sqlalchemy import text
            result = self.db.execute(text("SELECT 1")).fetchone()
            print("✅ Database connection: OK")
            
            # Check required tables
            health_checker = DatabaseHealthChecker()
            table_results = health_checker.check_required_tables(self.db)
            missing_tables = health_checker.get_missing_tables(self.db)
            
            print(f"📋 Table Check Results:")
            for table, exists in table_results.items():
                status = "✅" if exists else "❌"
                print(f"   {status} {table}")
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {missing_tables}")
                print("💡 Run: alembic upgrade head")
            else:
                print("✅ All required tables present")
            
            # Check test user
            test_user = self.db.query(User).filter(User.is_admin == True).first()
            if test_user:
                self.test_user_id = test_user.id
                print(f"✅ Test user found: {test_user.email} (ID: {test_user.id})")
            else:
                print("⚠️  No admin user found for testing")
            
            self.debug_results["database"] = {
                "connection": "OK",
                "tables": table_results,
                "missing_tables": missing_tables,
                "test_user_id": self.test_user_id
            }
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            self.debug_results["database"] = {"error": str(e)}
    
    async def _check_ai_provider_health(self):
        """Check AI provider connectivity and configuration"""
        print("\n🤖 Phase 2: AI Provider Health Check")
        print("-" * 40)
        
        try:
            # Get current provider configuration
            current_provider = ai_manager.get_current_provider()
            current_config = ai_manager.get_current_model_config()
            
            print(f"🔧 Current Provider: {current_provider.__class__.__name__}")
            print(f"🔧 Current Model: {current_config.model_name if current_config else 'Unknown'}")
            print(f"🔧 Endpoint: {current_config.endpoint_url if current_config else 'Unknown'}")
            
            # Test provider connectivity
            if isinstance(current_provider, OllamaProvider):
                await self._test_ollama_connectivity(current_provider)
            else:
                print(f"ℹ️  Provider type: {type(current_provider).__name__}")
            
            # Test simple completion
            print("\n🧪 Testing simple completion...")
            start_time = time.time()
            
            try:
                response = await current_provider.chat_completion([
                    {"role": "user", "content": "Say 'Hello from AI Debug' exactly"}
                ])
                elapsed = time.time() - start_time
                
                print(f"✅ Completion successful ({elapsed:.2f}s)")
                print(f"📝 Response: {response.get('content', 'No content')[:100]}...")
                
                self.debug_results["ai_provider"] = {
                    "provider": current_provider.__class__.__name__,
                    "model": current_config.model_name if current_config else None,
                    "response_time": elapsed,
                    "response_content": response.get('content', '')[:200]
                }
                
            except Exception as e:
                print(f"❌ Completion failed: {e}")
                self.debug_results["ai_provider"] = {"error": str(e)}
            
        except Exception as e:
            print(f"❌ Provider check failed: {e}")
            self.debug_results["ai_provider"] = {"error": str(e)}
    
    async def _test_ollama_connectivity(self, provider):
        """Test Ollama-specific connectivity"""
        import httpx
        
        print(f"🔍 Testing Ollama connectivity...")
        print(f"   Endpoint: {provider.base_url}")
        print(f"   Model: {provider.model}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Test basic endpoint
                response = await client.get(f"{provider.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available_models = [m["name"] for m in models]
                    
                    print(f"✅ Ollama connected")
                    print(f"📋 Available models ({len(available_models)}): {', '.join(available_models[:3])}{'...' if len(available_models) > 3 else ''}")
                    
                    if provider.model in available_models:
                        print(f"✅ Target model '{provider.model}' is available")
                    else:
                        print(f"⚠️  Target model '{provider.model}' not found")
                        print(f"💡 Available models: {available_models}")
                else:
                    print(f"❌ Ollama API error: {response.status_code}")
                    
        except httpx.ConnectError:
            print(f"❌ Cannot connect to Ollama at {provider.base_url}")
            print("💡 Make sure Ollama is running and accessible")
        except Exception as e:
            print(f"❌ Ollama connectivity error: {e}")
    
    async def _check_tool_system_health(self):
        """Check tool system functionality"""
        print("\n🛠️  Phase 3: Tool System Health Check")
        print("-" * 40)
        
        if not self.test_user_id:
            print("⚠️  Skipping tool tests - no test user available")
            return
        
        try:
            # Initialize tools
            tools = DynamicEventTools(self.db, self.test_user_id)
            tool_definitions = tools.get_tool_definitions()
            
            print(f"✅ Dynamic tools initialized")
            print(f"📋 Available tools: {len(tool_definitions)}")
            
            for i, tool in enumerate(tool_definitions):
                print(f"   {i+1}. {tool['name']}: {tool['description'][:50]}...")
            
            # Test schema validation
            print(f"\n🔍 Validating tool schemas...")
            schema_errors = []
            
            for tool in tool_definitions:
                try:
                    # Basic schema validation
                    assert "name" in tool
                    assert "description" in tool
                    assert "parameters" in tool
                    
                    params = tool["parameters"]
                    assert "type" in params
                    assert params["type"] == "object"
                    assert "properties" in params
                    
                    print(f"   ✅ {tool['name']}: Schema valid")
                    
                except AssertionError as e:
                    schema_errors.append(f"{tool['name']}: {e}")
                    print(f"   ❌ {tool['name']}: Schema invalid")
            
            if schema_errors:
                print(f"\n❌ Schema errors found: {len(schema_errors)}")
                for error in schema_errors:
                    print(f"      {error}")
            else:
                print(f"✅ All tool schemas valid")
            
            # Test tool execution
            print(f"\n🧪 Testing tool execution...")
            try:
                test_result = await tools.create_event_draft(
                    title="Debug Test Event",
                    description="A test event for debugging",
                    location="Debug Location"
                )
                
                if test_result.get("success"):
                    print(f"✅ Tool execution successful")
                    print(f"📋 Result: {test_result}")
                else:
                    print(f"⚠️  Tool execution returned error: {test_result.get('error')}")
                
            except Exception as e:
                print(f"❌ Tool execution failed: {e}")
            
            self.debug_results["tools"] = {
                "count": len(tool_definitions),
                "schema_errors": schema_errors,
                "tools": [tool["name"] for tool in tool_definitions]
            }
            
        except Exception as e:
            print(f"❌ Tool system error: {e}")
            self.debug_results["tools"] = {"error": str(e)}
    
    async def _check_agent_integration_health(self):
        """Check agent integration and workflow"""
        print("\n🎯 Phase 4: Agent Integration Health Check")
        print("-" * 40)
        
        if not self.test_user_id:
            print("⚠️  Skipping agent tests - no test user available")
            return
        
        try:
            # Test EventCreationAgent
            print("🔍 Testing EventCreationAgent...")
            agent = EventCreationAgent(self.db, self.test_user_id)
            print("✅ EventCreationAgent initialized")
            
            # Test conversation start
            conversation_result = await agent.start_conversation()
            if conversation_result.get("success"):
                print("✅ Conversation start successful")
                conversation_id = conversation_result["conversation_id"]
                
                # Test message processing (with mock to avoid external dependencies)
                print("🧪 Testing message processing...")
                
                # This will likely fail due to AI provider issues, but we'll capture the error
                try:
                    message_result = await agent.process_message(
                        conversation_id,
                        "Debug test: Create a simple event"
                    )
                    
                    if message_result.get("success"):
                        print("✅ Message processing successful")
                    else:
                        print(f"⚠️  Message processing failed: {message_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"⚠️  Message processing exception: {e}")
                    # This is expected if AI provider is not working
                
            else:
                print(f"❌ Conversation start failed: {conversation_result.get('error')}")
            
            # Test ThinkingEventAgent
            print("\n🔍 Testing ThinkingEventAgent...")
            thinking_agent = ThinkingEventAgent()
            print("✅ ThinkingEventAgent initialized")
            
            self.debug_results["agents"] = {
                "event_creation_agent": "initialized",
                "thinking_event_agent": "initialized",
                "conversation_start": conversation_result.get("success", False)
            }
            
        except Exception as e:
            print(f"❌ Agent integration error: {e}")
            self.debug_results["agents"] = {"error": str(e)}
    
    async def _check_function_calling_health(self):
        """Check function calling capabilities"""
        print("\n📞 Phase 5: Function Calling Health Check")
        print("-" * 40)
        
        try:
            provider = ai_manager.get_current_provider()
            
            # Test simple function calling
            print("🧪 Testing simple function call...")
            
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "debug_test_function",
                        "description": "A simple test function for debugging",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Test message"
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["success", "error"],
                                    "description": "Test status"
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
                    "content": "Please call the debug_test_function with message='Debug test successful' and status='success'"
                }
            ]
            
            start_time = time.time()
            result = await provider.chat_completion(messages, tools)
            elapsed = time.time() - start_time
            
            print(f"⏱️  Function call test completed ({elapsed:.2f}s)")
            
            if result.get("tool_calls"):
                print(f"🎉 Function calls detected: {len(result['tool_calls'])}")
                for call in result["tool_calls"]:
                    print(f"   📞 {call['name']}: {call.get('arguments', {})}")
                
                self.debug_results["function_calling"] = {
                    "success": True,
                    "response_time": elapsed,
                    "tool_calls_count": len(result["tool_calls"])
                }
            else:
                print("⚠️  No function calls detected")
                print(f"📝 Response content: {result.get('content', 'No content')[:200]}...")
                
                # Check if it's a text-based response mentioning the function
                content = result.get('content', '').lower()
                if 'debug_test_function' in content or 'function' in content:
                    print("💡 Function mentioned in text - model may not support native function calling")
                
                self.debug_results["function_calling"] = {
                    "success": False,
                    "reason": "No tool calls in response",
                    "response_content": result.get('content', '')[:200]
                }
            
        except Exception as e:
            print(f"❌ Function calling test failed: {e}")
            self.debug_results["function_calling"] = {"error": str(e)}
    
    async def _run_end_to_end_tests(self):
        """Run end-to-end workflow tests"""
        print("\n🚀 Phase 6: End-to-End Testing")
        print("-" * 40)
        
        if not self.test_user_id:
            print("⚠️  Skipping E2E tests - no test user available")
            return
        
        print("🧪 Running event creation workflow...")
        
        # This would test the complete workflow from user input to event creation
        # For now, we'll do a simplified version that doesn't require external AI
        
        try:
            # Test database operations
            test_event = Event(
                title="Debug Test Event",
                description="Created during debug testing",
                location="Debug Location", 
                user_id=self.test_user_id,
                max_pupils=10,
                cost=0.0,
                event_type="homeschool"
            )
            
            self.db.add(test_event)
            self.db.commit()
            
            print("✅ Test event created successfully")
            
            # Clean up
            self.db.delete(test_event)
            self.db.commit()
            
            print("✅ Test cleanup successful")
            
            self.debug_results["end_to_end"] = {"database_operations": "success"}
            
        except Exception as e:
            print(f"❌ E2E test failed: {e}")
            self.debug_results["end_to_end"] = {"error": str(e)}
    
    def _generate_debug_report(self):
        """Generate comprehensive debug report"""
        print("\n📋 Debug Report Summary")
        print("=" * 60)
        
        # Overall status
        issues = []
        successes = []
        
        for component, result in self.debug_results.items():
            if isinstance(result, dict):
                if "error" in result:
                    issues.append(f"{component}: {result['error']}")
                else:
                    successes.append(component)
            else:
                successes.append(component)
        
        print(f"✅ Working Components: {len(successes)}")
        for success in successes:
            print(f"   - {success}")
        
        if issues:
            print(f"\n❌ Issues Found: {len(issues)}")
            for issue in issues:
                print(f"   - {issue}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if "database" in [i.split(':')[0] for i in issues]:
            print("   - Check database connection and run migrations")
        
        if "ai_provider" in [i.split(':')[0] for i in issues]:
            print("   - Verify AI provider (Ollama) is running and accessible")
            print("   - Check model availability with: ollama list")
        
        if "function_calling" in [i.split(':')[0] for i in issues]:
            print("   - Function calling may not be supported by current model")
            print("   - Try a different model or check model capabilities")
        
        if not issues:
            print("   🎉 All systems appear to be working correctly!")
        
        # Save detailed report
        report_file = f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.debug_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        print(f"📄 Debug log saved to: debug_ai_agent.log")


async def main():
    """Main entry point"""
    debugger = AIAgentDebugger()
    await debugger.run_full_diagnostic()


if __name__ == "__main__":
    asyncio.run(main()) 