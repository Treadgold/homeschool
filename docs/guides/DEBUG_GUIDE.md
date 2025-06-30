# 🔧 Agent System Debugging & Testing Guide

## 🚨 **Current Issues Resolved**

### ✅ **Fixed Issues**
1. **Stuck Status Indicator** - Enhanced status clearing and timing
2. **Database Migration Detection** - Automatic health checks and migration prompts
3. **AI Provider Timeout Handling** - Circuit breaker pattern and retry logic
4. **Error Message Improvements** - Specific error types with user-friendly messages
5. **Fallback Mode** - Graceful degradation when AI provider fails

### ✅ **New Enterprise Features**
- **Circuit Breaker Pattern** - Prevents cascading failures
- **Retry Logic with Backoff** - Handles transient failures
- **Database Health Checks** - Validates required tables exist
- **Comprehensive Logging** - Track all system activities
- **Graceful Error Handling** - User-friendly error messages

## 🛠️ **Debugging Steps**

### **Step 1: Check System Health**
Visit: `http://localhost:8000/api/ai/health`

**Expected Response (Healthy System):**
```json
{
  "timestamp": "2025-01-01T12:00:00",
  "overall_status": "healthy",
  "checks": {
    "database": {
      "status": "healthy",
      "missing_tables": [],
      "message": "All required tables present"
    },
    "ai_provider": {
      "status": "healthy",
      "provider": "OllamaProvider",
      "model": "devstral:latest"
    },
    "circuit_breaker": {
      "status": "monitoring",
      "message": "Circuit breaker pattern active for fault tolerance"
    }
  }
}
```

**If Migration Required:**
```json
{
  "overall_status": "requires_migration",
  "checks": {
    "database": {
      "status": "requires_migration",
      "missing_tables": ["chat_conversations", "chat_messages", "agent_sessions"]
    }
  }
}
```

### **Step 2: Run Database Migration**
If health check shows missing tables:

**Option A: Automatic Migration (Recommended)**
1. Visit the AI Event Creator page
2. System will detect missing tables
3. Click "🔧 Run Migration Now" button
4. Wait for success message
5. Refresh the page

**Option B: Manual Migration**
```bash
# Connect to your database and run:
psql -h localhost -U postgres -d homeschool -f migrations/add_agent_tables.sql
```

**Option C: API Migration**
```bash
curl -X POST http://localhost:8000/api/ai/migrate \
  -H "Content-Type: application/json" \
  -b "session=YOUR_SESSION_COOKIE"
```

### **Step 3: Test Agent Functionality**

#### **Basic Conversation Test**
1. Visit: `http://localhost:8000/ai-create-event`
2. Should see: "Hi! I'm here to help you create your event..."
3. Type: "I want to create a zoo trip"
4. Should see proper status updates:
   - "🤔 Agent: Processing your message..."
   - "🔧 Agent: Using tools..." (if tools are called)
   - "⏳ Agent: Waiting for your input"

#### **Tool Usage Test**
1. Ask: "Can we create a zoo trip called Auckland Zoo Adventure 2025 for children aged 5-15?"
2. Watch for:
   - Status indicators changing properly
   - Tools being used (check browser console for logs)
   - Natural language responses incorporating tool results

#### **Error Handling Test**
1. **Timeout Test**: If Ollama is slow, should see timeout messages
2. **Connection Test**: Stop Ollama, should see fallback responses
3. **Recovery Test**: Restart Ollama, should recover automatically

## 📊 **Monitoring & Logs**

### **Browser Console Logs**
Look for these log patterns:
- `✅ Health check passed`
- `🔧 Using X available tools`
- `⚠️ AI provider error, attempting fallback`
- `✅ Tool execution successful`

### **Server Logs**
Look for these patterns:
```
INFO:app.ai_agent:EventCreationAgent initialized for user 2
INFO:app.ai_agent:Getting AI provider for function calling
INFO:app.ai_agent:Using 14 available tools
INFO:app.ai_agent:Executing tool: create_event_draft
INFO:app.ai_agent:Successfully processed message in 2.34s
```

### **Error Patterns to Watch**
```
ERROR:app.ai_agent:Missing required database tables: ['chat_conversations']
ERROR:app.ai_agent:Circuit breaker opened after 5 failures
ERROR:app.ai_agent:AI provider call timed out after 30 seconds
```

## 🎯 **Test Scenarios**

### **Scenario 1: Normal Operation**
1. Start fresh conversation
2. Ask to create an event
3. Provide details step by step
4. Verify tool usage and responses

### **Scenario 2: Database Migration**
1. Drop agent tables (testing only)
2. Visit AI page
3. Should see migration prompt
4. Run migration
5. Test normal operation

### **Scenario 3: AI Provider Issues**
1. Stop Ollama service
2. Try to send message
3. Should see fallback responses
4. Restart Ollama
5. Should recover automatically

### **Scenario 4: Network Issues**
1. Simulate slow network
2. Should see timeout handling
3. Should retry with backoff
4. Should eventually succeed or gracefully fail

## 🔍 **Troubleshooting Common Issues**

### **"No AI model available"**
- **Cause**: Ollama not running or model not loaded
- **Fix**: Start Ollama and ensure devstral:latest is available
- **Check**: `curl http://localhost:11434/api/tags`

### **"Database migration required"**
- **Cause**: Agent tables don't exist
- **Fix**: Run migration via UI or manually
- **Check**: System health endpoint

### **Timeout errors**
- **Cause**: Ollama overloaded or slow
- **Fix**: System will retry automatically, or restart Ollama
- **Check**: Ollama resource usage

### **Status indicator stuck**
- **Cause**: Frontend error handling issue
- **Fix**: Should auto-clear after 5 seconds, or refresh page
- **Check**: Browser console for errors

## 🚀 **Performance Benchmarks**

### **Expected Response Times**
- **Health Check**: < 200ms
- **Start Conversation**: < 500ms
- **Simple Message**: < 2s
- **Tool Usage**: < 5s
- **Migration**: < 10s

### **Reliability Targets**
- **Circuit Breaker**: Opens after 5 failures
- **Retry Logic**: 3 attempts with backoff
- **Timeout Handling**: 30s for AI calls
- **Error Recovery**: Automatic fallback responses

## ✅ **Success Indicators**

Your system is working correctly when:
1. ✅ Health check returns "healthy"
2. ✅ Status indicators clear properly after responses
3. ✅ Agent uses tools (visible in logs and responses)
4. ✅ Error messages are specific and helpful
5. ✅ System recovers from temporary failures
6. ✅ Conversations persist across page navigation
7. ✅ Migration runs successfully when needed

## 📞 **Getting Help**

If issues persist:
1. Check all logs (browser console + server logs)
2. Run health check endpoint
3. Verify Ollama connectivity
4. Ensure database migration completed
5. Check circuit breaker status
6. Review error patterns in logs

The system now has comprehensive error handling and should provide clear guidance on any issues encountered. 