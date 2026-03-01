# bot/main.py

import sys
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Добавляем путь к корневой папке проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import BOT_TOKEN
from bot.database import init_db
from bot.handlers.start import router as start_router
from bot.handlers.commands import router as commands_router
from bot.handlers.documents import router as documents_router
from bot.handlers.chat import router as chat_router

# НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Настраиваем уровни логирования для разных библиотек
logging.getLogger('aiogram').setLevel(logging.INFO)
logging.getLogger('easyocr').setLevel(logging.WARNING)  # Только ошибки EasyOCR
logging.getLogger('bot').setLevel(logging.INFO)  # Наши логи

logger = logging.getLogger(__name__)

# Создание бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    try:
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise
    
    logger.info("🚀 Бот запущен и готов к работе")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🛑 Бот остановлен")
    await bot.session.close()

async def main():
    """Главная функция запуска бота"""
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(commands_router)
    dp.include_router(documents_router)
    dp.include_router(chat_router)
    
    # Регистрация функций запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        logger.info("🚀 Запуск бота в режиме polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())