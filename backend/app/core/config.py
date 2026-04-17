from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List

class Settings(BaseSettings):
    GEMINI_API_KEY: str = "AIzaSyCHaxTn3P6BJ79qCgFyeQhtXPBKxk05pIk"
    GEMINI_MODEL: str = "gemini-2.0-flash" # Defaulting to a very common stable one if not set
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 20

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def upload_path(self) -> Path:
        # Get the backend root directory (where main.py's parent's parent is)
        base_dir = Path(__file__).resolve().parent.parent.parent
        path = base_dir / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
