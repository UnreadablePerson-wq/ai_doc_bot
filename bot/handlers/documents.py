# bot/handlers/documents.py

import os
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from bot.ocr import extract_text
from bot.database import get_session
from bot.models import Document
from bot.handlers.start import get_document_actions_keyboard, get_navigation_keyboard, get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Разрешенные типы файлов (добавлен Word)
ALLOWED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/jpg': 'jpg',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
}

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}

@router.message(F.document)
@router.message(F.photo)
async def handle_document(message: types.Message):
    """Обработчик загрузки документов и фото"""
    user_id = message.from_user.id
    
    # Определяем тип файла
    file_id = None
    file_name = None
    file_size = None
    mime_type = None
    
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
        mime_type = message.document.mime_type
    elif message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_name = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_size = photo.file_size
        mime_type = "image/jpeg"
    
    if not file_id:
        await message.answer("❌ Не удалось получить файл.")
        return
    
    # Проверяем тип файла
    is_allowed = False
    detected_type = "unknown"
    
    if mime_type in ALLOWED_MIME_TYPES:
        is_allowed = True
        detected_type = ALLOWED_MIME_TYPES[mime_type]
    
    if not is_allowed and file_name:
        ext = os.path.splitext(file_name)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            is_allowed = True
            if ext == '.pdf':
                mime_type = 'application/pdf'
                detected_type = 'pdf'
            elif ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
                detected_type = 'jpg'
            elif ext == '.png':
                mime_type = 'image/png'
                detected_type = 'png'
            elif ext in ['.doc', '.docx']:
                if ext == '.doc':
                    mime_type = 'application/msword'
                else:
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                detected_type = 'word'
    
    if not is_allowed:
        await message.answer(
            "❌ Неподдерживаемый тип файла.\n\n"
            "📌 Поддерживаются:\n"
            "• PDF документы\n"
            "• Word документы (DOC, DOCX)\n"
            "• Изображения JPG/PNG"
        )
        return
    
    # Иконка для разных типов
    type_icon = {
        'pdf': '📄',
        'word': '📝',
        'jpg': '🖼',
        'png': '🖼'
    }.get(detected_type, '📎')
    
    # Сообщение о начале обработки
    processing_msg = await message.answer(
        f"{type_icon} <b>Получен файл:</b> {file_name}\n"
        f"⏳ Начинаю обработку... Это может занять некоторое время."
    )
    
    temp_file_path = None
    
    try:
        os.makedirs("temp", exist_ok=True)
        
        # Скачиваем файл
        safe_filename = file_name.replace('/', '_').replace('\\', '_')
        temp_file_path = f"temp/{file_id}_{safe_filename}"
        tg_file = await message.bot.get_file(file_id)
        await message.bot.download_file(tg_file.file_path, temp_file_path)
        
        logger.info(f"Файл скачан: {temp_file_path}")
        
        await processing_msg.edit_text(
            f"{type_icon} Файл получен\n"
            f"🔍 Извлекаю текст..."
        )
        
        # Извлекаем текст
        extracted_text = await extract_text(temp_file_path, mime_type)
        
        if not extracted_text or extracted_text.startswith("Ошибка") or extracted_text.startswith("Не удалось"):
            error_text = extracted_text if extracted_text else "Неизвестная ошибка"
            await processing_msg.edit_text(
                f"❌ Не удалось извлечь текст из файла.\n\n"
                f"Причина: {error_text}\n\n"
                f"Попробуйте другой файл или формат.",
                reply_markup=get_navigation_keyboard()
            )
            return
        
        # Сохраняем в базу данных
        doc_id = None
        try:
            with get_session() as session:
                doc = Document(
                    user_id=user_id,
                    file_name=file_name,
                    file_id=file_id,
                    file_size=file_size,
                    mime_type=mime_type,
                    text=extracted_text[:100000]  # Увеличил лимит до 100k символов
                )
                session.add(doc)
                session.flush()
                doc_id = doc.id
                logger.info(f"Документ сохранен в БД, id={doc_id}")
        except Exception as db_error:
            logger.error(f"Ошибка сохранения в БД: {db_error}")
            await processing_msg.edit_text(
                f"✅ Текст извлечен, но не удалось сохранить в базу.\n\n"
                f"<b>Превью:</b>\n<code>{extracted_text[:300]}...</code>",
                reply_markup=get_navigation_keyboard()
            )
            return
        
        # Подготовка превью
        text_preview = extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text
        word_count = len(extracted_text.split())
        line_count = len(extracted_text.split('\n'))
        
        success_text = (
            f"{type_icon} <b>Документ успешно обработан!</b>\n\n"
            f"📄 <b>Имя:</b> {file_name}\n"
            f"📊 <b>Размер:</b> {file_size // 1024 if file_size else 0} KB\n"
            f"📝 <b>Символов:</b> {len(extracted_text)}\n"
            f"🔤 <b>Слов:</b> {word_count}\n"
            f"📑 <b>Строк:</b> {line_count}\n\n"
            f"<b>Превью текста:</b>\n"
            f"<code>{text_preview}</code>"
        )
        
        await processing_msg.edit_text(
            success_text,
            reply_markup=get_document_actions_keyboard(doc_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке: {e}", exc_info=True)
        await processing_msg.edit_text(
            "❌ Ошибка при обработке документа.",
            reply_markup=get_main_keyboard()
        )
        
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")