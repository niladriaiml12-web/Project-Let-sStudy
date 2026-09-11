# Let'sStudy — Multi-Tenant Study RAG Platform

An AI-powered academic platform for engineering students. Digitizes handwritten class notes and PYQs, making them searchable and conversational with strict multi-tenant data isolation.

## Tech Stack
- **Backend**: Python + FastAPI
- **Vector DB**: ChromaDB (local persistent)
- **LLM + OCR**: Google Gemini (Vision + text-embedding-004)
- **Relational DB**: SQLite (dev) / PostgreSQL (prod)
- **AI Orchestration**: LangChain

## Quick Start

```bash
# 1. Copy and fill in your env vars
cp .env.example .env

# 2. Install dependencies
uv sync

# 3. Run the dev server
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs
