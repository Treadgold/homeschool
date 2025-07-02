"""
Qwen3-14B Optimized Agent Service
This agent is specifically optimized for Qwen3-14B's native function calling capabilities.
Based on research showing Qwen3 supports OpenAI-style function calling out of the box.
"""
import json
import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama


# Define tools using the modern @tool decorator
@tool
def create_event_draft(title: str, description: str = None, date: str = None, location: str = None, session_id: str = None) -> Dict[str, Any]:
    """Create a draft event with the given details.
    
    Args:
        title: The event title
        description: A description of the event  
        date: Event date in YYYY-MM-DD format
        location: Event location
        session_id: The session ID for this interaction
    
    Returns:
        Dict containing the created event details
    """
    # Import here to avoid circular imports
    from app.ai.langchain_tools import create_event_draft as core_create_event
    
    # Ensure we have a session_id
    if not session_id:
        raise ValueError("session_id is required for create_event_draft")
    
    # Call the core function with proper parameter mapping
    result = core_create_event.invoke({
        "session_id": session_id,  # First parameter as expected by core
        "title": title,
        "description": description or f"Event: {title}",
        "date": date,  # Let core handle default if None
        "timezone": "Pacific/Auckland"  # Default timezone
    })
    
    return result


@tool  
def add_ticket_type(name: str, price: float, description: str = None, quantity_available: int = 100, max_per_order: int = None, session_id: str = None) -> Dict[str, Any]:
    """Add a ticket type to an existing event.
    
    Args:
        name: Name of the ticket type (e.g., "General Admission", "VIP")
        price: Price per ticket in dollars
        description: A description of what the ticket includes
        quantity_available: Number of tickets available
        max_per_order: Maximum tickets per order
        session_id: The session ID for this interaction
        
    Returns:
        Dict containing the ticket type details
    """
    # Import here to avoid circular imports
    from app.ai.langchain_tools import add_ticket_type as core_add_ticket
    
    # Ensure we have a session_id
    if not session_id:
        raise ValueError("session_id is required for add_ticket_type")
    
    # Call the core function with correct parameter mapping
    result = core_add_ticket.invoke({
        "session_id": session_id,  # First parameter as expected by core
        "name": name,
        "price": price,
        "description": description,
        "quantity_available": quantity_available,
        "max_per_order": max_per_order
    })
    
    return result


def get_database_conversation_history(session_id: str, limit: int = 6) -> List[Dict[str, str]]:
    """Get conversation history from database instead of global memory"""
    try:
        from app.database import get_db
        from app.models import ChatMessage
        
        db = next(get_db())
        
        # Get recent messages from database, ordered by creation time
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        
        # Convert to LangChain message format, reverse to chronological order
        conversation_history = []
        for msg in reversed(messages):
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        db.close()
        return conversation_history
        
    except Exception as e:
        # Fallback to empty history if database access fails
        print(f"Warning: Could not load conversation history: {e}")
        return []


class Qwen3OptimizedAgent:
    """
    Agent specifically optimized for Qwen3-14B's native function calling capabilities.
    Uses database conversation history instead of global memory for proper user isolation.
    """
    
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        
        # Create LLM optimized for Qwen3-14B function calling 
        self.llm = ChatOllama(
            model=model, 
            base_url=self.ollama_endpoint, 
            temperature=0.7,  # Higher temperature for better reasoning (per Qwen3 docs)
            timeout=60,
            # Additional parameters to control Qwen3 behavior
            options={
                "seed": 42,  # For more consistent outputs
                "top_p": 0.8,  # Control randomness
                "repeat_penalty": 1.05,  # Reduce repetition
            }
        )
        
        # Available tools
        self.tools = [create_event_draft, add_ticket_type]
        
        # Bind tools directly to the model (this approach works with Qwen3-14B)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    def _filter_thinking_tokens(self, text: str) -> str:
        """
        Filter out Qwen3's thinking mode tokens from the response.
        Qwen3 sometimes outputs internal reasoning that should be hidden from users.
        """
        import re
        
        if not text:
            return text
        
        # Remove thinking tags and content between them
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
        
        # Remove common thinking patterns that Qwen3 uses
        thinking_patterns = [
            r'^(Hmm,? .*?\.)',  # "Hmm, this is a tricky situation."
            r'^(Alternatively,? .*?\.)',  # "Alternatively, the user might..."
            r'^(So,? .*?\.)',  # "So, the event draft would have..."
            r'^(Let me think.*?\.)',  # "Let me think about this..."
            r'^(I think.*?\.)',  # "I think we should..."
            r'^(The user might.*?\.)',  # "The user might not have..."
            r'^(Next,? .*?\.)',  # "Next, adding the ticket type."
            r'^(The function.*?\.)',  # "The function requires event_id..."
            r'^(The .* isn\'t.*?\.)',  # "The event_id isn't provided yet..."
            r'^(Wait,? .*?\.)',  # "Wait, the user said..."
            r'^(Quantity.*?\.)',  # "Quantity isn't specified..."
        ]
        
        for pattern in thinking_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # Remove excessive thinking-style explanations at the start
        lines = text.split('\n')
        filtered_lines = []
        skip_thinking = True
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines that look like internal reasoning
            if skip_thinking and any(phrase in line.lower() for phrase in [
                'alternatively', 'hmm', 'this is a tricky', 'the user might', 
                'however', 'perhaps proceed', 'that\'s an assumption',
                'best guess given', 'might not have provided enough',
                'next, adding', 'the function requires', 'the event_id isn\'t provided',
                'but after creating', 'wait, the user said', 'the user specified',
                'quantity isn\'t specified', 'so i\'ll set it to', 'the session_id remains',
                'in a real test', 'for the test session', 'that\'s not accurate'
            ]):
                continue
            
            # Start including content when we hit action-oriented text
            if any(phrase in line.lower() for phrase in [
                'i\'ll create', 'let me create', 'creating', 'i\'m creating',
                'i\'ve created', 'great!', 'perfect!', 'excellent!',
                'i can help', 'i\'ll help', 'sure!'
            ]):
                skip_thinking = False
            
            if not skip_thinking:
                filtered_lines.append(line)
        
        # If we filtered everything, return a clean version
        if not filtered_lines:
            # Try to extract any tool-call related content
            if 'create' in text.lower() or 'event' in text.lower():
                return "I'll help you create that event!"
            return text.strip()
        
        return '\n'.join(filtered_lines).strip()
    
    def _get_qwen3_optimized_prompt(self) -> str:
        """System prompt optimized for Qwen3-14B's capabilities"""
        return """You are an expert AI assistant specialized in creating educational events for homeschool communities.

🎯 YOUR CAPABILITIES:
- create_event_draft: Create new event drafts with title, description, date, location
- add_ticket_type: Add ticket types to events with pricing and quantity limits

🧠 REASONING APPROACH:
You excel at step-by-step reasoning and function calling. When users describe events:
1. UNDERSTAND what they want to create
2. EXTRACT key details (title, date, location, etc.)
3. USE the appropriate tools immediately when you have enough information
4. FOLLOW UP with additional details or tickets if requested

⚠️ IMPORTANT: Respond directly and clearly. Do NOT include internal reasoning like "Hmm, this is tricky" or "The user might have..." in your responses. Users should only see your helpful, actionable responses.

💡 EXAMPLES:
User: "Create a science fair for kids on August 15th"
→ You should IMMEDIATELY call create_event_draft with the science fair details

User: "Add general admission tickets for $15 each"
→ You should call add_ticket_type with the pricing information

🎨 COMMUNICATION STYLE:
- Be enthusiastic and helpful
- Confirm what you're creating before proceeding
- Provide clear summaries of what was accomplished
- Ask for clarification only when essential details are missing

Remember: You have access to powerful reasoning capabilities - use them to understand user intent and take appropriate actions promptly."""

    async def process_message(self, user_input: str) -> Dict[str, Any]:
        """Process user message using the optimized Qwen3 agent with database conversation history"""
        try:
            # Get conversation history from DATABASE (not global memory!)
            db_conversation_history = get_database_conversation_history(self.session_id, limit=6)
            
            # Prepare messages
            messages = [
                SystemMessage(content=self._get_qwen3_optimized_prompt()),
            ]
            
            # Add recent conversation history from database
            for msg in db_conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add current user message
            messages.append(HumanMessage(content=user_input))
            
            # Call the model with tools bound
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Handle tool calls
            intermediate_steps = []
            # Filter out thinking tokens from Qwen3's response
            final_content = self._filter_thinking_tokens(response.content)
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # Ensure session_id is included
                    if 'session_id' not in tool_args:
                        tool_args['session_id'] = self.session_id
                    
                    # Find and execute the tool
                    for tool_obj in self.tools:
                        if tool_obj.name == tool_name:
                            try:
                                tool_output = tool_obj.invoke(tool_args)
                                intermediate_steps.append((
                                    {
                                        "name": tool_name,
                                        "arguments": tool_args,
                                        "type": "function_call"
                                    },
                                    tool_output
                                ))
                                
                                # Create a clean success message without exposing thinking
                                if tool_name == "create_event_draft":
                                    event_title = tool_args.get('title', 'event')
                                    final_content = f"Perfect! I've created your '{event_title}' event draft. You can now add ticket types or make any adjustments you'd like."
                                elif tool_name == "add_ticket_type":
                                    ticket_name = tool_args.get('name', 'ticket')
                                    ticket_price = tool_args.get('price', 0)
                                    final_content = f"Excellent! I've added the '{ticket_name}' ticket type for ${ticket_price}. The event is ready for more details if needed."
                                else:
                                    final_content = f"Great! I've successfully completed the {tool_name.replace('_', ' ')} action."
                                
                            except Exception as e:
                                error_output = {"error": str(e), "tool": tool_name}
                                intermediate_steps.append((
                                    {
                                        "name": tool_name,
                                        "arguments": tool_args,
                                        "type": "function_call"
                                    },
                                    error_output
                                ))
                            break
            
            return {
                "output": final_content,
                "intermediate_steps": intermediate_steps,
                "agent_type": "qwen3_optimized",
                "reasoning_iterations": len(intermediate_steps),
                "success": True
            }
            
        except Exception as e:
            return {
                "output": f"I encountered an error while processing your request: {str(e)}. Please try rephrasing your message.",
                "intermediate_steps": [],
                "agent_type": "qwen3_optimized",
                "success": False,
                "error": str(e)
            }


# Main interface functions
async def invoke_qwen3_optimized_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """
    Main entry point for the Qwen3-optimized agent.
    Uses database conversation history for proper user isolation.
    """
    agent = Qwen3OptimizedAgent(model, session_id)
    result = await agent.process_message(user_prompt)
    
    # Note: We no longer maintain a separate chat history here!
    # The ChatService handles database storage of all messages.
    # This prevents the cross-user memory leak bug.
    
    return result


# Backward compatibility
async def invoke_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await invoke_qwen3_optimized_agent(session_id, user_prompt, model) 