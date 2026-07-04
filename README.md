# TikTok Multi-Account Dashboard

One dashboard to view performance and videos across all your TikTok accounts.
Built with **FastAPI** (Python) + **React** (Vite/TypeScript).

It connects each account through TikTok's official **Login Kit (OAuth)** and reads
data from the **Display API**. No passwords are ever stored — only short-lived
OAuth tokens, and those are encrypted at rest.

> **Want to put it online?** See [DEPLOY.md](DEPLOY.md) for one-click hosting on
> Render (free tier, includes database + auto-sync). The steps below are for
> running it locally.

```
┌────────────┐   OAuth login    ┌──────────────┐   Display API   ┌──────────┐
│  React UI  │ ───────────────▶ │   FastAPI    │ ──────────────▶ │  TikTok  │
│ dashboard  │ ◀─────────────── │  + SQLite    │ ◀────────────── │   API    │
└────────────┘   your own DB    └──────────────┘   videos/stats  └──────────┘
```

---

## Step 1 — Create your TikTok developer app

You have nothing set up yet, so start here. Everything below works in **sandbox
mode** against your own accounts, so you don't have to wait for app review to build.

1. Go to <https://developers.tiktok.com> and log in with one of your TikTok accounts.
2. **Manage apps → Connect an app** → fill in name/description.
3. In the app, **Add products → Login Kit**. Then add **Display API**.
4. Under Login Kit settings, add a **Redirect URI**, exactly:
   ```
   http://localhost:8000/api/auth/tiktok/callback
   ```
5. Request these scopes: `user.info.basic`, `user.info.stats`, `video.list`.
6. Under **Sandbox**, add each of your 5 TikTok accounts as **target users** so you
   can log them in before the app is approved for production.
7. Copy the **Client key** and **Client secret** — you'll paste them into `.env` next.

> When you're ready to go live (all 5 accounts, no sandbox limits), submit the app
> for review in the developer portal. For deeper analytics (audience demographics,
> views-over-time), also apply for a **TikTok Business Account** and its analytics scopes.

---

## Step 2 — Run the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Generate an encryption key and paste it into .env as ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Also paste your TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET into .env

uvicorn app.main:app --reload --port 8000
```

Check <http://localhost:8000/api/health> — it should show `"tiktok_configured": true`.

## Step 3 — Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Step 4 — Connect your accounts

1. Click **Connect account** → you'll be sent to TikTok to authorize.
2. Log in with account #1, approve. You'll land back on the dashboard.
3. Repeat **Connect account** for the other 4 (log out of TikTok in between, or
   use a private window, so you can pick a different account each time).
4. Click **Sync all** to pull videos + stats.

---

## How it stays fresh

- Each **Sync** pulls current profile stats + videos and writes a dated snapshot.
- The follower-trend chart builds up as snapshots accumulate, so sync regularly.
- To automate it, hit `POST /api/sync` on a schedule. Simplest option is cron:
  ```bash
  # every 6 hours
  0 */6 * * * curl -X POST http://localhost:8000/api/sync
  ```
  (Or run the backend on a small server / Render / Railway and use their scheduler.)

## What each part does

| Path | Purpose |
|------|---------|
| `backend/app/tiktok.py` | OAuth + Display API client (PKCE, token refresh, video/user fetch) |
| `backend/app/sync.py` | Pulls data into the DB, refreshes tokens, writes trend snapshots |
| `backend/app/routers/auth.py` | `/login` and `/callback` OAuth endpoints |
| `backend/app/routers/accounts.py` | Read endpoints + manual sync triggers |
| `backend/app/crypto.py` | Encrypts tokens at rest (Fernet) |
| `frontend/src/App.tsx` | Dashboard: account switcher, KPIs, chart, video grid |

## Notes & limits

- The Display API returns **your own** videos and their public counts (views,
  likes, comments, shares) — perfect for this use case.
- Richer analytics (impressions, audience, watch time) need the Business API +
  approval. The schema here is easy to extend once you have that access.
- This is a **single-user, local** setup. Before deploying publicly, add auth in
  front of the dashboard and move the OAuth `state` store out of memory (e.g. Redis).
