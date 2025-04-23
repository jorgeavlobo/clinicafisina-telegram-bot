import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN   = os.environ["BOT_TOKEN"]
DB_URL      = os.environ["DATABASE_URL"]
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
TIMEZONE    = os.getenv("LOCAL_TIMEZONE", "Europe/Zurich")
