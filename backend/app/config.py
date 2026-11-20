"""Application settings, read from environment variables or a .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    app_name: str = "PneumoScope"
    database_url: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    var_dir: Path = BACKEND_DIR / "var"
    artifacts_dir: Path = PROJECT_ROOT / "artifacts"
    data_dir: Path = PROJECT_ROOT / "data"
    model_version: str = "v1.1.0"

    max_upload_mb: float = 10.0
    min_image_side: int = 128
    max_image_side: int = 8192
    torch_threads: int = 4

    mlflow_tracking_uri: str | None = None  # used by the training scripts only

    # Login
    secret_key: str | None = None          # generated and stored in var/ if not set
    session_hours: int = 12
    cookie_secure: bool = False
    admin_email: str | None = None         # optional first account, created on start-up
    admin_password: str | None = None
    admin_name: str = "Administrator"

    def get_secret_key(self) -> str:
        if self.secret_key:
            return self.secret_key
        self.var_dir.mkdir(parents=True, exist_ok=True)
        f = self.var_dir / ".secret_key"
        if not f.exists():
            import secrets
            f.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        self.secret_key = f.read_text(encoding="utf-8").strip()
        return self.secret_key

    @field_validator("var_dir", "artifacts_dir", "data_dir", mode="after")
    @classmethod
    def _resolve(cls, v: Path) -> Path:
        return v if v.is_absolute() else (PROJECT_ROOT / v).resolve()

    @property
    def uploads_dir(self) -> Path:
        return self.var_dir / "uploads"

    @property
    def gradcam_dir(self) -> Path:
        return self.var_dir / "gradcam"

    @property
    def models_dir(self) -> Path:
        return self.artifacts_dir / "models"

    @property
    def model_dir(self) -> Path:
        return self.models_dir / self.model_version

    @property
    def datasets_dir(self) -> Path:
        return self.artifacts_dir / "datasets"

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.var_dir / 'pneumoscope.db').as_posix()}"

    @property
    def resolved_mlflow_uri(self) -> str:
        return self.mlflow_tracking_uri or f"sqlite:///{(PROJECT_ROOT / 'mlflow' / 'mlflow.db').as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    def ensure_dirs(self) -> None:
        for d in (self.var_dir, self.uploads_dir, self.gradcam_dir, self.models_dir, self.datasets_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
