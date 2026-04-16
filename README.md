USE CI FOR:
UI Automation Test Cases
Smoke Test cases
Flaky Test cases
Pytest cases

# InSiteful Mind

InSiteful Mind is a Flask + Upstash Redis web app for lightweight mental-health reflection.
The current build supports journal entries and three-word reflections, with placeholder pages
for the questionnaire and trends dashboard.

**Team:** David Pan, Kysen Krishnaswamy, Addison Thurston, Prabhnoor Singh

## Current Project State

### Implemented
- Journal flow: create, list, search, date-filter, and delete entries
- Three-word reflection flow: mood slider, up to 3 words, save, and recent history view
- Flask API with Redis-backed per-user data


### In Progress / Placeholder
- `check-in.html` is still a questionnaire placeholder
- `trends.html` and `index.html` are placeholder/dashboard shells
- AI-powered feedback/advice is not yet implemented
- Additional production hardening for auth/session lifecycle

## Pages

- `login.html` - Google sign-in UI and client-side credential parsing
- `index.html` - dashboard placeholder and navigation hub
- `journal.html` - journal entry UI (create/search/filter/delete)
- `three-word-reflection.html` - mood slider + word selection + history panel
- `check-in.html` - placeholder for guided questionnaire flow
- `trends.html` - placeholder for trend analytics

## Backend and Data Model

The backend is in `server.py` and serves both static files and API routes.

- Journal entries are stored in Redis hash keys: `journal:{username}`
- Reflection check-ins are stored in Redis hash keys: `checkin:{username}`
- User scoping is done with backend session cookies after Google sign-in

Session cookies are signed by Flask and marked `HttpOnly` and `SameSite=Lax`.

## API Endpoints

All data API routes require an authenticated session cookie.

- `POST /api/auth/google` - verify Google credential and create session
- `GET /api/auth/session` - validate current session
- `POST /api/auth/logout` - clear session cookie

- `GET /api/entries` - list all journal entries (newest first)
- `POST /api/entries` - create journal entry (`content` required, `title` optional)
- `DELETE /api/entries/<entry_id>` - delete one journal entry
- `GET /api/checkin` - list check-ins (supports `?limit=<positive-int>`)
- `POST /api/checkin` - create check-in (`words` 1-3, `moodScore`, `moodLabel`)
- `DELETE /api/checkin/<checkin_id>` - delete one check-in

## Setup

### Prerequisites
- Python 3.x
- Upstash Redis credentials

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
4. Create `.env` in project root:
   ```env
  UPSTASH_REDIS_REST_URL=your_redis_url
  UPSTASH_REDIS_REST_TOKEN=your_redis_token
  GOOGLE_CLIENT_ID=your_google_oauth_client_id
  FLASK_SECRET_KEY=your_random_secret
  COOKIE_SECURE=false
  PORT=3000
   ```
5. Start the app:
   ```bash
   python server.py
   ```
6. Open `http://localhost:3000`.

## Testing

Test files:
- `test_journal.py` - journal API behavior tests
- `test_three.py` - three-word/check-in API behavior tests
- `test_redis.py` - Redis integration checks

Run all tests:
```bash
pytest -q
```

## Near-Term Roadmap

- Implement full questionnaire flow on `check-in.html`
- Build trends visualizations on `trends.html`
- Add AI-assisted journal insights once backend auth/data flows are finalized
