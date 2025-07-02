#!/usr/bin/env python3
"""
Test script for the fixed ReAct agent
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/home/mike/code/homeschool')

from app.ai.services.react_agent_service import invoke_react_agent

async def test_react_agent():
    """Test the fixed ReAct agent with simple scenarios"""
    
    print("🧪 Testing Fixed ReAct Agent")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Event Creation",
            "input": "Create a birthday party for Emma",
            "expected": "Should use reasoning to create event"
        },
        {
            "name": "Multi-step Request", 
            "input": "Create a science workshop for kids, $15 per child, max 20 kids",
            "expected": "Should create event and add ticket pricing"
        },
        {
            "name": "General Question",
            "input": "What can you help me with?",
            "expected": "Should provide helpful response without forced tool usage"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        print(f"Expected: {test_case['expected']}")
        print("-" * 30)
        
        try:
            # Test with a session ID
            session_id = f"test_session_{i}"
            model = "qwen2.5:7b"  # Use available model
            
            # Run the test
            result = await invoke_react_agent(session_id, test_case['input'], model)
            
            # Display results
            print(f"✅ Output: {result['output']}")
            print(f"📊 Iterations: {result.get('react_details', {}).get('iterations', 'N/A')}")
            print(f"✔️ Success: {result.get('react_details', {}).get('success', 'N/A')}")
            
            # Show intermediate steps (reasoning chain)
            steps = result.get('react_details', {}).get('original_steps', [])
            if steps:
                print("🔗 Reasoning Chain:")
                for step in steps:
                    print(f"  Iteration {step.get('iteration', '?')}")
                    print(f"    Thought: {step.get('thought', 'N/A')[:100]}...")
                    print(f"    Action: {step.get('action', 'N/A')}")
                    print(f"    Observation: {step.get('observation', 'N/A')[:100]}...")
            else:
                print("🔗 No reasoning steps recorded")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_react_agent()) 