#!/usr/bin/env python3
"""
Simple test script for the LangChain agent service.
This avoids circular imports by directly testing the agent service.
"""

import asyncio
import os
import sys
import uuid

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_simple_langchain():
    """Test the LangChain agent directly."""
    
    print("🧪 Testing LangChain Agent (Simple)...")
    print("=" * 50)
    
    # Import here to avoid circular imports
    from app.ai.services.react_agent_service import invoke_agent
    
    # Use a test model - you can change this to match your available models
    model_name = "qwen3:14b"  # Change this to your preferred model
    
    print(f"   Using Model: {model_name}")
    
    # Set up environment
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    # A unique session ID for this test run
    test_session_id = f"test-run-{uuid.uuid4()}"
    print(f"   Test Session ID: {test_session_id}")

    # Test message designed to trigger the 'create_event_draft' tool
    test_message = "I'd like to create an event for a 'Homeschool Science Fair' on August 1st, 2025."
    print(f"   Test Prompt: \"{test_message}\"")
    print("-" * 50)
    
    try:
        # Invoke the agent
        response = await invoke_agent(
            session_id=test_session_id,
            user_prompt=test_message,
            model=model_name
        )
        
        print("\n✅ Test completed successfully!")
        print("-" * 50)
        print("Agent Response:")
        print(f"   Output: {response.get('output')}")
        
        if response.get("intermediate_steps"):
            print("\n🛠️ Tools Used:")
            for step in response["intermediate_steps"]:
                # Handle different intermediate_steps formats
                if isinstance(step, tuple) and len(step) >= 2:
                    call_info = step[0]
                    tool_output = step[1]
                    
                    if isinstance(call_info, dict):
                        tool_name = call_info.get("name", "unknown")
                        tool_input = call_info.get("arguments", {})
                    else:
                        tool_name = str(call_info)
                        tool_input = "unknown"
                    
                    print(f"   - Tool: {tool_name}")
                    print(f"     Input: {tool_input}")
                    print(f"     Output: {tool_output}")
                else:
                    print(f"   - Step: {step}")
        else:
            print("\n⚠️ No tools were used by the agent.")

    except Exception as e:
        print(f"\n❌ Test failed during agent invocation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_langchain()) 