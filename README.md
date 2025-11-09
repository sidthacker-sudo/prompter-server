# Prompt Optimizer API

FastAPI backend service for the Prompt Optimizer Chrome extension. Provides AI-powered prompt scoring, improvement suggestions, and conversation chain features.

## Features

- **Prompt Scoring**: Analyze prompts and assign quality scores (0-100)
- **AI-Powered Improvements**: Generate optimized versions of prompts using Claude AI
- **Next Prompt Suggestions**: Get contextual follow-up prompts based on conversations
- **Metadata Inference**: Automatically categorize and title prompts
- **Rate Limiting**: 10 requests per minute per IP to prevent abuse
- **Security**: CORS restricted to Chrome extension origins only

## API Endpoints

### `POST /score`
Score and improve a prompt.

**Request:**
```json
{
  "text": "write code",
  "api_key": "your-anthropic-api-key"
}
```

**Response:**
```json
{
  "score": 45,
  "rewrite": "As an experienced programmer...",
  "goal": "generate or write code"
}
```

### `POST /suggest-next`
Generate follow-up prompt suggestions.

**Request:**
```json
{
  "last_prompt": "Explain quantum computing",
  "last_response": "Quantum computing is...",
  "api_key": "your-anthropic-api-key"
}
```

**Response:**
```json
{
  "suggestions": [
    "What are the practical applications of quantum computing?",
    "How does quantum computing compare to classical computing?"
  ]
}
```

### `POST /infer-metadata`
Automatically infer title and category for a prompt.

**Request:**
```json
{
  "prompt": "Help me debug this Python function",
  "api_key": "your-anthropic-api-key"
}
```

**Response:**
```json
{
  "title": "Debug Python Function",
  "category": "coding"
}
```

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "prompt-optimizer-api"
}
```

## Deployment

### Railway (Production)

1. **Connect Repository**:
   ```bash
   git clone https://github.com/sidthacker-sudo/prompter-server.git
   cd prompter-server
   ```

2. **Deploy to Railway**:
   - Go to [railway.app](https://railway.app)
   - Create new project from GitHub repo
   - Railway will auto-detect Python and deploy

3. **Configuration**:
   - No environment variables required
   - Users provide API keys via extension settings
   - Procfile handles startup command

### Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Server**:
   ```bash
   uvicorn score_server:app --host 0.0.0.0 --port 8001
   ```

3. **Test**:
   ```bash
   curl http://localhost:8001/health
   ```

## Security Features

- **CORS Protection**: Only accepts requests from `chrome-extension://` origins
- **Rate Limiting**: 10 requests per minute per IP address
- **No API Key Storage**: Users provide their own Anthropic API keys
- **Input Validation**: All requests validated with Pydantic models

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Server**: Uvicorn
- **AI**: Anthropic Claude (Haiku model)
- **Validation**: Pydantic
- **Deployment**: Railway

## License

MIT License - See LICENSE file for details
