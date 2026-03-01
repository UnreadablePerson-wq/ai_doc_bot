# bot/handlers/chat.py

import logging
import re
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from bot.database import get_session
from bot.models import Message as Msg, Document
from bot.openrouter_api import ask_openrouter
from bot.handlers.start import get_main_keyboard, get_document_actions_keyboard, get_question_mode_keyboard

router = Router()
logger = logging.getLogger(__name__)

class ChatStates(StatesGroup):
    waiting_for_question = State()

MODELS_PRIORITY = [
    "openrouter/free",
    "google/gemma-3-4b-it:free",
]

def clean_ai_response(text: str) -> str:
    """Очищает ответ от форматирования"""
    if not text:
        return text
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    if len(text) > 4000:
        text = text[:4000] + "...\n\n(сообщение обрезано)"
    return text.strip()

@router.callback_query(lambda c: c.data.startswith("ask_doc_"))
async def ask_document_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Начать режим вопросов по документу"""
    doc_id = int(callback.data.split("_")[2])
    
    # Получаем название документа и превью текста
    doc_name = "документу"
    doc_preview = ""
    
    with get_session() as session:
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc_name = doc.file_name
            if doc.text:
                # Берем первые 500 символов для превью
                doc_preview = doc.text[:500] + "..." if len(doc.text) > 500 else doc.text
    
    await state.update_data(current_doc_id=doc_id)
    await state.set_state(ChatStates.waiting_for_question)
    
    # Формируем сообщение с превью текста
    text = (
        f"🤖 <b>Режим вопросов</b>\n\n"
        f"📄 <b>Документ:</b> {doc_name}\n\n"
    )
    
    if doc_preview:
        text += (
            f"<b>Превью текста:</b>\n"
            f"<code>{doc_preview}</code>\n\n"
        )
    
    text += (
        f"✍️ Напишите ваш вопрос, и я отвечу только на основе этого документа.\n\n"
        f"<i>Для выхода нажмите кнопку ниже</i>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_question_mode_keyboard(doc_id, show_text=True)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "exit_question_mode")
async def exit_question_mode(callback: types.CallbackQuery, state: FSMContext):
    """Выход из режима вопросов"""
    await state.clear()
    await callback.message.edit_text(
        "🏠 Вы вернулись в главное меню",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.message(ChatStates.waiting_for_question)
async def handle_document_question(message: types.Message, state: FSMContext):
    """Обработка вопроса по конкретному документу"""
    user_id = message.from_user.id
    user_text = message.text.strip()
    
    if user_text.startswith('/'):
        return
    
    data = await state.get_data()
    doc_id = data.get("current_doc_id")
    
    if not doc_id:
        await state.clear()
        await message.answer(
            "❌ Ошибка режима.",
            reply_markup=get_main_keyboard()
        )
        return
    
    await message.bot.send_chat_action(chat_id=user_id, action="typing")
    
    try:
        # Получаем документ и историю
        doc_text = ""
        doc_name = ""
        
        with get_session() as session:
            doc = session.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id
            ).first()
            
            if not doc:
                await message.answer(
                    "❌ Документ не найден.",
                    reply_markup=get_main_keyboard()
                )
                await state.clear()
                return
            
            doc_text = doc.text[:4000] if doc.text else ""
            doc_name = doc.file_name
            
            # Получаем последние сообщения для контекста
            recent = session.query(Msg).filter(
                Msg.user_id == user_id,
                Msg.document_id == doc_id
            ).order_by(Msg.created_at.desc()).limit(5).all()
            
            # Сохраняем вопрос
            user_msg = Msg(
                user_id=user_id, 
                role="user", 
                content=user_text,
                document_id=doc_id
            )
            session.add(user_msg)
        
        # Формируем промпт с контекстом
        prompt = (
            f"Ты отвечаешь ТОЛЬКО на основе документа.\n\n"
            f"Документ: {doc_name}\n"
            f"Содержание:\n{doc_text}\n\n"
            f"Вопрос: {user_text}\n\n"
            f"Ответь кратко и по существу, только на основе документа:"
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        # Получаем ответ
        answer = None
        for model in MODELS_PRIORITY:
            answer = ask_openrouter(messages, model=model, max_tokens=800)
            if answer and not answer.startswith("❌"):
                break
        
        if not answer:
            answer = "❌ Не удалось получить ответ от нейросети."
        else:
            answer = clean_ai_response(answer)
        
        # Сохраняем ответ
        with get_session() as session:
            bot_msg = Msg(
                user_id=user_id, 
                role="assistant", 
                content=answer,
                document_id=doc_id
            )
            session.add(bot_msg)
        
        # Отправляем ответ
        await message.answer(
            answer,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Ещё вопрос", callback_data=f"ask_doc_{doc_id}")],
                [InlineKeyboardButton(text="📋 К списку документов", callback_data="my_docs")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

@router.message()
async def handle_general_question(message: types.Message, state: FSMContext):
    """Обработка общих вопросов по всем документам"""
    user_id = message.from_user.id
    user_text = message.text.strip()
    
    if user_text.startswith('/'):
        return
    
    # Проверяем, не в режиме ли вопросов
    current_state = await state.get_state()
    if current_state == ChatStates.waiting_for_question:
        return
    
    await message.bot.send_chat_action(chat_id=user_id, action="typing")
    
    try:
        # Получаем все документы пользователя
        docs_data = []
        with get_session() as session:
            docs = session.query(Document).filter(
                Document.user_id == user_id
            ).order_by(Document.created_at.desc()).all()
            
            if not docs:
                await message.answer(
                    "📌 У вас пока нет документов.\n\n"
                    "Загрузите документ через кнопку «Загрузить документ» в меню.",
                    reply_markup=get_main_keyboard()
                )
                return
            
            # Сохраняем вопрос
            user_msg = Msg(user_id=user_id, role="user", content=user_text)
            session.add(user_msg)
            
            # Собираем данные документов
            for doc in docs[:3]:
                docs_data.append({
                    'name': doc.file_name,
                    'text': doc.text[:500] if doc.text else ""
                })
        
        # Формируем контекст из всех документов
        doc_context = ""
        for i, doc in enumerate(docs_data, 1):
            doc_context += f"Документ {i}: {doc['name']}\n{doc['text']}\n\n"
        
        prompt = (
            f"Ты отвечаешь на основе документов пользователя.\n\n"
            f"Документы:\n{doc_context}\n\n"
            f"Вопрос: {user_text}\n\n"
            f"Ответь кратко, только на основе документов:"
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        answer = None
        for model in MODELS_PRIORITY:
            answer = ask_openrouter(messages, model=model, max_tokens=800)
            if answer and not answer.startswith("❌"):
                break
        
        if not answer:
            answer = "❌ Не удалось получить ответ от нейросети."
        else:
            answer = clean_ai_response(answer)
        
        with get_session() as session:
            bot_msg = Msg(user_id=user_id, role="assistant", content=answer)
            session.add(bot_msg)
        
        await message.answer(answer, reply_markup=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка.",
            reply_markup=get_main_keyboard()
        )