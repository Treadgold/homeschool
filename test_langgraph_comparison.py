#!/usr/bin/env python3
"""
Test script to compare LangGraph vs Traditional LangChain approaches
This demonstrates how LangGraph provides explicit workflow control
"""
import asyncio
import sys
sys.path.append('/app')

async def test_both_agents():
    """Test both the traditional Qwen3 agent and the new LangGraph agent"""
    
    test_message = "create an event for 20 people. it's at the zoo and it's $10 for kids, $25 for adults"
    test_session = "comparison-test-123"
    
    print("🔍 AGENT COMPARISON TEST")
    print("=" * 60)
    print(f"Test Message: {test_message}")
    print(f"Session ID: {test_session}")
    print()
    
    # Test 1: Traditional Qwen3 Optimized Agent
    print("🤖 Testing Traditional Qwen3 Agent...")
    print("-" * 40)
    try:
        from app.ai.services.qwen3_optimized_agent import invoke_agent
        
        result1 = await invoke_agent(
            session_id=test_session,
            user_prompt=test_message,
            model="qwen3:14b"
        )
        
        print("✅ Traditional Agent Results:")
        print(f"   Output: {result1['output'][:100]}...")
        print(f"   Tools Called: {len(result1.get('intermediate_steps', []))}")
        print(f"   Success: {result1.get('success', False)}")
        
        for i, step in enumerate(result1.get('intermediate_steps', [])):
            print(f"   Tool {i+1}: {step[0].get('name', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Traditional Agent Error: {e}")
    
    print()
    
    # Test 2: LangGraph Agent
    print("🔄 Testing LangGraph Agent...")
    print("-" * 40)
    try:
        from app.ai.services.langgraph_event_agent import invoke_langgraph_event_agent
        
        result2 = await invoke_langgraph_event_agent(
            session_id=test_session + "-lg",
            user_prompt=test_message,
            model="qwen3:14b"
        )
        
        print("✅ LangGraph Agent Results:")
        print(f"   Output: {result2['output'][:100]}...")
        print(f"   Tools Called: {len(result2.get('intermediate_steps', []))}")
        print(f"   Success: {result2.get('success', False)}")
        
        for i, step in enumerate(result2.get('intermediate_steps', [])):
            print(f"   Tool {i+1}: {step[0].get('name', 'unknown')}")
        
        # Show workflow state if available
        final_state = result2.get('final_state', {})
        if final_state:
            print(f"   Current Step: {final_state.get('current_step', 'unknown')}")
            print(f"   Event Created: {bool(final_state.get('event_draft', {}).get('success'))}")
            print(f"   Tickets Added: {len(final_state.get('tickets', []))}")
        
    except Exception as e:
        print(f"❌ LangGraph Agent Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("🏁 COMPARISON COMPLETE")
    print("=" * 60)
    print("Key Differences Expected:")
    print("• Traditional: May generate thinking text instead of calling tools")
    print("• LangGraph: Guarantees tool execution at specific workflow steps")
    print("• LangGraph: Provides explicit state management and workflow control")
    print("• LangGraph: Better debugging with step-by-step workflow visibility")


if __name__ == "__main__":
    asyncio.run(test_both_agents()) 