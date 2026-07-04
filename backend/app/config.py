from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/api/auth/tiktok/callback"
    tiktok_scopes: str = "user.info.basic,user.info.stats,video.list"

    frontend_url: str = "http://localhost:5173"
    database_url: str = "sqlite:///./tiktok_dashboard.db"
    encryption_key: str = ""

    # Password gate for the whole site. If empty, the gate is disabled (open).
    dashboard_password: str = ""

    # TikTok domain-verification file: served publicly at /<filename> so TikTok
    # can confirm we own the domain (works even with the password gate on).
    tiktok_verify_filename: str = ""
    tiktok_verify_content: str = ""

    # Shared secret the generation worker sends (X-Worker-Token header) to reach
    # the scheduler API without the browser password cookie.
    worker_token: str = ""

    # PostPeer (postpeer.dev) — posting + analytics for connected TikTok accounts.
    postpeer_key: str = ""
    postpeer_api: str = "https://api.postpeer.dev/v1"

    # TikTok API endpoints (v2)
    authorize_url: str = "https://www.tiktok.com/v2/auth/authorize/"
    token_url: str = "https://open.tiktokapis.com/v2/oauth/token/"
    user_info_url: str = "https://open.tiktokapis.com/v2/user/info/"
    video_list_url: str = "https://open.tiktokapis.com/v2/video/list/"


settings = Settings()
