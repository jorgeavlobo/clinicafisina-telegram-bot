# bot/config.py

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()          # carrega .env quando correr fora de Docker
                       # dentro de Docker as vars já vêm do ambiente

def _need(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"❌ Missing config var {key}")
    return v

# Telegram
BOT_TOKEN = _need("BOT_TOKEN")

# Base de dados
# Se DATABASE_URL estiver definido, usa-o; senão compõe a partir dos campos simples
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = _need("DB_USER")
    pw   = quote_plus(_need("DB_PASSWORD"))   # escapa ! @ / etc.
    host = _need("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = _need("DB_NAME")
    ssl  = os.getenv("DB_SSLMODE", "disable")
    DATABASE_URL = (
        f"postgresql://{user}:{pw}@{host}:{port}/{name}?sslmode={ssl}"
    )

# Outros parâmetros
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE  = os.getenv("LOCAL_TIMEZONE", "Europe/Zurich")
