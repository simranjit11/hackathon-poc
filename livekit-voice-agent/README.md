# LiveKit Voice Agent

Voice AI agent built with LiveKit Agents framework for banking services.

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up Presidio (PII masking):**
   ```bash
   ./setup_presidio.sh
   ```
   This will download the spaCy English language model required by Presidio.

3. **Configure environment variables:**
   Create a `.env` file with:
   ```bash
   # LiveKit
   LIVEKIT_URL=wss://your-livekit-server.com
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   
   # OpenAI (for LLM)
   OPENAI_API_KEY=your-openai-key
   
   # AssemblyAI (for STT)
   ASSEMBLYAI_API_KEY=your-assemblyai-key
   
   # Deepgram (alternative STT)
   DEEPGRAM_API_KEY=your-deepgram-key
   ```

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

### Presidio Model Not Found
If you get errors about missing spaCy model:
```bash
uv run python -m spacy download en_core_web_lg
```

