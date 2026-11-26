from __future__ import annotations

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database
    sqlite_db_path: str = str(BASE_DIR / "backend" / "database" / "comic_factory.db")

    # LLM Engine (local Ollama by default; optional 'gemini' for headless CI/GitHub Actions)
    llm_provider: str = "ollama"  # ollama | gemini
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 180
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ComfyUI
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_checkpoint: str = "dreamshaper_8.safetensors"
    comfyui_width: int = 1080
    comfyui_height: int = 1350
    comfyui_steps: int = 25
    comfyui_cfg: float = 7.5
    comfyui_enable_fallback_renderer: bool = True

    # Instagram Graph API (supports both INSTAGRAM_* and IG_* env names)
    instagram_access_token: str = ""
    instagram_account_id: str = ""
    ig_access_token: str = ""
    ig_user_id: str = ""
    instagram_graph_api_version: str = "v21.0"
    instagram_app_id: str = ""
    instagram_app_secret: str = ""

    @property
    def resolved_instagram_access_token(self) -> str:
        return self.instagram_access_token or self.ig_access_token

    @property
    def resolved_instagram_account_id(self) -> str:
        return self.instagram_account_id or self.ig_user_id

    # Media Hosting
    media_hosting_provider: str = "local"  # local | cloudflare_r2 | local_tunnel | github_raw
    github_repository: str = ""
    github_branch: str = "main"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "ai-comic-factory"
    r2_public_url: str = ""
    cloudflare_tunnel_url: str = ""

    # Automation & Scheduling
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Asia/Kolkata"
    default_carousel_post_hour: int = 10
    default_individual_post_hour: int = 18
    n8n_webhook_url: str = "http://localhost:5678/webhook/comic-factory"
    n8n_api_key: str = ""

    # Security
    admin_api_key: str = "change-me-local-secret"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def generated_dir(self) -> Path:
        return BASE_DIR / "generated"

    @property
    def logs_dir(self) -> Path:
        return BASE_DIR / "logs"

    @property
    def comfyui_workflows_dir(self) -> Path:
        return BASE_DIR / "comfyui" / "workflows"


settings = Settings()
