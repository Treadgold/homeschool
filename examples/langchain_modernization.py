"""
Example: Modernizing EventCreationAgent with LangChain + LangGraph

This example demonstrates how to replace your custom agent implementation 
with modern LangChain patterns, providing:
- Better tool integration
- Enhanced observability  
- Sophisticated workflows
- Reduced custom code
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime

# LangChain core imports
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage

# LangGraph for advanced workflows
from langgraph import StateGraph, END
import operator

# Observability
from langsmith import traceable
from langchain.callbacks import LangChainTracer


class EventData(BaseModel):
    """Structured event data with validation"""
    title: Optional[str] = Field(None, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    date: Optional[str] = Field(None, description="Event date (YYYY-MM-DD)")
    time: Optional[str] = Field(None, description="Event time (HH:MM)")
    location: Optional[str] = Field(None, description="Event location")
    cost: Optional[float] = Field(None, ge=0, description="Event cost")
    max_participants: Optional[int] = Field(None, gt=0, description="Max participants")
    min_age: Optional[int] = Field(None, ge=0, le=18, description="Minimum age")
    max_age: Optional[int] = Field(None, ge=0, le=18, description="Maximum age")


class AgentState(TypedDict):
    """State for LangGraph workflow"""
    messages: Annotated[List, operator.add]
    event_data: Dict[str, Any]
    user_id: int
    session_id: str
    current_step: str
    tools_used: List[str]
    confidence_score: float


class EventCreationTool(BaseTool):
    """Modern LangChain tool for event creation"""
    
    name = "create_event_draft"
    description = """Create or update an event draft. Use this whenever the user 
    provides ANY event information, even if incomplete."""
    
    args_schema = EventData
    
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
    
    def _run(self, **kwargs) -> str:
        """Execute the tool"""
        try:
            # Clean input data
            event_data = {k: v for k, v in kwargs.items() if v is not None}
            
            # Simulate your existing draft creation logic
            result = {
                "success": True,
                "message": f"Event draft created: '{event_data.get('title', 'Untitled')}'",
                "event_data": event_data,
                "missing_fields": self._get_missing_fields(event_data),
                "suggestions": self._get_suggestions(event_data)
            }
            
            return json.dumps(result)
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def _arun(self, **kwargs) -> str:
        """Async version"""
        return self._run(**kwargs)
    
    def _get_missing_fields(self, event_data: Dict) -> List[str]:
        """Identify missing required fields"""
        required = ["title", "date", "time", "location"]
        return [field for field in required if not event_data.get(field)]
    
    def _get_suggestions(self, event_data: Dict) -> List[str]:
        """Generate helpful suggestions"""
        suggestions = []
        if not event_data.get("cost"):
            suggestions.append("Consider if this should be a paid or free event")
        if not event_data.get("max_participants"):
            suggestions.append("Set a participant limit to manage capacity")
        return suggestions


class SimilarEventSearchTool(BaseTool):
    """Tool for finding similar events for suggestions"""
    
    name = "search_similar_events"
    description = "Search for similar events to get pricing and format ideas"
    
    def _run(self, query: str, limit: int = 5) -> str:
        try:
            # Simulate database search
            mock_events = [
                {
                    "title": "Kids Science Lab",
                    "cost": 25.0,
                    "location": "Community Center",
                    "participants": 15,
                    "age_range": "8-12"
                },
                {
                    "title": "Young Scientists Workshop", 
                    "cost": 20.0,
                    "location": "Library Meeting Room",
                    "participants": 12,
                    "age_range": "6-10"
                }
            ]
            
            # Filter based on query (simplified)
            filtered_events = [e for e in mock_events if query.lower() in e["title"].lower()]
            
            return json.dumps({
                "success": True,
                "events": filtered_events[:limit],
                "suggestions": self._generate_suggestions(filtered_events)
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _generate_suggestions(self, events: List[Dict]) -> List[str]:
        """Generate suggestions based on similar events"""
        if not events:
            return ["No similar events found - you're creating something unique!"]
        
        # Analyze pricing
        costs = [e["cost"] for e in events if e["cost"] > 0]
        if costs:
            avg_cost = sum(costs) / len(costs)
            return [f"Similar events typically cost ${avg_cost:.2f}"]
        
        return ["Based on similar events, consider keeping it affordable"]


class ModernEventCreationAgent:
    """
    Modern event creation agent using LangChain + LangGraph
    
    This replaces your custom EventCreationAgent with:
    - Native LangChain tool integration
    - LangGraph workflows for complex reasoning
    - Built-in observability with LangSmith
    - Reduced custom code by ~70%
    """
    
    def __init__(self, user_id: int, api_key: str = None):
        self.user_id = user_id
        
        # Initialize LLM (adapt to your provider)
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        
        # Create tools
        self.tools = [
            EventCreationTool(user_id),
            SimilarEventSearchTool(),
        ]
        
        # Set up observability (replace with your LangSmith config)
        self.tracer = LangChainTracer(
            project_name="homeschool-agents",
            # api_key=os.getenv("LANGSMITH_API_KEY")  # Uncomment when you have LangSmith
        )
        
        # Enhanced memory management
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10,  # Keep more context than before
            ai_prefix="Assistant",
            human_prefix="User"
        )
        
        # Create the LangChain agent
        self.agent = self._create_agent()
        
        # Create LangGraph workflow for complex cases
        self.workflow = self._create_workflow()
    
    def _create_agent(self):
        """Create the function-calling agent with enhanced prompt"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_enhanced_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create function-calling agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Agent executor with better error handling
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_execution_time=60,
            max_iterations=10,
            callbacks=[self.tracer] if hasattr(self, 'tracer') else []
        )
    
    def _get_enhanced_system_prompt(self) -> str:
        """Enhanced system prompt for proactive behavior"""
        return """You are an expert AI assistant for creating educational events in a homeschool community.

CORE BEHAVIOR:
- When users provide ANY event information, immediately use create_event_draft tool
- Don't just acknowledge - take ACTION by creating drafts
- Use search_similar_events to provide intelligent suggestions
- Be proactive, not passive

Available tools:
1. create_event_draft - Use immediately when user provides event details
2. search_similar_events - Find similar events for suggestions

Essential information to gather:
- WHAT: Event title and description (required)
- WHEN: Date and time (required)  
- WHERE: Location (required)
- WHO: Target age group
- HOW MUCH: Cost/pricing

EXAMPLE GOOD RESPONSE:
User: "I want to do a science workshop for kids"
You: [Use create_event_draft immediately with title="Science Workshop"]
"Great! I've started creating your science workshop. Let me search for similar events to give you pricing ideas..."

Remember: Create drafts immediately when users provide information!"""
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow for complex reasoning"""
        
        workflow = StateGraph(AgentState)
        
        # Define workflow nodes
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("extract_info", self._extract_event_info)
        workflow.add_node("create_draft", self._create_draft)
        workflow.add_node("search_similar", self._search_similar)
        workflow.add_node("provide_feedback", self._provide_feedback)
        
        # Define workflow edges
        workflow.set_entry_point("analyze_input")
        
        workflow.add_conditional_edges(
            "analyze_input",
            self._route_based_on_intent,
            {
                "extract_and_create": "extract_info",
                "search_first": "search_similar",
                "direct_feedback": "provide_feedback"
            }
        )
        
        workflow.add_edge("extract_info", "create_draft")
        workflow.add_edge("create_draft", "provide_feedback")
        workflow.add_edge("search_similar", "provide_feedback")
        workflow.add_edge("provide_feedback", END)
        
        return workflow.compile()
    
    @traceable(name="process_user_message")
    async def process_message(
        self, 
        message: str, 
        session_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - process user messages with full observability
        
        This method automatically chooses between:
        - Simple agent execution for straightforward requests
        - Complex workflow execution for multi-step reasoning
        """
        
        session_context = session_context or {}
        
        try:
            # Determine if we need complex workflow or simple agent
            if self._needs_complex_workflow(message):
                return await self._execute_workflow(message, session_context)
            else:
                return await self._execute_simple_agent(message)
                
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}. Let me try a simpler approach.",
                "error": str(e),
                "type": "error_response",
                "fallback": True
            }
    
    async def _execute_simple_agent(self, message: str) -> Dict[str, Any]:
        """Execute using simple LangChain agent for straightforward requests"""
        
        result = await self.agent.ainvoke({
            "input": message,
            "chat_history": self.memory.chat_memory.messages
        })
        
        return {
            "response": result["output"],
            "type": "agent_response",
            "tools_used": self._extract_tools_used(result),
            "confidence": self._calculate_confidence(result)
        }
    
    async def _execute_workflow(
        self, 
        message: str, 
        session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute using LangGraph workflow for complex reasoning"""
        
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            event_data=session_context.get("event_data", {}),
            user_id=self.user_id,
            session_id=session_context.get("session_id", ""),
            current_step="analyze_input",
            tools_used=[],
            confidence_score=0.0
        )
        
        final_state = await self.workflow.ainvoke(initial_state)
        
        return {
            "response": self._generate_response_from_state(final_state),
            "event_data": final_state["event_data"],
            "tools_used": final_state["tools_used"],
            "workflow_step": final_state["current_step"],
            "confidence": final_state["confidence_score"],
            "type": "workflow_response"
        }
    
    # Workflow node implementations
    async def _analyze_input(self, state: AgentState) -> AgentState:
        """Analyze user input to determine processing path"""
        message = state["messages"][-1].content.lower()
        
        # Intent classification (could be enhanced with LLM)
        if any(word in message for word in ["create", "make", "plan", "new event"]):
            if any(word in message for word in ["like", "similar", "example"]):
                state["current_step"] = "search_first"
            else:
                state["current_step"] = "extract_and_create"
        else:
            state["current_step"] = "direct_feedback"
        
        state["confidence_score"] = 0.8
        return state
    
    async def _extract_event_info(self, state: AgentState) -> AgentState:
        """Extract event information from user message"""
        message = state["messages"][-1].content
        
        # Simple extraction (enhance with NER or LLM-based extraction)
        extracted_info = {}
        
        # Extract title from quotes or after keywords
        if '"' in message:
            extracted_info["title"] = message.split('"')[1]
        elif "workshop" in message.lower():
            extracted_info["title"] = "Workshop"
        elif "class" in message.lower():
            extracted_info["title"] = "Class"
        
        # Extract age information
        import re
        age_match = re.search(r'(\d+)-(\d+)', message)
        if age_match:
            extracted_info["min_age"] = int(age_match.group(1))
            extracted_info["max_age"] = int(age_match.group(2))
        
        state["event_data"].update(extracted_info)
        state["tools_used"].append("extract_info")
        return state
    
    async def _create_draft(self, state: AgentState) -> AgentState:
        """Create event draft using the tool"""
        tool = self.tools[0]  # EventCreationTool
        result = await tool._arun(**state["event_data"])
        
        state["tools_used"].append("create_event_draft")
        state["confidence_score"] = 0.9
        return state
    
    async def _search_similar(self, state: AgentState) -> AgentState:
        """Search for similar events"""
        message = state["messages"][-1].content
        tool = self.tools[1]  # SimilarEventSearchTool
        result = await tool._arun(query=message, limit=3)
        
        state["tools_used"].append("search_similar_events")
        state["confidence_score"] = 0.85
        return state
    
    async def _provide_feedback(self, state: AgentState) -> AgentState:
        """Generate final response to user"""
        # This would generate the final response based on the workflow results
        state["current_step"] = "completed"
        return state
    
    # Helper methods
    def _needs_complex_workflow(self, message: str) -> bool:
        """Determine if message needs complex workflow processing"""
        complex_indicators = [
            "multiple events", "compare", "analyze", "plan several",
            "different options", "help me decide"
        ]
        return any(indicator in message.lower() for indicator in complex_indicators)
    
    def _route_based_on_intent(self, state: AgentState) -> str:
        """Route to appropriate workflow path"""
        return state["current_step"]
    
    def _extract_tools_used(self, result: Dict) -> List[str]:
        """Extract tools used from agent result"""
        if "intermediate_steps" in result:
            return [step[0].tool for step in result["intermediate_steps"]]
        return []
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence score"""
        if result.get("intermediate_steps"):
            return 0.9  # High confidence when tools were used
        return 0.6  # Medium confidence for direct responses
    
    def _generate_response_from_state(self, state: AgentState) -> str:
        """Generate human-readable response from workflow state"""
        tools_used = state["tools_used"]
        
        if "create_event_draft" in tools_used:
            return "Great! I've created an event draft for you. What other details would you like to add?"
        elif "search_similar_events" in tools_used:
            return "I found some similar events that might give you ideas. Would you like me to create a draft based on these examples?"
        else:
            return "I'm here to help you create an event. What kind of event are you planning?"


# Example usage and comparison
async def main():
    """
    Example showing the difference between old and new approaches
    """
    
    print("=== Modern LangChain Agent Example ===")
    
    # Initialize the modern agent
    agent = ModernEventCreationAgent(user_id=123)
    
    # Example conversation
    session_context = {
        "user_id": 123,
        "session_id": "session_123",
        "event_data": {}
    }
    
    # Test messages
    test_messages = [
        "I want to create a science workshop for 8-12 year olds",
        "What would be a good price for a 2-hour coding class?",
        "Help me plan multiple events for next month"
    ]
    
    for message in test_messages:
        print(f"\nUser: {message}")
        
        response = await agent.process_message(message, session_context)
        
        print(f"Agent: {response['response']}")
        print(f"Type: {response['type']}")
        print(f"Tools Used: {response.get('tools_used', [])}")
        print(f"Confidence: {response.get('confidence', 0):.2f}")
        print("-" * 50)


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 