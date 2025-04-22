"""
Configuração central da aplicação 🤖

• Carrega variáveis de ambiente de forma tipada (Pydantic v1.x).
• Expõe‑as no objecto `settings`, acessível em todo o projecto:
      from shared.config import settings
• Acrescenta utilidades (WEBHOOK_URL e DATABASE_URL prontos a usar).
"""

from pydantic import BaseSettings, Field
from functools import lru_cache


class Settings(BaseSettings):
    # ────────────── Credenciais Telegram ──────────────
    BOT_TOKEN:      str = Field(..., env="TELEGRAM_TOKEN")
    SECRET_TOKEN:   str = Field(..., env="TELEGRAM_SECRET_TOKEN")

    # ─────────────── Webhook / domínio ────────────────
    DOMAIN:         str = Field("telegram.fisina.pt", env="DOMAIN")
    WEBHOOK_PORT:   int = Field(8444, env="WEBAPP_PORT")

    # ─────────────────── Redis FSM ────────────────────
    REDIS_HOST:     str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT:     int = Field(6379, env="REDIS_PORT")
    REDIS_DB:       int = Field(0, env="REDIS_DB")
    REDIS_PREFIX:   str = Field("fsm", env="REDIS_PREFIX")

    # ─────────────────── PostgreSQL ───────────────────
    DB_HOST:        str = Field("localhost", env="DB_HOST")
    DB_PORT:        int = Field(5432, env="DB_PORT")
    DB_USER:        str = Field("jorgeavlobo", env="DB_USER")
    DB_PASSWORD:    str = Field("", env="DB_PASSWORD")
    DB_NAME_FISINA: str = Field("fisina", env="DB_NAME_FISINA")
    DB_NAME_LOGS:   str = Field("logs",   env="DB_NAME_LOGS")

    # ──────────────── Conveniências ───────────────────
    LOG_LEVEL:      str = Field("INFO", env="LOG_LEVEL")

    # --------- propriedades calculadas ---------------
    @property
    def WEBHOOK_PATH(self) -> str:
        return f"/{self.BOT_TOKEN}"

    @property
    def WEBHOOK_URL(self) -> str:
        return f"https://{self.DOMAIN}{self.WEBHOOK_PATH}"

    @property
    def DATABASE_URL_FISINA(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME_FISINA}"
        )

    @property
    def DATABASE_URL_LOGS(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME_LOGS}"
        )

    class Config:  # noqa: D106
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# usamos cache para evitar recriações repetidas
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
