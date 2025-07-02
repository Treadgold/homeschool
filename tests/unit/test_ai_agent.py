"""
Unit tests for AI Agent functionality
Tests individual components without external dependencies
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Fix imports to use absolute paths
from app.models import User, Event, EventBooking  
from app.database import Base
from app.ai_agents.event_creation_agent import EventCreationAgent
from app.ai_agents.thinking_event_agent import ThinkingEventAgent
from app.ai_agents.circuit_breaker import CircuitBreaker
from app.ai_providers import MockAIProvider, ModelConfig


@pytest.mark.unit
class TestEventCreationAgent:
    """Test EventCreationAgent without external dependencies"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()
        return session
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Mock AI provider"""
        provider = AsyncMock(spec=MockAIProvider)
        provider.chat_completion.return_value = {
            "content": "Event created successfully",
            "tool_calls": [
                {
                    "name": "create_event_draft", 
                    "arguments": {
                        "title": "Test Event",
                        "description": "A test event",
                        "location": "Test Location",
                        "start_time": "2024-12-01T10:00:00Z",
                        "max_participants": 10,
                        "price": 25.0
                    }
                }
            ]
        }
        return provider
    
    @pytest.fixture
    def agent(self, mock_db_session, mock_ai_provider):
        """Create EventCreationAgent with mocked dependencies"""
        return EventCreationAgent(
            db_session=mock_db_session,
            ai_provider=mock_ai_provider,
            user_id=1
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initializes properly"""
        assert agent is not None
        assert agent.user_id == 1
        assert hasattr(agent, 'db_session')
        assert hasattr(agent, 'ai_provider')
    
    @pytest.mark.asyncio
    async def test_process_request_success(self, agent, mock_ai_provider):
        """Test successful event creation request processing"""
        user_request = "Create a birthday party for 10 kids at the park, cost $25"
        
        result = await agent.process_request(user_request)
        
        # Verify AI provider was called
        mock_ai_provider.chat_completion.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "content" in result or "tool_calls" in result
    
    @pytest.mark.asyncio
    async def test_process_request_with_tool_calls(self, agent, mock_ai_provider):
        """Test event creation with tool calls"""
        user_request = "Create a birthday party"
        
        result = await agent.process_request(user_request)
        
        # Check that tools were provided to AI
        call_args = mock_ai_provider.chat_completion.call_args
        messages, tools = call_args[0]
        
        assert isinstance(messages, list)
        assert len(messages) > 0
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == user_request
        
        # Verify tools were provided
        assert tools is not None
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    @pytest.mark.asyncio 
    async def test_process_request_error_handling(self, agent, mock_ai_provider):
        """Test error handling in request processing"""
        mock_ai_provider.chat_completion.side_effect = Exception("AI Provider Error")
        
        result = await agent.process_request("Create an event")
        
        assert isinstance(result, dict)
        assert result.get("success") is False
        assert "error" in result
    
    def test_get_tool_definitions(self, agent):
        """Test tool definitions are properly formatted"""
        tools = agent.tools.get_tool_definitions()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check first tool structure
        tool = tools[0]
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        
        function = tool["function"]
        assert "name" in function
        assert "description" in function
        assert "parameters" in function


@pytest.mark.unit
class TestThinkingEventAgent:
    """Test ThinkingEventAgent cognitive reasoning"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        # Mock a sample event query result
        sample_event = Mock()
        sample_event.id = 1
        sample_event.title = "Sample Event"
        session.query.return_value.filter.return_value.all.return_value = [sample_event]
        return session
    
    @pytest.fixture
    def mock_ai_provider(self):
        """Mock AI provider for thinking agent"""
        provider = AsyncMock(spec=MockAIProvider)
        provider.chat_completion.return_value = {
            "content": "Based on the event data, I recommend creating similar events due to high demand.",
            "reasoning": "Analysis of past events shows good attendance"
        }
        return provider
    
    @pytest.fixture
    def thinking_agent(self, mock_db_session, mock_ai_provider):
        """Create ThinkingEventAgent with mocked dependencies"""
        return ThinkingEventAgent(
            db_session=mock_db_session,
            ai_provider=mock_ai_provider,
            user_id=1
        )
    
    @pytest.mark.asyncio
    async def test_analyze_events(self, thinking_agent, mock_ai_provider):
        """Test event analysis functionality"""
        analysis = await thinking_agent.analyze_events()
        
        # Verify AI was called for analysis
        mock_ai_provider.chat_completion.assert_called_once()
        
        # Verify analysis result
        assert isinstance(analysis, dict)
        assert "content" in analysis
    
    @pytest.mark.asyncio
    async def test_make_recommendation(self, thinking_agent, mock_ai_provider):
        """Test recommendation generation"""
        context = "User wants to create children's events"
        
        recommendation = await thinking_agent.make_recommendation(context)
        
        # Verify recommendation structure
        assert isinstance(recommendation, dict)
        assert "content" in recommendation
        
        # Verify AI was called with context
        mock_ai_provider.chat_completion.assert_called_once()
        call_args = mock_ai_provider.chat_completion.call_args[0]
        messages = call_args[0]
        
        # Check that context was included
        message_content = " ".join([msg["content"] for msg in messages])
        assert context in message_content
    
    def test_agent_initialization(self, thinking_agent):
        """Test thinking agent initializes properly"""
        assert thinking_agent is not None
        assert thinking_agent.user_id == 1
        assert hasattr(thinking_agent, 'db_session')
        assert hasattr(thinking_agent, 'ai_provider')


@pytest.mark.unit  
class TestCircuitBreaker:
    """Test CircuitBreaker pattern for AI provider reliability"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker with test settings"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,  # 1 second for testing
            expected_exception=Exception
        )
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self, circuit_breaker):
        """Test circuit breaker with successful calls"""
        
        @circuit_breaker
        async def successful_function():
            return "success"
        
        result = await successful_function()
        assert result == "success"
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self, circuit_breaker):
        """Test circuit breaker opens after failure threshold"""
        
        @circuit_breaker
        async def failing_function():
            raise Exception("Test failure")
        
        # Call function to reach failure threshold
        for i in range(3):
            with pytest.raises(Exception):
                await failing_function()
        
        # Circuit should now be open
        assert circuit_breaker.state == "open"
        assert circuit_breaker.failure_count == 3
        
        # Next call should fail fast
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await failing_function()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, circuit_breaker):
        """Test circuit breaker recovery after timeout"""
        
        call_count = 0
        
        @circuit_breaker
        async def recovering_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Failure")
            return "recovered"
        
        # Cause failures to open circuit
        for i in range(3):
            with pytest.raises(Exception):
                await recovering_function()
        
        assert circuit_breaker.state == "open"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should enter half-open state and succeed
        result = await recovering_function()
        assert result == "recovered"
        assert circuit_breaker.state == "closed"
    
    def test_circuit_breaker_state_transitions(self, circuit_breaker):
        """Test circuit breaker state transitions"""
        assert circuit_breaker.state == "closed"
        
        # Simulate failures
        circuit_breaker.failure_count = 3
        circuit_breaker._update_state()
        assert circuit_breaker.state == "open"
        
        # Simulate recovery timeout
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        circuit_breaker._update_state()
        assert circuit_breaker.state == "half_open"


@pytest.mark.unit
class TestModelConfiguration:
    """Test AI model configuration and validation"""
    
    def test_model_config_creation(self):
        """Test ModelConfig creation and validation"""
        config = ModelConfig(
            provider="ollama",
            model_name="devstral:latest", 
            endpoint_url="http://localhost:11434",
            max_tokens=3000,
            temperature=0.7
        )
        
        assert config.provider == "ollama"
        assert config.model_name == "devstral:latest"
        assert config.endpoint_url == "http://localhost:11434"
        assert config.max_tokens == 3000
        assert config.temperature == 0.7
    
    def test_model_config_defaults(self):
        """Test ModelConfig with default values"""
        config = ModelConfig(
            provider="mock",
            model_name="test-model"
        )
        
        assert config.provider == "mock"
        assert config.model_name == "test-model"
        # Test that defaults are set appropriately
        assert hasattr(config, 'max_tokens')
        assert hasattr(config, 'temperature')


@pytest.mark.unit
class TestDatabaseModels:
    """Test database model functionality without database connection"""
    
    def test_user_model_creation(self):
        """Test User model instantiation"""
        user = User(
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
    
    def test_event_model_creation(self):
        """Test Event model instantiation"""  
        event = Event(
            title="Test Event",
            description="A test event",
            location="Test Location",
            organizer_id=1,
            max_participants=10,
            price=25.0
        )
        
        assert event.title == "Test Event"
        assert event.description == "A test event"
        assert event.location == "Test Location" 
        assert event.organizer_id == 1
        assert event.max_participants == 10
        assert event.price == 25.0
    
    def test_event_booking_model_creation(self):
        """Test EventBooking model instantiation"""
        booking = EventBooking(
            event_id=1,
            user_id=1,
            participants_count=2,
            total_amount=50.0
        )
        
        assert booking.event_id == 1
        assert booking.user_id == 1
        assert booking.participants_count == 2
        assert booking.total_amount == 50.0 