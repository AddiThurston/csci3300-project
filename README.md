# InSiteful Mind

**Live site:** [http://insite.addithurston.com](http://insite.addithurston.com)

InSiteful Mind is a Flask + Upstash Redis web app for guided reflection and mood tracking. Google Sign-In scopes data per user; journal entries, check-ins, questionnaire history, and trends are stored in Redis. **The project is feature-complete** (journal, three-word reflection, full questionnaire check-in, trends with charts, multiple UI themes, optional Gemini insights, and private trends sharing). A **Docker** image is supported for deployment.

**Team:** David Pan, Kysen Krishnaswamy, Addison Thurston, Prabhnoor Singh

## Current project state

**Status:** All planned features for this course build are implemented and the app is deployed in production at the URL above.

### Features

- **Auth:** Google Identity Services on the client, session cookies on the server (`HttpOnly`, `SameSite=Lax`)
- **Journal:** Create, list, search, date filter, delete; optional Gemini side panel for pattern questions
- **Three-word reflection:** Mood slider, word bank, save, and history
- **Guided check-in (questionnaire):** Full 1–5 scale questionnaire on `check-in.html` with per-entry history
- **Trends:** Mood over time (Chart.js), summary metrics, top words; **share trends** with specific Google accounts (email-based access)
- **Themes:** Multiple themes (e.g. light, dark, meadow, forest, twilight) via `settings.html` and `theme-early.js`
- **AI (Gemini):** Server-side `/api/gemini` using recent journal, check-ins, and questionnaire context (requires API key in env)
- **Docker:** `Dockerfile` and `docker-compose.yml` for containerized runs

## Pages

- `login.html` — Google sign-in
- `index.html` — Dashboard / navigation hub (bubble UI)
- `journal.html` — Journal entries + Gemini drawer
- `three-word-reflection.html` — Mood + three-word flow + Gemini
- `check-in.html` — Guided questionnaire + history
- `trends.html` — Charts, metrics, sharing, shared-with-you + Gemini
- `settings.html` — Theme selection

## Backend and data model

The backend is `server.py`; static assets and HTML are served from the repo root.

- Journal: Redis hash `journal:{username}`
- Three-word / mood check-ins: `checkin:{username}`
- Questionnaire responses: `questionnaire:{username}`
- Trends sharing: Redis sets for grants and “shared with me” lookups

## API endpoints (authenticated unless noted)

**Auth**

- `POST /api/auth/google` — verify Google credential, create session
- `GET /api/auth/session` — current session
- `POST /api/auth/logout` — clear session

**Journal**

- `GET /api/entries` — list entries (newest first)
- `POST /api/entries` — create entry (`content` required, `title` optional)
- `DELETE /api/entries/<entry_id>` — delete entry

**Check-ins (three-word)**

- `GET /api/checkin` — list (optional `?limit=`)
- `POST /api/checkin` — create (`words` 1–3, `moodScore`, `moodLabel`)
- `DELETE /api/checkin/<checkin_id>` — delete

**Questionnaire**

- `GET /api/questionnaire` — list responses
- `POST /api/questionnaire` — save one full questionnaire response

**AI**

- `POST /api/gemini` — Gemini insight (uses server-side history for the signed-in user)

**Trends sharing**

- `POST /api/trends/share` — grant access by email
- `DELETE /api/trends/share` — revoke access
- `GET /api/trends/shares` — list viewers you granted
- `GET /api/trends/shared-with-me` — list owners who shared with you
- `GET /api/trends/shared-checkins?owner=email` — viewer fetch (if granted)

## Setup (local)

### Prerequisites

- Python 3.11+ recommended (matches CI / Docker; `google-genai` needs 3.9+)
- Upstash Redis REST URL + token
- Google OAuth client ID (and Gemini API key if you use AI)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/AddiThurston/csci3300-project.git
   cd csci3300-project
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` in the project root (example):

   ```env
   UPSTASH_REDIS_REST_URL=your_redis_url
   UPSTASH_REDIS_REST_TOKEN=your_redis_token
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   FLASK_SECRET_KEY=your_random_secret
   GEMINI_API_KEY=your_gemini_api_key
   COOKIE_SECURE=false
   PORT=3000
   ```

5. Start the app:

   ```bash
   python server.py
   ```

6. Open `http://localhost:3000`.

## Docker

Build the image:

```bash
docker build -t insiteful-mind .
```

Run the container:

```bash
docker run --rm -p 3000:3000 \
  -e UPSTASH_REDIS_REST_URL=your_redis_url \
  -e UPSTASH_REDIS_REST_TOKEN=your_redis_token \
  -e GOOGLE_CLIENT_ID=your_google_oauth_client_id \
  -e FLASK_SECRET_KEY=your_random_secret \
  -e GEMINI_API_KEY=your_gemini_api_key \
  -e COOKIE_SECURE=false \
  -e PORT=3000 \
  insiteful-mind
```

Then open `http://localhost:3000`.

### Docker Compose

From this directory:

```bash
docker compose up --build
```

Compose loads variables from a local `.env` if present. Set at least Redis and secrets (and `GEMINI_API_KEY` if you use AI).

To push the built image to Docker Hub, use a **full image name** `yourdockerhubuser/repo:tag`, then:

```bash
docker login
docker compose build
docker compose push
```

## Testing

Test files:

- `test_journal.py` — journal API
- `test_three.py` — check-in API
- `test_questionnaire.py` — questionnaire API
- `test_redis.py` — Redis helpers
- `test_chat_agent.py` — Gemini / `/api/gemini` contract tests

Run all tests:

```bash
pytest -q
```
