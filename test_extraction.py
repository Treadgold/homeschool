#!/usr/bin/env python3
"""
Test Enhanced Information Extraction and Tool Usage
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai_assistant import ThinkingEventAgent
from app.database import get_db

async def test_extraction():
    """Test information extraction from natural language"""
    
    print("🧪 Testing Enhanced Information Extraction & Tool Usage")
    print("=" * 60)
    
    # Test message
    test_message = "I need a birthday party event for my 10 year old son James on August 12th at 914 South Head Road in South Head, Auckland. We need people there by 11am for cake and lunch is at 12."
    
    print(f"📝 Test Message:")
    print(f"   {test_message}")
    print()
    
    # Test extraction
    agent = ThinkingEventAgent()
    extracted = agent._extract_event_information(test_message)
    
    print("🔍 Extracted Information:")
    for key, value in extracted.items():
        print(f"   {key}: {value}")
    print()
    
    # Test with database
    try:
        db = next(get_db())
        print("✅ Database connection successful")
        
        # Test full chat flow
        print("\n🎯 Testing Full Chat Flow:")
        response = await agent.chat(
            user_message=test_message,
            conversation_history=[],
            user_id=1,  # Admin user
            db=db
        )
        
        print(f"Response Type: {response.get('type')}")
        print(f"Response: {response.get('response', '')[:200]}...")
        print(f"Has Event Preview: {bool(response.get('event_preview'))}")
        print(f"Has Tool Results: {bool(response.get('tool_results'))}")
        
        if response.get('event_preview'):
            print("\n📋 Event Preview:")
            preview = response['event_preview']
            for key, value in preview.items():
                print(f"   {key}: {value}")
        
        if response.get('tool_results'):
            print(f"\n🛠️  Tool Results: {len(response['tool_results'])} tools executed")
            for tool in response['tool_results']:
                print(f"   - {tool.get('function')}: {tool.get('result', {}).get('status', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_extraction()) 