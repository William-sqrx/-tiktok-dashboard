import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
