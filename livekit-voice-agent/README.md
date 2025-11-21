# LiveKit Voice Agent

Voice AI agent built with LiveKit Agents framework for banking services.

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up Presidio (PII masking) - OPTIONAL:**
   ```bash
   ./setup_presidio.sh
   ```
   This will download the spaCy English language model required by Presidio.
   
   **Note:** PII masking is disabled by default. To enable it, set:
   ```bash
   export ENABLE_PII_MASKING=true
   ```
   Or add `ENABLE_PII_MASKING=true` to your `.env` file.

3. **Configure environment variables:**
   Create a `.env` file with:
   ```bash
   # LiveKit
   LIVEKIT_URL=wss://your-livekit-server.com
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   
   # AI Gateway (APIM) - Recommended
   AI_GATEWAY_ENDPOINT=https://<your-gateway-endpoint>/openai/v1
   AI_GATEWAY_API_KEY=your-gateway-api-key
   
   # AI Model Configuration (optional)
   AI_MODEL_ID=gpt-4.1-mini  # Options: gpt-4.1-mini, gpt-4.1
   AI_MODEL_NAME=GPT-4.1 Mini  # Display name (optional)
   
   # OpenAI (for LLM) - Fallback if AI Gateway not configured
   OPENAI_API_KEY=your-openai-key
   
   # AssemblyAI (for STT)
   ASSEMBLYAI_API_KEY=your-assemblyai-key
   
   # Deepgram (alternative STT)
   DEEPGRAM_API_KEY=your-deepgram-key
   
   # Redis Configuration - REQUIRED for session context memory
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=  # Optional, leave empty if no password
   REDIS_DB=0  # Database number (0-15)
   ```
   
   **Note:** If `AI_GATEWAY_ENDPOINT` and `AI_GATEWAY_API_KEY` are set, the agent will use the APIM gateway. Otherwise, it falls back to direct OpenAI API using `OPENAI_API_KEY`.
   
   **Redis Configuration:** Redis is required for the agent to remember conversation context across turns. Without Redis, the agent will not retain previous context.

## Running the Agent

### Development Mode (Console)
```bash
uv run python agent.py dev
```

### Production Mode (Worker)
```bash
uv run python agent.py start
```

### With Custom Options
```bash
uv run python agent.py dev --log-level debug
```

## Troubleshooting

### "No module named pip" Error
This error occurs when using incorrect command syntax. Always use:
```bash
uv run python agent.py [command]
```
NOT: `uv run agent.py [command]`

### Proxy Issues
If you see proxy timeout errors, you may need to:
1. Configure proxy settings in your environment
2. Or disable proxy for local development:
   ```bash
   unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
   ```

### PII Masking Configuration

PII masking is **optional** and disabled by default. The agent will work fine without it.

**To enable PII masking:**
1. Install Presidio dependencies:
   ```bash
   ./setup_presidio.sh
   ```
2. Set environment variable:
   ```bash
   export ENABLE_PII_MASKING=true
   ```
   Or add to `.env`:
   ```
   ENABLE_PII_MASKING=true
   ```

**To disable PII masking:**
- Simply don't set `ENABLE_PII_MASKING` (or set it to `false`)
- The agent will work normally without masking

**PII Masking Module:**
- PII masking code is in `pii_masking.py` (separate module)
- Uses Presidio Analyzer and Anonymizer
- Gracefully handles missing dependencies (returns text as-is if Presidio not installed)

### Presidio Model Not Found
If you get errors about missing spaCy model (only needed if PII masking is enabled):
```bash
uv run python -m spacy download en_core_web_lg
```

