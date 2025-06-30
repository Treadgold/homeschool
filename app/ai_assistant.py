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
        return """You are an intelligent AI agent that helps users create events for a homeschool community platform.

Your primary goal: Help users create events by gathering information through conversation and actively using the available tools.

CRITICAL: When a user provides event information, you should USE TOOLS to help them, not just provide generic responses.

Available tools (USE THESE!):
- create_event_draft: Create event drafts with any details provided (use this when user gives event info)
- query_database: Find similar events, check conflicts, get user history
- suggest_event_details: Get intelligent suggestions for pricing, timing, capacity
- validate_event_data: Check event data for issues before creation

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
                # Direct text response
                content = response.get("content", "").strip()
                
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
        """Extract event information from natural language using pattern matching"""
        import re
        from datetime import datetime, timedelta
        
        extracted = {}
        message = user_message.lower()
        
        # Extract event type/title
        event_patterns = [
            r"(birthday party|science workshop|field trip|nature walk|coding workshop|art class|music lesson|sports event|cooking class|story time)",
            r"(workshop|party|trip|walk|class|lesson|event|activity)"
        ]
        
        for pattern in event_patterns:
            match = re.search(pattern, message)
            if match:
                event_type = match.group(1)
                # Try to get more context for title
                if "birthday party" in message:
                    age_match = re.search(r"(\d+)\s*year\s*old", message)
                    name_match = re.search(r"(?:son|daughter)\s+([a-zA-Z]+)", message)
                    if age_match and name_match:
                        age = age_match.group(1)
                        name = name_match.group(1)
                        extracted["title"] = f"{name.title()}'s {age}th Birthday Party"
                    else:
                        extracted["title"] = "Birthday Party"
                elif event_type:
                    extracted["title"] = event_type.title()
                break
        
        # Extract date information
        date_patterns = [
            r"august\s+(\d+)",
            r"on\s+(\w+)\s+(\d+)",
            r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                if "august" in pattern:
                    day = match.group(1)
                    # Assume current year
                    current_year = datetime.now().year
                    extracted["date"] = f"{current_year}-08-{day.zfill(2)}"
                # Add more date parsing as needed
                break
        
        # Extract location
        location_patterns = [
            r"at\s+([^,\n]+)",
            r"in\s+([^,\n]+)",
            r"(\d+\s+[^,\n]+(?:road|street|avenue|lane|drive|court))",
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                location = match.group(1).strip()
                # Clean up the location
                if len(location) > 5 and not location.startswith("the "):
                    extracted["location"] = location.title()
                break
        
        # Extract time information
        time_patterns = [
            r"(\d+)am",
            r"(\d+):(\d+)am",
            r"(\d+)pm", 
            r"(\d+):(\d+)pm",
            r"by\s+(\d+)am",
        ]
        
        times_found = []
        for pattern in time_patterns:
            matches = re.finditer(pattern, message)
            for match in matches:
                times_found.append(match.group(0))
        
        if times_found:
            extracted["time_details"] = ", ".join(times_found)
        
        # Extract age information
        age_match = re.search(r"(\d+)\s*year\s*old", message)
        if age_match:
            age = int(age_match.group(1))
            extracted["min_age"] = max(1, age - 2)  # Age range
            extracted["max_age"] = age + 2
        
        # Extract purpose/description from context
        if "birthday" in message:
            extracted["description"] = "A fun birthday party celebration with cake, games, and activities"
        elif "workshop" in message:
            extracted["description"] = "An educational workshop with hands-on activities"
        
        # Add event type
        if "birthday" in message:
            extracted["event_type"] = "social"
        elif "workshop" in message or "class" in message:
            extracted["event_type"] = "educational"
        else:
            extracted["event_type"] = "homeschool"
        
        return extracted

# Backward compatibility
EventCreationAssistant = ThinkingEventAgent 