from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Mandatory
    NVIDIA_API_KEY: str
    
    # Optional with Defaults
    NVIDIA_MODEL: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 20
    CHROMA_PERSIST_DIR: str = "chroma_store"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def upload_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent.parent
        path = base_dir / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        base_dir = Path(__file__).resolve().parent.parent.parent
        path = base_dir / self.CHROMA_PERSIST_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Using pydantic-settings to load .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(Path(__file__).parent.parent.parent, ".env"),
        extra="ignore"
    )

try:
    settings = Settings()
except Exception as e:
    # Print a clean error if validation fails (e.g. missing API key)
    import sys
    print(f"\n[BACKEND CONFIG ERROR] Initialization failed: {e}")
    print("Please ensure your 'backend/.env' file exists and contains NVIDIA_API_KEY.\n")
    # We allow the app to import but it will likely fail later if we don't exit.
    # However, to avoid crashing the whole import chain if not desired, 
    # we could just set a flag. But the user said "raise a clean readable backend error".
    # We'll re-raise or exit.
    sys.exit(1)
