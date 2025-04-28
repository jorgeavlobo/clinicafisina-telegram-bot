# bot/config.py
"""
Carrega variáveis de ambiente (.env ou variáveis do contêiner) e
expõe-as para o resto da aplicação.

Suporta dois cenários de Base de Dados:
1.  DATABASE_URL já definida (string completa)
2.  Variáveis granulares DB_HOST / DB_USER / DB_PASSWORD  (gera URL)

Exporta ainda parâmetros de webhook e, agora, as credenciais Redis
necessárias ao RedisStorage da FSM.
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# ───────────────────────────────────────────────────────────────
# .env  (só faz efeito fora de Docker; em Docker já vem por ENV)
# ───────────────────────────────────────────────────────────────
load_dotenv()

# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────
def _need(key: str) -> str:
    """Obtém uma variável de ambiente; falha com RuntimeError se indefinida/vazia."""
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"❌ Missing required config var: {key}")
    return val


# ───────────── Telegram ─────────────
BOT_TOKEN: str = _need("BOT_TOKEN")

# ────────── Webhook settings ─────────
DOMAIN: str       = _need("DOMAIN")                       # ex.: telegram.fisina.pt
WEBAPP_PORT: int  = int(os.getenv("WEBAPP_PORT", "8444")) # porta onde o aiohttp escuta
SECRET_TOKEN: str = _need("TELEGRAM_SECRET_TOKEN")        # cabeçalho X-Telegram-Bot-Api-Secret-Token

WEBHOOK_PATH: str = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL:  str = f"https://{DOMAIN}{WEBHOOK_PATH}"

# ───────────── Base de Dados ─────────────
DATABASE_URL: str | None = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Constrói URL a partir das variáveis individuais
    db_user = _need("DB_USER")
    db_pw   = quote_plus(_need("DB_PASSWORD"))             # escapa ! @ / …
    db_host = _need("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = _need("DB_NAME")
    sslmode = os.getenv("DB_SSLMODE", "disable")           # disable | require | verify-full
    DATABASE_URL = (
        f"postgresql://{db_user}:{db_pw}@{db_host}:{db_port}/{db_name}"
        f"?sslmode={sslmode}"
    )

# ───────────── Redis (FSM) ─────────────
REDIS_HOST:   str = _need("REDIS_HOST")
REDIS_PORT:   int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB:     int = int(os.getenv("REDIS_DB",   "0"))
REDIS_PREFIX: str = os.getenv("REDIS_PREFIX", "fsm")       # chave-prefixo no Redis

# ───────────── Diversos ─────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE: str  = os.getenv("LOCAL_TIMEZONE", "Europe/Zurich")

# ───────────── Timeouts (Menus) ─────────────
MENU_TIMEOUT: int = int(os.getenv("MENU_TIMEOUT", "60"))
MESSAGE_TIMEOUT: int = int(os.getenv("MESSAGE_TIMEOUT", "60"))
