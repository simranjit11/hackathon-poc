#!/bin/bash
# Script to check if JWT secrets are configured and match

echo "🔍 Checking JWT Secret Configuration..."
echo ""

# Check Next.js
echo "📦 Next.js (agent-starter-react):"
if [ -f "agent-starter-react/.env.local" ]; then
    NEXTJS_SECRET=$(grep "^AUTH_SECRET_KEY=" agent-starter-react/.env.local | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$NEXTJS_SECRET" ]; then
        echo "  ✅ AUTH_SECRET_KEY is set: ${NEXTJS_SECRET:0:20}..."
    else
        echo "  ⚠️  AUTH_SECRET_KEY not found in .env.local (using default)"
    fi
else
    echo "  ⚠️  .env.local not found (using default)"
fi

# Check MCP Server
echo ""
echo "📦 MCP Server (mcp-server):"
if [ -f "mcp-server/.env" ]; then
    MCP_SECRET=$(grep "^MCP_JWT_SECRET_KEY=" mcp-server/.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$MCP_SECRET" ]; then
        echo "  ✅ MCP_JWT_SECRET_KEY is set: ${MCP_SECRET:0:20}..."
    else
        echo "  ⚠️  MCP_JWT_SECRET_KEY not found in .env (using default)"
    fi
else
    echo "  ⚠️  .env not found (using default)"
fi

# Check Voice Agent
echo ""
echo "📦 Voice Agent (livekit-voice-agent):"
if [ -f "livekit-voice-agent/.env" ]; then
    VOICE_SECRET=$(grep "^MCP_JWT_SECRET_KEY=" livekit-voice-agent/.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$VOICE_SECRET" ]; then
        echo "  ✅ MCP_JWT_SECRET_KEY is set: ${VOICE_SECRET:0:20}..."
    else
        echo "  ⚠️  MCP_JWT_SECRET_KEY not found in .env (using default)"
    fi
else
    echo "  ⚠️  .env not found (using default)"
fi

echo ""
echo "💡 Tip: All three should be set to the SAME value!"
echo "   If they don't match, token validation will fail."
