#!/bin/bash
# Qdrant + Ollama Setup Verification Script

echo "🔍 Verifying Qdrant + Ollama Setup..."
echo ""

# Check Qdrant
echo "1. Checking Qdrant Docker container..."
if docker ps --filter name=qdrant-gravitea --format "{{.Names}}" | grep -q qdrant-gravitea; then
    echo "   ✅ Qdrant container is running"
    echo "   📍 Web UI: http://localhost:6333/dashboard"
else
    echo "   ❌ Qdrant container not running"
    echo "   🔧 Fix: docker start qdrant-gravitea"
fi

echo ""

# Check Qdrant API
echo "2. Checking Qdrant API..."
if curl -s http://localhost:6333 | grep -q "qdrant"; then
    echo "   ✅ Qdrant API responding"
else
    echo "   ❌ Qdrant API not accessible"
fi

echo ""

# Check Ollama (detect via API since Windows apps may not be on Git Bash PATH)
echo "3. Checking Ollama installation..."
if curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "   ✅ Ollama installed and running"

    # Check for ARCA embedding model (qwen3-embedding)
    if curl -s http://localhost:11434/api/tags | grep -q "qwen3-embedding"; then
        echo "   ✅ qwen3-embedding model available (ARCA collections, 2560 dims)"
    else
        echo "   ⚠️  qwen3-embedding model not found"
        echo "   🔧 Fix: ollama pull qwen3-embedding:4b"
    fi

    # Check for wikis embedding model (nomic-embed-text)
    if curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text"; then
        echo "   ✅ nomic-embed-text model available (wikis collection, 768 dims)"
    else
        echo "   ⚠️  nomic-embed-text model not found"
        echo "   🔧 Fix: ollama pull nomic-embed-text"
    fi
elif command -v ollama &> /dev/null; then
    echo "   ✅ Ollama installed but service not running"
    echo "   🔧 Fix: Start Ollama app or run 'ollama serve'"
else
    echo "   ❌ Ollama not detected (API not responding and not on PATH)"
    echo "   🔧 Fix: Install from https://ollama.com/download"
    echo "   💡 If already installed, start the Ollama app first"
fi

echo ""
echo "4. Summary:"
echo "   Once all checks pass, restart Claude Code to activate Qdrant MCP"
echo "   You can then ingest your ARCA PDFs for semantic search!"
