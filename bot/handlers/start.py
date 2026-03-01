# bot/handlers/start.py

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime, timedelta
import os

from bot.database import get_session
from bot.models import User, Document, Message

router = Router()
logger = logging.getLogger(__name__)

# Главное меню
def get_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📎 Загрузить документ", callback_data="upload_doc")],
        [InlineKeyboardButton(text="📄 Мои документы", callback_data="my_docs")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="reset_chat")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню работы с документом
def get_document_actions_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📝 Показать полный текст", callback_data=f"show_text_{doc_id}")],
        [InlineKeyboardButton(text="🤖 Задать вопрос по документу", callback_data=f"ask_doc_{doc_id}")],
        [InlineKeyboardButton(text="🗑 Удалить документ", callback_data=f"delete_doc_{doc_id}")],
        [InlineKeyboardButton(text="📋 Все документы", callback_data="my_docs")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню для режима вопросов (с сохранением текста)
def get_question_mode_keyboard(doc_id: int, show_text: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if show_text:
        buttons.append([InlineKeyboardButton(text="📝 Показать текст документа", callback_data=f"show_text_{doc_id}")])
    buttons.extend([
        [InlineKeyboardButton(text="❌ Выйти из режима", callback_data="exit_question_mode")],
        [InlineKeyboardButton(text="📋 К списку документов", callback_data="my_docs")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Навигационное меню
def get_navigation_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="📎 Загрузить ещё", callback_data="upload_doc")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню после показа текста
def get_after_text_keyboard(doc_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🤖 Задать вопрос по документу", callback_data=f"ask_doc_{doc_id}")],
        [InlineKeyboardButton(text="📋 К списку документов", callback_data="my_docs")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    try:
        with get_session() as session:
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                user = User(
                    telegram_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                logger.info(f"Новый пользователь: {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    
    welcome_text = (
        f"👋 Привет, {first_name or 'пользователь'}!\n\n"
        "📄 Я бот для анализа документов с искусственным интеллектом.\n\n"
        "🔹 <b>Что я умею:</b>\n"
        "• Принимать PDF, Word и изображения (JPG, PNG)\n"
        "• Извлекать текст даже с картинок\n"
        "• Отвечать на вопросы по документам\n"
        "• Хранить историю ваших документов\n\n"
        "👇 <b>Выберите действие:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
    except:
        await callback.message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == "help")
async def help_menu(callback: types.CallbackQuery):
    """Помощь и инструкция"""
    help_text = (
        "📚 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ <b>Загрузите документ</b>\n"
        "   • 📄 PDF файлы\n"
        "   • 📝 Word документы (DOC, DOCX)\n"
        "   • 🖼 Изображения (JPG, PNG)\n\n"
        "2️⃣ <b>После обработки</b>\n"
        "   • Бот извлечёт весь текст\n"
        "   • Появится меню действий\n\n"
        "3️⃣ <b>Что можно делать:</b>\n"
        "   • 📝 Посмотреть полный текст документа\n"
        "   • 🤖 Задать вопрос по документу\n"
        "   • 🗑 Удалить документ\n"
        "   • 📋 Посмотреть все документы\n\n"
        "4️⃣ <b>Особенности:</b>\n"
        "   • ИИ отвечает только по вашим документам\n"
        "   • История диалога сохраняется\n"
        "   • Можно очистить историю кнопкой\n"
        "   • Документы удаляются полностью из базы\n\n"
        "🔹 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/reset - Очистить историю"
    )
    
    try:
        await callback.message.edit_text(help_text, reply_markup=get_main_keyboard())
    except:
        await callback.message.answer(help_text, reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "upload_doc")
async def upload_doc_prompt(callback: types.CallbackQuery):
    """Приглашение загрузить документ"""
    text = (
        "📎 <b>Загрузите документ</b>\n\n"
        "Отправьте мне файл в одном из форматов:\n"
        "• 📄 PDF (документы)\n"
        "• 📝 Word (DOC, DOCX)\n"
        "• 🖼 JPG / PNG (фото, скриншоты)\n\n"
        "Я извлеку текст и предложу дальнейшие действия!"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=get_navigation_keyboard())
    except:
        await callback.message.answer(text, reply_markup=get_navigation_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "my_docs")
async def my_documents(callback: types.CallbackQuery):
    """Список всех документов пользователя"""
    user_id = callback.from_user.id
    
    try:
        # Получаем документы в отдельной сессии и сразу извлекаем данные
        docs_data = []
        with get_session() as session:
            docs = session.query(Document).filter(
                Document.user_id == user_id
            ).order_by(Document.created_at.desc()).all()
            
            # Извлекаем все данные из сессии, пока она открыта
            for doc in docs:
                # Корректируем время (UTC+3 для Москвы)
                created_at = doc.created_at + timedelta(hours=3)
                docs_data.append({
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'mime_type': doc.mime_type,
                    'created_at': created_at.strftime("%d.%m.%Y %H:%M")
                })
        
        if not docs_data:
            await callback.message.edit_text(
                "📭 У вас пока нет загруженных документов.\n\n"
                "Нажмите «Загрузить документ», чтобы начать!",
                reply_markup=get_main_keyboard()
            )
            await callback.answer()
            return
        
        # Создаем красивое меню со всеми документами
        buttons = []
        for i, doc in enumerate(docs_data, 1):
            # Обрезаем длинные названия
            name = doc['file_name']
            if len(name) > 30:
                name = name[:30] + "..."
            
            # Добавляем иконку в зависимости от типа
            if doc['mime_type'] == 'application/pdf':
                icon = "📄"
            elif doc['mime_type'] in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                icon = "📝"
            else:
                icon = "🖼"
            
            buttons.append([InlineKeyboardButton(
                text=f"{icon} {i}. {name} ({doc['created_at']})", 
                callback_data=f"select_doc_{doc['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            "📄 <b>Ваши документы</b>\n\n"
            "Выберите документ для работы:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при получении документов: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("select_doc_"))
async def select_document(callback: types.CallbackQuery):
    """Выбор конкретного документа для работы"""
    doc_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    try:
        # Получаем данные документа
        doc_data = None
        with get_session() as session:
            doc = session.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id
            ).first()
            
            if doc:
                # Корректируем время
                created_at = doc.created_at + timedelta(hours=3)
                doc_data = {
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'mime_type': doc.mime_type,
                    'created_at': created_at.strftime("%d.%m.%Y %H:%M"),
                    'text_length': len(doc.text) if doc.text else 0,
                    'word_count': len(doc.text.split()) if doc.text else 0
                }
        
        if not doc_data:
            await callback.message.edit_text(
                "❌ Документ не найден.",
                reply_markup=get_main_keyboard()
            )
            await callback.answer()
            return
        
        # Иконка для типа документа
        if doc_data['mime_type'] == 'application/pdf':
            icon = "📄"
            type_text = "PDF документ"
        elif doc_data['mime_type'] in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            icon = "📝"
            type_text = "Word документ"
        else:
            icon = "🖼"
            type_text = "Изображение"
        
        text = (
            f"{icon} <b>{doc_data['file_name']}</b>\n\n"
            f"📅 Загружен: {doc_data['created_at']}\n"
            f"📊 Тип: {type_text}\n"
            f"📝 Символов: {doc_data['text_length']}\n"
            f"🔤 Слов: {doc_data['word_count']}\n\n"
            f"👇 <b>Выберите действие:</b>"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_document_actions_keyboard(doc_id)
        )
    except Exception as e:
        logger.error(f"Ошибка при выборе документа: {e}")
        await callback.message.edit_text(
            "❌ Ошибка загрузки документа.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("show_text_"))
async def show_document_text(callback: types.CallbackQuery):
    """Показать полный текст документа"""
    doc_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    try:
        # Получаем текст документа
        doc_text = ""
        doc_name = ""
        
        with get_session() as session:
            doc = session.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id
            ).first()
            
            if not doc or not doc.text:
                await callback.message.edit_text(
                    "❌ Текст документа не найден.",
                    reply_markup=get_main_keyboard()
                )
                await callback.answer()
                return
            
            doc_text = doc.text
            doc_name = doc.file_name
        
        # Сохраняем в памяти, что мы показывали этот текст
        # (это нужно для кнопки "Задать вопрос")
        
        # Отправляем заголовок
        await callback.message.edit_text(
            f"📄 <b>{doc_name}</b>\n\n"
            f"<b>Полный текст документа:</b>"
        )
        
        # Разбиваем текст на части по 3500 символов
        parts = [doc_text[i:i+3500] for i in range(0, len(doc_text), 3500)]
        
        # Отправляем каждую часть
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Последняя часть с кнопками
                await callback.message.answer(
                    f"<code>{part}</code>",
                    reply_markup=get_after_text_keyboard(doc_id)
                )
            else:
                # Промежуточная часть
                await callback.message.answer(
                    f"<code>{part}</code>\n\n<i>→ продолжение следует...</i>"
                )
        
    except Exception as e:
        logger.error(f"Ошибка при показе текста: {e}")
        await callback.message.answer(
            "❌ Ошибка загрузки текста.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_doc_"))
async def delete_document_prompt(callback: types.CallbackQuery):
    """Подтверждение удаления документа"""
    doc_id = int(callback.data.split("_")[2])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{doc_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"select_doc_{doc_id}")]
    ])
    
    await callback.message.edit_text(
        "🗑 <b>Удаление документа</b>\n\n"
        "Вы уверены, что хотите удалить этот документ?\n"
        "Все связанные с ним сообщения также будут удалены.",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def confirm_delete_document(callback: types.CallbackQuery):
    """Подтвержденное удаление документа"""
    doc_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    try:
        with get_session() as session:
            # Удаляем документ (связанные сообщения удалятся автоматически)
            doc = session.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id
            ).first()
            
            if doc:
                file_name = doc.file_name
                session.delete(doc)
                logger.info(f"Документ {doc_id} ({file_name}) удален пользователем {user_id}")
                
                await callback.message.edit_text(
                    f"✅ Документ <b>{file_name}</b> успешно удален!",
                    reply_markup=get_main_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "❌ Документ не найден.",
                    reply_markup=get_main_keyboard()
                )
    except Exception as e:
        logger.error(f"Ошибка при удалении документа: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при удалении документа.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == "reset_chat")
async def reset_chat_prompt(callback: types.CallbackQuery):
    """Подтверждение сброса истории"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, очистить всё", callback_data="confirm_reset")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(
            "🗑 <b>Очистка истории</b>\n\n"
            "Вы уверены, что хотите удалить всю историю переписки?\n"
            "Документы останутся, удалятся только сообщения.",
            reply_markup=keyboard
        )
    except:
        await callback.message.answer(
            "🗑 <b>Очистка истории</b>\n\n"
            "Вы уверены, что хотите удалить всю историю переписки?\n"
            "Документы останутся, удалятся только сообщения.",
            reply_markup=keyboard
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == "confirm_reset")
async def confirm_reset(callback: types.CallbackQuery):
    """Подтвержденный сброс истории"""
    user_id = callback.from_user.id
    
    try:
        with get_session() as session:
            from bot.models import Message
            deleted = session.query(Message).filter(
                Message.user_id == user_id
            ).delete()
        
        await callback.message.edit_text(
            f"✅ История диалога очищена!\n"
            f"Удалено сообщений: {deleted}",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при сбросе: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при очистке.",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()