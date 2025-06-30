"""
Example: Modernizing EventCreationAgent with LangChain + LangGraph
This example shows how to replace your custom agent implementation with modern LangChain patterns.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime

# LangChain imports
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool, StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage

# LangGraph imports for advanced workflows
from langgraph import StateGraph, END
import operator

# LangSmith for observability
from langsmith import traceable
from langchain.callbacks import LangChainTracer

# Your existing imports (adapt as needed)
from sqlalchemy.orm import Session
# from app.models import User, Event, ChatConversation


class EventData(BaseModel):
    """Enhanced event data model with validation"""
    title: Optional[str] = Field(None, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    date: Optional[str] = Field(None, description="Event date (YYYY-MM-DD)")
    time: Optional[str] = Field(None, description="Event time (HH:MM)")
    location: Optional[str] = Field(None, description="Event location")
    cost: Optional[float] = Field(None, ge=0, description="Event cost")
    max_participants: Optional[int] = Field(None, gt=0, description="Max participants")
    min_age: Optional[int] = Field(None, ge=0, le=18, description="Minimum age")
    max_age: Optional[int] = Field(None, ge=0, le=18, description="Maximum age")
    category: Optional[str] = Field(None, description="Event category")


class AgentState(TypedDict):
    """State management for the agent workflow"""
    messages: Annotated[List, operator.add]
    event_data: Dict[str, Any]
    user_id: int
    session_id: str
    current_step: str
    tools_used: List[str]
    validation_errors: List[str]
    confidence_score: float


class EventCreationTool(BaseTool):
    """Modern LangChain tool for event creation"""
    
    name = "create_event_draft"
    description = """Create or update an event draft with provided information.
    Use this tool whenever the user provides ANY event details, even if incomplete.
    This tool can be called multiple times to build the event iteratively."""
    
    args_schema = EventData
    
    def __init__(self, db_session: Session, user_id: int):
        super().__init__()
        self.db = db_session
        self.user_id = user_id
    
    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously"""
        try:
            # Clean the input data
            event_data = {k: v for k, v in kwargs.items() if v is not None}
            
            # Your existing event creation logic here
            result = self._create_or_update_draft(event_data)
            
            return json.dumps({
                "success": True,
                "message": f"Event draft created: '{event_data.get('title', 'Untitled')}'",
                "event_data": result,
                "missing_fields": self._get_missing_fields(event_data),
                "suggestions": self._get_suggestions(event_data)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "event_data": kwargs
            })
    
    async def _arun(self, **kwargs) -> str:
        """Async version"""
        return self._run(**kwargs)
    
    def _create_or_update_draft(self, event_data: Dict) -> Dict:
        """Your existing draft creation logic"""
        # Implement your existing event draft creation
        return event_data
    
    def _get_missing_fields(self, event_data: Dict) -> List[str]:
        """Identify missing required fields"""
        required_fields = ["title", "date", "time", "location"]
        return [field for field in required_fields if not event_data.get(field)]
    
    def _get_suggestions(self, event_data: Dict) -> List[str]:
        """Generate helpful suggestions"""
        suggestions = []
        if not event_data.get("cost"):
            suggestions.append("Consider if this should be a paid or free event")
        if not event_data.get("max_participants"):
            suggestions.append("Set a participant limit to manage capacity")
        return suggestions


class SimilarEventSearchTool(BaseTool):
    """Tool for finding similar events"""
    
    name = "search_similar_events"
    description = "Search for similar events to get pricing and format ideas"
    
    def __init__(self, db_session: Session):
        super().__init__()
        self.db = db_session
    
    def _run(self, query: str, limit: int = 5) -> str:
        try:
            # Your existing search logic
            similar_events = self._search_events(query, limit)
            
            return json.dumps({
                "success": True,
                "events": similar_events,
                "suggestions": self._generate_suggestions(similar_events)
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def _search_events(self, query: str, limit: int) -> List[Dict]:
        """Your existing event search logic"""
        # Implement your database search here
        return []
    
    def _generate_suggestions(self, events: List[Dict]) -> List[str]:
        """Generate suggestions based on similar events"""
        if not events:
            return ["No similar events found - you're creating something unique!"]
        
        # Analyze pricing, locations, etc.
        return ["Based on similar events, consider pricing around $15-25"]


class ModernEventCreationAgent:
    """Modern event creation agent using LangChain + LangGraph"""
    
    def __init__(self, db_session: Session, user_id: int):
        self.db = db_session
        self.user_id = user_id
        
        # Initialize LLM with proper configuration
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            streaming=True
        )
        
        # Create tools
        self.tools = [
            EventCreationTool(db_session, user_id),
            SimilarEventSearchTool(db_session),
            # Add more tools as needed
        ]
        
        # Set up observability
        self.tracer = LangChainTracer(project_name="homeschool-agents")
        
        # Create memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
        
        # Create the agent
        self.agent = self._create_agent()
        
        # Create LangGraph workflow
        self.workflow = self._create_workflow()
    
    def _create_agent(self):
        """Create the LangChain agent"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_execution_time=60,
            callbacks=[self.tracer]
        )
    
    def _get_system_prompt(self) -> str:
        """Enhanced system prompt for better agent behavior"""
        return """You are an expert AI assistant for creating educational events in a homeschool community.

Your primary goal: Help users create events by gathering information through conversation and actively using available tools.

CRITICAL BEHAVIOR:
- When a user provides ANY event information, immediately use create_event_draft tool
- Don't just acknowledge - take action by creating drafts
- Use search_similar_events to provide intelligent suggestions
- Ask focused follow-up questions for missing information

Available tools:
1. create_event_draft - Use whenever user provides event details (use immediately!)
2. search_similar_events - Find similar events for pricing/format suggestions

Essential information to gather:
- WHAT: Event title and description (required)
- WHEN: Date and time (required)  
- WHERE: Location (required)
- WHO: Target age group
- HOW MUCH: Cost/pricing

Example good responses:
User: "I want to do a science workshop for kids"
You: [Immediately use create_event_draft with title="Science Workshop"] 
"Great! I've started creating your science workshop. Let me also search for similar events to give you some ideas..."

Be proactive, not passive. Create drafts immediately when users provide information!"""
    
    def _create_workflow(self) -> StateGraph:
        """Create advanced LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("create_draft", self._create_draft)
        workflow.add_node("search_similar", self._search_similar)
        workflow.add_node("validate_data", self._validate_data)
        workflow.add_node("get_feedback", self._get_feedback)
        workflow.add_node("finalize", self._finalize_event)
        
        # Define edges and routing
        workflow.set_entry_point("analyze_input")
        
        workflow.add_conditional_edges(
            "analyze_input",
            self._route_after_analysis,
            {
                "create": "create_draft",
                "search": "search_similar", 
                "validate": "validate_data",
                "feedback": "get_feedback"
            }
        )
        
        workflow.add_edge("create_draft", "validate_data")
        workflow.add_edge("search_similar", "create_draft") 
        workflow.add_edge("validate_data", "get_feedback")
        workflow.add_edge("get_feedback", END)
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    @traceable(name="process_user_message")
    async def process_message(
        self, 
        message: str, 
        session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message with full observability"""
        
        try:
            # For simple cases, use the agent directly
            if self._is_simple_request(message):
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
            
            # For complex cases, use the workflow
            else:
                initial_state = AgentState(
                    messages=[HumanMessage(content=message)],
                    event_data=session_context.get("event_data", {}),
                    user_id=self.user_id,
                    session_id=session_context.get("session_id", ""),
                    current_step="analyze_input",
                    tools_used=[],
                    validation_errors=[],
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
                
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}. Let me try a different approach.",
                "error": str(e),
                "type": "error_response"
            }
    
    # Workflow node implementations
    async def _analyze_input(self, state: AgentState) -> AgentState:
        """Analyze user input to determine next action"""
        message = state["messages"][-1].content
        
        # Simple rule-based routing (could be enhanced with LLM classification)
        if any(word in message.lower() for word in ["create", "make", "plan", "event"]):
            if any(word in message.lower() for word in ["like", "similar", "example"]):
                state["current_step"] = "search"
            else:
                state["current_step"] = "create"
        else:
            state["current_step"] = "feedback"
        
        return state
    
    async def _create_draft(self, state: AgentState) -> AgentState:
        """Create event draft using the tool"""
        message = state["messages"][-1].content
        
        # Extract event information (simplified - you could use NER or LLM extraction)
        event_info = self._extract_event_info(message)
        
        # Use the tool
        tool = self.tools[0]  # EventCreationTool
        result = await tool._arun(**event_info)
        
        state["tools_used"].append("create_event_draft")
        state["event_data"].update(event_info)
        state["current_step"] = "validate"
        
        return state
    
    def _extract_event_info(self, message: str) -> Dict[str, Any]:
        """Extract event information from message (simplified)"""
        # This is a simplified extraction - in reality, you'd use more sophisticated NLP
        info = {}
        
        # Extract title (look for quotes or key phrases)
        if '"' in message:
            title = message.split('"')[1]
            info["title"] = title
        
        # Extract other information using keywords and patterns
        # This could be enhanced with spaCy, regex, or LLM-based extraction
        
        return info
    
    def _route_after_analysis(self, state: AgentState) -> str:
        """Route to next node based on analysis"""
        return state["current_step"]
    
    def _is_simple_request(self, message: str) -> bool:
        """Determine if this is a simple request that doesn't need workflow"""
        complex_indicators = ["multiple", "several", "compare", "analyze", "plan"]
        return not any(indicator in message.lower() for indicator in complex_indicators)
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence score for the response"""
        # Simple heuristic - could be enhanced
        if result.get("intermediate_steps"):
            return 0.9  # High confidence if tools were used
        else:
            return 0.6  # Medium confidence for direct responses


# Example usage
async def main():
    """Example of how to use the modernized agent"""
    
    # Mock database session (replace with your actual session)
    db_session = None  # Your database session here
    user_id = 123
    
    # Create the modern agent
    agent = ModernEventCreationAgent(db_session, user_id)
    
    # Example conversation
    session_context = {
        "user_id": user_id,
        "session_id": "session_123",
        "event_data": {}
    }
    
    # Test message processing
    user_message = "I want to create a science workshop for 8-12 year olds next Saturday"
    
    response = await agent.process_message(user_message, session_context)
    
    print(f"Agent Response: {response['response']}")
    print(f"Tools Used: {response.get('tools_used', [])}")
    print(f"Confidence: {response.get('confidence', 0)}")


if __name__ == "__main__":
    asyncio.run(main()) 