#!/bin/bash

# start.sh — launches your AI tutor with one command

cd "$(dirname "$0")"
echo "🎓 Starting AI Tutor..."

# Activate virtual environment
source venv/bin/activate

# Check if Ollama is already running, start it if not
if ! pgrep -x "ollama" > /dev/null; then
    echo "🤖 Starting Ollama in background..."
    ollama serve &
    sleep 3
else
    echo "✅ Ollama already running"
fi

# Smart ingest: run if db is missing OR new/modified PDFs detected
NEEDS_INGEST=false
if [ ! -d "db" ] || [ -z "$(ls -A db 2>/dev/null)" ]; then
    echo "📂 No database found. Indexing materials..."
    NEEDS_INGEST=true
elif [ ! -f ".last_ingest" ]; then
    echo "📂 No ingest record found. Indexing materials..."
    NEEDS_INGEST=true
elif find materials -name "*.pdf" -newer ".last_ingest" | grep -q .; then
    echo "📂 New or updated PDFs detected. Re-indexing..."
    NEEDS_INGEST=true
else
    echo "✅ Course materials up to date"
fi

if [ "$NEEDS_INGEST" = true ]; then
    python ingest.py
fi

# Launch the app
echo "🚀 Launching tutor UI..."
streamlit run app.py
