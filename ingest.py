# ingest.py — run this once to load your PDFs into ChromaDB

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

print("📂 Loading PDFs from ./materials ...")
loader = PyPDFDirectoryLoader("./materials")
docs = loader.load()
print(f"✅ Loaded {len(docs)} pages")

print("✂️  Splitting into chunks ...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=60
)
chunks = splitter.split_documents(docs)
print(f"✅ Created {len(chunks)} chunks")

print("🔢 Embedding and storing in ChromaDB ...")
embeddings = OllamaEmbeddings(model="nomic-embed-text")
db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./db"
)
print("✅ Done! Your materials are indexed and ready.")

import pathlib
pathlib.Path(".last_ingest").touch()