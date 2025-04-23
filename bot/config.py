import os
from dotenv import load_dotenv

load_dotenv()  # só funciona fora de Docker ou se montares o ficheiro

def _need(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise RuntimeError(f"❌ Config variável {var} em falta")
    return value

BOT_TOKEN   = _need("BOT_TOKEN")
DB_URL      = _need("DATABASE_URL")
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE    = os.getenv("LOCAL_TIMEZONE", "Europe/Zurich")
