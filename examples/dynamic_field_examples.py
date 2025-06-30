"""
Practical Examples: Dynamic Fields & Auto-Updating AI Tools
Answers to user questions with concrete examples
"""

from sqlalchemy.orm import Session
from app.models import Event, TicketType, DynamicFieldDefinition, User
from app.ai.tools.dynamic_tools import DynamicToolGenerator, DynamicToolExecutor

# ================================================================================
# QUESTION 1: Can we handle dynamic fields like "staff_id_number"?
# ================================================================================

def example_1_dynamic_fields(db: Session, user_id: int):
    """
    Example: Adding a staff_id_number field to Events without touching the core schema
    """
    
    print("🎯 EXAMPLE 1: Adding Dynamic Fields to Events")
    print("=" * 60)
    
    # 1. Add a dynamic field definition
    staff_id_field = DynamicFieldDefinition(
        target_model="Event",
        field_name="staff_id_number",
        field_type="string",
        field_label="Staff ID Number",
        description="Internal staff member ID responsible for this event",
        is_required=True,
        validation_rules={"pattern": "^STAFF[0-9]{4}$"},  # Must be STAFF#### format
        created_by=user_id
    )
    db.add(staff_id_field)
    db.commit()
    
    # 2. Create an event and set the dynamic field
    event = Event(
        title="Advanced Python Workshop",
        description="Learn advanced Python concepts",
        created_by=user_id
    )
    db.add(event)
    db.commit()
    
    # 3. Set the dynamic field value
    event.set_dynamic_field("staff_id_number", "STAFF1234")
    
    # 4. Access the dynamic field
    print(f"✅ Event created: {event.title}")
    print(f"✅ Staff ID: {event.dynamic_fields.get('staff_id_number')}")
    
    # 5. Add more complex dynamic fields
    complex_field = DynamicFieldDefinition(
        target_model="Event",
        field_name="special_requirements",
        field_type="json",
        field_label="Special Requirements",
        description="Complex requirements data",
        created_by=user_id
    )
    db.add(complex_field)
    db.commit()
    
    # Set complex data
    event.set_dynamic_field("special_requirements", {
        "equipment": ["projector", "microphone", "extension_cables"],
        "accessibility": {
            "wheelchair_accessible": True,
            "sign_language_interpreter": False,
            "hearing_loop": True
        },
        "catering": {
            "dietary_restrictions": ["vegetarian", "gluten_free"],
            "meal_count": 25
        }
    })
    
    print(f"✅ Complex requirements: {event.dynamic_fields.get('special_requirements')}")
    
    return event

# ================================================================================
# QUESTION 2: Do AI tools update automatically?
# ================================================================================

async def example_2_auto_updating_ai_tools(db: Session, user_id: int):
    """
    Example: AI tools automatically detecting and using new dynamic fields
    """
    
    print("\n🤖 EXAMPLE 2: Auto-Updating AI Tools")
    print("=" * 60)
    
    # 1. Generate AI tools based on current schema
    tool_generator = DynamicToolGenerator(db, user_id)
    tools_before = tool_generator.generate_dynamic_tools()
    
    print(f"🔧 Tools available before adding dynamic fields: {len(tools_before)}")
    for tool in tools_before[:3]:  # Show first 3
        print(f"   - {tool['name']}: {tool['description']}")
    
    # 2. Add new dynamic fields
    new_fields = [
        {
            "target_model": "Event",
            "field_name": "instructor_certification",
            "field_type": "string",
            "field_label": "Instructor Certification",
            "description": "Required certification level for instructor"
        },
        {
            "target_model": "TicketType", 
            "field_name": "membership_discount",
            "field_type": "decimal",
            "field_label": "Membership Discount %",
            "description": "Discount percentage for members"
        }
    ]
    
    for field_data in new_fields:
        field_def = DynamicFieldDefinition(**field_data, created_by=user_id)
        db.add(field_def)
    db.commit()
    
    # 3. Generate tools again - they now include the new fields!
    tools_after = tool_generator.generate_dynamic_tools()
    
    print(f"🔧 Tools available after adding dynamic fields: {len(tools_after)}")
    
    # 4. Show how the create_event tool now includes new fields
    create_event_tool = next(tool for tool in tools_after if tool['name'] == 'create_event')
    properties = create_event_tool['parameters']['properties']
    
    print(f"\n📝 create_event tool now includes these fields:")
    for field_name, field_schema in properties.items():
        if field_name in ['instructor_certification', 'staff_id_number', 'special_requirements']:
            print(f"   ✨ {field_name}: {field_schema['description']}")
    
    # 5. Use the AI tool to create an event with dynamic fields
    tool_executor = DynamicToolExecutor(db, user_id)
    
    result = await tool_executor.execute_dynamic_tool("create_event", {
        "title": "AI-Generated Workshop",
        "description": "Created by AI with dynamic fields",
        "instructor_certification": "ADVANCED_PYTHON_CERT",
        "staff_id_number": "STAFF5678",
        "special_requirements": {
            "room_setup": "classroom_style",
            "tech_requirements": ["laptop_per_student", "wifi_access"]
        }
    })
    
    print(f"\n🎉 AI tool result: {result}")
    
    return tools_after

# ================================================================================
# COMPLETE WORKFLOW EXAMPLE
# ================================================================================

async def complete_workflow_example(db: Session, user_id: int):
    """
    Complete example showing the full dynamic system in action
    """
    
    print("\n🚀 COMPLETE WORKFLOW: Dynamic Event Creation")
    print("=" * 60)
    
    # 1. User requests a new field type through AI
    tool_executor = DynamicToolExecutor(db, user_id)
    
    # AI tool adds the dynamic field
    field_result = await tool_executor.execute_dynamic_tool("add_dynamic_field", {
        "target_model": "Event",
        "field_name": "sustainability_rating",
        "field_type": "integer",
        "field_label": "Sustainability Rating",
        "description": "Environmental sustainability rating (1-5 stars)",
        "validation_rules": {"min": 1, "max": 5}
    })
    
    print(f"✅ Dynamic field added: {field_result}")
    
    # 2. AI tools automatically update to include this field
    tool_generator = DynamicToolGenerator(db, user_id)
    updated_tools = tool_generator.generate_dynamic_tools()
    
    # 3. Create an event using the new field
    event_result = await tool_executor.execute_dynamic_tool("create_event", {
        "title": "Eco-Friendly Coding Workshop",
        "description": "Learn to code while minimizing environmental impact",
        "sustainability_rating": 5,  # This is our new dynamic field!
        "staff_id_number": "STAFF9999"
    })
    
    print(f"✅ Event created with dynamic fields: {event_result}")
    
    # 4. Query events with dynamic fields
    events_with_dynamic = db.query(Event).all()
    for event in events_with_dynamic:
        dynamic_data = event.dynamic_fields
        if dynamic_data:
            print(f"📊 {event.title}: {dynamic_data}")

# ================================================================================
# COMPARISON WITH CURRENT SYSTEM
# ================================================================================

def comparison_with_current_system():
    """
    Show the difference between current and enhanced systems
    """
    
    print("\n📊 COMPARISON: Current vs Enhanced System")
    print("=" * 60)
    
    current_system = {
        "Custom Registration Fields": "✅ Available via EventCustomField",
        "Dynamic Event Properties": "❌ Requires migration",
        "AI Tool Updates": "❌ Manual code updates required",
        "Real-time Field Addition": "❌ Not possible",
        "Complex Field Types": "⚠️  Limited to registration forms"
    }
    
    enhanced_system = {
        "Custom Registration Fields": "✅ Enhanced with better UI",
        "Dynamic Event Properties": "✅ Add any field to any model",
        "AI Tool Updates": "✅ Automatic schema detection",
        "Real-time Field Addition": "✅ No downtime required",
        "Complex Field Types": "✅ JSON, validation, conditional logic"
    }
    
    print("CURRENT SYSTEM:")
    for feature, status in current_system.items():
        print(f"  {status} {feature}")
    
    print("\nENHANCED SYSTEM:")
    for feature, status in enhanced_system.items():
        print(f"  {status} {feature}")

# ================================================================================
# USAGE SCENARIOS
# ================================================================================

def usage_scenarios():
    """
    Real-world scenarios where dynamic fields would be useful
    """
    
    scenarios = [
        {
            "scenario": "School District Integration",
            "fields": {
                "school_district_id": "string",
                "curriculum_standards": "json",
                "grade_level_mapping": "json"
            },
            "ai_conversation": "I need to integrate with Wellington School District. They require tracking curriculum standards and grade mappings."
        },
        {
            "scenario": "Corporate Training",
            "fields": {
                "employee_id": "string", 
                "department": "string",
                "manager_approval": "boolean",
                "training_credits": "decimal"
            },
            "ai_conversation": "We're running corporate training events. Need to track employee IDs, departments, and training credits."
        },
        {
            "scenario": "International Events",
            "fields": {
                "visa_requirements": "json",
                "language_preferences": "string",
                "currency_local": "string",
                "time_zone_local": "string"
            },
            "ai_conversation": "I'm organizing events in multiple countries. Need to handle visas, languages, and local currencies."
        }
    ]
    
    print("\n🌟 REAL-WORLD USAGE SCENARIOS")
    print("=" * 60)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['scenario']}")
        print(f"   User says: \"{scenario['ai_conversation']}\"")
        print(f"   AI adds these dynamic fields:")
        for field_name, field_type in scenario['fields'].items():
            print(f"     - {field_name} ({field_type})")

if __name__ == "__main__":
    # This would be run in a real database session
    print("🎯 DYNAMIC FIELD SYSTEM EXAMPLES")
    print("Run these examples with a real database session:")
    print("1. example_1_dynamic_fields(db, user_id)")
    print("2. await example_2_auto_updating_ai_tools(db, user_id)")
    print("3. await complete_workflow_example(db, user_id)")
    
    comparison_with_current_system()
    usage_scenarios() 