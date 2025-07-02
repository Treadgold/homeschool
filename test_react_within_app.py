#!/usr/bin/env python3
"""
Test ReAct Agent within App Container Context
This test works with the full app setup and networking
"""
import asyncio
import os
import sys
import requests
import json
from datetime import datetime

async def test_ollama_connection():
    """Test if Ollama is accessible from the container"""
    print("🔗 Testing Ollama Connection...")
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    try:
        response = requests.get(f"{ollama_endpoint}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama connected! Available models: {len(models)}")
            for model in models[:5]:  # Show first 5 models
                print(f"   - {model.get('name', 'Unknown')}")
            return True, [m.get('name', '') for m in models]
        else:
            print(f"❌ Ollama connection failed: HTTP {response.status_code}")
            return False, []
    except Exception as e:
        print(f"❌ Ollama connection error: {str(e)}")
        return False, []

async def test_react_agent_direct():
    """Test the ReAct agent directly using the ReActAgent class"""
    print("\n🧪 Testing ReAct Agent Direct...")
    
    try:
        # Import directly to avoid circular imports
        sys.path.insert(0, '/app')
        from app.ai.services.react_agent_service import ReActAgent
        
        # Use available model
        model = "qwen3:14b"  # Use the available model
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user_prompt = "Create a birthday party for Emma"
        
        print(f"Session: {session_id}")
        print(f"Model: {model}")
        print(f"Prompt: {user_prompt}")
        
        # Create agent directly
        agent = ReActAgent(model, session_id)
        print("✅ Agent instance created")
        
        # Call the agent
        start_time = datetime.now()
        result = await agent.run_react_loop(user_prompt)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n📤 Response ({elapsed:.1f}s):")
        print(f"✅ Output: {result.get('output', 'No output')}")
        print(f"🔄 Iterations: {result.get('iterations', 'N/A')}")
        print(f"✔️ Success: {result.get('success', 'N/A')}")
        
        # Show reasoning chain if available
        steps = result.get('intermediate_steps', [])
        if steps:
            print(f"\n🧠 Reasoning Chain ({len(steps)} steps):")
            for i, step in enumerate(steps, 1):
                print(f"  Step {i}:")
                thought = step.get('thought', 'N/A')
                action = step.get('action', 'N/A')
                observation = step.get('observation', 'N/A')
                
                print(f"    💭 Thought: {thought[:100]}..." if len(thought) > 100 else f"    💭 Thought: {thought}")
                print(f"    🔧 Action: {action}")
                print(f"    👁️ Observation: {observation[:100]}..." if len(observation) > 100 else f"    👁️ Observation: {observation}")
                print()
        else:
            print("🔗 No reasoning steps found")
            
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ ReAct test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_react_multi_step():
    """Test multi-step ReAct reasoning"""
    print("\n🔄 Testing Multi-Step ReAct...")
    
    try:
        from app.ai.services.react_agent_service import ReActAgent
        
        # More complex request that should trigger multiple steps
        model = "qwen3:14b"  # Use the available model
        session_id = f"multi_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user_prompt = "Create a science workshop for kids with $15 tickets, max 20 participants"
        
        print(f"Testing complex prompt: {user_prompt}")
        
        agent = ReActAgent(model, session_id)
        
        start_time = datetime.now()
        result = await agent.run_react_loop(user_prompt)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n📤 Multi-step Response ({elapsed:.1f}s):")
        print(f"✅ Output: {result.get('output', 'No output')}")
        
        # Check if it used multiple iterations
        iterations = result.get('iterations', 0)
        print(f"🔄 Iterations Used: {iterations}")
        
        steps = result.get('intermediate_steps', [])
        if steps:
            print(f"🧠 Reasoning Steps: {len(steps)}")
            for i, step in enumerate(steps, 1):
                action = step.get('action', 'N/A')
                print(f"  Step {i}: {action}")
        
        if iterations > 1 or len(steps) > 1:
            print("✅ Multi-step reasoning working!")
            return True
        else:
            print("⚠️ Expected multiple iterations for complex request")
            return False
            
    except Exception as e:
        print(f"❌ Multi-step test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_basic_prompt_understanding():
    """Test if the model understands ReAct format"""
    print("\n📋 Testing ReAct Format Understanding...")
    
    try:
        from langchain_ollama import ChatOllama
        
        model = "qwen3:14b"
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        
        llm = ChatOllama(
            model=model,
            base_url=ollama_endpoint,
            temperature=0.5,
            timeout=60
        )
        
        # Simple ReAct test
        test_prompt = """Use the ReAct format to respond:

Thought: [Think about what to do]
Action: [If you need to take action]
Action Input: [Parameters for the action]
Final Answer: [Your response]

Question: What would you do to create a birthday party?

Thought:"""

        start_time = datetime.now()
        response = await llm.ainvoke([{"role": "user", "content": test_prompt}])
        elapsed = (datetime.now() - start_time).total_seconds()
        
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        print(f"✅ Model responded ({elapsed:.1f}s)")
        print(f"📝 Response preview (first 300 chars):")
        print(f"   {response_content[:300]}...")
        
        # Check format understanding
        has_thought = "Thought:" in response_content
        has_action = "Action:" in response_content
        has_final = "Final Answer:" in response_content
        
        print(f"\n🔍 Format Analysis:")
        print(f"   Has 'Thought:': {'✅' if has_thought else '❌'}")
        print(f"   Has 'Action:': {'✅' if has_action else '❌'}")
        print(f"   Has 'Final Answer:': {'✅' if has_final else '❌'}")
        
        return has_thought
        
    except Exception as e:
        print(f"❌ Format test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🚀 Testing ReAct Agent within App Container")
    print("=" * 60)
    
    # Test 1: Ollama connection
    ollama_ok, models = await test_ollama_connection()
    
    if not ollama_ok:
        print("\n❌ Cannot test ReAct agent without Ollama connection")
        print("💡 Make sure Ollama is running on Windows and accessible via host.docker.internal:11434")
        return
    
    # Test 2: Basic format understanding
    format_ok = await test_basic_prompt_understanding()
    
    # Test 3: Basic ReAct agent
    basic_ok = await test_react_agent_direct()
    
    # Test 4: Multi-step reasoning
    multi_ok = await test_react_multi_step()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 40)
    print(f"🔗 Ollama Connection: {'✅ PASS' if ollama_ok else '❌ FAIL'}")
    print(f"📋 ReAct Format: {'✅ PASS' if format_ok else '❌ FAIL'}")
    print(f"🧠 Basic ReAct Test: {'✅ PASS' if basic_ok else '❌ FAIL'}")
    print(f"🔄 Multi-step Test: {'✅ PASS' if multi_ok else '❌ FAIL'}")
    
    overall_success = ollama_ok and format_ok and basic_ok
    
    if overall_success:
        print(f"\n🎉 ReAct Agent Implementation: ✅ WORKING!")
        print("The fixes have successfully improved the ReAct reasoning.")
        if multi_ok:
            print("✨ Multi-step reasoning is also working correctly!")
    else:
        print(f"\n⚠️ ReAct Agent Implementation: ❌ NEEDS WORK")
        print("Some issues remain in the ReAct implementation.")
        
    print(f"\nAvailable models: {', '.join(models[:3])}...")

if __name__ == "__main__":
    asyncio.run(main()) 