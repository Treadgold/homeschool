#!/usr/bin/env python3
"""
Test the actual fixed ReAct service
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the app path
sys.path.insert(0, '/app')

async def test_fixed_service():
    """Test the actual fixed ReAct service"""
    print("🧪 Testing Fixed ReAct Service")
    print("=" * 50)
    
    try:
        # Import the actual service components directly
        from app.ai.services.react_agent_service import ReActAgent
        
        # Create agent with our fixes
        model = "qwen3:14b"
        session_id = f"service_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        agent = ReActAgent(model, session_id)
        print(f"✅ Agent created with model: {model}")
        
        # Test cases
        test_cases = [
            "Create a birthday party for Emma",
            "Create a science workshop for kids with $15 tickets, max 20 participants"
        ]
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_input}")
            print("-" * 40)
            
            start_time = datetime.now()
            result = await agent.run_react_loop(test_input)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            success = result.get('success', False)
            output = result.get('output', 'No output')
            iterations = result.get('iterations', 0)
            steps = result.get('intermediate_steps', [])
            
            print(f"⏱️ Time: {elapsed:.1f}s")
            print(f"✅ Success: {success}")
            print(f"🔄 Iterations: {iterations}")
            print(f"🛠️ Steps: {len(steps)}")
            print(f"📤 Output: {output[:150]}..." if len(output) > 150 else f"📤 Output: {output}")
            
            if steps:
                print("🔗 Reasoning steps:")
                for step in steps:
                    action = step.get('action', 'N/A')
                    print(f"  - {action}")
            
            print("✅ PASS" if success else "❌ FAIL")
        
        print(f"\n🎉 Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_qwen3_optimized_agent():
    """Test the new Qwen3-optimized agent with session isolation"""
    print("\n🚀 Testing Qwen3-Optimized Agent with Session Management")
    print("=" * 60)
    
    try:
        from app.ai.services.qwen3_optimized_agent import invoke_agent
        
        # Test 1: Session Isolation Test
        print("\n🔒 Test 1: Session Isolation")
        print("-" * 40)
        
        # Create two different sessions
        session_1 = f"session_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_2 = f"session_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}" 
        
        # Create event in session 1
        print(f"Creating event in Session 1: {session_1}")
        result_1 = await invoke_agent(
            session_id=session_1,
            user_prompt="Create an event draft for 'Alice's Birthday Party' on July 4th, 2025",
            model="qwen3:14b"
        )
        
        # Create different event in session 2  
        print(f"Creating event in Session 2: {session_2}")
        result_2 = await invoke_agent(
            session_id=session_2,
            user_prompt="Create an event draft for 'Bob's Coding Workshop' on August 15th, 2025", 
            model="qwen3:14b"
        )
        
        # Check session 1 again - should NOT remember session 2's event
        print(f"Checking Session 1 memory isolation...")
        result_1_check = await invoke_agent(
            session_id=session_1,
            user_prompt="What events have we discussed?",
            model="qwen3:14b"
        )
        
        # Analyze results
        alice_mentioned = "Alice" in result_1_check.get("output", "")
        bob_mentioned = "Bob" in result_1_check.get("output", "")
        
        print(f"✅ Session 1 remembers Alice: {alice_mentioned}")
        print(f"🔒 Session 1 isolated from Bob: {not bob_mentioned}")
        
        if alice_mentioned and not bob_mentioned:
            print("✅ Session isolation working correctly!")
        else:
            print("❌ Session isolation FAILED - sessions are leaking memory!")
            
        # Test 2: Function Calling Test
        print("\n🔧 Test 2: Function Calling")
        print("-" * 40)
        
        session_3 = f"session_3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result_3 = await invoke_agent(
            session_id=session_3,
            user_prompt="Create a science fair event for kids on September 10th",
            model="qwen3:14b"
        )
        
        tool_calls = result_3.get("intermediate_steps", [])
        success = result_3.get("success", False)
        
        print(f"✅ Function calling success: {success}")
        print(f"🛠️ Tool calls made: {len(tool_calls)}")
        
        if tool_calls:
            for i, step in enumerate(tool_calls):
                if isinstance(step, tuple) and len(step) >= 2:
                    call_info = step[0]
                    result_info = step[1]
                    tool_name = call_info.get("name", "unknown") if isinstance(call_info, dict) else str(call_info)
                    print(f"   {i+1}. {tool_name}: {str(result_info)[:100]}...")
        
        # Test 3: Database Integration Test  
        print("\n💾 Test 3: Database History Integration")
        print("-" * 40)
        
        # This should use database history, not global memory
        session_4 = f"session_4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create an event
        await invoke_agent(
            session_id=session_4,
            user_prompt="Create a cooking class for teens",
            model="qwen3:14b"
        )
        
        # Check if it remembers from database (not global memory)
        result_4 = await invoke_agent(
            session_id=session_4,
            user_prompt="What was the last event we created?",
            model="qwen3:14b"
        )
        
        cooking_mentioned = "cooking" in result_4.get("output", "").lower()
        print(f"✅ Database history working: {cooking_mentioned}")
        
        print("\n🎉 Qwen3-Optimized Agent Tests Complete!")
        
    except Exception as e:
        print(f"❌ Qwen3 agent tests failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_session_management_bug_fix():
    """Specifically test the session management bug fix"""
    print("\n🐛 Testing Session Management Bug Fix")
    print("=" * 50)
    
    try:
        from app.ai.services.qwen3_optimized_agent import invoke_agent
        
        # Simulate the exact scenario the user experienced
        print("Simulating user logout/login scenario...")
        
        # Session 1: User creates "William and Sally's Wedding"
        session_user_1 = "user_1_session"
        print(f"👤 User 1 creates wedding event in session: {session_user_1}")
        
        result_user_1 = await invoke_agent(
            session_id=session_user_1,
            user_prompt="Create an event draft for 'William and Sally's Wedding' on August 25, 2025",
            model="qwen3:14b"
        )
        
        wedding_success = result_user_1.get("success", False)
        print(f"✅ Wedding event created: {wedding_success}")
        
        # Session 2: Different user logs in - should NOT see wedding
        session_user_2 = "user_2_session" 
        print(f"👤 User 2 logs in with fresh session: {session_user_2}")
        
        result_user_2 = await invoke_agent(
            session_id=session_user_2,
            user_prompt="What events have been discussed recently?",
            model="qwen3:14b"
        )
        
        # Check if User 2 can see User 1's wedding (should NOT happen)
        wedding_leaked = "William" in result_user_2.get("output", "") or "Sally" in result_user_2.get("output", "")
        
        print(f"🔒 Privacy preserved (no wedding leak): {not wedding_leaked}")
        
        if not wedding_leaked:
            print("✅ BUG FIXED: Session isolation working correctly!")
            print("   Different users can't see each other's conversations")
        else:
            print("❌ BUG STILL EXISTS: Session data leaking between users!")
            print(f"   User 2 can see: {result_user_2.get('output', '')[:200]}...")
            
        # Test 3: Same user logs back in - SHOULD see their own data
        print(f"👤 User 1 logs back in with same session: {session_user_1}")
        
        result_user_1_return = await invoke_agent(
            session_id=session_user_1,
            user_prompt="What events did we create earlier?",
            model="qwen3:14b"
        )
        
        wedding_remembered = "William" in result_user_1_return.get("output", "") or "Sally" in result_user_1_return.get("output", "")
        
        print(f"💾 User 1 remembers their wedding: {wedding_remembered}")
        
        if wedding_remembered:
            print("✅ Session persistence working: Users keep their own data")
        else:
            print("⚠️  Session persistence issue: User lost their own data")
            
    except Exception as e:
        print(f"❌ Session bug test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_tool_execution_debug():
    """Debug test to check if tools are actually being called and storing data"""
    print("\n🔍 DEBUG: Tool Execution & Data Storage Test")
    print("=" * 60)
    
    try:
        from app.ai.services.qwen3_optimized_agent import invoke_agent
        from app.database import get_db
        from app.event_draft_manager import EventDraftManager
        
        # Create a test session
        session_id = f"debug_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"🧪 Debug Session: {session_id}")
        
        # Test 1: Check tools are called
        print("\n1️⃣ Testing Tool Calls")
        print("-" * 30)
        
        result = await invoke_agent(
            session_id=session_id,
            user_prompt="Create an event called 'Movie Night' for 50 people, $27 each, over 18s only",
            model="qwen3:14b"
        )
        
        intermediate_steps = result.get("intermediate_steps", [])
        print(f"📊 Agent returned {len(intermediate_steps)} intermediate steps")
        print(f"🎯 Agent success: {result.get('success', False)}")
        print(f"💬 Agent output: {result.get('output', 'No output')[:100]}...")
        
        if intermediate_steps:
            print("🔧 Tools called:")
            for i, step in enumerate(intermediate_steps):
                if isinstance(step, tuple) and len(step) >= 2:
                    call_info = step[0]
                    tool_output = step[1]
                    tool_name = call_info.get("name", "unknown") if isinstance(call_info, dict) else str(call_info)
                    print(f"   {i+1}. {tool_name}")
                    print(f"      Input: {call_info.get('arguments', {}) if isinstance(call_info, dict) else 'N/A'}")
                    print(f"      Output: {str(tool_output)[:150]}...")
        else:
            print("❌ NO TOOLS CALLED! This is the issue.")
        
        # Test 2: Check data storage  
        print("\n2️⃣ Testing Data Storage")
        print("-" * 30)
        
        # Get database session
        db = next(get_db())
        draft_manager = EventDraftManager(db)
        
        # Check if data was stored
        current_draft = draft_manager.get_current_draft(session_id)
        
        if current_draft:
            print("✅ Data found in EventDraftManager!")
            print(f"📋 Draft data keys: {list(current_draft.keys())}")
            print(f"🎬 Event title: {current_draft.get('title', 'Not found')}")
            print(f"📅 Event date: {current_draft.get('date', 'Not found')}")
            print(f"💰 Tickets: {current_draft.get('tickets', 'Not found')}")
        else:
            print("❌ NO DATA found in EventDraftManager!")
            print("   This means tools aren't storing data properly.")
        
        db.close()
        
        # Test 3: Simulate chat service logic
        print("\n3️⃣ Simulating Chat Service Logic")
        print("-" * 30)
        
        tools_used = result.get("intermediate_steps", [])
        tool_calls_made = len(tools_used) > 0
        
        print(f"🔧 Tools used: {len(tools_used)}")
        print(f"🚨 tool_calls_made flag: {tool_calls_made}")
        
        if tool_calls_made:
            print("✅ HTMX should trigger event preview update!")
        else:
            print("❌ HTMX will NOT trigger - no tools detected")
        
    except Exception as e:
        print(f"❌ Debug test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE AI AGENT TEST SUITE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run all test suites
    await test_fixed_service()
    await test_qwen3_optimized_agent() 
    await test_session_management_bug_fix()
    await test_tool_execution_debug()  # NEW DEBUG TEST
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main()) 