#!/usr/bin/env python3
"""
Standalone test for the modern LangChain agent that avoids circular imports.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def log_with_time(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

async def test_standalone_modern_agent():
    """Test the modern agent without circular import issues."""
    
    log_with_time("🚀 Testing Modern LangChain Agent (Standalone)")
    print("=" * 60)
    
    # Set up environment
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    try:
        # Import directly to avoid circular imports
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
        from langchain_core.tools import tool
        from langchain_ollama import ChatOllama
        import json
        
        log_with_time("✅ Successfully imported LangChain modules")
        
        # Define tools directly (same as in modern service)
        @tool
        def create_event_draft(title: str, description: str, start_date: str, end_date: str, session_id: str) -> Dict[str, Any]:
            """Create a draft event with the given details."""
            log_with_time(f"🔧 Creating event: {title}")
            event_id = f"event_{hash(title + start_date) % 10000}"
            return {
                "event_id": event_id,
                "title": title,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "status": "draft",
                "message": f"Successfully created draft event: {title}"
            }
        
        @tool  
        def add_ticket_type(event_id: str, name: str, price: float, quantity: int, session_id: str) -> Dict[str, Any]:
            """Add a ticket type to an existing event."""
            log_with_time(f"🎫 Adding ticket: {name} to event {event_id}")
            ticket_id = f"ticket_{hash(event_id + name) % 10000}"
            return {
                "ticket_id": ticket_id,
                "event_id": event_id,
                "name": name,
                "price": price,
                "quantity": quantity,
                "message": f"Successfully added {quantity} '{name}' tickets at ${price} each"
            }
        
        tools = [create_event_draft, add_ticket_type]
        log_with_time(f"✅ Defined {len(tools)} tools")
        
        # Create LLM and bind tools
        model_name = "qwen3:14b"
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
        
        llm = ChatOllama(
            model=model_name, 
            base_url=ollama_endpoint, 
            temperature=0.6,
            timeout=30,
        )
        
        llm_with_tools = llm.bind_tools(tools)
        log_with_time(f"✅ Created model and bound tools")
        
        # Test parameters
        test_session_id = f"test-standalone-{uuid.uuid4()}"
        log_with_time(f"Using session ID: {test_session_id}")
        
        # Test 1: Simple conversation
        log_with_time("📞 Test 1: Simple conversation")
        
        messages = [
            SystemMessage(content="You are a helpful assistant for managing events and tickets."),
            HumanMessage(content="Hello! How are you today?")
        ]
        
        simple_response = await llm_with_tools.ainvoke(messages)
        
        log_with_time(f"✅ Simple response received")
        log_with_time(f"Response: {simple_response.content[:100]}...")
        
        # Test 2: Event creation (should trigger tool use)
        log_with_time("🎫 Test 2: Event creation with tools")
        
        event_messages = [
            SystemMessage(content="""You are a helpful assistant for managing events and tickets. 

You have access to tools for creating events and adding ticket types.
When users ask you to create events, use the create_event_draft tool.
Always include the session_id parameter when calling tools."""),
            HumanMessage(content="Create a 'Modern AI Workshop' event for December 15th, 2025. It's a one-day workshop about modern AI techniques.")
        ]
        
        event_response = await llm_with_tools.ainvoke(event_messages)
        
        log_with_time(f"✅ Event creation response received")
        log_with_time(f"Response: {event_response.content[:100]}...")
        
        # Check for tool calls
        if hasattr(event_response, 'tool_calls') and event_response.tool_calls:
            log_with_time(f"🎯 Found {len(event_response.tool_calls)} tool calls")
            
            for i, tool_call in enumerate(event_response.tool_calls):
                log_with_time(f"  Tool Call {i+1}: {tool_call['name']}")
                log_with_time(f"    Args: {tool_call['args']}")
                
                # Execute the tool
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                # Ensure session_id is included
                if 'session_id' not in tool_args:
                    tool_args['session_id'] = test_session_id
                
                # Find and execute the tool
                for tool_obj in tools:
                    if tool_obj.name == tool_name:
                        try:
                            result = tool_obj.invoke(tool_args)
                            log_with_time(f"    Result: {result}")
                        except Exception as e:
                            log_with_time(f"    Error: {e}")
                        break
        else:
            log_with_time("⚠️ No tool calls were made")
            
        # Test 3: Direct tool call test
        log_with_time("🔧 Test 3: Direct tool invocation")
        
        try:
            direct_result = create_event_draft.invoke({
                "title": "Direct Test Event",
                "description": "Testing direct tool invocation",
                "start_date": "2025-01-01",
                "end_date": "2025-01-01",
                "session_id": test_session_id
            })
            log_with_time(f"✅ Direct tool call successful: {direct_result}")
        except Exception as e:
            log_with_time(f"❌ Direct tool call failed: {e}")
            
        log_with_time("🎉 Standalone modern agent test completed!")
        
    except Exception as e:
        log_with_time(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_standalone_modern_agent()) 