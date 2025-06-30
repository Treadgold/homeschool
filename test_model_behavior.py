#!/usr/bin/env python3
"""
Simple AI Model Behavior Test
Tests how different models respond to function calling prompts
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add app to path
sys.path.insert(0, "/app")

from app.ai_providers import ai_manager
from app.database import get_db
from app.ai_tools import DynamicEventTools
from app.models import User

async def test_model_behavior():
    """Test how the current model responds to function calling prompts"""
    print("🧪 AI Model Function Calling Behavior Test")
    print("=" * 50)
    
    # Get current model info
    try:
        current_provider = ai_manager.get_current_provider()
        model_name = getattr(current_provider, 'model', 'unknown')
        print(f"🤖 Testing model: {model_name}")
        print(f"🔗 Provider: {current_provider.__class__.__name__}")
        
        # Get a test user
        db = next(get_db())
        test_user = db.query(User).first()
        if not test_user:
            print("❌ No test user found - skipping tool tests")
            return
        
        # Initialize tools
        tools = DynamicEventTools(db, test_user.id)
        tool_definitions = tools.get_tool_definitions()
        
        print(f"\n📋 Available tools: {len(tool_definitions)}")
        for tool in tool_definitions:
            print(f"   - {tool['name']}")
        
        # Test different prompt styles
        test_cases = [
            {
                "name": "Natural Language",
                "messages": [
                    {
                        "role": "user",
                        "content": "Create a birthday party event for a 10-year-old. Set the title to 'Birthday Party Fun', location to 'Community Hall', cost to 25 dollars, and max participants to 15."
                    }
                ]
            },
            {
                "name": "Explicit Function Call Request", 
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an event creation assistant. When the user asks to create an event, you MUST call the create_event_draft function with the provided details. Do not respond with text explanations - only make function calls."
                    },
                    {
                        "role": "user",
                        "content": "Use the create_event_draft function to create a birthday party event for a 10-year-old. Set the title to 'Birthday Party Fun', location to 'Community Hall', cost to 25, and max_pupils to 15."
                    }
                ]
            },
            {
                "name": "Direct Tool Instruction",
                "messages": [
                    {
                        "role": "user", 
                        "content": "Call create_event_draft with these parameters: title='Birthday Party Fun', location='Community Hall', cost=25, max_pupils=15, description='Birthday party for a 10-year-old'"
                    }
                ]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['name']}")
            print("-" * 30)
            
            try:
                print("📤 Sending request...")
                start_time = asyncio.get_event_loop().time()
                
                response = await current_provider.chat_completion(
                    test_case['messages'], 
                    tool_definitions
                )
                
                elapsed = asyncio.get_event_loop().time() - start_time
                print(f"⏱️  Response received ({elapsed:.2f}s)")
                
                # Analyze response
                print("\n📋 Response Analysis:")
                print(f"   Response type: {type(response)}")
                print(f"   Has content: {'content' in response}")
                print(f"   Has tool_calls: {'tool_calls' in response}")
                
                if response.get('content'):
                    content = response['content'][:200] + "..." if len(response['content']) > 200 else response['content']
                    print(f"   Content preview: {content}")
                
                if response.get('tool_calls'):
                    print(f"   ✅ Function calls detected: {len(response['tool_calls'])}")
                    for call in response['tool_calls']:
                        func_name = call.get('name', call.get('function', {}).get('name', 'unknown'))
                        print(f"      📞 {func_name}")
                        
                        # Try to parse arguments
                        try:
                            if 'arguments' in call:
                                args = call['arguments']
                            elif 'function' in call and 'arguments' in call['function']:
                                args = call['function']['arguments']
                            else:
                                args = "No arguments"
                            
                            if isinstance(args, str):
                                args = json.loads(args)
                            
                            print(f"         Args: {json.dumps(args, indent=10)}")
                        except Exception as e:
                            print(f"         Args parsing error: {e}")
                else:
                    print("   ❌ No function calls detected")
                
                # Full response (for debugging)
                print(f"\n📄 Full Response:")
                print(json.dumps(response, indent=2, default=str))
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                import traceback
                traceback.print_exc()
        
        db.close()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_model_behavior()) 