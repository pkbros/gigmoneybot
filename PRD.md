# SkillToken: Implementation Plan

## Objective
Implement a Telegram-native micro-gig marketplace prototype (v0.1) for college campuses where students can register skills and search for help using natural language. 

## Scope & Constraints
- **In Scope:** Commands `/start`, `/register`, `/search`, `/myskills`. Integration with Supabase (PostgreSQL + pgvector) and Vertex AI (`text-embedding-004`). Webhook-based Telegram bot architecture deployed on Google Cloud Run.
- **Out of Scope:** Payments, ratings, scheduling, admin panel, verification, location filtering.

## Architecture
- **Bot Framework:** `python-telegram-bot` running inside a lightweight asynchronous web framework (e.g., `FastAPI`) to receive webhook requests.
- **Database:** Supabase with `pgvector`. Backend accesses data using the Supabase Service Role Key to bypass RLS.
- **Embeddings:** Google Cloud Vertex AI SDK. Authentication is handled implicitly via GCP application default credentials (ADC) provided by Cloud Run.

## Implementation Steps

### Phase 1: Project Setup & Infrastructure
1. **Initialize Project:** 
   - Create `requirements.txt` with dependencies.
   - Create project structure (`main.py`, `handlers/`, `services/`, `models/`, `sql/`).
2. **Supabase Schema:**
   - Provide SQL migrations for creating `users` and `listings` tables.
   - Setup `pgvector` extension and the cosine similarity index (`ivfflat`).
   - Create a PostgreSQL function for semantic search.

### Phase 2: Core Services Integration
1. **Database Service:** 
   - Create `services/db.py` to handle Supabase connections using the Service Role Key.
2. **AI Service:**
   - Create `services/ai.py` to handle Vertex AI.

### Phase 3: Bot Handlers & Conversation Flows
1. **User Tracking:** Captures info in `users` table.
2. **`/register` Flow:** Multi-step registration.
3. **`/search` Flow:** Semantic similarity lookup.
4. **`/myskills` Flow:** View/Delete listings.

### Phase 4: Webhook & Cloud Run Integration
1. **Web Server Setup:** FastAPI endpoint for `/webhook`.
2. **Lifecycle Management:** Automated `setWebhook` on startup.
