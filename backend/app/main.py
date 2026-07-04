import hashlib
import hmac
import os
import re

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import accounts, auth

# Create tables on startup (simple; swap for Alembic migrations if it grows).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TikTok Multi-Account Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)


@app.get("/api/health")
def health():
    configured = bool(settings.tiktok_client_key and settings.tiktok_client_secret)
    return {"status": "ok", "tiktok_configured": configured}


# --- Password gate ----------------------------------------------------------
# A single shared password protects the whole site. Set DASHBOARD_PASSWORD to
# enable it; leave it empty (e.g. local dev) and the gate is off.
AUTH_COOKIE = "dash_auth"

# Matches TikTok's domain-verification filenames, e.g. tiktokABC123.txt
_TIKTOK_VERIFY_RE = re.compile(r"^tiktok([A-Za-z0-9_-]+)\.txt$")

# Paths reachable WITHOUT the password:
#  - /api/health           Render's uptime probe has no cookie
#  - /login, /api/login     the login page and its form POST
#  - the TikTok OAuth callback: TikTok redirects the browser here with a
#    server-validated `state`, so it's safe and must not be blocked
_OPEN_PATHS = {
    "/api/health",
    "/login",
    "/api/login",
    "/api/auth/tiktok/callback",
    # Public legal pages (TikTok requires reachable ToS/Privacy URLs).
    "/terms",
    "/privacy",
}


def _auth_token() -> str:
    """Deterministic cookie value derived from the server's secret."""
    secret = (settings.encryption_key or "dev-secret").encode()
    return hmac.new(secret, b"dashboard-authorized", hashlib.sha256).hexdigest()


@app.middleware("http")
async def password_gate(request: Request, call_next):
    path = request.url.path

    # Serve TikTok's domain-verification files publicly, before any gating, so
    # verification works even with the password gate on. TikTok always names the
    # file tiktok<CODE>.txt with contents
    # "tiktok-developers-site-verification=<CODE>", so we can answer any such
    # request, at the domain root or under any path prefix.
    _m = _TIKTOK_VERIFY_RE.match(path.rsplit("/", 1)[-1])
    if _m:
        return PlainTextResponse(
            f"tiktok-developers-site-verification={_m.group(1)}"
        )

    if not settings.dashboard_password:
        return await call_next(request)  # gate disabled

    # Normalize trailing slashes so e.g. "/terms/" matches "/terms".
    norm = path.rstrip("/") or "/"
    if norm in _OPEN_PATHS or path in _OPEN_PATHS:
        return await call_next(request)
    if request.cookies.get(AUTH_COOKIE) == _auth_token():
        return await call_next(request)
    # Not authenticated.
    if path.startswith("/api/"):
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return RedirectResponse("/login")


_LOGIN_HTML = """<!doctype html>
<html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Sign in</title>
<style>
  body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
    background:#0f0f12;color:#f1f1f4;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  form{background:#17171c;border:1px solid #2a2a34;border-radius:12px;padding:28px;width:300px}
  h1{font-size:18px;margin:0 0 4px}
  p.sub{color:#9a9aa8;font-size:13px;margin:0 0 18px}
  input{width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #2a2a34;
    background:#1e1e26;color:#f1f1f4;font-size:14px}
  button{width:100%;margin-top:12px;padding:11px;border:0;border-radius:8px;background:#ff0050;
    color:#fff;font-size:14px;font-weight:600;cursor:pointer}
  p.err{color:#ffb3c4;font-size:13px;margin:12px 0 0}
</style></head>
<body>
  <form method="post" action="/api/login">
    <h1>TikTok Dashboard</h1>
    <p class="sub">Enter the password to continue.</p>
    <input type="password" name="password" placeholder="Password" autofocus required autocomplete="current-password"/>
    <button type="submit">Sign in</button>
    {{ERROR}}
  </form>
</body></html>"""


@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    msg = '<p class="err">Wrong password — try again.</p>' if error else ""
    return _LOGIN_HTML.replace("{{ERROR}}", msg)


@app.post("/api/login")
def do_login(request: Request, password: str = Form(...)):
    if not settings.dashboard_password or password != settings.dashboard_password:
        return RedirectResponse("/login?error=1", status_code=303)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        AUTH_COOKIE,
        _auth_token(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(AUTH_COOKIE, path="/")
    return resp


_LEGAL_CSS = (
    "max-width:720px;margin:40px auto;padding:0 20px;line-height:1.6;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
    "color:#1a1a1a"
)


@app.get("/terms", response_class=HTMLResponse)
def terms():
    return f"""<!doctype html><html><head><meta charset="utf-8"/>
<title>Terms of Service</title></head><body style="{_LEGAL_CSS}">
<h1>Terms of Service</h1>
<p>This is a private, personal dashboard used by its owner to view analytics for
TikTok accounts they own and have authorized. It is read-only and does not post,
modify, or share any content.</p>
<p>The service is provided "as is", without warranty of any kind. The owner is
responsible for how it is used and for complying with TikTok's Terms of Service.</p>
<p>Access is restricted by a password and by TikTok's own authorization: only
accounts whose owners explicitly sign in and grant permission are shown.</p>
<p>Contact: williamjacob0910@gmail.com</p>
</body></html>"""


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    return f"""<!doctype html><html><head><meta charset="utf-8"/>
<title>Privacy Policy</title></head><body style="{_LEGAL_CSS}">
<h1>Privacy Policy</h1>
<p>This dashboard connects to TikTok accounts via TikTok's official Login Kit
(OAuth). It stores only the access tokens returned by TikTok (encrypted at rest)
and the public profile and video statistics those tokens grant access to
(follower counts, video views, likes, comments, and shares).</p>
<p>It never receives or stores TikTok passwords. Data is used solely to display
each connected account's own performance to the account owner, and is not sold,
shared, or sent to any third party.</p>
<p>You can disconnect an account at any time, which deletes its stored tokens and
data from this application.</p>
<p>Contact: williamjacob0910@gmail.com</p>
</body></html>"""


# --- Serve the built React app (production) ---------------------------------
# In dev, the React dev server runs separately on :5173 and this dir won't exist,
# so we only mount static files when a build is present.
STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(os.path.dirname(__file__), "..", "static"))
_index = os.path.join(STATIC_DIR, "index.html")

if os.path.isdir(STATIC_DIR) and os.path.isfile(_index):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Anything that isn't an API route falls through to the single-page app.
        candidate = os.path.join(STATIC_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_index)
