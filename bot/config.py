# bot/config.py

import os
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Параметры базы данных
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_doc_bot")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не найден в .env")

if not OPENROUTER_API_KEY:
    raise ValueError("❌ OPENROUTER_API_KEY не найден в .env")

if not DB_PASSWORD:
    raise ValueError("❌ DB_PASSWORD не найден в .env")