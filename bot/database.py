# bot/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager
from typing import Generator
import logging

from bot.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)

# Простое формирование строки подключения
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Подключение к БД: {DB_HOST}:{DB_PORT}/{DB_NAME}")

try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )
    
    # Проверяем подключение
    with engine.connect() as conn:
        logger.info("✅ Подключение к базе данных успешно")
        
except Exception as e:
    logger.error(f"❌ Ошибка подключения к базе данных: {e}")
    logger.error(f"URL: {DATABASE_URL.replace(DB_PASSWORD, '****')}")
    raise

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

def init_db():
    try:
        logger.info("Создание таблиц в базе данных...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы успешно созданы")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise

@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Ошибка при работе с БД: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def cleanup_old_messages(days: int = 30):
    """Удаляет сообщения старше N дней"""
    from datetime import datetime, timedelta
    from bot.models import Message
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    with get_session() as session:
        deleted = session.query(Message).filter(
            Message.created_at < cutoff_date
        ).delete()
        logger.info(f"Очистка БД: удалено {deleted} старых сообщений")

def cleanup_old_files(days: int = 7):
    """Удаляет временные файлы старше N дней"""
    import os
    import shutil
    from datetime import datetime, timedelta
    
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        return
    
    cutoff = datetime.now() - timedelta(days=days)
    
    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if os.path.isfile(filepath):
            file_time = datetime.fromtimestamp(os.path.getctime(filepath))
            if file_time < cutoff:
                try:
                    os.remove(filepath)
                    logger.info(f"Удален старый временный файл: {filename}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении {filename}: {e}")