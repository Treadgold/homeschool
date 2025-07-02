#!/usr/bin/env python3
"""
Test ReAct Thinking Fix
Validates that internal reasoning is not exposed to users
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_thinking_filter():
    """Test that thinking content is properly filtered"""
    print("🧠 Testing ReAct Thinking Content Filter")
    print("=" * 60)
    
    try:
        from app.ai.services.react_agent_service import ReActAgent
        
        # Create test agent
        agent = ReActAgent("qwen3:14b", "test-session")
        
        # Test 1: Filter obvious thinking content
        print("\n🧪 Test 1: Filter Thinking Content")
        print("-" * 40)
        
        raw_response_with_thinking = """
        Okay, the user wants to create an event for Brian's 10th birthday party. Let me start by extracting the necessary details.
        
        First, I need to use the create_event_draft tool. The parameters required would be the event name, date, time, location.
        
        Wait, the tools don't mention needing a session_id for create_event_draft. Let me check the instructions again.
        
        I've created an event draft for Brian's 10th birthday party with the following details:
        - Event Name: Brian's 10th Birthday Party
        - Date: 11 August 2023
        - Time: 10:00 AM
        - Location: 12 Escot Road
        """
        
        filtered_response = agent._filter_thinking_content(raw_response_with_thinking)
        
        print(f"📝 Original response length: {len(raw_response_with_thinking)} chars")
        print(f"📝 Filtered response length: {len(filtered_response)} chars")
        print(f"📝 Filtered response:")
        print(f"   {filtered_response}")
        
        # Check that thinking patterns are removed
        thinking_removed = not any(phrase in filtered_response.lower() for phrase in [
            'okay, the user wants',
            'let me start by',
            'first, i need',
            'wait, the tools'
        ])
        
        print(f"✅ Thinking patterns removed: {'Yes' if thinking_removed else 'No'}")
        
        # Test 2: Extract clean final answer
        print(f"\n🧪 Test 2: Extract Clean Final Answer")
        print("-" * 40)
        
        unstructured_response = """
        The user mentioned they want a birthday party. I should check what details they provided.
        
        I'll help you create that birthday party event!
        
        The parameters required would be title, date, session_id.
        """
        
        clean_answer = agent._extract_final_answer_from_text(unstructured_response)
        print(f"📝 Extracted answer: {clean_answer}")
        
        # Test 3: Generate clean response with fallback
        print(f"\n🧪 Test 3: Generate Clean Response")
        print("-" * 40)
        
        user_input = "Create a birthday party for Brian on August 11th"
        messy_response = "Okay, the user wants to create an event. I need to call create_event_draft tool."
        
        clean_response = agent._generate_clean_response(user_input, messy_response)
        print(f"📝 Clean response: {clean_response}")
        
        # Check that it's helpful and doesn't contain thinking
        is_helpful = len(clean_response) > 10 and not any(phrase in clean_response.lower() for phrase in [
            'okay, the user',
            'i need to call',
            'tool'
        ])
        
        print(f"✅ Response is helpful and clean: {'Yes' if is_helpful else 'No'}")
        
        print(f"\n🎉 Thinking filter tests completed!")
        
        if thinking_removed and clean_answer and is_helpful:
            print(f"✅ All tests passed! Thinking content is properly filtered.")
            return True
        else:
            print(f"❌ Some tests failed. Check implementation.")
            return False
            
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_thinking_filter()) 