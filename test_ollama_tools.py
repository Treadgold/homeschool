#!/usr/bin/env python3
"""
Test Ollama Enhanced Tool Calling
Tests the new tool parsing functionality for models that don't support native function calling
"""

import asyncio
import sys
import os
import json

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai_providers import ai_manager
from app.ai_tools import DynamicEventTools
from app.database import get_db

async def test_ollama_tool_calling():
    """Test enhanced tool calling with Ollama"""
    
    print("🧪 Testing Enhanced Ollama Tool Calling")
    print("=" * 60)
    
    try:
        # Get database session
        db = next(get_db())
        
        # Initialize tools
        tools = DynamicEventTools(db, user_id=1)  # Use admin user
        tool_definitions = tools.get_tool_definitions()
        
        print(f"✅ Tools initialized: {len(tool_definitions)} tools available")
        for tool in tool_definitions:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")
        
        # Get AI provider
        provider = ai_manager.get_current_provider()
        config = ai_manager.get_current_model_config()
        
        print(f"✅ Provider: {provider.__class__.__name__}")
        print(f"✅ Model: {config.model_name if config else 'unknown'}")
        
        # Test messages that should trigger tool usage
        test_messages = [
            {
                "role": "system",
                "content": """You are an AI assistant that helps create events. 

When a user provides event details, you should use the create_event_draft tool.

Available tools:
- create_event_draft: Create event drafts with provided details

When you need to use a tool, respond with exactly this format:
TOOL_CALL: tool_name {"parameter": "value", "parameter2": "value2"}

Example:
TOOL_CALL: create_event_draft {"title": "Birthday Party", "description": "Fun party for kids", "location": "Community Center", "date": "2024-08-12"}

Important: Use tools when helpful!"""
            },
            {
                "role": "user", 
                "content": "I need to create a birthday party event for my 10 year old son James on August 12th at 914 South Head Road in South Head, Auckland. We need people there by 11am for cake and lunch is at 12."
            }
        ]
        
        print("\n📤 Sending test message...")
        print(f"Message: {test_messages[1]['content'][:100]}...")
        
        # Format tools for provider
        formatted_tools = provider.format_tools_for_provider(tool_definitions)
        
        # Call AI provider
        response = await provider.chat_completion(test_messages, formatted_tools)
        
        print(f"\n📥 Response received:")
        print(f"   Content: {response.get('content', '')[:200]}...")
        print(f"   Has tool calls: {bool(response.get('tool_calls'))}")
        
        if response.get('tool_calls'):
            print(f"   Tool calls count: {len(response['tool_calls'])}")
            for i, call in enumerate(response['tool_calls']):
                print(f"   Tool {i+1}: {call}")
        
        # Test the specific parsing function
        if "TOOL_CALL:" in response.get('content', ''):
            print("\n🔍 Testing tool call parsing...")
            parsed_tools = provider._parse_tool_calls_from_text(
                response['content'], 
                tool_definitions
            )
            print(f"   Parsed {len(parsed_tools)} tool calls:")
            for call in parsed_tools:
                print(f"   - {call['function']['name']}: {call['function']['arguments']}")
        
        # Execute tools if any were called
        if response.get('tool_calls'):
            print("\n🛠️  Executing tool calls...")
            for tool_call in response['tool_calls']:
                func_name = tool_call['function']['name']
                func_args = json.loads(tool_call['function']['arguments'])
                
                try:
                    result = await tools.execute_tool(func_name, func_args)
                    print(f"   ✅ {func_name}: {result}")
                except Exception as e:
                    print(f"   ❌ {func_name}: Error - {e}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ollama_tool_calling()) 