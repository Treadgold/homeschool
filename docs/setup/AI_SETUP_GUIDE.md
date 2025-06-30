# 🤖 AI Event Creation Setup Guide

## Overview

The AI Event Creation feature allows admin users to create events through natural conversation instead of filling out forms. It uses **GPT-4o-mini** with function calling to interact with your existing booking system.

## Quick Start

### 1. Get OpenAI API Key

1. Sign up at [OpenAI Platform](https://platform.openai.com)
2. Create an API key
3. Add to your `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

The `openai>=1.0.0` package is now included in requirements.txt.

### 3. Test the AI Assistant

1. Start your application: `uvicorn app.main:app --reload`
2. Login as an admin user
3. Click the "🤖 AI Create" button in the navigation
4. Try saying: *"I want to create a science workshop for kids aged 8-12 next Saturday from 10am-2pm at the community center for $15"*

## How It Works

### 🛠️ Tool-Based Architecture

Instead of training a model on your booking logic, the AI uses **function calling** to interact with your existing system:

```python
# The AI can call these functions:
- create_event_draft()        # Create event preview
- check_date_availability()   # Check for conflicts
- get_similar_events()        # Find pricing references
- calculate_suggested_pricing() # Suggest prices
- get_venue_suggestions()     # Recommend venues
```

### 💰 Cost-Effective Model

**GPT-4o-mini** is perfect for this use case:
- **~90% cheaper** than GPT-4 ($0.15/1M tokens vs $5/1M)
- **Excellent tool calling** capabilities
- **Fast response times**
- **Great for conversational interfaces**

### 🔄 Maintainable Design

When you update your booking features, you only need to:
1. Update the tool definitions in `app/ai_tools.py`
2. No model retraining required!
3. Changes take effect immediately

## Example Conversation

```
AI: Hi! I'm here to help you create your event. What kind of event are you planning?

User: I want to run a coding workshop for teenagers

AI: Great! A coding workshop sounds exciting. When would you like to hold this workshop?

User: Next Friday from 2-5pm

AI: Perfect! Next Friday from 2-5pm works well. Where would you like to hold the coding workshop?

User: At the library meeting room

AI: 📅 Next Friday looks perfect - no conflicts!
💰 Similar events typically charge around $12.50
Range: $10.00 - $15.00

✅ Great! I've prepared your event draft.

[Event Preview Shows]
Title: Coding Workshop
Date: 2024-01-19
Location: Library meeting room
Cost: $12.50
```

## File Structure

```
app/
├── ai_assistant.py          # Main AI service using GPT-4o-mini
├── ai_tools.py             # Function definitions for AI to call
├── main.py                 # API endpoints added
└── templates/
    └── ai_create_event.html # Chat interface
```

## API Endpoints

- `POST /api/ai/chat/start` - Start new conversation
- `POST /api/ai/chat/{session_id}/message` - Send message
- `POST /api/ai/chat/{session_id}/create-event` - Create event
- `GET /ai-create-event` - Chat interface page

## Customization

### Adding New Tools

1. Add function to `EventCreationTools` class in `ai_tools.py`
2. Add to `get_tool_definitions()` method
3. Add handler in `send_chat_message()` endpoint

### Changing AI Behavior

Edit the system prompt in `ai_assistant.py`:

```python
def get_system_prompt(self) -> str:
    return """You are a helpful AI assistant for creating homeschool events...
    
    # Add your custom instructions here
    """
```

### Using Different Models

Change the model in `ai_assistant.py`:

```python
self.model = "gpt-4"  # or "gpt-3.5-turbo"
```

## Cost Estimation

### Monthly Usage Example:
- **50 events created** via AI
- **~10 messages per event** (500 total messages)
- **~100 tokens per message** (50,000 total tokens)

**Cost: ~$7.50/month** with GPT-4o-mini

Compare to form-based creation:
- **Time saved**: 10-15 minutes per event
- **User satisfaction**: Higher engagement
- **Error reduction**: AI validates data

## Troubleshooting

### Common Issues:

1. **"Authentication required" error**
   - Make sure `OPENAI_API_KEY` is set in `.env`
   - Restart the application after adding the key

2. **"Invalid date format" error**
   - The AI extracts dates automatically
   - If issues persist, try more specific date formats

3. **Tool execution fails**
   - Check database connection
   - Verify user permissions
   - Check application logs

### Testing Without OpenAI

For development/testing without API costs, you can modify `ai_assistant.py` to return mock responses:

```python
# In ai_assistant.py, add this for testing:
async def chat(self, user_message: str, ...):
    # Mock response for testing
    return {
        "response": f"Mock response to: {user_message}",
        "type": "text",
        "needs_input": True
    }
```

## Next Steps

1. **Try the basic functionality** - Create a few test events
2. **Customize the prompts** - Adjust AI behavior for your needs
3. **Add more tools** - Extend functionality as needed
4. **Monitor usage** - Track costs and performance
5. **Gather user feedback** - Improve based on admin user experience

## Future Enhancements

Consider adding:
- 🎤 **Voice input** for mobile users
- 📊 **Analytics** on AI conversation success rates
- 🔄 **Event templates** based on successful patterns
- 📧 **Email generation** for event confirmations
- 🎨 **Image analysis** for venue photos

The AI assistant is designed to grow with your platform while maintaining cost-effectiveness and ease of maintenance! 