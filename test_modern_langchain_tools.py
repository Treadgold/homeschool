#!/usr/bin/env python3
"""
Modern LangChain test using bind_tools() method with Qwen3-14B model.
This uses the latest LangChain features for tool calling.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_modern_langchain_tools():
    """Test modern LangChain tool binding with Qwen3-14B."""
    
    print("🚀 Testing Modern LangChain Tool Binding...")
    print("=" * 50)
    
    # Set up environment
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    # Import the latest LangChain modules
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    
    # Use Qwen3-14B model
    model_name = "qwen3:14b"
    print(f"   Using Model: {model_name}")
    
    # Create LLM instance with thinking mode disabled for tool calling
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
    llm = ChatOllama(
        model=model_name, 
        base_url=ollama_endpoint, 
        temperature=0.6,  # Recommended for Qwen3 thinking mode
        # Enable thinking mode as per Qwen3 docs for better reasoning
        format="json"  # This might help with structured responses
    )
    
    # Test 1: Define tools using the @tool decorator
    print("\n🛠️ Test 1: Defining Modern Tools")
    print("-" * 30)
    
    @tool
    def create_event_draft(title: str, description: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Create a draft event with the given details.
        
        Args:
            title: The event title
            description: A description of the event  
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            Dict containing the created event details
        """
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
    def add_ticket_type(event_id: str, name: str, price: float, quantity: int) -> Dict[str, Any]:
        """Add a ticket type to an existing event.
        
        Args:
            event_id: The ID of the event to add tickets to
            name: Name of the ticket type (e.g., "General Admission", "VIP")
            price: Price per ticket in dollars
            quantity: Number of tickets available
            
        Returns:
            Dict containing the ticket type details
        """
        ticket_id = f"ticket_{hash(event_id + name) % 10000}"
        return {
            "ticket_id": ticket_id,
            "event_id": event_id,
            "name": name,
            "price": price,
            "quantity": quantity,
            "message": f"Successfully added {quantity} '{name}' tickets at ${price} each"
        }
    
    # Create list of tools
    tools = [create_event_draft, add_ticket_type]
    
    print(f"✅ Defined {len(tools)} tools:")
    for tool_obj in tools:
        print(f"   - {tool_obj.name}: {tool_obj.description}")
    
    # Test 2: Bind tools to the model using modern approach
    print("\n🔗 Test 2: Binding Tools to Model")
    print("-" * 30)
    
    try:
        # Use the modern bind_tools() method
        llm_with_tools = llm.bind_tools(tools)
        print("✅ Successfully bound tools to model using bind_tools()")
        
        # Test basic tool calling
        messages = [
            SystemMessage(content="""You are a helpful assistant for creating events. 
            Use the available tools when users ask you to create events or add ticket types.
            Always use the tools rather than just describing what you would do."""),
            HumanMessage(content="I want to create a 'Homeschool Science Fair' event on August 1st, 2025. It should run for one day.")
        ]
        
        print(f"📝 Sending message: {messages[-1].content}")
        
        # Invoke the model with tools
        response = await llm_with_tools.ainvoke(messages)
        
        print(f"🤖 Model Response Type: {type(response)}")
        print(f"📄 Response Content: {response.content}")
        
        # Check if the model made tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"🎯 Tool Calls Made: {len(response.tool_calls)}")
            for i, tool_call in enumerate(response.tool_calls):
                print(f"   Tool Call {i+1}:")
                print(f"     Name: {tool_call['name']}")
                print(f"     Args: {tool_call['args']}")
                
                # Execute the tool call
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                # Find and execute the tool
                for tool_obj in tools:
                    if tool_obj.name == tool_name:
                        try:
                            result = tool_obj.invoke(tool_args)
                            print(f"     Result: {result}")
                        except Exception as e:
                            print(f"     Error executing tool: {e}")
                        break
        else:
            print("⚠️ No tool calls were made by the model")
            
    except Exception as e:
        print(f"❌ Tool binding failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Test with different prompting strategies
    print("\n💡 Test 3: Alternative Prompting Strategy")
    print("-" * 30)
    
    try:
        # Try a more direct approach
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an event management assistant. You have access to tools for creating events and adding ticket types.

When a user asks you to create an event, you MUST use the create_event_draft tool.
When a user asks to add tickets, you MUST use the add_ticket_type tool.

Available tools:
- create_event_draft: Creates a new event draft
- add_ticket_type: Adds ticket types to an event

Always call the appropriate tool instead of just describing what you would do."""),
            ("user", "{input}")
        ])
        
        # Create a chain with the prompt and tool-bound model
        chain = prompt | llm_with_tools
        
        # Test the chain
        result = await chain.ainvoke({
            "input": "Create a 'Summer Music Festival' event for July 15-17, 2025. The festival will feature live music performances over three days."
        })
        
        print(f"🎵 Chain Response: {result.content}")
        
        if hasattr(result, 'tool_calls') and result.tool_calls:
            print(f"🎸 Tool Calls from Chain: {len(result.tool_calls)}")
            for tool_call in result.tool_calls:
                print(f"   {tool_call['name']}: {tool_call['args']}")
        else:
            print("🤔 Chain did not make tool calls")
            
    except Exception as e:
        print(f"❌ Chain test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Check if Qwen3 thinking mode affects tool calling
    print("\n🧠 Test 4: Qwen3 Thinking Mode Test")
    print("-" * 30)
    
    try:
        # Create a new LLM instance with explicit thinking mode settings
        llm_thinking = ChatOllama(
            model=model_name,
            base_url=ollama_endpoint,
            temperature=0.6,
            # Try without format constraint to allow thinking
        )
        
        llm_thinking_with_tools = llm_thinking.bind_tools(tools)
        
        messages_thinking = [
            SystemMessage(content="""You are an expert event planner. Think step-by-step about what the user needs.

If they want to create an event, use the create_event_draft tool.
If they want to add tickets, use the add_ticket_type tool.

Think through the requirements carefully and then use the appropriate tools."""),
            HumanMessage(content="Please help me create a 'Tech Conference 2025' event for March 10-12, 2025. It's a three-day technology conference.")
        ]
        
        thinking_response = await llm_thinking_with_tools.ainvoke(messages_thinking)
        
        print(f"🤯 Thinking Response: {thinking_response.content[:200]}...")
        
        if hasattr(thinking_response, 'tool_calls') and thinking_response.tool_calls:
            print(f"🎯 Thinking Mode Tool Calls: {len(thinking_response.tool_calls)}")
        else:
            print("🤔 Thinking mode did not make tool calls")
            
    except Exception as e:
        print(f"❌ Thinking mode test failed: {e}")
    
    print("\n🎉 Modern LangChain Tool Tests Completed!")

if __name__ == "__main__":
    asyncio.run(test_modern_langchain_tools()) 