#!/bin/bash

# ingest_new.sh — run this whenever you add new PDFs to materials/

echo "📂 Ingesting new materials..."

source venv/bin/activate

# Clear old database so we start fresh
rm -rf db/
mkdir db

python ingest.py

echo "✅ Done! Run ./start.sh to launch the tutor."