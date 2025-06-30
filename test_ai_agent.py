#!/usr/bin/env python3
"""
Test script for diagnosing AI agent issues
Run this to test the AI agent independently from the web interface
"""

import asyncio
import logging
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.ai_assistant import ThinkingEventAgent
from app.ai_providers import ai_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_ai_agent():
    """Test the AI agent with a simple message"""
    
    print("🧪 Testing AI Agent...")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    # Test message
    test_message = "I need a birthday party event for my 10 year old son James."
    user_id = 2  # Admin user from your logs
    
    try:
        # Test AI provider first
        print("1. Testing AI Provider...")
        provider = ai_manager.get_current_provider()
        config = ai_manager.get_current_model_config()
        
        print(f"   Provider: {provider.__class__.__name__}")
        print(f"   Model: {config.model_name if config else 'Unknown'}")
        print(f"   Endpoint: {config.endpoint_url if config else 'Unknown'}")
        
        # Test simple chat completion
        simple_response = await provider.chat_completion([
            {"role": "user", "content": "Say hello"}
        ])
        
        print(f"   Simple test result: {simple_response.get('content', 'NO CONTENT')[:100]}...")
        
        print("\n2. Testing AI Agent...")
        
        # Initialize agent
        agent = ThinkingEventAgent()
        
        # Test with the user's message
        response = await agent.chat(
            user_message=test_message,
            conversation_history=[],
            user_id=user_id,
            db=db
        )
        
        print(f"   Response type: {response.get('type')}")
        print(f"   Response content: {response.get('response', 'NO RESPONSE')}")
        print(f"   Has tool results: {bool(response.get('tool_results'))}")
        print(f"   Has event preview: {bool(response.get('event_preview'))}")
        
        if response.get('tool_results'):
            print(f"   Tool results: {response['tool_results']}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ai_agent()) 