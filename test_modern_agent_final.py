#!/usr/bin/env python3
"""
Final test for the modern LangChain agent integrated with the app.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def log_with_time(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

async def test_modern_agent_final():
    """Test the modern agent integrated with the app."""
    
    log_with_time("🚀 Testing Modern LangChain Agent (Final Integration)")
    print("=" * 60)
    
    try:
        # Import the modern agent service
        from app.ai.services.modern_langchain_agent_service import invoke_agent
        log_with_time("✅ Successfully imported modern agent service")
        
        # Test parameters
        test_session_id = f"test-modern-{uuid.uuid4()}"
        model_name = "qwen3:14b"
        
        log_with_time(f"Using session ID: {test_session_id}")
        log_with_time(f"Using model: {model_name}")
        
        # Test 1: Simple conversation
        log_with_time("📞 Test 1: Simple conversation")
        
        simple_response = await invoke_agent(
            session_id=test_session_id,
            user_prompt="Hello! How are you today?",
            model=model_name
        )
        
        log_with_time(f"✅ Simple response received")
        log_with_time(f"Response: {simple_response['output'][:150]}...")
        log_with_time(f"Intermediate steps: {len(simple_response['intermediate_steps'])}")
        
        # Test 2: Event creation (should trigger tool use)
        log_with_time("🎫 Test 2: Event creation with tools")
        
        event_response = await invoke_agent(
            session_id=test_session_id,
            user_prompt="Create a 'Modern AI Workshop' event for December 15th, 2025. It's a one-day workshop about modern AI techniques.",
            model=model_name
        )
        
        log_with_time(f"✅ Event creation response received")
        log_with_time(f"Response: {event_response['output'][:150]}...")
        log_with_time(f"Tools used: {len(event_response['intermediate_steps'])}")
        
        if event_response['intermediate_steps']:
            for i, (tool_call, result) in enumerate(event_response['intermediate_steps']):
                log_with_time(f"  Tool {i+1}: {tool_call['name']} -> {type(result)}")
        
        # Test 3: Follow-up with ticket types
        log_with_time("🎟️ Test 3: Adding ticket types")
        
        # Extract event_id if available
        event_id = None
        if event_response['intermediate_steps']:
            for tool_call, result in event_response['intermediate_steps']:
                if isinstance(result, dict) and 'event_id' in result:
                    event_id = result['event_id']
                    break
        
        if event_id:
            ticket_prompt = f"Add ticket types to event {event_id}: 'General Admission' for $25 with 100 tickets, and 'VIP' for $50 with 20 tickets."
        else:
            ticket_prompt = "Add ticket types to the Modern AI Workshop: 'General Admission' for $25 with 100 tickets, and 'VIP' for $50 with 20 tickets."
        
        ticket_response = await invoke_agent(
            session_id=test_session_id,
            user_prompt=ticket_prompt,
            model=model_name
        )
        
        log_with_time(f"✅ Ticket creation response received")
        log_with_time(f"Response: {ticket_response['output'][:150]}...")
        log_with_time(f"Tools used: {len(ticket_response['intermediate_steps'])}")
        
        # Summary
        log_with_time("📊 Test Summary:")
        log_with_time(f"  - Simple conversation: ✅")
        log_with_time(f"  - Event creation: ✅ ({len(event_response['intermediate_steps'])} tools)")
        log_with_time(f"  - Ticket creation: ✅ ({len(ticket_response['intermediate_steps'])} tools)")
        
        total_tools = (len(simple_response['intermediate_steps']) + 
                      len(event_response['intermediate_steps']) + 
                      len(ticket_response['intermediate_steps']))
        
        log_with_time(f"  - Total tool calls: {total_tools}")
        
        if total_tools > 0:
            log_with_time("🎉 SUCCESS: Modern LangChain agent with bind_tools() is working!")
        else:
            log_with_time("⚠️ Warning: No tools were called. Check prompts and model behavior.")
            
    except Exception as e:
        log_with_time(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_modern_agent_final()) 