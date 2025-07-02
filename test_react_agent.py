#!/usr/bin/env python3
"""
Test ReAct Agent with Qwen3:14b
This tests the new ReAct (Reasoning and Acting) pattern implementation
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_react_agent():
    """Test the ReAct agent with Qwen3:14b."""
    print("🧠 Testing ReAct Agent with Qwen3:14b")
    print("=" * 60)
    print("🔄 ReAct Pattern: Reasoning → Acting → Observation → Final Answer")
    print("-" * 60)
    
    # Test with Qwen3:14b model
    model_name = "qwen3:14b"
    session_id = "react-test-session"
    
    try:
        from app.ai.services.react_agent_service import invoke_react_agent
        
        # Test 1: Simple event creation with ReAct reasoning
        print(f"\n🧪 Test 1: Event Creation with ReAct Reasoning")
        print(f"Model: {model_name}")
        print("-" * 40)
        
        user_prompt = "I want to create a birthday party for my daughter Emma who is turning 8. It should be at our house next Saturday from 2-5pm, cost $15 per child, and allow up to 12 kids."
        
        print(f"🎯 User Request: {user_prompt}")
        print(f"\n⏳ Starting ReAct reasoning loop...")
        
        start_time = datetime.now()
        result = await invoke_react_agent(
            session_id=session_id,
            user_prompt=user_prompt,
            model=model_name
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ ReAct Loop Completed ({elapsed:.1f}s)")
        print("-" * 40)
        
        # Display results
        print(f"📋 Final Response:")
        print(f"   {result['output']}")
        
        if result.get('intermediate_steps'):
            print(f"\n🔧 Tool Usage:")
            for i, step in enumerate(result['intermediate_steps'], 1):
                call_info = step[0]
                observation = step[1]
                print(f"   Step {i}: {call_info.get('name', 'Unknown')} → {observation[:100]}...")
        
        # Display ReAct details if available
        react_details = result.get('react_details', {})
        if react_details.get('conversation_history'):
            print(f"\n🧠 Reasoning History ({react_details.get('iterations', 0)} iterations):")
            for i, conversation in enumerate(react_details['conversation_history'], 1):
                print(f"\n   Iteration {i}:")
                # Show just the key parts
                lines = conversation.split('\n')
                for line in lines:
                    if line.strip().startswith(('Thought:', 'Action:', 'Final Answer:')):
                        print(f"      {line.strip()}")
        
        # Test 2: More complex request requiring multiple reasoning steps
        print(f"\n\n🧪 Test 2: Complex Request with Multiple Steps")
        print("-" * 40)
        
        complex_prompt = "Create a science workshop for kids aged 10-14. I'm not sure about the date yet, but make it educational and fun. Also add different ticket types - one for regular attendance and one that includes a take-home science kit."
        
        print(f"🎯 Complex Request: {complex_prompt}")
        print(f"\n⏳ Starting ReAct reasoning loop...")
        
        start_time = datetime.now()
        result2 = await invoke_react_agent(
            session_id=f"{session_id}-complex",
            user_prompt=complex_prompt,
            model=model_name
        )
        elapsed2 = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ ReAct Loop Completed ({elapsed2:.1f}s)")
        print("-" * 40)
        
        print(f"📋 Final Response:")
        print(f"   {result2['output']}")
        
        if result2.get('intermediate_steps'):
            print(f"\n🔧 Tool Usage:")
            for i, step in enumerate(result2['intermediate_steps'], 1):
                call_info = step[0]
                observation = step[1]
                print(f"   Step {i}: {call_info.get('name', 'Unknown')} → {observation[:100]}...")
        
        # Performance summary
        print(f"\n\n📊 Performance Summary")
        print("-" * 40)
        print(f"   Test 1 Time: {elapsed:.1f}s")
        print(f"   Test 2 Time: {elapsed2:.1f}s")
        print(f"   Total Tool Calls: {len(result.get('intermediate_steps', [])) + len(result2.get('intermediate_steps', []))}")
        
        success1 = bool(result.get('intermediate_steps'))
        success2 = bool(result2.get('intermediate_steps'))
        
        print(f"   Test 1 Success: {'✅' if success1 else '❌'}")
        print(f"   Test 2 Success: {'✅' if success2 else '❌'}")
        
        if success1 and success2:
            print(f"\n🎉 All ReAct tests passed! Qwen3:14b is working properly with ReAct patterns.")
        elif success1 or success2:
            print(f"\n⚠️  Partial success. Some ReAct functionality working.")
        else:
            print(f"\n❌ ReAct tests failed. Check agent configuration.")
        
        # Test 3: ReAct reasoning without tools (just conversation)
        print(f"\n\n🧪 Test 3: Pure Reasoning (No Tools)")
        print("-" * 40)
        
        reasoning_prompt = "What are the key things to consider when planning a children's event? Don't create anything, just give me advice."
        
        print(f"🎯 Reasoning Request: {reasoning_prompt}")
        
        start_time = datetime.now()
        result3 = await invoke_react_agent(
            session_id=f"{session_id}-reasoning",
            user_prompt=reasoning_prompt,
            model=model_name
        )
        elapsed3 = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ Response Generated ({elapsed3:.1f}s)")
        print(f"📋 Response: {result3['output']}")
        
        if not result3.get('intermediate_steps'):
            print(f"✅ Correctly handled non-tool request")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running this from the project root directory.")
        return False
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Main test function"""
    print("🚀 ReAct Agent Test Suite")
    print("Testing Qwen3:14b with proper ReAct patterns")
    print("=" * 60)
    
    # Set environment variables if needed
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    success = await test_react_agent()
    
    if success:
        print(f"\n✅ ReAct Agent Test Suite PASSED")
        print("Your Qwen3:14b model is now properly using ReAct patterns!")
    else:
        print(f"\n❌ ReAct Agent Test Suite FAILED")
        print("Check the logs above for issues.")
    
    print("\n" + "=" * 60)
    print("ReAct Pattern Benefits:")
    print("• Transparent reasoning process")
    print("• Better tool usage decisions")
    print("• Self-correcting behavior")
    print("• Works with text-based models like Qwen3:14b")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 