#!/usr/bin/env python3
"""
Modern LangChain test with comprehensive timing to debug performance issues.
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def log_with_time(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

def timer_decorator(func_name: str):
    """Decorator to time function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            log_with_time(f"🕐 Starting {func_name}...")
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                log_with_time(f"✅ Completed {func_name} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log_with_time(f"❌ Failed {func_name} after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator

async def test_modern_langchain_tools_timed():
    """Test modern LangChain tool binding with detailed timing."""
    
    log_with_time("🚀 Starting Modern LangChain Tool Binding Test...")
    print("=" * 60)
    
    # Set up environment
    log_with_time("Setting up environment...")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    # Import modules with timing
    import_start = time.time()
    log_with_time("Importing LangChain modules...")
    
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    
    import_time = time.time() - import_start
    log_with_time(f"✅ Imports completed in {import_time:.2f}s")
    
    # Model setup with timing
    model_start = time.time()
    model_name = "qwen3:14b"
    log_with_time(f"Creating ChatOllama instance for {model_name}...")
    
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
    log_with_time(f"Using endpoint: {ollama_endpoint}")
    
    try:
        llm = ChatOllama(
            model=model_name, 
            base_url=ollama_endpoint, 
            temperature=0.6,
            timeout=30,  # Add explicit timeout
        )
        model_time = time.time() - model_start
        log_with_time(f"✅ Model instance created in {model_time:.2f}s")
    except Exception as e:
        log_with_time(f"❌ Failed to create model: {e}")
        return
    
    # Test 1: Define tools with timing
    tools_start = time.time()
    log_with_time("🛠️ Defining tools...")
    
    @tool
    def create_event_draft(title: str, description: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Create a draft event with the given details."""
        log_with_time(f"🔧 Executing create_event_draft for: {title}")
        event_id = f"event_{hash(title + start_date) % 10000}"
        result = {
            "event_id": event_id,
            "title": title,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "status": "draft",
            "message": f"Successfully created draft event: {title}"
        }
        log_with_time(f"✅ create_event_draft completed for: {title}")
        return result
    
    @tool
    def add_ticket_type(event_id: str, name: str, price: float, quantity: int) -> Dict[str, Any]:
        """Add a ticket type to an existing event."""
        log_with_time(f"🎫 Executing add_ticket_type: {name} for event {event_id}")
        ticket_id = f"ticket_{hash(event_id + name) % 10000}"
        result = {
            "ticket_id": ticket_id,
            "event_id": event_id,
            "name": name,
            "price": price,
            "quantity": quantity,
            "message": f"Successfully added {quantity} '{name}' tickets at ${price} each"
        }
        log_with_time(f"✅ add_ticket_type completed: {name}")
        return result
    
    tools = [create_event_draft, add_ticket_type]
    tools_time = time.time() - tools_start
    log_with_time(f"✅ Tools defined in {tools_time:.2f}s")
    
    # Test 2: Bind tools with timing
    bind_start = time.time()
    log_with_time("🔗 Binding tools to model...")
    
    try:
        llm_with_tools = llm.bind_tools(tools)
        bind_time = time.time() - bind_start
        log_with_time(f"✅ Tools bound in {bind_time:.2f}s")
    except Exception as e:
        log_with_time(f"❌ Tool binding failed: {e}")
        return
    
    # Test 3: Simple model call with timeout
    simple_start = time.time()
    log_with_time("📞 Testing simple model call...")
    
    try:
        simple_response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Hello, just say 'Hi' back please.")]),
            timeout=10.0
        )
        simple_time = time.time() - simple_start
        log_with_time(f"✅ Simple call completed in {simple_time:.2f}s")
        log_with_time(f"Response: {simple_response.content[:100]}...")
    except asyncio.TimeoutError:
        log_with_time(f"⏰ Simple call timed out after {time.time() - simple_start:.2f}s")
        return
    except Exception as e:
        log_with_time(f"❌ Simple call failed: {e}")
        return
    
    # Test 4: Tool-bound model call with timeout
    tool_call_start = time.time()
    log_with_time("🔧 Testing tool-bound model call...")
    
    messages = [
        SystemMessage(content="You are a helpful assistant. Use tools when appropriate."),
        HumanMessage(content="Create a 'Test Event' for tomorrow.")
    ]
    
    try:
        log_with_time("Sending message to tool-bound model...")
        tool_response = await asyncio.wait_for(
            llm_with_tools.ainvoke(messages),
            timeout=15.0
        )
        tool_call_time = time.time() - tool_call_start
        log_with_time(f"✅ Tool-bound call completed in {tool_call_time:.2f}s")
        
        log_with_time(f"Response type: {type(tool_response)}")
        log_with_time(f"Response content: {tool_response.content[:200]}...")
        
        if hasattr(tool_response, 'tool_calls') and tool_response.tool_calls:
            log_with_time(f"🎯 Found {len(tool_response.tool_calls)} tool calls")
            for i, tool_call in enumerate(tool_response.tool_calls):
                log_with_time(f"  Tool Call {i+1}: {tool_call.get('name', 'unknown')}")
        else:
            log_with_time("⚠️ No tool calls in response")
            if hasattr(tool_response, '__dict__'):
                log_with_time(f"Response attributes: {list(tool_response.__dict__.keys())}")
                
    except asyncio.TimeoutError:
        log_with_time(f"⏰ Tool-bound call timed out after {time.time() - tool_call_start:.2f}s")
        log_with_time("This suggests the model is hanging during tool-bound inference")
        return
    except Exception as e:
        log_with_time(f"❌ Tool-bound call failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 5: Alternative approach without JSON format
    alt_start = time.time()
    log_with_time("🔄 Testing alternative approach...")
    
    try:
        llm_alt = ChatOllama(
            model=model_name,
            base_url=ollama_endpoint,
            temperature=0.7,
            # Remove format="json" to see if that was causing issues
        )
        
        llm_alt_with_tools = llm_alt.bind_tools(tools)
        
        alt_response = await asyncio.wait_for(
            llm_alt_with_tools.ainvoke([
                HumanMessage(content="Please create an event called 'Quick Test' for today.")
            ]),
            timeout=15.0
        )
        
        alt_time = time.time() - alt_start
        log_with_time(f"✅ Alternative approach completed in {alt_time:.2f}s")
        
    except asyncio.TimeoutError:
        log_with_time(f"⏰ Alternative approach timed out after {time.time() - alt_start:.2f}s")
    except Exception as e:
        log_with_time(f"❌ Alternative approach failed: {e}")
    
    total_time = time.time() - import_start
    log_with_time(f"🎉 Test completed! Total time: {total_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_modern_langchain_tools_timed()) 