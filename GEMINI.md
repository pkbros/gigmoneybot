# GEMINI.md: Project Instructions

This project is a Telegram bot acting as a micro-gig marketplace for college campuses (SkillToken).

## Architecture & Tech Stack
- **Framework:** `python-telegram-bot` (async).
- **Web Server for Webhooks:** `FastAPI` wrapper to receive updates from Telegram.
- **Hosting:** Google Cloud Run (provides automatic HTTPS for webhooks).
- **Database:** Supabase (PostgreSQL). We use the `pgvector` extension for semantic search.
- **Authentication:** Supabase Service Role Key is used within the backend bot to bypass RLS.
- **Embeddings:** Google Cloud Vertex AI `text-embedding-004`. Authentication relies on GCP Default Credentials provided by Cloud Run.

## Coding Conventions
- **Language:** Python 3.10+
- **Type Hinting:** Use strict type hinting everywhere.
- **Environment Variables:** Managed via `.env` file for local dev, injected by Cloud Run in production.
- **Error Handling:** All external calls (Supabase, Vertex AI, Telegram API) must be wrapped in try/except blocks with informative logging, preventing the bot from crashing.
- **Logging:** Use Python's built-in `logging` module. Avoid raw `print` statements.

## Project Structure
- `main.py`: Entry point, web server initialization.
- `handlers/`: Telegram command handlers (start, register, search, myskills).
- `services/`: External API logic (supabase, vertex_ai).
- `models/`: Pydantic models representing database tables and bot data.
- `sql/`: Database schema and migration scripts.