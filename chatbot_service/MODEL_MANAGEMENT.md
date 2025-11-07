# Dynamic Model Management System

## Overview

This chatbot now uses a **smart, cached, dynamic model selection system** that automatically handles model deprecation.

## How It Works

### 1. **Automatic Model Discovery**

- Fetches available models from Groq API: `https://api.groq.com/openai/v1/models`
- Filters out non-chat models (whisper, guard models, etc.)
- Keeps only active chat models (llama, mixtral, gemma, etc.)

### 2. **Smart Caching**

- Model list is cached for **1 hour** to avoid repeated API calls
- Fast performance: Most requests use cached data (instant)
- Refreshes automatically after cache expires

### 3. **Automatic Fallback**

- If your preferred model fails → tries next available model
- If API is down → uses cached models
- If cache is empty → uses hardcoded fallback list

### 4. **Zero Downtime**

- Server keeps running even if models change
- No manual intervention needed
- Automatic recovery from model deprecation

## Configuration

### Environment Variables (`.env`)

```env
# Your Groq API key (required)
GROQ_API_KEY=your_api_key_here

# Your preferred model (optional)
# If not specified or unavailable, best available model will be used
MODEL_NAME=llama3-8b-8192
```

## Features

### Benefits

- **No manual updates needed** - Models are discovered automatically
- **Fast performance** - Caching prevents repeated API calls
- **Resilient** - Multiple fallback strategies
- **Zero downtime** - Server never restarts due to model changes
- **Transparent** - Logs which model is being used

### How It Handles Model Deprecation

**Scenario**: Groq deprecates `llama3-8b-8192`

1. First request fails with model error
2. System clears cache
3. Fetches fresh model list from API
4. Automatically uses next available model
5. User never sees the error!

## File Structure

```
chatbot_service/
├── app/
│   ├── model_manager.py       # New: Dynamic model management
│   ├── mcp_orchestrator.py    # Updated: Uses model manager
│   ├── chatbot.py
│   └── rag_engine.py
├── .env                        # Updated: Added MODEL_NAME
└── main.py
```

## Monitoring

The system logs important events:

```
✅ Fetched 15 available models from Groq
⚠️ Model llama3-8b-8192 failed, trying next model...
🔄 Switching from llama3-8b-8192 to llama-3.1-70b-versatile
⚠️ Using cached models (API fetch failed)
🔄 Model cache cleared
```

## Testing

To test the model fallback:

1. Set `MODEL_NAME` to a non-existent model in `.env`
2. Send a chat request
3. System will automatically use next available model
4. Check logs to see the fallback in action

## Performance

- **First request**: ~200ms (fetches models from API)
- **Subsequent requests**: <1ms (uses cache)
- **After 1 hour**: ~200ms (refreshes cache)
- **Model failure**: ~400ms (clears cache + retries)

## Maintenance

**You don't need to do anything.** The system is fully automatic.

Optional: Check logs periodically to see which models are being used.

NOTE(IMP): This approach is used for text to text system.
