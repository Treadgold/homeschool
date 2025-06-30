"""
Pytest configuration and fixtures for the Homeschool Application
Provides comprehensive test setup for AI Agent, database, and service testing
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import User, Event, ChatConversation, ChatMessage, AgentSession
from app.ai_providers import AIProviderManager, ModelConfig, MockAIProvider
from app.ai_tools import DynamicEventTools
from app.ai_agent import EventCreationAgent
from app.ai_assistant import ThinkingEventAgent


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url():
    """Provide test database URL"""
    return "sqlite:///./test_homeschool.db"


@pytest.fixture(scope="function")
def test_db_engine(test_database_url):
    """Create a test database engine"""
    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_user(test_db_session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_admin=False
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(test_db_session):
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        hashed_password="hashed_password", 
        is_admin=True
    )
    test_db_session.add(admin)
    test_db_session.commit()
    test_db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def test_event(test_db_session, test_user):
    """Create a test event"""
    event = Event(
        title="Test Event",
        description="Test description",
        location="Test Location",
        max_pupils=10,
        cost=50.0,
        event_type="homeschool",
        user_id=test_user.id
    )
    test_db_session.add(event)
    test_db_session.commit()
    test_db_session.refresh(event)
    return event


@pytest.fixture(scope="function")
def mock_ai_provider():
    """Create a mock AI provider for testing"""
    config = ModelConfig(
        provider="mock",
        model_name="test-model",
        endpoint_url="http://localhost:11434",
        max_tokens=1000,
        temperature=0.7
    )
    return MockAIProvider(config)


@pytest.fixture(scope="function")
def ai_provider_manager_mock(mock_ai_provider):
    """Create a mock AI provider manager"""
    with patch('app.ai_providers.ai_manager') as mock_manager:
        mock_manager.get_current_provider.return_value = mock_ai_provider
        mock_manager.get_current_model_config.return_value = mock_ai_provider.config
        yield mock_manager


@pytest.fixture(scope="function")
def dynamic_event_tools(test_db_session, test_user):
    """Create dynamic event tools for testing"""
    return DynamicEventTools(test_db_session, test_user.id)


@pytest.fixture(scope="function")
def event_creation_agent(test_db_session, test_user):
    """Create an event creation agent for testing"""
    return EventCreationAgent(test_db_session, test_user.id)


@pytest.fixture(scope="function")
def thinking_event_agent():
    """Create a thinking event agent for testing"""
    return ThinkingEventAgent()


@pytest.fixture(scope="function")
def test_conversation(test_db_session, test_user):
    """Create a test conversation"""
    conversation = ChatConversation(
        id="test-conversation-id",
        user_id=test_user.id,
        title="Test Conversation",
        status="active"
    )
    test_db_session.add(conversation)
    test_db_session.commit()
    test_db_session.refresh(conversation)
    return conversation


@pytest.fixture(scope="function")
def test_chat_message(test_db_session, test_conversation):
    """Create a test chat message"""
    message = ChatMessage(
        id="test-message-id",
        conversation_id=test_conversation.id,
        role="user",
        content="Test message"
    )
    test_db_session.add(message)
    test_db_session.commit()
    test_db_session.refresh(message)
    return message


@pytest.fixture(scope="function")
def test_agent_session(test_db_session, test_conversation):
    """Create a test agent session"""
    session = AgentSession(
        id="test-session-id",
        conversation_id=test_conversation.id,
        agent_type="event_creator",
        current_step="active",
        plan={"goal": "test"},
        memory={},
        status="waiting",
        tools_used=[]
    )
    test_db_session.add(session)
    test_db_session.commit()
    test_db_session.refresh(session)
    return session


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up test files after each test"""
    yield
    # Clean up any test database files
    test_files = ["test_homeschool.db", "test_homeschool.db-journal"]
    for file in test_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except OSError:
                pass


# Utility functions for testing
def create_test_tool_response(success=True, data=None, error=None):
    """Create a standardized test tool response"""
    if success:
        return {
            "success": True,
            "data": data or {},
            "message": "Test tool executed successfully"
        }
    else:
        return {
            "success": False,
            "error": error or "Test error",
            "data": None
        }


def create_test_ai_response(content="Test response", tool_calls=None):
    """Create a standardized test AI response"""
    return {
        "content": content,
        "tool_calls": tool_calls or [],
        "provider": "mock",
        "model": "test-model"
    }


# Test markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.ai_agent = pytest.mark.ai_agent
pytest.mark.function_calling = pytest.mark.function_calling
pytest.mark.slow = pytest.mark.slow
pytest.mark.requires_ollama = pytest.mark.requires_ollama
pytest.mark.requires_db = pytest.mark.requires_db 