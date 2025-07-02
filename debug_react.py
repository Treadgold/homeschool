#!/usr/bin/env python3
"""
Debug script to show exactly what the ReAct agent is doing internally
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_log(message: str, indent: int = 0):
    """Log debug messages with indentation"""
    prefix = "  " * indent
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # milliseconds
    print(f"[{timestamp}] {prefix}{message}")

async def debug_single_test():
    """Debug a single test case to see detailed execution"""
    
    debug_log("🔍 DEBUGGING ReAct Agent Internal Execution")
    debug_log("=" * 50)
    
    try:
        # Import the ReAct agent class directly for detailed debugging
        from app.ai.services.react_agent_service import ReActAgent
        
        # Test the original failing case
        test_prompt = "Create an event draft for a 'Science Fair' on August 15, 2025"
        session_id = "debug-session"
        model = "qwen3:14b"
        
        debug_log(f"📝 Test Prompt: {test_prompt}")
        debug_log(f"🆔 Session ID: {session_id}")
        debug_log(f"🤖 Model: {model}")
        
        # Create agent instance
        debug_log("🏗️ Creating ReActAgent instance...")
        agent = ReActAgent(model, session_id)
        debug_log("✅ Agent created successfully")
        
        # Show available tools
        debug_log(f"🔧 Available tools: {list(agent.tools.keys())}")
        
        # Run the ReAct loop with detailed logging
        debug_log("🚀 Starting ReAct loop...")
        start_time = datetime.now()
        
        result = await agent.run_react_loop(test_prompt)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        debug_log(f"⏱️ Execution time: {elapsed:.2f}s")
        
        # Analyze the result in detail
        debug_log("📊 DETAILED RESULT ANALYSIS:")
        debug_log(f"   Success: {result.get('success', False)}", 1)
        debug_log(f"   Iterations: {result.get('iterations', 0)}", 1)
        debug_log(f"   Output length: {len(result.get('output', ''))}", 1)
        debug_log(f"   Intermediate steps: {len(result.get('intermediate_steps', []))}", 1)
        
        # Show the raw output
        output = result.get('output', '')
        debug_log("📜 Raw Output:", 1)
        for i, line in enumerate(output.split('\n')[:5], 1):  # First 5 lines
            debug_log(f"   Line {i}: {line}", 2)
        if len(output.split('\n')) > 5:
            debug_log("   ... (truncated)", 2)
        
        # Show intermediate steps in detail
        steps = result.get('intermediate_steps', [])
        if steps:
            debug_log("🔧 Tool Calls Found:", 1)
            for i, step in enumerate(steps, 1):
                debug_log(f"   Step {i}:", 2)
                debug_log(f"     Thought: {step.get('thought', 'N/A')}", 3)
                debug_log(f"     Action: {step.get('action', 'N/A')}", 3)
                debug_log(f"     Observation: {step.get('observation', 'N/A')[:100]}...", 3)
        else:
            debug_log("❌ No tool calls detected", 1)
        
        # Show conversation history
        conv_history = result.get('conversation_history', [])
        if conv_history:
            debug_log("💬 Conversation History:", 1)
            for i, entry in enumerate(conv_history[:4], 1):  # First 4 entries
                debug_log(f"   {i}: {entry[:80]}...", 2)
        
        # Test the intent detection manually
        debug_log("🎯 MANUAL INTENT DETECTION TEST:")
        
        # Simulate what the agent does internally
        fake_ai_response = "I'd be happy to help you create an event! Let me set that up for you."
        detected_action, detected_params = agent._detect_tool_intent(test_prompt, fake_ai_response)
        
        debug_log(f"   User input: {test_prompt}", 1)
        debug_log(f"   AI response: {fake_ai_response}", 1)
        debug_log(f"   Detected action: {detected_action}", 1)
        debug_log(f"   Detected params: {detected_params}", 1)
        
        if detected_action:
            debug_log("✅ Intent detection is working!", 1)
            
            # Parse the parameters
            try:
                import json
                params = json.loads(detected_params) if detected_params else {}
                debug_log("📋 Parsed parameters:", 1)
                for key, value in params.items():
                    debug_log(f"     {key}: {value}", 2)
            except:
                debug_log("❌ Failed to parse parameters", 1)
        else:
            debug_log("❌ Intent detection failed", 1)
        
        # Test the formatted response
        debug_log("🔄 TESTING FORMATTED RESPONSE:")
        from app.ai.services.react_agent_service import invoke_agent
        
        formatted_result = await invoke_agent(session_id, test_prompt, model)
        debug_log(f"   Formatted intermediate_steps: {len(formatted_result.get('intermediate_steps', []))}", 1)
        
        if formatted_result.get('intermediate_steps'):
            debug_log("✅ Formatted response has tool calls!", 1)
            for step in formatted_result['intermediate_steps']:
                if isinstance(step, tuple) and len(step) >= 2:
                    call_info, observation = step
                    if isinstance(call_info, dict):
                        debug_log(f"     Tool: {call_info.get('name', 'unknown')}", 2)
                        debug_log(f"     Args: {call_info.get('arguments', 'N/A')[:50]}...", 2)
                        debug_log(f"     Result: {str(observation)[:50]}...", 2)
        else:
            debug_log("❌ Formatted response has no tool calls", 1)
        
        debug_log("🎉 Debug complete!")
        return True
        
    except Exception as e:
        debug_log(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_single_test())
    sys.exit(0 if success else 1) 