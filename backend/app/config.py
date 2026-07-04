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

    # TikTok API endpoints (v2)
    authorize_url: str = "https://www.tiktok.com/v2/auth/authorize/"
    token_url: str = "https://open.tiktokapis.com/v2/oauth/token/"
    user_info_url: str = "https://open.tiktokapis.com/v2/user/info/"
    video_list_url: str = "https://open.tiktokapis.com/v2/video/list/"


settings = Settings()
