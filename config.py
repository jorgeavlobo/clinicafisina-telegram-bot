"""
config.py

Configuration settings for the Clinica Fisina Telegram bot, including Telegram token,
Redis for FSM storage, and PostgreSQL databases for client data and logs.
Sensitive information is loaded from environment variables for security.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (optional for local development)
load_dotenv()

# Telegram bot configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Redis configuration (for FSM storage)
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_DB = os.getenv('REDIS_DB', 0)
REDIS_PREFIX = os.getenv('REDIS_PREFIX', 'fisina_tel_bot:fsm')

# PostgreSQL database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', 5432)
DB_USER = os.getenv('DB_USER', 'default_user')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME_FISINA = os.getenv('DB_NAME_FISINA', 'fisina')
DB_NAME_LOGS = os.getenv('DB_NAME_LOGS', 'logs')
