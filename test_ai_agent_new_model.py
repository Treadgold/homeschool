#!/usr/bin/env python3
"""
Test AI Agent with New Enhanced Event Model
Comprehensive testing of AI agent functionality with all new event features
"""

import sys
import os
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Event, User, Child, Booking, TicketType, EventSession, EventCustomField, EventAddOn, EventDiscount, DynamicFieldDefinition, DynamicFieldValue
from app.ai_agent import EventCreationAgent
from app.ai_tools import DynamicEventTools
from app.ai_providers import ai_manager
from app.passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AIAgentNewModelTester:
    """Comprehensive tester for AI agent with new event model"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.test_user = None
        self.agent = None
        self.test_results = {}
        
    def setup_test_environment(self):
        """Set up test environment with required data"""
        print("🔧 Setting up test environment...")
        
        # Create test user
        self.test_user = self._create_test_user()
        
        # Initialize AI agent
        self.agent = EventCreationAgent(self.db, self.test_user.id)
        
        print("✅ Test environment ready")
    
    def _create_test_user(self) -> User:
        """Create a test user for AI agent testing"""
        email = "ai_test_user@example.com"
        
        # Check if user exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            return existing_user
        
        # Create new test user
        user = User(
            email=email,
            hashed_password=pwd_context.hash("testpass123"),
            first_name="AI",
            last_name="Tester",
            email_confirmed=True,
            is_admin=True,
            auth_provider='email'
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        print(f"✅ Created test user: {email}")
        return user
    
    async def test_ai_agent_initialization(self):
        """Test AI agent initialization with new model"""
        print("\n🧪 Testing AI Agent Initialization")
        print("-" * 40)
        
        try:
            # Test agent creation
            agent = EventCreationAgent(self.db, self.test_user.id)
            print("✅ AI Agent initialized successfully")
            
            # Test conversation start
            conversation = await agent.start_conversation()
            print(f"✅ Conversation started: {conversation['conversation_id']}")
            
            self.test_results["initialization"] = {
                "success": True,
                "conversation_id": conversation['conversation_id']
            }
            
        except Exception as e:
            print(f"❌ AI Agent initialization failed: {e}")
            self.test_results["initialization"] = {"success": False, "error": str(e)}
    
    async def test_dynamic_tools_with_new_model(self):
        """Test dynamic tools with enhanced event model"""
        print("\n🛠️ Testing Dynamic Tools with New Event Model")
        print("-" * 40)
        
        try:
            # Initialize tools
            tools = DynamicEventTools(self.db, self.test_user.id)
            
            # Test tool definitions
            tool_definitions = tools.get_tool_definitions()
            print(f"✅ Generated {len(tool_definitions)} tool definitions")
            
            # Check for enhanced event fields
            create_event_tool = next((t for t in tool_definitions if t['name'] == 'create_event_draft'), None)
            if create_event_tool:
                properties = create_event_tool['parameters']['properties']
                enhanced_fields = [
                    'subtitle', 'short_description', 'venue_type', 'event_format',
                    'venue_name', 'venue_address', 'online_meeting_url', 'category',
                    'what_to_bring', 'dress_code', 'accessibility_info', 'parking_info',
                    'early_bird_discount', 'group_discount', 'member_discount',
                    'image_url', 'banner_image_url', 'event_agenda', 'speaker_info'
                ]
                
                found_enhanced_fields = []
                for field in enhanced_fields:
                    if field in properties:
                        found_enhanced_fields.append(field)
                
                print(f"✅ Found {len(found_enhanced_fields)}/{len(enhanced_fields)} enhanced fields:")
                for field in found_enhanced_fields:
                    print(f"   - {field}")
                
                self.test_results["dynamic_tools"] = {
                    "success": True,
                    "tool_count": len(tool_definitions),
                    "enhanced_fields_found": len(found_enhanced_fields),
                    "enhanced_fields": found_enhanced_fields
                }
            else:
                print("❌ create_event_draft tool not found")
                self.test_results["dynamic_tools"] = {"success": False, "error": "Tool not found"}
                
        except Exception as e:
            print(f"❌ Dynamic tools test failed: {e}")
            self.test_results["dynamic_tools"] = {"success": False, "error": str(e)}
    
    async def test_event_creation_with_enhanced_fields(self):
        """Test creating events with enhanced fields"""
        print("\n🎯 Testing Event Creation with Enhanced Fields")
        print("-" * 40)
        
        try:
            tools = DynamicEventTools(self.db, self.test_user.id)
            
            # Test creating event with enhanced fields
            enhanced_event_data = {
                "title": "Advanced Science Workshop",
                "subtitle": "Hands-on experiments for curious minds",
                "short_description": "Interactive science workshop with real experiments",
                "description": "Join us for an exciting science workshop where children will conduct real experiments, learn about chemical reactions, and discover the wonders of physics through hands-on activities.",
                "date": (datetime.now() + timedelta(days=7)).isoformat(),
                "venue_type": "physical",
                "event_format": "workshop",
                "venue_name": "Community Science Center",
                "venue_address": "123 Science Street, Auckland",
                "category": "science",
                "max_participants": 15,
                "min_age": 8,
                "max_age": 12,
                "cost": 35.00,
                "what_to_bring": "Lab coat, safety glasses, and enthusiasm for learning",
                "dress_code": "Comfortable clothes that can get messy",
                "accessibility_info": "Wheelchair accessible, sign language interpreter available on request",
                "parking_info": "Free parking available on site",
                "early_bird_discount": 10.0,
                "image_url": "https://example.com/science-workshop.jpg",
                "event_agenda": "10:00 AM - Welcome and safety briefing\n10:30 AM - Chemistry experiments\n11:30 AM - Physics demonstrations\n12:30 PM - Lunch break\n1:30 PM - Biology exploration\n2:30 PM - Wrap-up and take-home experiments",
                "speaker_info": "Dr. Sarah Johnson, PhD in Chemistry with 10+ years teaching experience",
                "contact_name": "Dr. Sarah Johnson",
                "contact_email": "sarah@sciencecenter.org",
                "contact_phone": "+64 9 123 4567"
            }
            
            # Create event draft
            result = await tools.create_event_draft(**enhanced_event_data)
            
            if result.get("success"):
                print("✅ Enhanced event draft created successfully")
                print(f"📋 Event data: {json.dumps(result['event_data'], indent=2, default=str)}")
                
                # Validate the event data
                validation_result = await tools.validate_event_data(result['event_data'])
                if validation_result.get("valid"):
                    print("✅ Event data validation passed")
                else:
                    print(f"⚠️ Validation issues: {validation_result.get('issues', [])}")
                
                self.test_results["enhanced_event_creation"] = {
                    "success": True,
                    "event_data": result['event_data'],
                    "validation": validation_result
                }
            else:
                print(f"❌ Event creation failed: {result.get('error')}")
                self.test_results["enhanced_event_creation"] = {"success": False, "error": result.get('error')}
                
        except Exception as e:
            print(f"❌ Enhanced event creation test failed: {e}")
            self.test_results["enhanced_event_creation"] = {"success": False, "error": str(e)}
    
    async def test_ai_conversation_with_enhanced_model(self):
        """Test AI conversation with enhanced event model"""
        print("\n💬 Testing AI Conversation with Enhanced Model")
        print("-" * 40)
        
        try:
            # Start conversation
            conversation = await self.agent.start_conversation()
            conversation_id = conversation['conversation_id']
            
            # Test message processing with enhanced event details
            test_message = """
            I want to create a comprehensive art workshop for children. It should be:
            - Title: "Creative Art Studio"
            - Subtitle: "Unleash your child's artistic potential"
            - Date: Next Saturday at 2 PM
            - Location: Auckland Art Gallery
            - Format: In-person workshop
            - Age range: 6-12 years
            - Cost: $45 per child
            - Include early bird discount of 15%
            - Max 20 participants
            - What to bring: Art supplies provided, but bring old clothes
            - Agenda: 2 hours of painting, drawing, and sculpture
            - Contact: Jane Smith, jane@artstudio.co.nz
            """
            
            # Process the message
            response = await self.agent.process_message(conversation_id, test_message)
            
            if response.get("success"):
                print("✅ AI conversation processed successfully")
                print(f"🤖 AI Response: {response.get('response', 'No response')}")
                
                # Check if event preview was generated
                if response.get("event_preview"):
                    print("✅ Event preview generated")
                    preview_fields = list(response["event_preview"].keys())
                    print(f"📋 Preview fields: {preview_fields}")
                
                self.test_results["ai_conversation"] = {
                    "success": True,
                    "response": response.get('response'),
                    "event_preview": response.get('event_preview') is not None,
                    "preview_fields": list(response.get("event_preview", {}).keys())
                }
            else:
                print(f"❌ AI conversation failed: {response.get('error')}")
                self.test_results["ai_conversation"] = {"success": False, "error": response.get('error')}
                
        except Exception as e:
            print(f"❌ AI conversation test failed: {e}")
            self.test_results["ai_conversation"] = {"success": False, "error": str(e)}
    
    async def test_dynamic_field_integration(self):
        """Test dynamic field integration with AI tools"""
        print("\n🔧 Testing Dynamic Field Integration")
        print("-" * 40)
        
        try:
            # Create a dynamic field
            dynamic_field = DynamicFieldDefinition(
                target_model="Event",
                field_name="instructor_certification",
                field_type="string",
                field_label="Instructor Certification",
                description="Required certification level for instructor",
                is_required=False,
                created_by=self.test_user.id
            )
            self.db.add(dynamic_field)
            self.db.commit()
            
            # Test tools with dynamic field
            tools = DynamicEventTools(self.db, self.test_user.id)
            tool_definitions = tools.get_tool_definitions()
            
            create_event_tool = next((t for t in tool_definitions if t['name'] == 'create_event_draft'), None)
            if create_event_tool:
                properties = create_event_tool['parameters']['properties']
                
                if 'instructor_certification' in properties:
                    print("✅ Dynamic field integrated into AI tools")
                    
                    # Test creating event with dynamic field
                    event_with_dynamic = {
                        "title": "Test Event with Dynamic Field",
                        "date": (datetime.now() + timedelta(days=5)).isoformat(),
                        "instructor_certification": "Level 2 Teaching Certificate"
                    }
                    
                    result = await tools.create_event_draft(**event_with_dynamic)
                    if result.get("success"):
                        print("✅ Event created with dynamic field")
                        self.test_results["dynamic_fields"] = {
                            "success": True,
                            "field_integrated": True,
                            "event_created": True
                        }
                    else:
                        print(f"❌ Failed to create event with dynamic field: {result.get('error')}")
                        self.test_results["dynamic_fields"] = {"success": False, "error": result.get('error')}
                else:
                    print("❌ Dynamic field not found in tool properties")
                    self.test_results["dynamic_fields"] = {"success": False, "error": "Field not integrated"}
            else:
                print("❌ create_event_draft tool not found")
                self.test_results["dynamic_fields"] = {"success": False, "error": "Tool not found"}
                
        except Exception as e:
            print(f"❌ Dynamic field test failed: {e}")
            self.test_results["dynamic_fields"] = {"success": False, "error": str(e)}
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 AI AGENT NEW MODEL TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get("success"))
        failed_tests = total_tests - passed_tests
        
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            if result.get("success"):
                print(f"   ✅ {test_name}: PASSED")
                if "enhanced_fields" in result:
                    print(f"      Found {result['enhanced_fields_found']} enhanced fields")
                if "preview_fields" in result:
                    print(f"      Generated {len(result['preview_fields'])} preview fields")
            else:
                print(f"   ❌ {test_name}: FAILED")
                print(f"      Error: {result.get('error', 'Unknown error')}")
        
        # Save detailed results
        with open("ai_agent_new_model_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: ai_agent_new_model_test_results.json")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! AI agent is working perfectly with the new event model.")
        else:
            print(f"\n⚠️ {failed_tests} test(s) failed. Please review the errors above.")
        
        print("="*60)
    
    async def run_all_tests(self):
        """Run all AI agent tests"""
        print("🚀 Starting AI Agent New Model Tests")
        print("This will test the AI agent with all enhanced event model features")
        print("-" * 60)
        
        # Setup
        self.setup_test_environment()
        
        # Run tests
        await self.test_ai_agent_initialization()
        await self.test_dynamic_tools_with_new_model()
        await self.test_event_creation_with_enhanced_fields()
        await self.test_ai_conversation_with_enhanced_model()
        await self.test_dynamic_field_integration()
        
        # Print summary
        self.print_test_summary()
        
        # Cleanup
        self.db.close()

async def main():
    """Main test runner"""
    tester = AIAgentNewModelTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 