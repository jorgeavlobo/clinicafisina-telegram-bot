# bot/config.py
"""
Carrega variáveis de ambiente e expõe-as para o resto da aplicação.

Suporta dois cenários de BD:
1. `DATABASE_URL` já definida (string completa)
2. Variáveis granulares  DB_HOST / DB_USER / DB_PASSWORD  (gera URL)

Também exporta parâmetros de webhook (domain, porta, secret token).
"""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# Carregar .env (apenas útil fora de Docker; dentro já vem tudo)
# ──────────────────────────────────────────────────────────────
load_dotenv()


def _need(key: str) -> str:
    """Levanta RuntimeError se a variável não existir ou for vazia."""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"❌ Missing config var {key}")
    return value


# ───────────── Telegram ─────────────
BOT_TOKEN: str = _need("BOT_TOKEN")

# Webhook (HTTPS)
DOMAIN: str            = _need("DOMAIN")                # ex.: telegram.fisina.pt
WEBAPP_PORT: int       = int(os.getenv("WEBAPP_PORT", 8444))
SECRET_TOKEN: str      = _need("TELEGRAM_SECRET_TOKEN")  # cabeçalho X-Telegram-Bot-Api-Secret-Token
WEBHOOK_PATH: str      = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL: str       = f"https://{DOMAIN}{WEBHOOK_PATH}"

# ───────────── Base de Dados ─────────────
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    user = _need("DB_USER")
    pw   = quote_plus(_need("DB_PASSWORD"))  # escapa ! @ / etc.
    host = _need("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = _need("DB_NAME")
    ssl  = os.getenv("DB_SSLMODE", "disable")  # disable | require | verify-full
    DATABASE_URL = f"postgresql://{user}:{pw}@{host}:{port}/{name}?sslmode={ssl}"

# ───────────── Opções diversas ────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE:  str = os.getenv("LOCAL_TIMEZONE", "Europe/Zurich")
