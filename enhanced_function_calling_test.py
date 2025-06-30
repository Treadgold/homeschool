#!/usr/bin/env python3
"""
Enhanced Function Calling Test with Comprehensive Debugging
Designed to diagnose and fix function calling issues in the AI Agent
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.ai_providers import ai_manager, OllamaProvider, ModelConfig
from app.ai_tools import DynamicEventTools
from app.database import get_db
from app.models import User


class EnhancedFunctionCallingTester:
    """Enhanced function calling tester with comprehensive debugging"""
    
    def __init__(self):
        self.results = {}
        self.debug_log = []
    
    def log(self, message: str):
        """Add message to debug log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.debug_log.append(log_entry)
        print(log_entry)
    
    async def run_comprehensive_test(self):
        """Run comprehensive function calling tests"""
        self.log("🧪 Enhanced Function Calling Test Suite")
        self.log("=" * 60)
        
        # Phase 1: Environment Check
        await self._check_environment()
        
        # Phase 2: AI Provider Connectivity
        await self._test_ai_provider_connectivity()
        
        # Phase 3: Basic Function Call Test
        await self._test_basic_function_calling()
        
        # Phase 4: Event Creation Function Test
        await self._test_event_creation_functions()
        
        # Phase 5: AI Agent Integration Test
        await self._test_ai_agent_integration()
        
        # Generate comprehensive report
        self._generate_report()
        
        return self._get_overall_success()
    
    async def _check_environment(self):
        """Check environment and dependencies"""
        self.log("\n🔍 Phase 1: Environment Check")
        self.log("-" * 40)
        
        try:
            # Check database connection
            db = next(get_db())
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            self.log("✅ Database connection: OK")
            
            # Check for test user
            admin_user = db.query(User).filter(User.is_admin == True).first()
            if admin_user:
                self.log(f"✅ Admin user found: {admin_user.email}")
                self.test_user_id = admin_user.id
            else:
                self.log("⚠️  No admin user found")
                self.test_user_id = None
            
            db.close()
            
            self.results["environment"] = {"success": True, "has_admin": bool(admin_user)}
            
        except Exception as e:
            self.log(f"❌ Environment check failed: {e}")
            self.results["environment"] = {"success": False, "error": str(e)}
    
    async def _test_ai_provider_connectivity(self):
        """Test AI provider connectivity"""
        self.log("\n🤖 Phase 2: AI Provider Connectivity")
        self.log("-" * 40)
        
        try:
            # Get current provider
            provider = ai_manager.get_current_provider()
            config = ai_manager.get_current_model_config()
            
            self.log(f"🔧 Provider: {provider.__class__.__name__}")
            self.log(f"🔧 Model: {config.model_name if config else 'Unknown'}")
            self.log(f"🔧 Endpoint: {config.endpoint_url if config else 'Unknown'}")
            
            # Test connectivity based on provider type
            if isinstance(provider, OllamaProvider):
                connectivity_result = await self._test_ollama_connectivity(provider)
            else:
                self.log(f"ℹ️  Non-Ollama provider: {type(provider).__name__}")
                connectivity_result = {"connected": True, "reason": "Non-Ollama provider"}
            
            # Test basic completion
            self.log("\n🧪 Testing basic completion...")
            try:
                start_time = asyncio.get_event_loop().time()
                
                response = await provider.chat_completion([
                    {"role": "user", "content": "Respond with exactly: 'Function calling test ready'"}
                ])
                
                elapsed = asyncio.get_event_loop().time() - start_time
                
                if response.get("content"):
                    self.log(f"✅ Basic completion successful ({elapsed:.2f}s)")
                    self.log(f"📝 Response: {response['content'][:100]}...")
                    
                    basic_completion = {"success": True, "response_time": elapsed}
                else:
                    self.log("⚠️  Basic completion returned no content")
                    basic_completion = {"success": False, "reason": "No content"}
                
            except Exception as e:
                self.log(f"❌ Basic completion failed: {e}")
                basic_completion = {"success": False, "error": str(e)}
            
            self.results["ai_provider"] = {
                "provider": provider.__class__.__name__,
                "connectivity": connectivity_result,
                "basic_completion": basic_completion
            }
            
        except Exception as e:
            self.log(f"❌ AI provider test failed: {e}")
            self.results["ai_provider"] = {"success": False, "error": str(e)}
    
    async def _test_ollama_connectivity(self, provider):
        """Test Ollama-specific connectivity"""
        self.log("🔍 Testing Ollama connectivity...")
        self.log(f"   Endpoint: {provider.base_url}")
        self.log(f"   Model: {provider.model}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Test /api/tags endpoint
                response = await client.get(f"{provider.base_url}/api/tags")
                
                if response.status_code == 200:
                    models_data = response.json()
                    models = models_data.get("models", [])
                    available_models = [m["name"] for m in models]
                    
                    self.log(f"✅ Ollama API accessible")
                    self.log(f"📋 Available models: {available_models}")
                    
                    if provider.model in available_models:
                        self.log(f"✅ Target model '{provider.model}' available")
                        
                        # Test model loading
                        self.log("🔄 Testing model loading...")
                        test_response = await client.post(
                            f"{provider.base_url}/api/generate",
                            json={
                                "model": provider.model,
                                "prompt": "Test",
                                "stream": False
                            },
                            timeout=30
                        )
                        
                        if test_response.status_code == 200:
                            self.log("✅ Model loads successfully")
                            return {"connected": True, "model_available": True, "model_loads": True}
                        else:
                            self.log(f"⚠️  Model loading issue: {test_response.status_code}")
                            return {"connected": True, "model_available": True, "model_loads": False}
                    else:
                        self.log(f"❌ Target model '{provider.model}' not available")
                        self.log(f"💡 Available: {available_models}")
                        return {"connected": True, "model_available": False}
                else:
                    self.log(f"❌ Ollama API error: {response.status_code}")
                    return {"connected": False, "api_error": response.status_code}
                    
        except httpx.ConnectError:
            self.log(f"❌ Cannot connect to Ollama at {provider.base_url}")
            self.log("💡 Suggestions:")
            self.log("   - Ensure Ollama is running: ollama serve")
            self.log("   - Check if the endpoint is accessible from Docker")
            self.log("   - Try: docker run --network host ...")
            return {"connected": False, "reason": "connection_error"}
        except Exception as e:
            self.log(f"❌ Connectivity test error: {e}")
            return {"connected": False, "error": str(e)}
    
    async def _test_basic_function_calling(self):
        """Test basic function calling capabilities"""
        self.log("\n📞 Phase 3: Basic Function Calling Test")
        self.log("-" * 40)
        
        try:
            provider = ai_manager.get_current_provider()
            
            # Define a simple test function
            test_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "debug_test_function",
                        "description": "A simple function to test function calling capability",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "A test message to echo back"
                                },
                                "number": {
                                    "type": "integer", 
                                    "description": "A test number"
                                }
                            },
                            "required": ["message", "number"]
                        }
                    }
                }
            ]
            
            test_messages = [
                {
                    "role": "user",
                    "content": "Please call the debug_test_function with message='Hello Function Calling' and number=42"
                }
            ]
            
            self.log("🧪 Sending function calling request...")
            self.log(f"📋 Tool definition: {json.dumps(test_tools[0], indent=2)}")
            
            start_time = asyncio.get_event_loop().time()
            
            response = await provider.chat_completion(test_messages, test_tools)
            
            elapsed = asyncio.get_event_loop().time() - start_time
            
            self.log(f"⏱️  Response received ({elapsed:.2f}s)")
            self.log(f"📋 Full response: {json.dumps(response, indent=2)}")
            
            # Analyze response
            analysis = self._analyze_function_call_response(response, test_tools)
            
            self.results["basic_function_calling"] = {
                "response_time": elapsed,
                "response": response,
                "analysis": analysis
            }
            
            if analysis["has_function_calls"]:
                self.log("🎉 Function calling successful!")
                for call in analysis["function_calls"]:
                    self.log(f"   📞 Called: {call['name']} with {call.get('arguments', {})}")
            else:
                self.log("⚠️  No function calls detected")
                if analysis["mentions_function"]:
                    self.log("💡 Function mentioned in text - model may not support native function calling")
                self.log("🔧 Troubleshooting suggestions:")
                self.log("   - Try a different model that supports function calling")
                self.log("   - Check if the model requires specific prompt formatting")
                self.log("   - Verify the tool schema format")
            
        except Exception as e:
            self.log(f"❌ Basic function calling test failed: {e}")
            self.results["basic_function_calling"] = {"success": False, "error": str(e)}
    
    def _analyze_function_call_response(self, response, tools):
        """Analyze function call response"""
        analysis = {
            "has_function_calls": False,
            "function_calls": [],
            "mentions_function": False,
            "has_content": bool(response.get("content")),
            "response_type": "unknown"
        }
        
        # Check for native function calls
        if response.get("tool_calls"):
            analysis["has_function_calls"] = True
            analysis["function_calls"] = response["tool_calls"]
            analysis["response_type"] = "native_function_calls"
        
        # Check content for function mentions
        content = response.get("content", "").lower()
        for tool in tools:
            func_name = tool["function"]["name"]
            if func_name.lower() in content:
                analysis["mentions_function"] = True
                if not analysis["has_function_calls"]:
                    analysis["response_type"] = "text_based_function_mention"
        
        if analysis["has_content"] and not analysis["mentions_function"]:
            analysis["response_type"] = "plain_text"
        
        return analysis
    
    async def _test_event_creation_functions(self):
        """Test event creation function calling"""
        self.log("\n🎯 Phase 4: Event Creation Function Test")
        self.log("-" * 40)
        
        if not self.test_user_id:
            self.log("⚠️  Skipping event creation test - no test user")
            self.results["event_creation"] = {"skipped": True, "reason": "no_test_user"}
            return
        
        try:
            # Initialize event tools
            db = next(get_db())
            tools = DynamicEventTools(db, self.test_user_id)
            tool_definitions = tools.get_tool_definitions()
            
            self.log(f"✅ Event tools initialized")
            self.log(f"📋 Available tools: {len(tool_definitions)}")
            for tool in tool_definitions:
                self.log(f"   - {tool['name']}: {tool['description'][:50]}...")
            
            # Test with event creation request
            provider = ai_manager.get_current_provider()
            
            test_messages = [
                {
                    "role": "user",
                    "content": "Create a birthday party event for a 10-year-old. Set the title to 'Birthday Party Fun', location to 'Community Hall', cost to 25 dollars, and max participants to 15."
                }
            ]
            
            self.log("\n🧪 Testing event creation function calling...")
            
            start_time = asyncio.get_event_loop().time()
            response = await provider.chat_completion(test_messages, tool_definitions)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            self.log(f"⏱️  Event creation test completed ({elapsed:.2f}s)")
            
            # Analyze for event-specific function calls
            analysis = self._analyze_event_creation_response(response, tool_definitions)
            
            self.results["event_creation"] = {
                "response_time": elapsed,
                "analysis": analysis,
                "tools_count": len(tool_definitions)
            }
            
            if analysis["has_event_calls"]:
                self.log("🎉 Event creation function calls detected!")
                for call in analysis["event_calls"]:
                    self.log(f"   🎂 {call['name']}: {call.get('arguments', {})}")
            else:
                self.log("⚠️  No event creation function calls detected")
            
            db.close()
            
        except Exception as e:
            self.log(f"❌ Event creation test failed: {e}")
            self.results["event_creation"] = {"success": False, "error": str(e)}
    
    def _analyze_event_creation_response(self, response, tools):
        """Analyze event creation response"""
        analysis = {
            "has_event_calls": False,
            "event_calls": [],
            "has_function_calls": bool(response.get("tool_calls")),
            "mentions_event": False
        }
        
        if response.get("tool_calls"):
            for call in response["tool_calls"]:
                if "event" in call.get("name", "").lower():
                    analysis["has_event_calls"] = True
                    analysis["event_calls"].append(call)
        
        # Check if event creation is mentioned in text
        content = response.get("content", "").lower()
        event_keywords = ["event", "party", "create", "birthday"]
        if any(keyword in content for keyword in event_keywords):
            analysis["mentions_event"] = True
        
        return analysis
    
    async def _test_ai_agent_integration(self):
        """Test AI Agent integration with function calling"""
        self.log("\n🤝 Phase 5: AI Agent Integration Test")
        self.log("-" * 40)
        
        if not self.test_user_id:
            self.log("⚠️  Skipping AI agent test - no test user")
            self.results["ai_agent"] = {"skipped": True, "reason": "no_test_user"}
            return
        
        try:
            from app.ai_agent import EventCreationAgent
            
            db = next(get_db())
            agent = EventCreationAgent(db, self.test_user_id)
            
            self.log("✅ EventCreationAgent initialized")
            
            # Test conversation start
            self.log("🧪 Testing conversation start...")
            conversation_result = await agent.start_conversation()
            
            if conversation_result.get("success"):
                self.log("✅ Conversation started successfully")
                conversation_id = conversation_result["conversation_id"]
                
                # Test message processing
                self.log("🧪 Testing message processing with function calling...")
                
                test_message = "I want to create a science workshop event for teenagers aged 13-16. The workshop should be at the science center, cost $30, and allow up to 20 participants."
                
                try:
                    start_time = asyncio.get_event_loop().time()
                    message_result = await agent.process_message(conversation_id, test_message)
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    self.log(f"⏱️  Message processing completed ({elapsed:.2f}s)")
                    self.log(f"📋 Result: {json.dumps(message_result, indent=2, default=str)}")
                    
                    # Analyze agent response
                    agent_analysis = {
                        "success": message_result.get("success", False),
                        "has_tool_results": "tool_results" in message_result,
                        "response_time": elapsed
                    }
                    
                    if message_result.get("success"):
                        self.log("✅ AI Agent message processing successful")
                        if "tool_results" in message_result:
                            self.log(f"🎉 Tool results present: {len(message_result['tool_results'])}")
                            agent_analysis["tool_results_count"] = len(message_result["tool_results"])
                        else:
                            self.log("ℹ️  No tool results (agent may have responded without function calls)")
                    else:
                        self.log(f"⚠️  AI Agent processing failed: {message_result.get('error', 'Unknown error')}")
                    
                    self.results["ai_agent"] = agent_analysis
                    
                except Exception as e:
                    self.log(f"❌ Message processing error: {e}")
                    self.results["ai_agent"] = {"success": False, "error": str(e)}
                
            else:
                self.log(f"❌ Conversation start failed: {conversation_result.get('error')}")
                self.results["ai_agent"] = {"success": False, "error": "conversation_start_failed"}
            
            db.close()
            
        except Exception as e:
            self.log(f"❌ AI Agent integration test failed: {e}")
            self.results["ai_agent"] = {"success": False, "error": str(e)}
    
    def _generate_report(self):
        """Generate comprehensive test report"""
        self.log("\n📋 Test Results Summary")
        self.log("=" * 60)
        
        # Count successes and failures
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r.get("success") != False and not r.get("skipped"))
        failed_tests = sum(1 for r in self.results.values() if r.get("success") == False)
        skipped_tests = sum(1 for r in self.results.values() if r.get("skipped"))
        
        self.log(f"📊 Test Statistics:")
        self.log(f"   ✅ Successful: {successful_tests}")
        self.log(f"   ❌ Failed: {failed_tests}")
        self.log(f"   ⏭️  Skipped: {skipped_tests}")
        self.log(f"   📋 Total: {total_tests}")
        
        # Detailed results
        self.log(f"\n📋 Detailed Results:")
        for test_name, result in self.results.items():
            if result.get("skipped"):
                self.log(f"   ⏭️  {test_name}: Skipped ({result.get('reason')})")
            elif result.get("success") == False:
                self.log(f"   ❌ {test_name}: Failed - {result.get('error', 'Unknown error')}")
            else:
                self.log(f"   ✅ {test_name}: Passed")
        
        # Generate recommendations
        self._generate_recommendations()
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "debug_log": self.debug_log,
            "summary": {
                "total": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "skipped": skipped_tests
            }
        }
        
        report_file = "enhanced_function_calling_report.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.log(f"\n📄 Detailed report saved to: {report_file}")
    
    def _generate_recommendations(self):
        """Generate specific recommendations based on test results"""
        self.log(f"\n💡 Recommendations and Next Steps:")
        
        # Check environment issues
        if self.results.get("environment", {}).get("success") == False:
            self.log("   🔧 Fix database connection issues first")
            self.log("   💡 Run: alembic upgrade head")
        
        # Check AI provider issues
        ai_provider_result = self.results.get("ai_provider", {})
        if ai_provider_result.get("success") == False:
            self.log("   🤖 AI Provider not working:")
            if "connectivity" in ai_provider_result:
                connectivity = ai_provider_result["connectivity"]
                if not connectivity.get("connected"):
                    self.log("      - Start Ollama: ollama serve")
                    self.log("      - Check Docker networking")
                    self.log("      - Verify endpoint configuration")
                elif not connectivity.get("model_available"):
                    self.log("      - Install the required model: ollama pull devstral:latest")
                elif not connectivity.get("model_loads"):
                    self.log("      - Model may be corrupted, try: ollama pull devstral:latest --force")
        
        # Check function calling issues
        func_calling_result = self.results.get("basic_function_calling", {})
        if func_calling_result.get("analysis", {}).get("response_type") == "plain_text":
            self.log("   📞 Function calling not supported by current model:")
            self.log("      - Try a different model that supports function calling")
            self.log("      - Consider using text-based function parsing")
            self.log("      - Check if model requires specific prompting")
        
        # Check agent integration
        agent_result = self.results.get("ai_agent", {})
        if agent_result.get("success") == False:
            self.log("   🤝 AI Agent integration issues:")
            self.log("      - Check agent configuration")
            self.log("      - Verify tool integration")
            self.log("      - Review agent logs for specific errors")
        
        self.log(f"\n🔧 For detailed debugging, run: python scripts/debug_ai_agent.py")
    
    def _get_overall_success(self) -> bool:
        """Determine overall test success"""
        # Must have at least basic connectivity and environment working
        essential_tests = ["environment", "ai_provider"]
        
        for test in essential_tests:
            result = self.results.get(test, {})
            if result.get("success") == False:
                return False
        
        return True


async def main():
    """Main entry point"""
    tester = EnhancedFunctionCallingTester()
    
    try:
        success = await tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 Enhanced function calling test completed successfully!")
            return 0
        else:
            print("\n❌ Enhanced function calling test revealed issues")
            print("   Check the detailed report for specific recommendations")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 