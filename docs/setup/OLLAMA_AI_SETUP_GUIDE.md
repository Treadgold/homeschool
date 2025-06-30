# Multi-Provider AI Event Creation Setup Guide

This system supports **Ollama (local/free)**, **OpenAI**, and **Anthropic** AI providers with admin-configurable model selection.

## 🏠 Option 1: Ollama (Recommended - Free & Local)

### Benefits
- ✅ **Completely FREE** - No API costs
- ✅ **Privacy** - Data stays on your server  
- ✅ **Fast** - Once models are loaded
- ✅ **Offline** - Works without internet
- ✅ **Multiple models** - Llama 3.1, Mistral, CodeLlama

### Installation

1. **Install Ollama**
   ```bash
   # Linux/WSL
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # macOS
   brew install ollama
   
   # Windows: Download from https://ollama.ai
   ```

2. **Pull AI Models**
   ```bash
   # Recommended for event creation (8GB)
   ollama pull llama3.1:8b
   
   # Alternative models
   ollama pull mistral:7b        # Smaller, faster (4GB)
   ollama pull codellama:7b      # Good for structured tasks (4GB)
   ```

3. **Start Ollama Server**
   ```bash
   # Start the server (runs on port 11434)
   ollama serve
   
   # Or run as background service
   sudo systemctl enable ollama
   sudo systemctl start ollama
   ```

4. **Test Installation**
   ```bash
   curl http://localhost:11434/api/chat -d '{
     "model": "llama3.1:8b",
     "messages": [{"role": "user", "content": "Hello!"}],
     "stream": false
   }'
   ```

---

## 🌐 Option 2: OpenAI (API Required)

### Setup
1. Get API key from https://platform.openai.com
2. Add to your environment:
   ```bash
   echo "OPENAI_API_KEY=your_api_key_here" >> .env
   ```

### Cost Estimate
- **GPT-4o-mini**: ~$0.15/1M tokens
- **GPT-4**: ~$5/1M tokens  
- **Estimated**: ~$7.50/month for 50 events

---

## 🧠 Option 3: Anthropic Claude (API Required)

### Setup
1. Get API key from https://console.anthropic.com
2. Add to your environment:
   ```bash
   echo "ANTHROPIC_API_KEY=your_api_key_here" >> .env
   ```

### Features
- Excellent reasoning
- Good tool calling
- Similar pricing to OpenAI

---

## 🚀 Application Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Current Model (Optional)
```bash
# Default is Ollama Llama 3.1, but you can override:
echo "CURRENT_AI_MODEL=ollama_mistral" >> .env

# Available options:
# - ollama_llama3.1 (default)
# - ollama_mistral  
# - ollama_codellama
# - openai_gpt4o_mini
# - openai_gpt4
# - anthropic_claude
```

### 3. Start Your Application
```bash
uvicorn app.main:app --reload
```

### 4. Configure AI Models
1. Login as admin
2. Navigate to **⚙️ AI Models** 
3. Test available models
4. Switch between providers as needed

---

## 🔧 Admin Interface Features

### Model Management
- View all available AI providers
- Test model connectivity
- Switch active model with one click
- Real-time setup instructions

### Model Testing
- Basic connection test
- Chat functionality test
- Sample response preview
- Error diagnostics

### Multi-Provider Support
- **Ollama**: Local models with simulated function calling
- **OpenAI**: Native function calling support
- **Anthropic**: Claude with tool use capabilities

---

## 🛠️ Advanced Configuration

### Custom Ollama Endpoint
```bash
# If Ollama runs on different host/port
echo "OLLAMA_ENDPOINT=http://your-server:11434" >> .env
```

### Model Parameters
Each provider has configurable:
- Max tokens (default: 500)
- Temperature (default: 0.7)  
- Model-specific settings

### Tool Calling Behavior
- **OpenAI/Anthropic**: Native structured function calling
- **Ollama**: Simulated via prompt engineering
- All providers support the same tool definitions

---

## 📊 Performance Comparison

| Provider | Cost | Speed | Privacy | Tool Support |
|----------|------|-------|---------|--------------|
| Ollama | FREE | Fast* | 100% | Simulated |
| OpenAI | Low | Fast | API | Native |
| Anthropic | Low | Fast | API | Native |

*After initial model load (~30 seconds)

---

## 🔍 Troubleshooting

### Ollama Issues
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart service
sudo systemctl restart ollama

# Check logs
journalctl -u ollama -f
```

### API Issues
- Verify API keys in `.env` file
- Check API usage limits
- Ensure network connectivity

### Model Selection
- Use admin interface to test each model
- Check error messages in test results
- Verify environment variables

---

## 🎯 Recommendations

### For Production
1. **Start with Ollama** for cost savings
2. **Have OpenAI as backup** for reliability
3. **Test both** to find what works best

### For Development  
1. **Use Ollama** to avoid API costs during testing
2. **Switch to OpenAI** for comparing response quality
3. **Use admin interface** for easy model switching

### For Performance
- **Ollama**: Keep server running, models loaded
- **OpenAI**: Use GPT-4o-mini for best cost/performance
- **Anthropic**: Good for complex reasoning tasks

---

## 🎉 Next Steps

1. Install your preferred AI provider
2. Start the application
3. Visit `/admin/ai-models` to configure
4. Test event creation at `/ai-create-event`
5. Monitor usage and costs
6. Scale as needed!

The system automatically handles provider differences, so you can switch between them seamlessly based on your needs. 