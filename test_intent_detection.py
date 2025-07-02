#!/usr/bin/env python3
"""
Test script to demonstrate the improved ReAct agent with intent detection.
This will show how the agent now calls tools even when the LLM doesn't follow exact ReAct format.
"""
import asyncio
import json
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def log_test(message: str):
    """Log test messages with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

async def test_intent_detection():
    """Test the improved ReAct agent with intent detection"""
    
    print("🚀 ReAct Agent Intent Detection Test Suite")
    print("=" * 60)
    print("Testing aggressive tool detection that works even when")
    print("Qwen3:14b doesn't follow exact ReAct format")
    print("=" * 60)
    
    try:
        # Import our ReAct agent
        from app.ai.services.react_agent_service import invoke_agent
        
        # Test cases that should trigger tool usage
        test_cases = [
            {
                "name": "Original Failing Test",
                "prompt": "Create an event draft for a 'Science Fair' on August 15, 2025",
                "should_call_tools": True,
                "expected_tool": "create_event_draft"
            },
            {
                "name": "Zoo Visit Test",
                "prompt": "I need to set up a zoo visit for next Friday. It's for up to 50 people. Children from 5 - 15.",
                "should_call_tools": True,
                "expected_tool": "create_event_draft"
            },
            {
                "name": "Simple Workshop",
                "prompt": "Create a workshop for kids about science",
                "should_call_tools": True,
                "expected_tool": "create_event_draft"
            },
            {
                "name": "Party Planning",
                "prompt": "I want to organize a birthday party for my daughter",
                "should_call_tools": True,
                "expected_tool": "create_event_draft"
            },
            {
                "name": "Non-Event Question",
                "prompt": "What's the weather like today?",
                "should_call_tools": False,
                "expected_tool": None
            },
            {
                "name": "General Chat",
                "prompt": "Hello, how are you doing?",
                "should_call_tools": False,
                "expected_tool": None
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            log_test(f"🧪 Test {i}/{len(test_cases)}: {test_case['name']}")
            log_test(f"   Prompt: {test_case['prompt']}")
            log_test(f"   Expected: {'Should call tools' if test_case['should_call_tools'] else 'Should NOT call tools'}")
            
            try:
                # Call the agent
                start_time = datetime.now()
                response = await invoke_agent(
                    session_id=f"test-{i}",
                    user_prompt=test_case['prompt'],
                    model="qwen3:14b"
                )
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Analyze the response
                has_tools = bool(response.get('intermediate_steps'))
                tool_count = len(response.get('intermediate_steps', []))
                tool_names = []
                
                if has_tools:
                    for step in response['intermediate_steps']:
                        if isinstance(step, tuple) and len(step) >= 2:
                            call_info = step[0]
                            if isinstance(call_info, dict):
                                tool_name = call_info.get('name', 'unknown')
                            else:
                                tool_name = 'unknown'
                            tool_names.append(tool_name)
                
                # Determine if test passed
                passed = has_tools == test_case['should_call_tools']
                
                # Log results
                status = "✅ PASS" if passed else "❌ FAIL"
                log_test(f"   Result: {status} ({elapsed:.1f}s)")
                log_test(f"   Tools Called: {tool_count}")
                if tool_names:
                    log_test(f"   Tool Names: {', '.join(tool_names)}")
                
                # Show output preview
                output_preview = response.get('output', '')[:100]
                if len(output_preview) == 100:
                    output_preview += "..."
                log_test(f"   Output: {output_preview}")
                
                # Show ReAct details if available
                react_details = response.get('react_details', {})
                if react_details:
                    log_test(f"   ReAct Success: {react_details.get('success', False)}")
                    log_test(f"   Iterations: {react_details.get('iterations', 0)}")
                
                # Store result
                results.append({
                    'test_name': test_case['name'],
                    'passed': passed,
                    'tools_called': tool_count,
                    'tool_names': tool_names,
                    'elapsed': elapsed,
                    'expected_tools': test_case['should_call_tools'],
                    'actual_tools': has_tools
                })
                
                print()  # Add spacing between tests
                
            except Exception as e:
                log_test(f"   ❌ ERROR: {str(e)}")
                results.append({
                    'test_name': test_case['name'],
                    'passed': False,
                    'error': str(e),
                    'tools_called': 0,
                    'elapsed': 0
                })
                print()
        
        # Summary
        print("📊 TEST SUMMARY")
        print("=" * 40)
        
        passed_tests = sum(1 for r in results if r.get('passed', False))
        total_tests = len(results)
        
        log_test(f"Tests Passed: {passed_tests}/{total_tests}")
        
        for result in results:
            status = "✅" if result.get('passed', False) else "❌"
            test_name = result['test_name']
            tools_info = f"({result.get('tools_called', 0)} tools)" if result.get('tools_called', 0) > 0 else ""
            log_test(f"   {status} {test_name} {tools_info}")
        
        # Detailed analysis
        print("\n🔍 DETAILED ANALYSIS")
        print("=" * 40)
        
        tool_calling_tests = [r for r in results if r.get('expected_tools', False)]
        successful_tool_calls = [r for r in tool_calling_tests if r.get('actual_tools', False)]
        
        if tool_calling_tests:
            success_rate = len(successful_tool_calls) / len(tool_calling_tests) * 100
            log_test(f"Tool Calling Success Rate: {success_rate:.1f}%")
            log_test(f"   Expected to call tools: {len(tool_calling_tests)}")
            log_test(f"   Actually called tools: {len(successful_tool_calls)}")
        
        # Show which specific tools were called
        all_tools = []
        for result in results:
            all_tools.extend(result.get('tool_names', []))
        
        if all_tools:
            from collections import Counter
            tool_counts = Counter(all_tools)
            log_test(f"Tools Used:")
            for tool, count in tool_counts.items():
                log_test(f"   - {tool}: {count} times")
        
        print("\n🎯 INTENT DETECTION SUCCESS")
        print("=" * 40)
        
        if successful_tool_calls:
            log_test("✅ Intent detection is working!")
            log_test("   The agent now calls tools even when Qwen3:14b doesn't")
            log_test("   follow the exact ReAct format.")
            log_test("   This should fix the 'Model doesn't support function calling' error.")
        else:
            log_test("❌ Intent detection needs more work")
            log_test("   The agent is still not calling tools automatically")
        
        print("\n" + "=" * 60)
        log_test("🎉 Intent Detection Test Complete!")
        
        return passed_tests == total_tests
        
    except Exception as e:
        log_test(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_intent_detection())
    sys.exit(0 if success else 1) 