# bot/openrouter_api.py

import requests
import logging
import json
import time
from typing import List, Dict, Optional

from bot.config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# АКТУАЛЬНЫЕ БЕСПЛАТНЫЕ МОДЕЛИ
AVAILABLE_MODELS = {
    "openrouter/free": "Free Models Router (рекомендуется, работает из России)",
    "google/gemma-3-4b-it:free": "Google Gemma 3 4B",
    "google/gemma-3-12b-it:free": "Google Gemma 3 12B",
    "qwen/qwen3-4b:free": "Qwen3 4B",
    "meta-llama/llama-3.2-3b-instruct:free": "Meta Llama 3.2 3B",
}

DEFAULT_MODEL = "openrouter/free"  # Меняем на роутер по умолчанию

def ask_openrouter(
    messages: List[Dict[str, str]], 
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    retry_count: int = 2
) -> Optional[str]:
    """
    Отправка запроса к OpenRouter API
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/ai_doc_bot",
        "X-Title": "AI Document Bot"
    }
    
    # Для openrouter/free используем упрощенный формат
    json_data = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    # Пробуем отправить запрос с повторными попытками
    for attempt in range(retry_count + 1):
        try:
            logger.info(f"Отправка запроса к OpenRouter, модель: {model} (попытка {attempt + 1})")
            
            response = requests.post(
                BASE_URL, 
                json=json_data, 
                headers=headers, 
                timeout=60,
                verify=True
            )
            
            logger.info(f"Статус ответа: {response.status_code}")
            
            # Успешный ответ
            if response.status_code == 200:
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    
                    if not content or len(content.strip()) == 0:
                        logger.warning("Получен пустой ответ")
                        return None
                    
                    logger.info(f"✅ Получен ответ, длина: {len(content)} символов")
                    return content
                else:
                    logger.error(f"Неожиданный формат ответа: {data}")
                    return None
            
            # Обработка ошибок
            elif response.status_code == 429:
                logger.error("Слишком много запросов")
                if attempt < retry_count:
                    wait_time = 2 ** attempt
                    logger.info(f"Ждем {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
                return "❌ Слишком много запросов. Подождите немного."
            
            elif response.status_code == 400:
                error_text = response.text
                logger.error(f"Ошибка 400: {error_text}")
                
                # Для Gemma пробуем убрать system prompt
                if "Developer instruction is not enabled" in error_text:
                    if attempt < retry_count and len(messages) > 1:
                        logger.info("Убираем system prompt для Gemma...")
                        # Оставляем только последнее сообщение user
                        json_data["messages"] = [messages[-1]]
                        continue
                
                return f"❌ Ошибка запроса. Попробуйте другую модель."
            
            else:
                logger.error(f"Ошибка API {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Таймаут (попытка {attempt + 1})")
            if attempt < retry_count:
                continue
            return "❌ Таймаут соединения."
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Ошибка соединения (попытка {attempt + 1})")
            if attempt < retry_count:
                continue
            return "❌ Ошибка соединения."
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            if attempt < retry_count:
                continue
            return "❌ Внутренняя ошибка."
    
    return None