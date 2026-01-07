@'
# Assignment 2 — Review AI Dashboard & Analytics

![Architecture flow](Assignment1/ablation_study_results/architecture_flow.png)

End-to-end system that collects user reviews (rating + free text), generates AI insights for both users and vendors, and serves live analytics with caching.

**Workflow At A Glance**
1. User submits a review (rating + text) from the user dashboard → `POST /reviews`.
2. Backend persists the review (status: pending) and enqueues an analytics job.
3. Client opens/subscribes to WebSocket `/ws/analytics` with job id for real-time updates.
4. Analytics service checks the cache:
   - If cached: returns cached insights immediately via WebSocket.
   - If miss: runs analysis, calls the LLM for richer insights, caches results, and pushes progress + final results via WebSocket.
5. Frontend hides the insights card by default, shows an inline loader during processing, and displays insights when available.

**LLM Usage**
- Provider: Groq API (env `GROQ_API_KEY`).
- Default model: `openai/gpt-oss-20b` (override with `GROQ_MODEL`).
- Prompts produce strict JSON output containing:
  - `ai_summary_user`, `ai_suggestions_user[]`
  - `ai_summary_vendor`, `ai_suggestions_vendor[]`
  - `classification` (one of `product_issue`, `delivery_issue`, `sarcasm`, `genuine`, `other`)
- Fallback: deterministic heuristic summarizer when LLM unavailable or outputs invalid JSON.

**Caching**
- `/analytics/insights` caches results by filter key `(website, product, classification)`.
- Cache invalidation triggers when the latest review timestamp changes.
- Cached payload includes source/created timestamps for staleness checks.

**Backend**
- Framework: FastAPI
- Key endpoints:
  - `POST /reviews` — create review, enqueue job, return job id.
  - `GET /reviews` — list reviews (desc by `created_at`).
  - `GET /analytics/summary` — aggregate counts/averages.
  - `GET /analytics/insights` — cached analytics insight per filter.
  - `GET /health` — health checks.
  - `WS /ws/analytics` — push progress + final insights.
- Persistence: MongoDB (`MONGODB_URI`, default `mongodb://localhost:27017`, DB `review_system`, collection `reviews`).

**Frontend (User Dashboard)**
- Path: `frontend/user dashboard/`
- Two-card layout: form + insights (inline loader inside insights card).
- UX: insights hidden by default; loader appears only after submit; final insights replace loader.
- Health check and WebSocket subscription for real-time analytics updates.

**Optimizations**
- Inline loader to avoid layout thrash / flicker.
- LLM + heuristic fallback for robustness.
- Cache keyed by filter + timestamp invalidation to avoid expensive recompute.
- Async job dispatch + WebSocket broadcast so writes don't block user response.

**Run Locally**
- Backend:
  ```powershell
  cd backend
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  uvicorn app.main:app --reload