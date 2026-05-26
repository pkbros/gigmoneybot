# 🚀 SkillToken: Campus Micro-Gig Marketplace

SkillToken is a decentralized-style marketplace for college campuses, built as a Telegram bot. It allows students to trade skills, help with micro-tasks (like tutoring, delivery, or quick fixes), and earn small rewards or fees within their own campus community.

## 🌟 Key Features

- **College-Verified Profiles:** Users must register their specific college to ensure a trusted, localized community.
- **AI-Powered Semantic Search:** Uses Google Vertex AI (Gemini Embeddings) to understand intent. You don't need exact keywords; "I'm hungry" will find "Maggi cooking" or "Canteen delivery."
- **Context-Rich Listings:** Mandatory skill descriptions and fees (text-based, e.g., "₹50", "A Treat", or "Free") for clear communication.
- **Global Campus Alerts:** If a search fails, the bot broadcasts a "Skill Request" to all registered users, encouraging the community to fill the gap.
- **Campus Directory:** A `/allskills` view to see every active listing in your specific college.
- **Search Analytics:** Automatically logs every search query and username to track platform demand and identify missing skills.
- **Safe Communication:** Enforces Telegram @username requirements to ensure every helper is reachable via clickable links.

---

## 🏗️ Tech Stack

- **Backend:** Python (FastAPI + Uvicorn)
- **Deployment:** Google Cloud Run (Serverless, scales to zero)
- **Database:** Supabase (PostgreSQL with `pgvector` for AI search)
- **AI Engine:** Google Vertex AI (text-multilingual-embedding-002)
- **Interface:** Telegram Bot API (via `python-telegram-bot`)

---

## 💰 Cost Estimation (The $100 Runway)

Based on current infrastructure and Google Cloud's "Always Free" tier, here is how the project scales:

### 1. Cost per Operation (The "Unit" Cost)
- **Vertex AI Embedding:** ~$0.0001 per query.
- **Cloud Run Compute:** ~$0.00003 per request (covered by Free Tier up to 2M/month).
- **Supabase DB:** $0 (covered by Free Tier up to 500MB storage).

**Average cost per 20 user actions:** ~**$0.15** (unoptimized/pre-credit).

### 2. The "One College" Scenario
*Assumptions: 100 Daily Active Users, each performing 20 operations (Search/Register).*

| Period | Estimated Cost | Why? |
| :--- | :--- | :--- |
| **Daily** | **$0.21 - $0.45** | Includes AI embeddings and keeping a server instance "warm." |
| **Monthly** | **$6.30 - $13.50** | Fits well within standard cloud credits. |
| **Annual** | **$75 - $160** | Without any optimizations or credits. |

### 3. Survival on $100
- **Idle/Development:** $0.00 (Scales to zero).
- **Active Campus Launch:** **7 to 15 months.**
- **With Google Credits:** Potentially **infinite** for the first year (using the $300 trial).

---

## 🛡️ Operational Safety

1. **YOLO Mode Ready:** Deployed via Cloud Build and Cloud Run with automated health checks.
2. **Username Requirement:** Prevents "ghost" listings by ensuring every user is reachable.
3. **Optimized Startup:** Uses "Lazy Loading" for AI models to ensure the bot wakes up in < 5 seconds even after being idle.

---

## 🚀 How to Launch
1. Set up the Telegram Bot via `@BotFather`.
2. Configure environment variables (`SUPABASE_URL`, `TELEGRAM_TOKEN`, etc.).
3. Deploy to Cloud Run: `gcloud run deploy skill-token`.
4. Set the Webhook: `https://<your-url>/webhook`.

**SkillToken: Empowering students, one micro-gig at a time.**
