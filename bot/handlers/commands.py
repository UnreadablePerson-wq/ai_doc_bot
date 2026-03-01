# bot/handlers/commands.py

from aiogram import Router, types
from aiogram.filters import Command
import logging

from bot.database import get_session
from bot.models import Message as Msg, Document, User
from bot.handlers.start import get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("stats"))
async def stats_cmd(message: types.Message):
    """Расширенная статистика"""
    user_id = message.from_user.id
    
    try:
        with get_session() as session:
            # Общая статистика
            msg_count = session.query(Msg).filter(Msg.user_id == user_id).count()
            doc_count = session.query(Document).filter(Document.user_id == user_id).count()
            
            # Статистика по документам
            docs = session.query(Document).filter(Document.user_id == user_id).all()
            total_chars = sum(d.char_count or 0 for d in docs)
            total_words = sum(d.word_count or 0 for d in docs)
            
            # Последняя активность
            last_msg = session.query(Msg).filter(
                Msg.user_id == user_id
            ).order_by(Msg.created_at.desc()).first()
            
            # Количество диалогов с ботом
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            stats_text = (
                f"📊 <b>Ваша статистика</b>\n\n"
                f"👤 <b>Пользователь:</b> @{message.from_user.username or 'нет'}\n"
                f"📅 <b>В боте с:</b> {user.created_at.strftime('%d.%m.%Y') if user else 'неизвестно'}\n\n"
                f"📄 <b>Документы:</b>\n"
                f"• Всего: {doc_count}\n"
                f"• Всего символов: {total_chars:,}\n"
                f"• Всего слов: {total_words:,}\n\n"
                f"💬 <b>Диалоги:</b>\n"
                f"• Сообщений всего: {msg_count}\n"
            )
            
            if last_msg:
                stats_text += f"• Последнее сообщение: {last_msg.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            await message.answer(stats_text, reply_markup=get_main_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")
        await message.answer("❌ Ошибка получения статистики")