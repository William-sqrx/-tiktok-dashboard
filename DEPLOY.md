# Deploying your dashboard

This hosts the **whole app as one service** (the Python backend serves the built
React app), plus a managed Postgres database and an automatic sync job — all from
the included [`render.yaml`](render.yaml).

Render is used here because its free tier covers everything this app needs in a
single blueprint. (Railway or Fly.io work too — the Dockerfile is portable.)

There's a chicken-and-egg step: you deploy first to learn your app's URL, then
plug that URL into TikTok and back into Render. The steps below handle it in order.

---

## 1. Put the code on GitHub

```bash
cd tiktok-dashboard
git init && git add -A && git commit -m "TikTok dashboard"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/tiktok-dashboard.git
git push -u origin main
```

## 2. Create the services on Render

1. Sign up at <https://render.com> (free) and connect your GitHub.
2. **New → Blueprint**, pick this repo. Render reads `render.yaml` and proposes a
   web service, a cron job, and a Postgres database. Click **Apply**.
3. The first build takes a few minutes. When it finishes, Render shows your URL,
   e.g. `https://tiktok-dashboard.onrender.com`. **Copy it.** Call it `APP_URL`.

## 3. Register the TikTok app (if you haven't)

Follow **Step 1** in the [README](README.md), but use your live URL for the
Redirect URI instead of localhost:

```
https://<your-app>.onrender.com/api/auth/tiktok/callback
```

Grab the **Client key** and **Client secret**.

## 4. Fill in the secrets on Render

In the Render dashboard → your web service → **Environment**, set:

| Key | Value |
|-----|-------|
| `TIKTOK_CLIENT_KEY` | from TikTok |
| `TIKTOK_CLIENT_SECRET` | from TikTok |
| `TIKTOK_REDIRECT_URI` | `https://<your-app>.onrender.com/api/auth/tiktok/callback` |
| `FRONTEND_URL` | `https://<your-app>.onrender.com` |
| `ENCRYPTION_KEY` | run: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

`DATABASE_URL` is wired automatically from the database. Then on the **cron job**
service, set `APP_URL` to `https://<your-app>.onrender.com`.

Click **Save** — Render redeploys. Visit `…/api/health`; it should say
`"tiktok_configured": true`.

## 5. Use it

Open your app URL, click **Connect account**, log in with TikTok, and repeat for
all 5 accounts (log out of TikTok between each, or use a private window, so you
can pick a different account each time). Hit **Sync all**. Done — the cron job
keeps it fresh from here on.

---

### Notes

- **Free tier sleeps.** Render's free web service spins down when idle, so the
  first visit after a while takes ~30s to wake. Fine for personal use; upgrade to
  a paid instance if you want it always-on.
- **Keep `ENCRYPTION_KEY` stable.** It decrypts stored tokens. If you change it,
  every account has to reconnect. Don't lose it.
- **Sandbox vs production.** Until your TikTok app is approved, only the accounts
  you added as sandbox target users can log in. Submit for review when ready.
- **Redeploys** happen automatically on every `git push`.
