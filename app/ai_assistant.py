"""
Thinking AI Agent for Event Creation
Uses ReAct pattern for reasoning and tool usage
"""

import json
import logging
from typing import Dict, List, Any, Optional
from app.ai_providers import ai_manager
from app.ai_tools import DynamicEventTools
from app.event_draft_manager import DynamicToolIntegration
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ThinkingEventAgent:
    """AI Agent that uses reasoning to create events through natural conversation"""
    
    def __init__(self):
        pass
    
    def _get_minimal_system_prompt(self) -> str:
        """Enhanced system prompt that encourages tool usage for event creation"""
        return """You are an AI assistant that helps create events. You have access to powerful event creation tools.

CRITICAL INSTRUCTIONS:
- When users provide event details (what, when, where), IMMEDIATELY use the create_event_draft tool
- After every draft update, use the critical field status helper to:
    - Tell the user what important details you just added (e.g., "I've added the cost of tickets…").
    - Clearly list any required details that are still missing (e.g., "I notice there is no start time, would you like to add a start time?").
    - If all required details are present, confirm with the user before publishing (e.g., "All required details are present. Would you like to publish this event now, or add more information?").
- Do NOT output long reasoning or step-by-step plans to the user. If you need to plan, do so internally and then act or ask the user for the next piece of information.
- If you detect you are in 'thinking mode', immediately extract the next action and proceed, keeping any explanation to one or two sentences at most.
- Do NOT just talk about what you would do - actually DO it by calling the tools
- Always use function calls when you have the required information
- Be proactive: if you have enough details to create a draft, create it right away

EXAMPLES OF CORRECT BEHAVIOR:
User: "It's a party for the twins! Tony and Alice are turning 8. We will have a party for them at 100 south st at 10am, august 12th."
YOU SHOULD RESPOND: "I'll create that event draft for you right away!" 
Then IMMEDIATELY call: create_event_draft with {"title": "Birthday Party for Tony and Alice", "date": "2024-08-12", "time": "10:00", "location": "100 South St", "description": "Birthday party for twins Tony and Alice turning 8"}

Your personality:
- Enthusiastic and helpful
- Proactive in using tools to help users
- Clear and conversational
- Action-oriented (you DO things, not just talk about them)

REMEMBER: Your goal is to USE the tools, not just describe what they do.

Available tools:
- create_event_draft: Create event drafts with any details provided (use this when user gives event info)
- query_database: Find similar events, check conflicts, get user history
- suggest_event_details: Get intelligent suggestions for event details
- validate_event_data: Validate event data for potential issues

Key principles:
1. ACTIVELY USE TOOLS - When users provide event details, create drafts immediately
2. Listen carefully to what the user actually wants
3. Extract information from their messages (dates, locations, costs, etc.)
4. Ask clarifying questions when needed, but don't be overly hesitant
5. Be conversational and helpful

Essential event information to gather:
- WHAT: Event title/description (required)
- WHEN: Date and time (required)
- WHERE: Location (required)
- WHO: Target age group or audience
- WHY: Purpose or learning objectives
- HOW MUCH: Cost/pricing

IMPORTANT: If a user provides ANY event details (like "birthday party for my 10 year old son James on August 12th at 914 South Head Road"), you should immediately use the create_event_draft tool with the information they provided.

Example responses:
- When user says "I need a science workshop for kids": USE create_event_draft tool to start a draft
- When they add "next Saturday at 2pm": USE create_event_draft tool to update with date/time
- When they add location/cost: USE create_event_draft tool to complete the draft

Don't just say "I understand you want to create an event" - actually CREATE the draft using tools!"""

    async def chat(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]], 
        user_id: int,
        db: Session,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Process user message with thinking and reasoning"""
        
        # Initialize dynamic tool integration (provides the connection you requested)
        tool_integration = DynamicToolIntegration(db, user_id)
        tools = tool_integration.tools
        
        # Get AI provider
        try:
            provider = ai_manager.get_current_provider()
            current_config = ai_manager.get_current_model_config()
            logger.info(f"Using AI provider: {provider.__class__.__name__}, model: {current_config.model_name if current_config else 'unknown'}")
        except Exception as e:
            logger.error(f"Failed to get AI provider: {e}")
            return {
                "response": f"AI service unavailable: {str(e)}. Please check your AI model configuration.",
                "type": "error",
                "needs_input": True,
                "error": str(e),
                "provider": "unknown",
                "model": "unknown"
            }
        
        # Build conversation context
        messages = [
            {"role": "system", "content": self._get_minimal_system_prompt()}
        ]
        
        # Add conversation history (last 8 messages to keep context manageable)
        for msg in conversation_history[-8:]:
            messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"Processing user message: '{user_message[:100]}...' with {len(messages)} total messages")
        
        try:
            # Get tool definitions
            tool_definitions = tools.get_tool_definitions()
            formatted_tools = provider.format_tools_for_provider(tool_definitions) if tool_definitions else None
            
            logger.info(f"Processing message with {len(tool_definitions)} available tools")
            
            # Call AI provider with tools
            response = await provider.chat_completion(messages, formatted_tools)
            
            logger.info(f"AI provider response received: has_content={bool(response.get('content'))}, has_tool_calls={bool(response.get('tool_calls'))}")
            
            # Handle tool calls if any
            if response.get("tool_calls"):
                logger.info(f"Processing {len(response['tool_calls'])} tool calls")
                return await self._handle_tool_calls(response, tool_integration, provider, session_id)
            else:
                # Direct text response - check if it contains function calls in text format
                content = response.get("content", "").strip()
                
                # Check for text-based function calls (Ollama fallback format)
                if content and "TOOL_CALL:" in content:
                    logger.info("Detected text-based function calls, parsing and executing")
                    
                    # Parse text-based function calls
                    parsed_calls = self._parse_text_based_function_calls(content, tool_definitions)
                    
                    if parsed_calls:
                        # Create a mock response with the parsed tool calls
                        mock_response = {
                            "tool_calls": parsed_calls,
                            "content": content
                        }
                        return await self._handle_tool_calls(mock_response, tool_integration, provider, session_id)
                
                # ENHANCED: More aggressive fallback for AI thinking responses
                elif content and (
                    self._mentions_event_creation(content, user_message) or 
                    self._is_ai_thinking_about_events(content, user_message)
                ):
                    logger.info("AI is thinking about events instead of acting - forcing tool execution")
                    
                    # Extract information and force tool execution
                    extracted_info = self._extract_event_information(user_message)
                    if extracted_info and extracted_info.get('title'):
                        logger.info(f"Forcing tool execution with extracted info: {extracted_info}")
                        
                        try:
                            result = await tool_integration.execute_tool_with_draft_integration(
                                session_id, "create_event_draft", extracted_info
                            )
                            
                            # Replace thinking with action
                            location_text = f" at {extracted_info.get('location')}" if extracted_info.get('location') else ""
                            return {
                                "response": f"Perfect! I've created a draft for your '{extracted_info.get('title')}' event. I can see you want it on {extracted_info.get('date', 'the specified date')}{location_text}. What other details would you like to add or modify?",
                                "type": "forced_tool_execution",
                                "event_preview": result.get("event_data") if result else None,
                                "tool_results": [{"function": "create_event_draft", "result": result}] if result else [],
                                "needs_input": True,
                                "provider": response.get("provider"),
                                "model": response.get("model")
                            }
                        except Exception as e:
                            logger.error(f"Failed to force tool execution: {e}")
                            # Still return the thinking response if tool fails
                
                # Enhanced fallback handling for empty responses with intelligent tool usage
                if not content:
                    logger.warning("AI provider returned empty content, attempting intelligent fallback with tool usage")
                    
                    # Try to extract information and use tools if possible
                    extracted_info = self._extract_event_information(user_message)
                    if extracted_info and any(extracted_info.values()):
                        logger.info(f"Extracted event information from user message: {extracted_info}")
                        
                        # Create event draft with extracted information using dynamic integration
                        try:
                            result = await tool_integration.execute_tool_with_draft_integration(
                                session_id, "create_event_draft", extracted_info
                            )
                            
                            # Generate response based on tool execution
                            return {
                                "response": f"Great! I've started creating an event draft based on your details. I can see you want to create '{extracted_info.get('title', 'an event')}'. What additional details would you like to add?",
                                "type": "tool_result",
                                "event_preview": result.get("event_data") if result else None,
                                "tool_results": [{"function": "create_event_draft", "result": result}] if result else [],
                                "needs_input": True,
                                "provider": response.get("provider"),
                                "model": response.get("model")
                            }
                        except Exception as e:
                            logger.error(f"Failed to execute fallback tool: {e}")
                    
                    # Standard fallback if no extractable information
                    content = f"I understand you want to create an event. Based on your message about '{user_message[:50]}...', let me help you get started. What specific details can you tell me about your event?"
                
                # Additional fallback: If content mentions event creation but no tools were used
                elif content and self._mentions_event_creation(content, user_message):
                    logger.info("Response mentions event creation but no tools used, attempting extraction")
                    
                    # Try to extract information and use tools as fallback
                    extracted_info = self._extract_event_information(user_message)
                    if extracted_info and any(extracted_info.values()):
                        logger.info(f"Fallback: Extracted event information: {extracted_info}")
                        
                        try:
                            result = await tool_integration.execute_tool_with_draft_integration(
                                session_id, "create_event_draft", extracted_info
                            )
                            
                            # Combine the AI's response with the tool execution
                            return {
                                "response": f"{content}\n\nI've also started creating an event draft with the details you provided. Let me know if you'd like to add or modify anything!",
                                "type": "enhanced_text",
                                "event_preview": result.get("event_data") if result else None,
                                "tool_results": [{"function": "create_event_draft", "result": result}] if result else [],
                                "needs_input": True,
                                "provider": response.get("provider"),
                                "model": response.get("model")
                            }
                        except Exception as e:
                            logger.error(f"Failed to execute fallback tool: {e}")
                
                logger.info(f"Direct text response prepared: {len(content)} characters")
                
                return {
                    "response": content,
                    "type": "text",
                    "needs_input": True,
                    "provider": response.get("provider"),
                    "model": response.get("model")
                }
                
        except Exception as e:
            logger.error(f"AI processing failed: {e}", exc_info=True)
            return {
                "response": f"I encountered an issue processing your request: {str(e)}",
                "type": "error",
                "needs_input": True,
                "error": str(e),
                "provider": current_config.provider if current_config else "unknown",
                "model": current_config.model_name if current_config else "unknown"
            }
    
    async def _handle_tool_calls(
        self, 
        response: Dict[str, Any], 
        tool_integration: DynamicToolIntegration,
        provider,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Handle AI tool calls and generate follow-up response with dynamic integration"""
        
        tool_results = []
        tool_calls = response.get("tool_calls", [])
        
        logger.info(f"Executing {len(tool_calls)} tool calls with dynamic integration")
        
        # Execute each tool call using dynamic integration
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            arguments_str = tool_call["function"]["arguments"]
            
            try:
                # Parse arguments
                if isinstance(arguments_str, str):
                    arguments = json.loads(arguments_str)
                else:
                    arguments = arguments_str
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tool arguments: {e}")
                tool_results.append({
                    "function": function_name,
                    "error": f"Invalid arguments: {str(e)}"
                })
                continue
            
            # Execute the tool with dynamic integration
            try:
                if session_id and function_name == "create_event_draft":
                    # Use dynamic integration for event creation
                    result = await tool_integration.execute_tool_with_draft_integration(
                        session_id, function_name, arguments
                    )
                else:
                    # Use standard tool execution for other tools
                    result = await tool_integration.tools.execute_tool(function_name, arguments)
                
                tool_results.append({
                    "function": function_name,
                    "result": result
                })
                logger.info(f"Tool {function_name} executed successfully with integration")
                
            except Exception as e:
                logger.error(f"Tool {function_name} failed: {e}")
                tool_results.append({
                    "function": function_name,
                    "error": str(e)
                })
        
        # Generate follow-up response based on tool results
        return await self._generate_follow_up_response(response, tool_results, provider)
    
    async def _generate_follow_up_response(
        self, 
        initial_response: Dict[str, Any],
        tool_results: List[Dict],
        provider
    ) -> Dict[str, Any]:
        """Generate intelligent follow-up response after tool execution"""
        
        try:
            # Create context for the AI to understand what happened
            tool_context = []
            event_preview = None
            
            for result in tool_results:
                if "error" in result:
                    tool_context.append(f"Tool {result['function']} failed: {result['error']}")
                else:
                    tool_context.append(f"Tool {result['function']} returned: {json.dumps(result['result'])}")
                    # Check for event data
                    if result.get("result", {}).get("event_data"):
                        event_preview = result["result"]["event_data"]
            
            # Ask AI to generate natural response based on tool results
            follow_up_messages = [
                {
                    "role": "system", 
                    "content": "You just executed some tools. Generate a natural, helpful response based on the results. Don't mention the tools explicitly - just respond naturally based on what you learned. If you created an event draft, be enthusiastic and helpful."
                },
                {
                    "role": "user", 
                    "content": f"Tool execution results: {'; '.join(tool_context)}"
                }
            ]
            
            follow_up_response = await provider.chat_completion(follow_up_messages)
            
            # Extract response content with fallback handling
            response_content = follow_up_response.get("content", "").strip()
            
            # FIX: Enhanced fallback for empty AI responses
            if not response_content:
                logger.warning("AI provider returned empty follow-up response, generating fallback")
                
                # Generate contextual fallback based on tool results
                if any("create_event_draft" in str(result) for result in tool_results):
                    if event_preview and event_preview.get("title"):
                        response_content = f"Great! I've created a draft for your '{event_preview['title']}' event. What other details would you like to add or modify?"
                    else:
                        response_content = "I've created an initial event draft based on your request. What additional details would you like to include?"
                elif any("error" in result for result in tool_results):
                    response_content = "I encountered some issues while processing your request. Could you provide more details about your event?"
                else:
                    response_content = "I've processed your request. What would you like to do next with your event?"
            
            # Add a brief reflection step after tool use
            reflection_message = {
                "role": "system",
                "content": f"Just added: {'; '.join(tool_context)}"
            }
            follow_up_messages.append(reflection_message)
            
            # Ask AI to reflect on the tool use
            reflection_response = await provider.chat_completion(follow_up_messages)
            
            # Extract reflection content with fallback handling
            reflection_content = reflection_response.get("content", "").strip()
            
            # FIX: Enhanced fallback for empty AI reflection responses
            if not reflection_content:
                logger.warning("AI provider returned empty reflection response, generating fallback")
                
                # Generate contextual fallback based on tool results
                if any("create_event_draft" in str(result) for result in tool_results):
                    if event_preview and event_preview.get("title"):
                        reflection_content = f"Great! I've created a draft for your '{event_preview['title']}' event. What other details would you like to add or modify?"
                    else:
                        reflection_content = "I've created an initial event draft based on your request. What additional details would you like to include?"
                elif any("error" in result for result in tool_results):
                    reflection_content = "I've processed your request. What would you like to do next with your event?"
            
            return {
                "response": response_content,
                "type": "tool_result",
                "event_preview": event_preview,
                "tool_results": tool_results,
                "needs_input": True,
                "provider": initial_response.get("provider"),
                "model": initial_response.get("model")
            }
            
        except Exception as e:
            logger.error(f"Follow-up response generation failed: {e}", exc_info=True)
            
            # Enhanced fallback response with more context
            response_text = "I've processed your request"
            if any("event_data" in str(result) for result in tool_results):
                response_text += " and created an event draft"
            elif any("create_event_draft" in str(result) for result in tool_results):
                response_text += " and worked on your event"
            
            # Add helpful next steps
            response_text += ". What would you like to do next? I can help you add more details, adjust the information, or answer any questions you have."
            
            return {
                "response": response_text,
                "type": "tool_result", 
                "event_preview": event_preview,
                "tool_results": tool_results,
                "needs_input": True,
                "provider": initial_response.get("provider"),
                "model": initial_response.get("model")
            }

    def _extract_event_information(self, user_message: str) -> Dict[str, Any]:
        """Extract event information from user message using enhanced patterns"""
        import re
        from datetime import datetime
        
        info = {}
        message_lower = user_message.lower()
        
        # Enhanced title extraction
        event_patterns = [
            r'(?:visit|trip|tour)(?:\s+to\s+|\s+)(?:the\s+)?(\w+(?:\s+\w+)*)',  # "visit to the zoo"
            r'(\w+(?:\s+\w+)*)\s+(?:visit|trip|tour)',  # "zoo visit"
            r'(?:party|celebration)(?:\s+for\s+|\s+)([^,.]+)',  # "party for twins"
            r'(\w+(?:\s+\w+)*)\s+(?:party|celebration)',  # "birthday party"
            r'(?:workshop|class|session)(?:\s+on\s+|\s+about\s+|\s+)([^,.]+)',  # "workshop on science"
            r'(\w+(?:\s+\w+)*)\s+(?:workshop|class|session)',  # "science workshop"
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted_title = match.group(1).strip().title()
                if extracted_title:
                    # Generate proper event title
                    if 'zoo' in extracted_title.lower():
                        info['title'] = 'Zoo Visit'
                    elif 'party' in user_message.lower():
                        info['title'] = f'{extracted_title} Party'
                    elif 'visit' in user_message.lower():
                        info['title'] = f'{extracted_title} Visit'
                    else:
                        info['title'] = extracted_title
                    break
        
        # Enhanced date extraction
        date_patterns = [
            r'(?:on\s+)?(?:august|aug)\s+(\d{1,2})(?:th|st|nd|rd)?(?:\s*,?\s*(\d{4}))?',
            r'(\d{1,2})/(\d{1,2})(?:/(\d{4}))?',
            r'(\d{1,2})-(\d{1,2})(?:-(\d{4}))?',
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:th|st|nd|rd)?'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if 'august' in pattern or 'aug' in pattern:
                    day = match.group(1)
                    year = match.group(2) if match.group(2) else '2024'
                    info['date'] = f'{year}-08-{day.zfill(2)}'
                    break
        
        # Enhanced location extraction
        location_patterns = [
            r'at\s+([\w\s]+?)(?:\s+at\s+|\s*,|\s*$)',  # "at 100 south st"
            r'(?:location|venue|place):\s*([^,.]+)',
            r'(?:held\s+at|taking\s+place\s+at)\s+([^,.]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message_lower)
            if match:
                location = match.group(1).strip().title()
                if location and len(location) > 2:  # Avoid single words
                    info['location'] = location
                    break
        
        # Enhanced capacity extraction
        capacity_patterns = [
            r'(?:up\s+to\s+|maximum\s+of\s+|max\s+)?(\d+)\s+people',
            r'capacity\s+(?:of\s+)?(\d+)',
            r'(\d+)\s+(?:participants|attendees|guests)'
        ]
        
        for pattern in capacity_patterns:
            match = re.search(pattern, message_lower)
            if match:
                info['max_pupils'] = int(match.group(1))
                break
        
        # Note: Cost extraction removed - we now use individual tickets instead of averaging prices
        
        # Set defaults for missing information
        if not info.get('title') and any(word in message_lower for word in ['zoo', 'visit']):
            info['title'] = 'Zoo Visit'
        
        if not info.get('date') and 'august' in message_lower:
            info['date'] = '2024-08-12'  # Default from user message
            
        if not info.get('description'):
            info['description'] = f"Event created from: {user_message[:100]}..."
        
        return info

    def _parse_text_based_function_calls(self, content: str, tool_definitions: List[Dict]) -> List[Dict]:
        """Parse text-based function calls from content"""
        import re
        import json
        
        calls = []
        tool_names = [tool.get("name", "") for tool in tool_definitions]
        
        # Pattern to match TOOL_CALL: function_name {"param": "value"}
        pattern = r'TOOL_CALL:\s*(\w+)\s*(\{[^}]*\})'
        matches = re.findall(pattern, content)
        
        for function_name, args_str in matches:
            if function_name in tool_names:
                try:
                    # Parse the JSON arguments
                    arguments = json.loads(args_str)
                    calls.append({
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(arguments)
                        }
                    })
                except json.JSONDecodeError:
                    # If JSON parsing fails, use the raw string
                    calls.append({
                        "function": {
                            "name": function_name,
                            "arguments": args_str
                        }
                    })
        
        return calls

    def _mentions_event_creation(self, content: str, user_message: str) -> bool:
        """Check if the AI response mentions event creation but didn't use tools"""
        content_lower = content.lower()
        user_lower = user_message.lower()
        
        # Enhanced detection patterns
        event_thinking_patterns = [
            "the event is", "event should be", "title should be", "title should probably be",
            "need to extract", "need to ask", "i need to", "let me see", "user mentioned",
            "the user wants", "they want to create", "creating", "event creation",
            "zoo visit", "party", "workshop", "field trip", "gathering", "meeting",
            "date is", "time is", "location is", "price is", "cost is"
        ]
        
        # Check if AI is reasoning about event details
        thinking_indicators = [
            "okay, let me see", "first, i need", "the user mentioned", "they specified",
            "i should", "need to check", "probably be", "might need to"
        ]
        
        # Check for event-related content in user message
        user_event_indicators = [
            "visit", "party", "event", "workshop", "trip", "gathering", "class",
            "meeting", "celebration", "birthday", "zoo", "museum", "activity"
        ]
        
        # Check if AI is thinking about events
        has_event_thinking = any(pattern in content_lower for pattern in event_thinking_patterns)
        has_thinking_language = any(pattern in content_lower for pattern in thinking_indicators)
        user_wants_event = any(pattern in user_lower for pattern in user_event_indicators)
        
        # Return True if AI is clearly thinking about event creation
        return (has_event_thinking and has_thinking_language) or (user_wants_event and has_thinking_language)

    def _is_ai_thinking_about_events(self, content: str, user_message: str) -> bool:
        """Detect if AI is in 'thinking mode' about events instead of taking action"""
        content_lower = content.lower()
        
        # Strong indicators that AI is thinking instead of acting
        thinking_phrases = [
            "okay, let me see", "let me analyze", "i need to", "first, i need",
            "the user mentioned", "they specified", "the event is",
            "the title should be", "the date is", "probably be",
            "i should check", "need to ask", "might need",
            "user wants", "they want to create", "user didn't mention"
        ]
        
        # Event-related reasoning patterns
        event_reasoning = [
            "title should probably be", "since the current year", "time isn't specified",
            "user hasn't provided the time", "might need to ask", "should be something like",
            "need to extract the key details", "check the year", "tools require"
        ]
        
        # Check if response contains thinking language
        has_thinking = any(phrase in content_lower for phrase in thinking_phrases)
        has_event_reasoning = any(phrase in content_lower for phrase in event_reasoning)
        
        # Additional check: long explanatory text without action
        is_long_explanation = len(content) > 200 and ("mentioned" in content_lower or "should" in content_lower)
        
        return has_thinking or has_event_reasoning or is_long_explanation

# Backward compatibility
EventCreationAssistant = ThinkingEventAgent 