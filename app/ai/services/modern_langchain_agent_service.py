"""
Modern LangChain Agent Service using bind_tools() method.
This replaces the previous multi-step agent with proper LangChain tool calling.
"""
import json
import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

# We'll use a simple dictionary to store history for different chat sessions.
chat_history_store: Dict[str, List[Any]] = {}


def get_session_history(session_id: str):
    """Retrieves or creates a chat history for a given session."""
    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    return chat_history_store[session_id]


# Define our tools using the modern @tool decorator
@tool
def create_event_draft(title: str, description: str, start_date: str, end_date: str, session_id: str) -> Dict[str, Any]:
    """Create a draft event with the given details.
    
    Args:
        title: The event title
        description: A description of the event  
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        session_id: The session ID for this interaction
    
    Returns:
        Dict containing the created event details
    """
    # Import here to avoid circular imports
    from app.ai.langchain_tools import create_event_draft as core_create_event
    
    # Call the core function
    result = core_create_event.invoke({
        "title": title,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "session_id": session_id
    })
    
    return result


@tool  
def add_ticket_type(event_id: str, name: str, price: float, quantity: int, session_id: str) -> Dict[str, Any]:
    """Add a ticket type to an existing event.
    
    Args:
        event_id: The ID of the event to add tickets to
        name: Name of the ticket type (e.g., "General Admission", "VIP")
        price: Price per ticket in dollars
        quantity: Number of tickets available
        session_id: The session ID for this interaction
        
    Returns:
        Dict containing the ticket type details
    """
    # Import here to avoid circular imports
    from app.ai.langchain_tools import add_ticket_type as core_add_ticket
    
    # Call the core function
    result = core_add_ticket.invoke({
        "event_id": event_id,
        "name": name,
        "price": price,
        "quantity": quantity,
        "session_id": session_id
    })
    
    return result


# Create the tools list
AVAILABLE_TOOLS = [create_event_draft, add_ticket_type]


async def invoke_modern_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """
    Invokes a modern LangChain agent using bind_tools() method.
    This replaces the previous multi-step approach with proper tool calling.
    """
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
    
    # Create LLM instance optimized for Qwen3
    llm = ChatOllama(
        model=model, 
        base_url=ollama_endpoint, 
        temperature=0.6,  # Recommended for Qwen3 thinking mode
        timeout=30,  # Reasonable timeout
    )
    
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)
    
    # Get chat history
    chat_history = get_session_history(session_id)
    
    # Prepare messages including history
    messages = [
        SystemMessage(content="""You are a helpful assistant for managing events and tickets. 

You have access to the following tools:
- create_event_draft: Create a new event draft
- add_ticket_type: Add ticket types to existing events

When users ask you to create events or manage tickets, use the appropriate tools.
Always include the session_id parameter when calling tools.

Be helpful and provide clear confirmations of what you've accomplished.""")
    ]
    
    # Add chat history
    messages.extend(chat_history)
    
    # Add current user message
    messages.append(HumanMessage(content=user_prompt))
    
    # Call the model with tools
    response = await llm_with_tools.ainvoke(messages)
    
    # Track intermediate steps for compatibility
    intermediate_steps = []
    
    # Handle tool calls if present
    if hasattr(response, 'tool_calls') and response.tool_calls:
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Ensure session_id is included
            if 'session_id' not in tool_args:
                tool_args['session_id'] = session_id
            
            # Find and execute the tool
            for tool_obj in AVAILABLE_TOOLS:
                if tool_obj.name == tool_name:
                    try:
                        tool_output = tool_obj.invoke(tool_args)
                        intermediate_steps.append((tool_call, tool_output))
                        
                        # Add tool message to history for context
                        messages.append(ToolMessage(
                            content=json.dumps(tool_output),
                            tool_call_id=tool_call.get('id', 'unknown')
                        ))
                        
                    except Exception as e:
                        error_output = {"error": str(e), "tool": tool_name}
                        intermediate_steps.append((tool_call, error_output))
                    break
        
        # If tools were called, get a follow-up response that incorporates the results
        if intermediate_steps:
            try:
                final_response = await llm.ainvoke(messages + [
                    HumanMessage(content="Please provide a summary of what was accomplished.")
                ])
                final_content = final_response.content
            except Exception:
                # Fallback to the original response if follow-up fails
                final_content = response.content
        else:
            final_content = response.content
    else:
        # No tool calls, use the original response
        final_content = response.content
    
    # Update chat history
    chat_history.append(HumanMessage(content=user_prompt))
    chat_history.append(AIMessage(content=final_content))
    
    return {
        "output": final_content,
        "intermediate_steps": intermediate_steps,
    }


# For backward compatibility, keep the original function name
async def invoke_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """Backward compatibility wrapper for the modern agent."""
    return await invoke_modern_agent(session_id, user_prompt, model) 