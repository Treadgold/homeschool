#!/usr/bin/env python3
"""
Simple test script for the fixed ReAct agent
"""
import asyncio
import sys
import os
import json

# Add necessary paths
sys.path.append('/app')

# Direct imports to avoid circular dependencies
from app.ai.services.react_agent_service import ReActAgent

async def test_react_simple():
    """Simple test of the ReAct agent"""
    
    print("🧪 Testing Fixed ReAct Agent (Simple)")
    print("=" * 50)
    
    # Create agent directly
    model = "qwen2.5:7b"
    session_id = "test_session"
    
    try:
        agent = ReActAgent(model, session_id)
        print("✅ Agent created successfully")
        
        # Test simple reasoning
        user_input = "Create a birthday party for Emma"
        print(f"\n🔍 Testing: {user_input}")
        
        result = await agent.run_react_loop(user_input)
        
        print(f"📤 Output: {result.get('output', 'No output')}")
        print(f"🔄 Iterations: {result.get('iterations', 'N/A')}")
        print(f"✔️ Success: {result.get('success', 'N/A')}")
        
        # Show intermediate steps
        steps = result.get('intermediate_steps', [])
        if steps:
            print("\n🔗 Reasoning Chain:")
            for step in steps:
                print(f"  Iteration {step.get('iteration', '?')}")
                thought = step.get('thought', 'N/A')
                action = step.get('action', 'N/A') 
                observation = step.get('observation', 'N/A')
                
                print(f"    Thought: {thought[:150]}..." if len(thought) > 150 else f"    Thought: {thought}")
                print(f"    Action: {action}")
                print(f"    Observation: {observation[:150]}..." if len(observation) > 150 else f"    Observation: {observation}")
                print()
        else:
            print("🔗 No reasoning steps recorded")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_react_simple()) 