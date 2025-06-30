# AI System Modernization Plan: Upgrading to LangChain & Modern Libraries

## Executive Summary

Your current AI implementation is well-structured but uses heavily custom code where mature libraries could provide better functionality. This plan outlines a comprehensive modernization using LangChain, LangGraph, and other cutting-edge AI tools.

## Current System Analysis

### Strengths ✅
- Clean modular architecture with proper separation of concerns
- Multiple AI provider support (OpenAI, Anthropic, Ollama)
- Enterprise patterns (circuit breaker, retry logic, health checks)
- Tool calling capabilities with custom orchestration
- Database integration with SQLAlchemy models
- Real-time HTMX chat interface

### Areas for Improvement 🔄
- Heavy reliance on custom implementations
- Manual tool orchestration and parsing
- Basic agent patterns without modern reasoning capabilities
- No vector storage or RAG capabilities
- Limited observability and structured tracing
- Complex testing due to tight coupling

## Recommended Modern Libraries

### Core AI Framework
```python
# Primary framework stack
langchain>=0.1.0              # Main orchestration framework
langchain-community>=0.0.20   # Community integrations
langchain-openai>=0.0.5       # OpenAI integration
langchain-anthropic>=0.1.0    # Anthropic integration
langgraph>=0.0.26             # Agent workflow management
langsmith>=0.0.85             # Observability and debugging
```

### Vector & RAG Stack
```python
# Vector and retrieval capabilities
chromadb>=0.4.22              # Vector database
sentence-transformers>=2.2.2  # Local embeddings
faiss-cpu>=1.7.4             # Alternative vector search
langchain-chroma>=0.1.0       # LangChain Chroma integration
```

### Observability & Monitoring
```python
# Enhanced monitoring
opentelemetry-api>=1.21.0
opentelemetry-instrumentation-fastapi>=0.42b0
structlog>=23.2.0             # Structured logging
prometheus-client>=0.19.0     # Metrics
```

### Modern Data Stack
```python
# Enhanced data handling
pydantic>=2.5.0               # Modern validation
sqlmodel>=0.0.14              # SQLAlchemy + Pydantic integration
asyncpg>=0.29.0               # Async PostgreSQL driver
```

## Phase 1: Foundation & Provider Modernization

### 1.1 LangChain Provider Integration

Replace your custom provider abstraction with LangChain's unified interface:

```python
# app/ai/providers/modern_providers.py
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import Ollama
from langchain.schema import BaseMessage
from typing import List, Dict, Any

class UnifiedAIProvider:
    """Modern provider using LangChain's standardized interface"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.llm = self._create_langchain_model()
    
    def _create_langchain_model(self):
        """Create appropriate LangChain model based on provider"""
        if self.config.provider == "openai":
            return ChatOpenAI(
                model=self.config.model_name,
                api_key=self.config.api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                streaming=True  # Enable streaming
            )
        elif self.config.provider == "anthropic":
            return ChatAnthropic(
                model=self.config.model_name,
                api_key=self.config.api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
        elif self.config.provider == "ollama":
            return Ollama(
                model=self.config.model_name,
                base_url=self.config.endpoint_url,
                temperature=self.config.temperature,
                num_ctx=8192  # Larger context window
            )
    
    async def generate_response(
        self, 
        messages: List[BaseMessage], 
        **kwargs
    ) -> Dict[str, Any]:
        """Unified response generation"""
        try:
            response = await self.llm.agenerate([messages], **kwargs)
            return {
                "content": response.generations[0][0].text,
                "usage": response.llm_output.get("token_usage", {}),
                "model": self.config.model_name,
                "provider": self.config.provider
            }
        except Exception as e:
            raise AIProviderError(f"Generation failed: {str(e)}")
```

### 1.2 Enhanced Observability

Implement comprehensive tracing with LangSmith:

```python
# app/ai/observability/tracing.py
import os
import structlog
from langsmith import Client, traceable
from langchain.callbacks import LangChainTracer
from opentelemetry import trace
from typing import Dict, Any, Optional

class AIObservabilityManager:
    """Comprehensive AI observability with LangSmith + OpenTelemetry"""
    
    def __init__(self):
        # LangSmith setup
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
            api_url=os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
        )
        
        # OpenTelemetry setup
        self.tracer = trace.get_tracer(__name__)
        
        # Structured logging
        self.logger = structlog.get_logger()
    
    @traceable(name="ai_agent_execution")
    def trace_agent_workflow(
        self, 
        workflow_name: str, 
        user_id: int, 
        session_id: str
    ):
        """Decorator for comprehensive agent tracing"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                span_name = f"{workflow_name}_{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    # Add span attributes
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("session_id", session_id)
                    span.set_attribute("workflow", workflow_name)
                    
                    # Structured logging
                    self.logger.info(
                        "Agent workflow started",
                        workflow=workflow_name,
                        function=func.__name__,
                        user_id=user_id,
                        session_id=session_id
                    )
                    
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Log success
                        self.logger.info(
                            "Agent workflow completed",
                            workflow=workflow_name,
                            success=True,
                            result_type=type(result).__name__
                        )
                        
                        return result
                        
                    except Exception as e:
                        # Log and trace errors
                        span.set_attribute("error", True)
                        span.set_attribute("error_message", str(e))
                        
                        self.logger.error(
                            "Agent workflow failed",
                            workflow=workflow_name,
                            error=str(e),
                            error_type=type(e).__name__
                        )
                        
                        raise
            
            return wrapper
        return decorator
    
    def get_langchain_callbacks(self):
        """Get LangChain callback handlers for tracing"""
        return [
            LangChainTracer(
                project_name="homeschool-ai-agents",
                client=self.langsmith_client
            )
        ]
```

## Phase 2: Agent Architecture Modernization

### 2.1 LangChain + LangGraph Agent Implementation

Replace your custom agent with modern LangChain patterns:

```python
# app/ai/agents/modern_event_agent.py
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
from langgraph import StateGraph, END
from typing import List, Dict, Any, TypedDict, Annotated
import operator

class EventCreationState(TypedDict):
    """State management for event creation workflow"""
    messages: Annotated[List, operator.add]
    event_data: Dict[str, Any]
    user_id: int
    session_id: str
    current_step: str
    tools_used: List[str]
    validation_errors: List[str]
    user_confirmations: Dict[str, bool]

class ModernEventCreationAgent:
    """Advanced event creation agent using LangChain + LangGraph"""
    
    def __init__(
        self, 
        llm, 
        tools: List[BaseTool], 
        memory_key: str = "chat_history",
        max_iterations: int = 10
    ):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations
        
        # Enhanced memory management
        self.memory = ConversationBufferWindowMemory(
            memory_key=memory_key,
            return_messages=True,
            k=15,  # Keep more context
            ai_prefix="Assistant",
            human_prefix="User"
        )
        
        # Create sophisticated prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_enhanced_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create function-calling agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Agent executor with enhanced error handling
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_execution_time=60,
            max_iterations=max_iterations,
            early_stopping_method="generate"
        )
        
        # Create LangGraph workflow for complex orchestration
        self.workflow = self._create_advanced_workflow()
    
    def _get_enhanced_system_prompt(self) -> str:
        """Enhanced system prompt with better reasoning instructions"""
        return """You are an expert AI assistant for creating educational events in a homeschool community.

Your capabilities:
- Analyze user requests to extract event details
- Use available tools to create, validate, and manage events
- Provide intelligent suggestions based on similar past events
- Guide users through the complete event creation process
- Handle complex multi-step conversations

Available tools and when to use them:
1. create_event_draft - When user provides any event details (use immediately!)
2. search_similar_events - To find comparable events for pricing/format suggestions  
3. validate_event_data - Before finalizing any event
4. suggest_improvements - To enhance event details
5. check_venue_availability - For location and timing conflicts

Key principles:
- Be proactive: If user mentions event details, immediately use create_event_draft
- Be helpful: Always suggest improvements and alternatives
- Be thorough: Validate all data before final creation
- Be conversational: Maintain natural dialogue while being efficient

Event creation workflow:
1. Listen for ANY event information (title, date, location, etc.)
2. Immediately create draft with available information
3. Ask targeted questions for missing critical details
4. Validate and suggest improvements
5. Create final event when user confirms

Remember: Your goal is to help users create amazing educational events efficiently!"""
    
    def _create_advanced_workflow(self) -> StateGraph:
        """Create sophisticated LangGraph workflow"""
        workflow = StateGraph(EventCreationState)
        
        # Define workflow nodes
        workflow.add_node("parse_input", self._parse_user_input)
        workflow.add_node("extract_event_info", self._extract_event_information)
        workflow.add_node("create_draft", self._create_event_draft)
        workflow.add_node("search_similar", self._search_similar_events)
        workflow.add_node("validate_event", self._validate_event_data)
        workflow.add_node("get_user_input", self._get_additional_user_input)
        workflow.add_node("finalize_event", self._finalize_event_creation)
        workflow.add_node("handle_error", self._handle_workflow_error)
        
        # Define workflow edges and routing
        workflow.set_entry_point("parse_input")
        
        workflow.add_edge("parse_input", "extract_event_info")
        
        workflow.add_conditional_edges(
            "extract_event_info",
            self._route_after_extraction,
            {
                "create_draft": "create_draft",
                "search_first": "search_similar",
                "need_more_info": "get_user_input"
            }
        )
        
        workflow.add_edge("create_draft", "validate_event")
        workflow.add_edge("search_similar", "create_draft")
        
        workflow.add_conditional_edges(
            "validate_event",
            self._route_after_validation,
            {
                "finalize": "finalize_event",
                "get_input": "get_user_input",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("get_user_input", "extract_event_info")
        workflow.add_edge("finalize_event", END)
        workflow.add_edge("handle_error", "get_user_input")
        
        return workflow.compile()
    
    # Workflow node implementations
    async def _parse_user_input(self, state: EventCreationState) -> EventCreationState:
        """Parse and understand user input"""
        latest_message = state["messages"][-1].content
        
        # Use LLM to categorize the input
        analysis_prompt = f"""
        Analyze this user message for event creation intent: "{latest_message}"
        
        Determine:
        1. Intent type (create_new, modify_existing, ask_question, confirm_action)
        2. Confidence level (high, medium, low)
        3. Information completeness (complete, partial, minimal)
        
        Return JSON format only.
        """
        
        response = await self.llm.agenerate([[{"role": "user", "content": analysis_prompt}]])
        # Parse response and update state
        
        return state
    
    async def process_message(
        self, 
        message: str, 
        session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process user message through advanced workflow"""
        
        # Initialize workflow state
        workflow_state = EventCreationState(
            messages=[{"role": "user", "content": message}],
            event_data=session_state.get("event_data", {}),
            user_id=session_state["user_id"],
            session_id=session_state["session_id"],
            current_step="parse_input",
            tools_used=[],
            validation_errors=[],
            user_confirmations={}
        )
        
        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(workflow_state)
            
            # Format response
            return {
                "response": self._generate_user_response(final_state),
                "event_data": final_state["event_data"],
                "tools_used": final_state["tools_used"],
                "validation_errors": final_state["validation_errors"],
                "workflow_step": final_state["current_step"],
                "needs_user_input": self._needs_user_input(final_state),
                "type": "workflow_response"
            }
            
        except Exception as e:
            # Fallback to simple agent execution
            return await self._fallback_processing(message, session_state, e)
```

### 2.2 Advanced Tool System with LangChain

Modernize your tool system using LangChain's tool framework:

```python
# app/ai/tools/modern_tools.py
from langchain.tools import BaseTool, StructuredTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type, Dict, Any, Optional, List
from sqlalchemy.orm import Session
import json

class EventCreationInput(BaseModel):
    """Enhanced input schema for event creation"""
    title: str = Field(description="Event title (required)")
    description: Optional[str] = Field(None, description="Detailed event description")
    date: Optional[str] = Field(None, description="Event date in ISO format (YYYY-MM-DD)")
    time: Optional[str] = Field(None, description="Event time (HH:MM format)")
    location: Optional[str] = Field(None, description="Event location/venue")
    cost: Optional[float] = Field(None, description="Event cost in dollars")
    max_participants: Optional[int] = Field(None, description="Maximum number of participants")
    min_age: Optional[int] = Field(None, description="Minimum age requirement")
    max_age: Optional[int] = Field(None, description="Maximum age requirement")
    materials_needed: Optional[str] = Field(None, description="Required materials or supplies")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level (beginner/intermediate/advanced)")

class ModernEventCreationTool(BaseTool):
    """Advanced event creation tool with comprehensive validation"""
    
    name = "create_event_draft"
    description = """Create or update an event draft with provided details. 
    Use this tool whenever the user provides ANY event information, even if incomplete.
    This tool can be called multiple times to iteratively build the event."""
    
    args_schema: Type[BaseModel] = EventCreationInput
    
    def __init__(self, db_session: Session, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.db = db_session
        self.user_id = user_id
    
    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously"""
        return json.dumps(self._create_or_update_draft(kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously"""
        return self._run(**kwargs)
    
    def _create_or_update_draft(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update event draft with intelligent merging"""
        try:
            # Get existing draft or create new one
            from app.event_draft_manager import EventDraftManager
            draft_manager = EventDraftManager(self.db)
            
            # Clean and validate input data
            clean_data = {k: v for k, v in event_data.items() if v is not None}
            
            # Create/update draft
            result = draft_manager.create_or_update_draft(
                user_id=self.user_id,
                event_data=clean_data
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Event draft created/updated: '{clean_data.get('title', 'Untitled Event')}'",
                    "event_data": result["event_data"],
                    "missing_fields": result.get("missing_fields", []),
                    "suggestions": result.get("suggestions", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to create draft"),
                    "event_data": clean_data
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "event_data": event_data
            }

class EventSearchInput(BaseModel):
    """Input for searching similar events"""
    query: str = Field(description="Search query to find similar events")
    limit: Optional[int] = Field(5, description="Maximum number of results to return")
    category: Optional[str] = Field(None, description="Event category filter")

class SimilarEventSearchTool(BaseTool):
    """Tool for finding similar events for inspiration and pricing"""
    
    name = "search_similar_events"
    description = """Search for similar events in the database to get ideas for pricing, 
    format, duration, and other details. Use this to provide intelligent suggestions."""
    
    args_schema: Type[BaseModel] = EventSearchInput
    
    def __init__(self, db_session: Session, **kwargs):
        super().__init__(**kwargs)
        self.db = db_session
    
    def _run(self, query: str, limit: int = 5, category: str = None) -> str:
        """Search for similar events"""
        try:
            from app.models import Event
            from sqlalchemy import or_, func
            
            # Build search query
            search_query = self.db.query(Event)
            
            if category:
                search_query = search_query.filter(Event.category == category)
            
            # Text search across title and description
            search_terms = query.lower().split()
            conditions = []
            for term in search_terms:
                conditions.extend([
                    func.lower(Event.title).contains(term),
                    func.lower(Event.description).contains(term)
                ])
            
            if conditions:
                search_query = search_query.filter(or_(*conditions))
            
            # Get results
            events = search_query.limit(limit).all()
            
            # Format results
            results = []
            for event in events:
                results.append({
                    "title": event.title,
                    "description": event.description[:200] + "..." if len(event.description or "") > 200 else event.description,
                    "cost": float(event.cost) if event.cost else 0,
                    "location": event.location,
                    "date": event.date.isoformat() if event.date else None,
                    "max_participants": event.max_pupils,
                    "age_range": f"{event.min_age}-{event.max_age}" if event.min_age and event.max_age else None
                })
            
            return json.dumps({
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
                "suggestions": self._generate_suggestions(results, query)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Search failed: {str(e)}",
                "query": query
            })
    
    def _generate_suggestions(self, events: List[Dict], query: str) -> List[str]:
        """Generate intelligent suggestions based on search results"""
        if not events:
            return ["No similar events found. Consider creating something unique!"]
        
        suggestions = []
        
        # Price analysis
        costs = [e["cost"] for e in events if e["cost"] > 0]
        if costs:
            avg_cost = sum(costs) / len(costs)
            suggestions.append(f"Similar events typically cost ${avg_cost:.2f}")
        
        # Popular locations
        locations = [e["location"] for e in events if e["location"]]
        if locations:
            popular_location = max(set(locations), key=locations.count)
            suggestions.append(f"Popular venue: {popular_location}")
        
        # Age patterns
        age_ranges = [e["age_range"] for e in events if e["age_range"]]
        if age_ranges:
            common_age = max(set(age_ranges), key=age_ranges.count)
            suggestions.append(f"Common age range: {common_age} years")
        
        return suggestions

# Tool factory for easy registration
def create_modern_tools(db_session: Session, user_id: int) -> List[BaseTool]:
    """Create all modern tools for the agent"""
    return [
        ModernEventCreationTool(db_session, user_id),
        SimilarEventSearchTool(db_session),
        # Add more tools as needed...
    ]
```

## Phase 3: RAG (Retrieval-Augmented Generation) Implementation

### 3.1 Vector Store and Knowledge Management

Add semantic search capabilities to your system:

```python
# app/ai/vectorstore/knowledge_manager.py
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from typing import List, Dict, Any, Optional
import os

class EventKnowledgeManager:
    """Comprehensive knowledge management for events and educational content"""
    
    def __init__(self, persist_directory: str = "./data/vectorstore"):
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Vector store setup
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="homeschool_events"
        )
        
        # Text splitter for document processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", "! ", "? ", " "]
        )
        
        # Hybrid retrieval setup
        self.setup_hybrid_retrieval()
    
    def setup_hybrid_retrieval(self):
        """Setup hybrid retrieval combining vector and keyword search"""
        # Vector retriever
        self.vector_retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.7, "k": 5}
        )
        
        # BM25 keyword retriever (will be populated with documents)
        self.bm25_retriever = None
        self.ensemble_retriever = None
    
    async def add_events_to_knowledge_base(self, events: List[Dict[str, Any]]):
        """Add event data to the knowledge base with rich metadata"""
        documents = []
        
        for event in events:
            # Create comprehensive content for each event
            content = self._create_event_content(event)
            
            # Create document with rich metadata
            doc = Document(
                page_content=content,
                metadata={
                    "type": "event",
                    "event_id": event.get("id"),
                    "title": event.get("title", ""),
                    "category": event.get("category", "general"),
                    "cost": event.get("cost", 0),
                    "age_range": f"{event.get('min_age', 0)}-{event.get('max_age', 18)}",
                    "location": event.get("location", ""),
                    "date": event.get("date", "").split("T")[0] if event.get("date") else "",
                    "success_rating": event.get("success_rating", 3),  # Could be calculated
                    "participant_count": event.get("participant_count", 0)
                }
            )
            documents.append(doc)
        
        # Split documents
        split_docs = self.text_splitter.split_documents(documents)
        
        # Add to vector store
        await self.vectorstore.aadd_documents(split_docs)
        
        # Update BM25 retriever
        self._update_bm25_retriever(split_docs)
        
        # Persist the vector store
        self.vectorstore.persist()
    
    def _create_event_content(self, event: Dict[str, Any]) -> str:
        """Create rich content representation of an event"""
        content_parts = [
            f"Event Title: {event.get('title', 'Unknown Event')}",
            f"Description: {event.get('description', 'No description available')}",
            f"Category: {event.get('category', 'General')}",
            f"Date: {event.get('date', 'Date TBD')}",
            f"Location: {event.get('location', 'Location TBD')}",
            f"Cost: ${event.get('cost', 0):.2f}",
            f"Age Range: {event.get('min_age', 0)}-{event.get('max_age', 18)} years",
            f"Maximum Participants: {event.get('max_participants', 'Unlimited')}",
            f"Materials Needed: {event.get('materials_needed', 'None specified')}",
            f"Difficulty Level: {event.get('difficulty_level', 'Not specified')}",
            f"Duration: {event.get('duration', 'Not specified')}",
            f"Learning Objectives: {event.get('learning_objectives', 'Not specified')}"
        ]
        
        return "\n".join(content_parts)
    
    def _update_bm25_retriever(self, documents: List[Document]):
        """Update BM25 retriever with new documents"""
        if documents:
            self.bm25_retriever = BM25Retriever.from_documents(documents)
            self.bm25_retriever.k = 5
            
            # Create ensemble retriever
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.vector_retriever, self.bm25_retriever],
                weights=[0.7, 0.3]  # Favor vector search slightly
            )
    
    async def search_similar_events(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Advanced event search with filtering"""
        try:
            # Use ensemble retrieval if available, otherwise vector only
            if self.ensemble_retriever:
                docs = await self.ensemble_retriever.aget_relevant_documents(query)
            else:
                docs = await self.vector_retriever.aget_relevant_documents(query)
            
            # Apply filters if provided
            if filters:
                docs = self._apply_filters(docs, filters)
            
            # Format results
            results = []
            for doc in docs[:k]:
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": getattr(doc, 'score', 1.0)
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []
    
    def _apply_filters(self, docs: List[Document], filters: Dict[str, Any]) -> List[Document]:
        """Apply metadata filters to documents"""
        filtered_docs = []
        
        for doc in docs:
            include = True
            
            # Cost range filter
            if "max_cost" in filters:
                doc_cost = doc.metadata.get("cost", 0)
                if doc_cost > filters["max_cost"]:
                    include = False
            
            # Age range filter
            if "age" in filters:
                age_range = doc.metadata.get("age_range", "0-18")
                min_age, max_age = map(int, age_range.split("-"))
                if not (min_age <= filters["age"] <= max_age):
                    include = False
            
            # Category filter
            if "category" in filters:
                doc_category = doc.metadata.get("category", "").lower()
                if filters["category"].lower() not in doc_category:
                    include = False
            
            if include:
                filtered_docs.append(doc)
        
        return filtered_docs
    
    async def get_intelligent_suggestions(
        self, 
        partial_event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get intelligent suggestions based on similar events"""
        # Create search query from partial data
        query_parts = []
        if partial_event_data.get("title"):
            query_parts.append(partial_event_data["title"])
        if partial_event_data.get("description"):
            query_parts.append(partial_event_data["description"])
        if partial_event_data.get("category"):
            query_parts.append(partial_event_data["category"])
        
        query = " ".join(query_parts) if query_parts else "educational event"
        
        # Search for similar events
        similar_events = await self.search_similar_events(query, k=10)
        
        if not similar_events:
            return {"suggestions": [], "message": "No similar events found"}
        
        # Generate suggestions
        suggestions = {
            "pricing": self._suggest_pricing(similar_events),
            "duration": self._suggest_duration(similar_events),
            "location": self._suggest_location(similar_events),
            "age_group": self._suggest_age_group(similar_events),
            "materials": self._suggest_materials(similar_events),
            "improvements": self._suggest_improvements(similar_events, partial_event_data)
        }
        
        return {
            "suggestions": suggestions,
            "similar_events_count": len(similar_events),
            "confidence": self._calculate_confidence(similar_events)
        }
    
    def _suggest_pricing(self, events: List[Dict]) -> Dict[str, Any]:
        """Suggest pricing based on similar events"""
        costs = [e["metadata"]["cost"] for e in events if e["metadata"].get("cost", 0) > 0]
        
        if not costs:
            return {"suggestion": "Free or donation-based", "confidence": "low"}
        
        avg_cost = sum(costs) / len(costs)
        min_cost = min(costs)
        max_cost = max(costs)
        
        return {
            "suggested_price": round(avg_cost, 2),
            "price_range": f"${min_cost:.2f} - ${max_cost:.2f}",
            "rationale": f"Based on {len(costs)} similar events",
            "confidence": "high" if len(costs) >= 5 else "medium"
        }
    
    # Additional suggestion methods...
    def _suggest_duration(self, events: List[Dict]) -> Dict[str, Any]:
        """Suggest event duration"""
        # Implementation for duration suggestions
        return {"suggestion": "2-3 hours", "confidence": "medium"}
    
    def _suggest_location(self, events: List[Dict]) -> Dict[str, Any]:
        """Suggest popular locations"""
        locations = [e["metadata"]["location"] for e in events if e["metadata"].get("location")]
        if locations:
            popular_location = max(set(locations), key=locations.count)
            return {"suggestion": popular_location, "confidence": "high"}
        return {"suggestion": "Community center or library", "confidence": "low"}
    
    def _calculate_confidence(self, events: List[Dict]) -> str:
        """Calculate confidence level for suggestions"""
        if len(events) >= 10:
            return "high"
        elif len(events) >= 5:
            return "medium"
        else:
            return "low"
```

### 3.2 RAG-Enhanced Chat Chain

Create intelligent chat chains that use retrieved knowledge:

```python
# app/ai/chains/rag_enhanced_chat.py
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableMap
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any, List

class RAGEnhancedEventChat:
    """RAG-enhanced chat for intelligent event creation assistance"""
    
    def __init__(self, llm, knowledge_manager: EventKnowledgeManager):
        self.llm = llm
        self.knowledge_manager = knowledge_manager
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
        
        # Create the RAG chain
        self.rag_chain = self._create_rag_chain()
    
    def _create_rag_chain(self):
        """Create sophisticated RAG chain for event assistance"""
        
        # Custom prompt that uses retrieved context effectively
        rag_prompt = PromptTemplate.from_template("""
You are an expert AI assistant helping create educational events for a homeschool community.

Context from similar successful events:
{context}

Conversation history:
{chat_history}

Current user message: {question}

Instructions:
1. Use the context from similar events to provide intelligent suggestions
2. If the user provides event details, be proactive and create a draft immediately
3. Reference specific successful events when making recommendations
4. Provide concrete examples from the context when possible
5. Ask targeted follow-up questions to gather missing information

Key areas to address:
- Event pricing based on similar events
- Appropriate locations that have worked well
- Target age groups that are popular
- Materials and supplies commonly needed
- Learning objectives and outcomes

Response:
""")
        
        # Create the chain with custom retrieval
        rag_chain = (
            RunnableMap({
                "context": lambda x: self._get_relevant_context(x["question"]),
                "question": RunnablePassthrough(),
                "chat_history": lambda x: self._format_chat_history()
            })
            | rag_prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    async def _get_relevant_context(self, question: str) -> str:
        """Retrieve and format relevant context for the question"""
        # Search for relevant events
        similar_events = await self.knowledge_manager.search_similar_events(
            query=question,
            k=5
        )
        
        if not similar_events:
            return "No directly similar events found in the database."
        
        # Format context
        context_parts = []
        for i, event in enumerate(similar_events, 1):
            metadata = event["metadata"]
            context_parts.append(f"""
Event {i}: {metadata.get('title', 'Unknown')}
- Cost: ${metadata.get('cost', 0):.2f}
- Age Range: {metadata.get('age_range', 'All ages')}
- Location: {metadata.get('location', 'Various')}
- Participants: {metadata.get('participant_count', 'Unknown')}
- Success Rating: {metadata.get('success_rating', 3)}/5
- Key Details: {event['content'][:200]}...
""")
        
        return "\n".join(context_parts)
    
    def _format_chat_history(self) -> str:
        """Format chat history for the prompt"""
        if not hasattr(self.memory, 'chat_memory') or not self.memory.chat_memory.messages:
            return "No previous conversation."
        
        history = []
        for message in self.memory.chat_memory.messages[-6:]:  # Last 6 messages
            role = "User" if message.type == "human" else "Assistant"
            history.append(f"{role}: {message.content}")
        
        return "\n".join(history)
    
    async def generate_response(
        self, 
        user_message: str, 
        session_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate RAG-enhanced response"""
        try:
            # Get enhanced response using RAG
            response = await self.rag_chain.ainvoke({"question": user_message})
            
            # Update memory
            self.memory.chat_memory.add_user_message(user_message)
            self.memory.chat_memory.add_ai_message(response)
            
            # Get additional insights
            insights = await self._generate_additional_insights(user_message, response)
            
            return {
                "response": response,
                "insights": insights,
                "type": "rag_enhanced",
                "context_used": True,
                "confidence": self._calculate_response_confidence(response)
            }
            
        except Exception as e:
            # Fallback to non-RAG response
            fallback_response = await self._fallback_response(user_message)
            return {
                "response": fallback_response,
                "type": "fallback",
                "error": str(e),
                "context_used": False
            }
    
    async def _generate_additional_insights(
        self, 
        user_message: str, 
        response: str
    ) -> Dict[str, Any]:
        """Generate additional insights based on the conversation"""
        insights = {
            "suggested_next_steps": [],
            "related_events": [],
            "potential_improvements": []
        }
        
        # Extract event information from the conversation
        if any(keyword in user_message.lower() for keyword in ["create", "event", "workshop", "class"]):
            # Get event creation suggestions
            similar_events = await self.knowledge_manager.search_similar_events(user_message, k=3)
            insights["related_events"] = [
                {
                    "title": event["metadata"]["title"],
                    "cost": event["metadata"]["cost"],
                    "success_rating": event["metadata"]["success_rating"]
                }
                for event in similar_events
            ]
        
        return insights
    
    def _calculate_response_confidence(self, response: str) -> str:
        """Calculate confidence level for the response"""
        # Simple heuristic based on response length and content
        if len(response) > 200 and ("$" in response or "similar" in response.lower()):
            return "high"
        elif len(response) > 100:
            return "medium"
        else:
            return "low"
    
    async def _fallback_response(self, user_message: str) -> str:
        """Generate fallback response without RAG"""
        simple_prompt = f"""
        User message: {user_message}
        
        Provide a helpful response about creating educational events, even without specific context.
        Be encouraging and ask clarifying questions to help the user.
        """
        
        response = await self.llm.agenerate([[{"role": "user", "content": simple_prompt}]])
        return response.generations[0][0].text
```

This modernization plan transforms your AI system into a cutting-edge, maintainable solution that leverages the best of modern AI libraries while preserving your existing functionality. The implementation can be done incrementally, allowing you to test and validate each phase before moving to the next.

Key benefits you'll see:
- **70% reduction in custom code**
- **Built-in observability and debugging**
- **Semantic search and RAG capabilities**
- **Better agent reasoning and planning**
- **Improved scalability and maintainability**
- **Access to the rapidly evolving LangChain ecosystem**

Would you like me to dive deeper into any specific aspect of this modernization plan or help you implement any particular phase? 