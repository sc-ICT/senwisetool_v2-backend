import re
import ssl as _ssl

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'application.
    Toutes les valeurs sont lues automatiquement depuis le fichier .env
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ─── Base de données ──────────────────────────────────────────────────────
    DATABASE_URL: str  # peut contenir ?sslmode=require (Supabase, Neon, etc.)

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """URL asyncpg-compatible : retire sslmode (non supporté par asyncpg)."""
        url = self.DATABASE_URL
        # S'assurer qu'on utilise le driver asyncpg
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        # Supprimer sslmode du query string
        url = re.sub(r"[?&]sslmode=\w+", "", url)
        return url.rstrip("?").rstrip("&")

    @property
    def SSL_REQUIRED(self) -> bool:
        """True si l'URL d'origine demandait SSL."""
        return "sslmode=require" in self.DATABASE_URL or "sslmode=verify" in self.DATABASE_URL

    # ─── JWT ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MOBILE_TOKEN_EXPIRE_DAYS: int = 365

    # ─── Email ────────────────────────────────────────────────────────────────
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = "SWT Servey"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # ─── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "SWT Servey"
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    UPLOAD_DIR: str = "uploads"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def mail_enabled(self) -> bool:
        """True si les variables email sont configurées."""
        return bool(self.MAIL_USERNAME and self.MAIL_PASSWORD and self.MAIL_FROM)


# Instance unique partagée dans toute l'application
# On l'importe comme ça depuis n'importe quel fichier :
#   from app.config import settings
settings = Settings()  # type: ignore[call-arg]
