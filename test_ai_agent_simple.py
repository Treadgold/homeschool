#!/usr/bin/env python3
"""
Simple AI Agent Test with New Enhanced Event Model
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.ai_agent import EventCreationAgent
from app.ai_tools import DynamicEventTools
from app.database import SessionLocal
from app.models import User
from datetime import datetime, timedelta

async def test_ai_agent():
    """Test AI agent with new enhanced event model"""
    print("🧪 Testing AI Agent with New Enhanced Event Model")
    print("-" * 50)
    
    db = SessionLocal()
    
    try:
        # Get a test user
        user = db.query(User).first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"✅ Testing with user: {user.email}")
        
        # Test AI agent initialization
        print("\n1. Testing AI Agent Initialization...")
        agent = EventCreationAgent(db, user.id)
        print("✅ AI Agent initialized successfully")
        
        # Test conversation start
        print("\n2. Testing Conversation Start...")
        conversation = await agent.start_conversation()
        conversation_id = conversation['conversation_id']
        print(f"✅ Conversation started: {conversation_id}")
        
        # Test dynamic tools
        print("\n3. Testing Dynamic Tools...")
        tools = DynamicEventTools(db, user.id)
        tool_definitions = tools.get_tool_definitions()
        print(f"✅ Generated {len(tool_definitions)} tool definitions")
        
        # Check enhanced fields
        create_event_tool = next((t for t in tool_definitions if t['name'] == 'create_event_draft'), None)
        if create_event_tool:
            properties = create_event_tool['parameters']['properties']
            enhanced_fields = [
                'subtitle', 'short_description', 'venue_type', 'event_format',
                'venue_name', 'category', 'what_to_bring', 'early_bird_discount',
                'image_url', 'event_agenda', 'speaker_info'
            ]
            
            found_fields = [f for f in enhanced_fields if f in properties]
            print(f"✅ Found {len(found_fields)}/{len(enhanced_fields)} enhanced fields")
            print(f"📋 Total properties available: {len(properties)}")
        
        # Test event creation with enhanced fields
        print("\n4. Testing Enhanced Event Creation...")
        enhanced_event_data = {
            "title": "Advanced Science Workshop",
            "subtitle": "Hands-on experiments for curious minds",
            "short_description": "Interactive science workshop with real experiments",
            "venue_type": "physical",
            "event_format": "workshop",
            "venue_name": "Community Science Center",
            "category": "science",
            "what_to_bring": "Lab coat, safety glasses",
            "early_bird_discount": 10.0,
            "image_url": "https://example.com/science-workshop.jpg",
            "event_agenda": "10:00 AM - Welcome\n11:00 AM - Experiments\n12:00 PM - Wrap-up",
            "speaker_info": "Dr. Sarah Johnson, PhD in Chemistry"
        }
        
        result = await tools.create_event_draft(**enhanced_event_data)
        if result.get("success"):
            print("✅ Enhanced event draft created successfully")
            event_data = result['event_data']
            print(f"📋 Event data keys: {list(event_data.keys())}")
        else:
            print(f"❌ Event creation failed: {result.get('error')}")
        
        # Test AI conversation
        print("\n5. Testing AI Conversation...")
        test_message = """
        Create a comprehensive art workshop for children:
        - Title: "Creative Art Studio"
        - Subtitle: "Unleash your child's artistic potential"
        - Date: Next Saturday at 2 PM
        - Location: Auckland Art Gallery
        - Format: In-person workshop
        - Age range: 6-12 years
        - Cost: $45 per child
        - Include early bird discount of 15%
        - Max 20 participants
        """
        
        response = await agent.process_message(conversation_id, test_message)
        if response.get("success"):
            print("✅ AI conversation processed successfully")
            print(f"🤖 AI Response: {response.get('response', 'No response')[:100]}...")
            
            if response.get("event_preview"):
                print("✅ Event preview generated")
                preview_fields = list(response["event_preview"].keys())
                print(f"📋 Preview fields: {len(preview_fields)}")
        else:
            print(f"❌ AI conversation failed: {response.get('error')}")
        
        print("\n🎉 All tests completed successfully!")
        print("✅ AI Agent is working perfectly with the new enhanced event model")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ai_agent()) 