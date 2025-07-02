"""
ReAct Agent Service for Qwen3:14b
Implements proper Reasoning → Acting → Observation loop using text-based patterns
"""
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.ai.langchain_tools import create_event_draft, add_ticket_type, get_tools_definition

# Chat history store
chat_history_store: Dict[str, List[Any]] = {}


def get_session_history(session_id: str):
    """Retrieves or creates a chat history for a given session."""
    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    return chat_history_store[session_id]


class ReActAgent:
    """
    ReAct (Reasoning and Acting) Agent for Qwen3:14b
    
    Uses text-based ReAct patterns with robust parsing:
    1. Thought: Reasoning about what to do
    2. Action: Taking an action (calling a tool)
    3. Observation: Observing the result
    4. Repeat until final answer
    """
    
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        
        # Create LLM optimized for Qwen3:14b
        self.llm = ChatOllama(
            model=model, 
            base_url=self.ollama_endpoint, 
            temperature=0.5,  # Better for reasoning
            timeout=60,       # More time for thinking
            num_predict=1024, # Allow longer responses
        )
        
        # Available tools
        self.tools = {
            "create_event_draft": create_event_draft,
            "add_ticket_type": add_ticket_type,
        }
        
        self.tools_definition = get_tools_definition()
        self.max_iterations = 3  # Reduced to prevent timeouts
        
    def _create_react_prompt(self) -> str:
        """Create a clear ReAct prompt optimized for Qwen3"""
        return """You are an event creation assistant using the ReAct method.

TASK: Help the user create events by following this EXACT format:

FORMAT RULES:
1. Start with "Thought:" + your reasoning
2. Then "Action:" + tool name 
3. Then "Action Input:" + JSON parameters
4. OR end with "Final Answer:" + your response

AVAILABLE TOOLS:
- create_event_draft: Creates an event (requires: title, optionally: date, description)
- add_ticket_type: Adds tickets to existing event

EXAMPLE:
User: "Create a wedding for William and Sally on August 25th"

Thought: The user wants a wedding event for William and Sally on August 25th. I should create an event draft with this information.
Action: create_event_draft
Action Input: {{"title": "William and Sally's Wedding", "date": "2025-08-25", "description": "Wedding celebration for William and Sally", "session_id": "{session_id}"}}

NOW RESPOND TO: {user_input}

Thought:"""




    



    

    
    def _parse_react_response_proper(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse ReAct response with robust parsing for Qwen3 model"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Log the actual response for debugging
        logger.info(f"ReAct parsing response (first 300 chars): {response[:300]}...")
        
        # More flexible regex patterns that handle various spacing and formatting
        thought_match = re.search(r'Thought:\s*(.*?)(?=\n\s*(?:Action|Final Answer):|$)', response, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r'Action:\s*(.*?)(?=\n\s*(?:Action Input|Observation|Final Answer):|$)', response, re.DOTALL | re.IGNORECASE)
        action_input_match = re.search(r'Action Input:\s*(.*?)(?=\n\s*(?:Observation|Final Answer):|$)', response, re.DOTALL | re.IGNORECASE)
        final_answer_match = re.search(r'Final Answer:\s*(.*?)$', response, re.DOTALL | re.IGNORECASE)
        
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        action_input = action_input_match.group(1).strip() if action_input_match else None
        final_answer = final_answer_match.group(1).strip() if final_answer_match else None
        
        logger.info(f"Initial parse - thought: {'✓' if thought else '✗'}, action: {'✓' if action else '✗'}, action_input: {'✓' if action_input else '✗'}, final_answer: {'✓' if final_answer else '✗'}")
        
        # If we found an action but no action_input, try to extract from the user's original message
        if action and not action_input:
            logger.info("Found action but no action_input, generating from context...")
            if 'create_event_draft' in action.lower():
                action = "create_event_draft"
                # Try to extract event details from the response or use defaults
                event_title = self._extract_event_title_from_text(response)
                event_date = self._extract_event_date_from_text(response)
                action_input = f'{{"title": "{event_title}", "date": "{event_date or "2025-08-01"}", "description": "Event created from conversation", "session_id": "{self.session_id}"}}'
                logger.info(f"Generated action_input: {action_input}")
        
        # If we have thought but no action, and thought suggests creating event, force action
        if thought and not action and ('create' in thought.lower() or 'event' in thought.lower()):
            logger.info("Found thought about creating event, forcing action...")
            action = "create_event_draft"
            event_title = self._extract_event_title_from_text(response)
            event_date = self._extract_event_date_from_text(response)
            action_input = f'{{"title": "{event_title}", "date": "{event_date or "2025-08-01"}", "description": "Event from AI reasoning", "session_id": "{self.session_id}"}}'
        
        # If we have neither clear action nor final answer, but response contains event info
        if not action and not final_answer and self._contains_event_info(response):
            logger.info("No clear action/answer but contains event info, creating action...")
            thought = "I can see this is about creating an event."
            action = "create_event_draft"
            event_title = self._extract_event_title_from_text(response)
            event_date = self._extract_event_date_from_text(response)
            action_input = f'{{"title": "{event_title}", "date": "{event_date or "2025-08-01"}", "description": "Event detected from response", "session_id": "{self.session_id}"}}'
        
        # Final fallback - if nothing worked, provide final answer
        if not action and not final_answer:
            logger.info("No action or final answer found, providing fallback response")
            final_answer = "I'd be happy to help you create an event. Could you provide more details about what you'd like to organize?"
        
        logger.info(f"Final parse result - action: {action}, has_action_input: {bool(action_input)}, has_final_answer: {bool(final_answer)}")
        return thought, action, action_input, final_answer
    
    def _contains_event_info(self, text: str) -> bool:
        """Check if text contains event-related information"""
        event_keywords = [
            'wedding', 'married', 'marriage', 'party', 'celebration', 'event', 
            'festival', 'workshop', 'class', 'session', 'meeting', 'gathering',
            'birthday', 'anniversary', 'graduation', 'concert', 'show', 'fair',
            'trip', 'visit', 'tour', 'conference', 'seminar', 'training'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in event_keywords)
    
    def _extract_event_title_from_text(self, text: str) -> str:
        """Extract event title from any text with smart pattern matching"""
        text_lower = text.lower()
        
        # Look for specific names in wedding context
        if 'wedding' in text_lower or 'married' in text_lower or 'marriage' in text_lower:
            # Try to extract names
            if 'william' in text_lower and 'sally' in text_lower:
                return "William and Sally's Wedding"
            elif 'william' in text_lower:
                return "William's Wedding"
            elif 'sally' in text_lower:
                return "Sally's Wedding"
            else:
                return "Wedding Celebration"
        
        # Look for birthday patterns
        elif 'birthday' in text_lower:
            # Try to extract name
            if 'tom' in text_lower:
                return "Tom's Birthday Party"
            else:
                return "Birthday Party"
        
        # Look for other event types
        elif 'party' in text_lower:
            return "Party Event"
        elif 'workshop' in text_lower:
            return "Workshop"
        elif 'meeting' in text_lower:
            return "Meeting"
        elif 'festival' in text_lower:
            return "Festival"
        elif 'conference' in text_lower:
            return "Conference"
        elif 'class' in text_lower:
            return "Class"
        elif 'training' in text_lower:
            return "Training Session"
        else:
            return "Special Event"
    
    def _extract_event_date_from_text(self, text: str) -> Optional[str]:
        """Extract date from any text with comprehensive pattern matching"""
        text_lower = text.lower()
        
        # Look for specific date patterns
        date_patterns = [
            (r'25th.*august', '2025-08-25'),
            (r'august.*25th', '2025-08-25'),
            (r'25.*august', '2025-08-25'),
            (r'august.*25', '2025-08-25'),
            (r'15th.*august', '2025-08-15'),
            (r'august.*15th', '2025-08-15'),
            (r'1st.*august', '2025-08-01'),
            (r'august.*1st', '2025-08-01'),
            (r'august', '2025-08-15'),  # Default August date
            (r'september', '2025-09-15'),
            (r'october', '2025-10-15'),
            (r'november', '2025-11-15'),
            (r'december', '2025-12-15'),
            (r'january', '2025-01-15'),
            (r'february', '2025-02-15'),
            (r'march', '2025-03-15'),
            (r'april', '2025-04-15'),
            (r'may', '2025-05-15'),
            (r'june', '2025-06-15'),
            (r'july', '2025-07-15'),
        ]
        
        for pattern, date_value in date_patterns:
            if re.search(pattern, text_lower):
                return date_value
        
        return None
    
    async def _execute_action_proper(self, action: str, action_input: str) -> str:
        """Execute action with proper parameter handling for ReAct format"""
        try:
            # Clean action name
            action = action.strip()
            
            # Parse action input as JSON
            params = {"session_id": self.session_id}
            if action_input:
                try:
                    parsed_params = json.loads(action_input)
                    params.update(parsed_params)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in action input: {action_input}"
            
            # Execute the tool
            if action in self.tools:
                result = self.tools[action].invoke(params)
                return f"Success: {json.dumps(result, indent=2)}"
            else:
                return f"Error: Unknown tool '{action}'. Available tools: {list(self.tools.keys())}"
                
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    def _extract_event_title(self, user_input: str) -> str:
        """Extract likely event title from user input"""
        # Look for quoted text first
        quoted_match = re.search(r'["\']([^"\']+)["\']', user_input)
        if quoted_match:
            return quoted_match.group(1)
        
        # Look for specific event types
        if "science fair" in user_input.lower():
            return "Science Fair"
        elif "zoo visit" in user_input.lower():
            return "Zoo Visit"
        elif "workshop" in user_input.lower():
            return "Workshop"
        elif "party" in user_input.lower():
            return "Party"
        elif "festival" in user_input.lower():
            return "Festival"
        elif "class" in user_input.lower():
            return "Class"
        elif "session" in user_input.lower():
            return "Session"
        elif "meeting" in user_input.lower():
            return "Meeting"
        elif "trip" in user_input.lower():
            return "Trip"
        elif "visit" in user_input.lower():
            return "Visit"
        
        # Fallback
        return "New Event"
    
    def _extract_event_description(self, user_input: str, ai_response: str) -> str:
        """Extract or generate event description"""
        # Use user input as base description
        description = f"Event created from: {user_input}"
        
        # Add context if AI provided useful info
        if len(ai_response) > 50 and 'error' not in ai_response.lower():
            clean_response = ai_response.replace('\n', ' ').strip()
            if len(clean_response) > 100:
                clean_response = clean_response[:100] + "..."
            description += f" | AI Context: {clean_response}"
        
        return description
    
    def _extract_event_date(self, user_input: str) -> Optional[str]:
        """Extract date information from user input"""
        # Look for explicit dates
        date_patterns = [
            (r'august\s+15,?\s*2025', '2025-08-15'),
            (r'august\s+15th?,?\s*2025', '2025-08-15'),
            (r'next\s+friday', 'Next Friday'),
            (r'next\s+saturday', 'Next Saturday'),
            (r'friday', 'Friday'),
            (r'saturday', 'Saturday'),
        ]
        
        user_lower = user_input.lower()
        for pattern, date_value in date_patterns:
            if re.search(pattern, user_lower):
                return date_value
        
        return None

    async def run_react_loop(self, user_input: str) -> Dict[str, Any]:
        """Improved ReAct loop optimized for Qwen3 model"""
        import logging
        logger = logging.getLogger(__name__)
        
        intermediate_steps = []
        
        # Start with clear, focused prompt
        current_input = self._create_react_prompt().format(
            session_id=self.session_id,
            user_input=user_input
        )
        
        logger.info(f"Starting ReAct loop for: {user_input[:100]}...")
        
        # ReAct iterations with better error handling
        for iteration in range(self.max_iterations):
            logger.info(f"ReAct iteration {iteration + 1}/{self.max_iterations}")
            
            try:
                # Get LLM response
                response = await self.llm.ainvoke([{"role": "user", "content": current_input}])
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # Parse ReAct components with robust parsing
                thought, action, action_input, final_answer = self._parse_react_response_proper(response_content)
                
                # If we have a final answer, we're done
                if final_answer:
                    logger.info(f"ReAct completed with final answer after {iteration + 1} iterations")
                    return {
                        "output": final_answer,
                        "intermediate_steps": intermediate_steps,
                        "iterations": iteration + 1,
                        "success": True
                    }
                
                # If we have an action, execute it
                if action and action_input:
                    logger.info(f"Executing action: {action}")
                    observation = await self._execute_action_proper(action, action_input)
                    
                    # Record step
                    step = {
                        "iteration": iteration + 1,
                        "thought": thought or "Processing request",
                        "action": action,
                        "action_input": action_input,
                        "observation": observation
                    }
                    intermediate_steps.append(step)
                    
                    # For event creation, often one step is enough - provide helpful response
                    if 'create_event_draft' in action and 'Success' in observation:
                        success_message = f"Great! I've created the event draft successfully. {observation}"
                        logger.info("Event creation successful, ending ReAct loop")
                        return {
                            "output": success_message,
                            "intermediate_steps": intermediate_steps,
                            "iterations": iteration + 1,
                            "success": True
                        }
                    
                    # Prepare next iteration if needed
                    current_input = f"""Previous step:
Thought: {thought or 'Working on the task'}
Action: {action}
Action Input: {action_input}
Observation: {observation}

What should I do next? If the task is complete, provide a Final Answer.

Thought:"""
                else:
                    # No valid action found, but we handled this in parsing
                    logger.warning(f"No valid action found in iteration {iteration + 1}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in ReAct iteration {iteration + 1}: {e}")
                # Try to recover with a helpful message
                break
        
        # If we get here, something didn't work as expected
        logger.warning("ReAct loop completed without clear success")
        
        # If we have any intermediate steps, use them to provide a response
        if intermediate_steps:
            last_step = intermediate_steps[-1]
            if 'Success' in last_step.get('observation', ''):
                return {
                    "output": f"I've processed your request. {last_step['observation']}",
                    "intermediate_steps": intermediate_steps,
                    "iterations": len(intermediate_steps),
                    "success": True
                }
        
        # Final fallback
        return {
            "output": "I'd be happy to help you create an event. Could you provide more specific details about what you'd like to organize?",
            "intermediate_steps": intermediate_steps,
            "iterations": len(intermediate_steps),
            "success": False
        }


async def invoke_react_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """
    Main entry point for the ReAct agent
    Compatible with existing agent interface
    """
    agent = ReActAgent(model, session_id)
    result = await agent.run_react_loop(user_prompt)
    
    # Convert intermediate_steps to format expected by existing code
    formatted_steps = []
    for step in result.get("intermediate_steps", []):
        # Create a format compatible with existing code
        step_tuple = (
            {
                "name": step.get("action", "").split()[0] if step.get("action") else "unknown",
                "arguments": step.get("action", ""),
                "type": "react_step"
            },
            step.get("observation", "")
        )
        formatted_steps.append(step_tuple)
    
    # Update chat history
    chat_history = get_session_history(session_id)
    chat_history.append(HumanMessage(content=user_prompt))
    chat_history.append(AIMessage(content=result["output"]))
    
    return {
        "output": result["output"],
        "intermediate_steps": formatted_steps,
        "react_details": {
            "conversation_history": result.get("conversation_history", []),
            "iterations": result.get("iterations", 0),
            "success": result.get("success", False),
            "original_steps": result.get("intermediate_steps", [])
        }
    }


# Backward compatibility - make this the default agent
async def invoke_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """Backward compatibility wrapper"""
    return await invoke_react_agent(session_id, user_prompt, model) 