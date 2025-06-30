#!/usr/bin/env python3
"""
Test script for AI Module Phase 1 Implementation
Verifies that the AI module foundation is working correctly
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_ai_module_imports():
    """Test that AI module imports work correctly"""
    print("🧪 Testing AI module imports...")
    
    try:
        from app.ai import ai_router, __version__, AI_MODULE_CONFIG
        print(f"✅ AI module imported successfully")
        print(f"   Version: {__version__}")
        print(f"   Phase: {AI_MODULE_CONFIG['phase']}")
        print(f"   Status: {AI_MODULE_CONFIG['status']}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import AI module: {e}")
        return False

def test_ai_dependencies():
    """Test AI dependencies and health checks"""
    print("\n🧪 Testing AI dependencies...")
    
    try:
        from app.ai.dependencies import (
            get_ai_model_info,
            check_ai_system_health,
            get_ai_config
        )
        
        # Test model info (should handle errors gracefully)
        model_info = get_ai_model_info()
        print(f"✅ Model info: {model_info}")
        
        # Test health check (should handle errors gracefully)
        health = check_ai_system_health()
        print(f"✅ Health check: {list(health.keys())}")
        
        # Test config
        config = get_ai_config()
        print(f"✅ Config loaded: {len(config)} settings")
        
        return True
    except Exception as e:
        print(f"❌ Dependencies test failed: {e}")
        return False

def test_ai_schemas():
    """Test AI schemas (Pydantic models)"""
    print("\n🧪 Testing AI schemas...")
    
    try:
        from app.ai.schemas.chat import (
            StartChatRequest,
            SendMessageRequest,
            ChatResponse
        )
        from app.ai.schemas.health import (
            HealthStatus,
            SystemHealth,
            ComponentStatus
        )
        
        # Test creating schema instances
        chat_request = StartChatRequest(title="Test Chat")
        print(f"✅ Chat request schema: {chat_request.title}")
        
        # Test enums
        assert HealthStatus.HEALTHY == "healthy"
        assert ComponentStatus.ERROR == "error"
        print("✅ Health schemas and enums working")
        
        return True
    except Exception as e:
        print(f"❌ Schemas test failed: {e}")
        return False

def test_ai_base_agents():
    """Test AI base agent classes"""
    print("\n🧪 Testing AI base agents...")
    
    try:
        from app.ai.agents.base import (
            BaseAgent,
            ConversationalAgent,
            ToolCapableAgent,
            AgentStatus,
            AgentResponse
        )
        
        # Test agent status enum
        assert AgentStatus.THINKING == "thinking"
        print("✅ Agent status enum working")
        
        # Test agent response
        response = AgentResponse(
            response="Test response",
            status=AgentStatus.WAITING
        )
        response_dict = response.to_dict()
        assert response_dict["response"] == "Test response"
        assert response_dict["status"] == "waiting"
        print("✅ Agent response serialization working")
        
        return True
    except Exception as e:
        print(f"❌ Base agents test failed: {e}")
        return False

def test_ai_router():
    """Test AI router configuration"""
    print("\n🧪 Testing AI router...")
    
    try:
        from app.ai.router import ai_router
        from fastapi import FastAPI
        
        # Test router configuration
        assert ai_router.prefix == "/api/ai"
        assert "AI System" in ai_router.tags
        
        # Test that we can add router to FastAPI app
        test_app = FastAPI()
        test_app.include_router(ai_router)
        
        print("✅ AI router configuration working")
        print(f"   Prefix: {ai_router.prefix}")
        print(f"   Tags: {ai_router.tags}")
        
        return True
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

def test_directory_structure():
    """Test that all required directories and files exist"""
    print("\n🧪 Testing directory structure...")
    
    required_files = [
        "app/ai/__init__.py",
        "app/ai/router.py", 
        "app/ai/dependencies.py",
        "app/ai/agents/__init__.py",
        "app/ai/agents/base.py",
        "app/ai/services/__init__.py",
        "app/ai/providers/__init__.py",
        "app/ai/tools/__init__.py",
        "app/ai/schemas/__init__.py",
        "app/ai/schemas/chat.py",
        "app/ai/schemas/health.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print(f"✅ All {len(required_files)} required files exist")
        return True

def main():
    """Run all tests"""
    print("🚀 AI Module Phase 1 Test Suite")
    print("=" * 50)
    
    tests = [
        test_directory_structure,
        test_ai_module_imports,
        test_ai_dependencies,
        test_ai_schemas,
        test_ai_base_agents,
        test_ai_router
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AI module foundation is ready.")
        print("\n📋 Next steps:")
        print("   1. Integrate AI router into main.py")
        print("   2. Begin Phase 2: Service layer implementation")
        print("   3. Refactor existing AI agents")
        print("   4. Implement chat functionality")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 