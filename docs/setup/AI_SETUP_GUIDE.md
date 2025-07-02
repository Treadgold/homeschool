# 🤖 AI Event Creation Setup Guide - Langraph Edition

## Overview

The AI Event Creation system uses **Langraph workflows** for reliable, production-ready event creation through natural conversation. It features explicit state management, guaranteed tool execution, and support for multiple AI providers (OpenAI, Anthropic, Ollama).

## 🚀 Quick Start (3 Minutes)

### 1. Clone and Start
```bash
git clone https://github.com/yourusername/homeschool-platform.git
cd homeschool-platform

# Start 4-container architecture
docker-compose up --build

# Access AI system
open http://localhost:8000/admin/ai-models  # Admin dashboard
open http://localhost:8000/ai-create-event  # Event creation
```

### 2. Configure AI Provider (Choose One)

#### Option A: OpenAI (Recommended for Production)
```bash
# Add to .env file
OPENAI_API_KEY=sk-proj-your_openai_key_here
CURRENT_AI_MODEL=openai_gpt4_turbo
```

#### Option B: Anthropic Claude  
```bash
# Add to .env file
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
CURRENT_AI_MODEL=anthropic_claude
```

#### Option C: Ollama (Free Local)
```bash
# Install Ollama on Windows host
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.1:8b

# Models auto-detected at http://host.docker.internal:11434
# Set in admin dashboard: /admin/ai-models
```

### 3. Test Langraph Workflow
1. **Go to**: http://localhost:8000/ai-create-event (admin required)
2. **Say**: *"Create a coding workshop for teenagers next Saturday from 2-4pm at the community center, $15 per student, max 20 students"*
3. **Watch** the Langraph workflow execute:
   ```
   ✅ Extract Details Node    - Parsing user input
   ✅ Create Event Draft Node - Building event structure  
   ✅ Check Tickets Node      - Analyzing ticket requirements
   ✅ Add Ticket Types Node   - Creating pricing tiers
   ✅ Generate Response Node  - Preparing user feedback
   ```
4. **Result**: Complete event with all details and ticket types created

## 🏗️ **Architecture Overview**

### **Current Implementation**
```
app/ai/ (Complete AI Subsystem)
├── services/
│   ├── langgraph_event_agent.py  ✅ Langraph workflow engine
│   ├── chat_service.py           ✅ Conversation management
│   ├── health_service.py         ✅ System monitoring
│   └── migration_service.py      ✅ Database operations
├── agents/                       ✅ Multi-agent support
├── tools/                        ✅ 14+ specialized tools
├── providers/                    ✅ Multi-provider management
└── router.py                     ✅ 19 AI endpoints
```

### **Langraph Workflow Engine**
The core AI system uses Langraph for explicit workflow control:

```python
# Workflow nodes (guaranteed execution)
extract_details → create_event → check_tickets → add_ticket → generate_response
                                      ↓               ↓
                               (conditional)    (conditional)
```

**Benefits**:
- **Guaranteed Execution**: Tools always run when conditions are met
- **State Persistence**: Workflow state survives interruptions
- **Explicit Control**: No ambiguous AI behavior or failed tool calls
- **Debugging**: Full visibility into workflow execution

## 🛠️ **Advanced Configuration**

### **Multi-Provider Setup**

#### OpenAI Configuration
```bash
# .env file
OPENAI_API_KEY=sk-proj-...
OPENAI_ORG_ID=org-...              # Optional
OPENAI_PROJECT_ID=proj_...         # Optional
```

**Models Available**:
- `gpt-4-turbo-preview` (Best for complex workflows)
- `gpt-4o-mini` (Cost-effective, fast)
- `gpt-3.5-turbo` (Budget option)

#### Anthropic Configuration  
```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
```

**Models Available**:
- `claude-3-sonnet-20240229` (Balanced performance)
- `claude-3-haiku-20240307` (Fast, efficient)
- `claude-3-opus-20240229` (Most capable)

#### Ollama Configuration
```bash
# Windows host setup
ollama pull llama3.1:8b      # 4GB RAM minimum
ollama pull llama3.1:70b     # 64GB RAM minimum  
ollama pull mistral:7b       # Alternative model
ollama pull codellama:13b    # Code-focused model

# Models automatically appear in admin dashboard
```

### **System Health Monitoring**

Access comprehensive health monitoring:
- **URL**: http://localhost:8000/api/ai/health
- **Admin UI**: http://localhost:8000/admin/ai-models

**Health Checks Include**:
```json
{
  "database": "healthy",
  "ai_providers": {
    "openai": "connected",
    "anthropic": "connected", 
    "ollama": "available"
  },
  "workflows": {
    "langraph_agent": "operational",
    "react_agent": "operational"
  },
  "tools": {
    "total": 14,
    "operational": 14,
    "failed": 0
  }
}
```

## 🧪 **Testing & Validation**

### **Automated Testing**
```bash
# Run comprehensive AI tests
docker-compose --profile test up test

# Test specific components
docker-compose exec app python -m pytest tests/ai/ -v

# Test Langraph workflows specifically  
docker-compose exec app python test_langraph_comparison.py
```

### **Interactive Testing**
The admin dashboard provides interactive testing:

1. **Model Testing**: Test chat, function calling, and workflows
2. **Workflow Visualization**: See Langraph execution in real-time
3. **Performance Monitoring**: Track response times and success rates
4. **Error Debugging**: View detailed error logs and recovery

### **Manual Validation**
Try these test cases in the AI interface:

```
Test Case 1: Simple Event
"Create a book club meeting this Friday at 7pm"

Test Case 2: Complex Event with Tickets
"Create a science workshop for kids 8-12, next Saturday 10am-2pm, 
$15 per child, max 20 students, at the community center"

Test Case 3: Multi-Step Conversation
User: "I want to create a workshop"
AI: "What kind of workshop?"
User: "Cooking class for teenagers"
AI: "When would you like to schedule it?"
User: "Next weekend, Saturday afternoon"
```

## 💰 **Cost Management**

### **Model Cost Comparison**
| Provider | Model | Cost/1M Tokens | Use Case |
|----------|-------|----------------|----------|
| OpenAI | GPT-4 Turbo | $10 | Complex workflows |
| OpenAI | GPT-4o-mini | $0.15 | Cost-effective |
| Anthropic | Claude 3 Sonnet | $3 | Balanced choice |
| Ollama | Local Models | $0 | Free (hardware only) |

### **Cost Optimization**
```bash
# Use cost-effective models for development
CURRENT_AI_MODEL=openai_gpt4o_mini

# Use local models for testing
CURRENT_AI_MODEL=ollama_llama3_1_8b

# Switch to premium for production
CURRENT_AI_MODEL=openai_gpt4_turbo
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### "No AI models available"
```bash
# Check configuration
docker-compose exec app python -c "
from app.ai_providers import AIProviderManager
manager = AIProviderManager()
print(manager.get_available_models())
"
```

#### "Langraph workflow fails"
```bash
# Check Langraph agent status
curl http://localhost:8000/api/ai/health | jq .workflows
```

#### "Ollama not connecting"
```bash
# Test Ollama connectivity from container
docker-compose exec app curl http://host.docker.internal:11434/api/tags
```

### **Debug Mode**
```bash
# Enable detailed logging
DEBUG=true docker-compose up

# Run debug service
docker-compose --profile debug up debug
```

### **Performance Issues**
```bash
# Monitor AI performance
docker-compose exec app python scripts/monitor_ai_performance.py

# Clear request queue
curl -X POST http://localhost:8000/api/ai/clear-queue
```

## 📊 **Production Deployment**

### **Environment Variables**
```bash
# Production .env
DATABASE_URL=postgresql://user:secure_pass@prod_db:5432/homeschool
REDIS_URL=redis://prod_redis:6379
OPENAI_API_KEY=sk-proj-production_key
CURRENT_AI_MODEL=openai_gpt4_turbo

# Security
SECRET_KEY=very_secure_random_key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=INFO
```

### **Health Monitoring**
Set up monitoring endpoints:
- **Health Check**: `GET /api/ai/health`
- **Metrics**: `GET /api/ai/metrics`
- **Status Page**: `GET /admin/ai-models`

### **Scaling Considerations**
```yaml
# docker-compose.prod.yml
services:
  app:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
    environment:
      - AI_MAX_CONCURRENT_REQUESTS=10
      - AI_REQUEST_TIMEOUT=30
```

## 📚 **Additional Resources**

- **[Langraph Documentation](https://langchain-ai.github.io/langgraph/)** - Official Langraph guides
- **[Architecture Design](../architecture/AI_ARCHITECTURE_DESIGN.md)** - Technical architecture
- **[Agent Implementation](../../AGENT_IMPLEMENTATION.md)** - Multi-agent system details
- **[Development Guide](../guides/DEBUG_GUIDE.md)** - Local development setup

## 🎯 **Next Steps**

1. **✅ Complete Setup** - Get AI working with your preferred provider
2. **✅ Test Workflows** - Verify Langraph execution in admin dashboard  
3. **✅ Create Events** - Try the conversational event creation
4. **🔄 Monitor Performance** - Use health dashboard to track AI system
5. **🚀 Production Deploy** - Move to production environment with monitoring

---

**🎉 Your Langraph-powered AI event creation system is ready to transform how users create events!** 