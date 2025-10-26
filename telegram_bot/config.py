"""
Конфигурация Telegram бота
Загрузка настроек из переменных окружения
"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # GigaChat API
    GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
    GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
    GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-Lite")
    GIGACHAT_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", 0.2))
    GIGACHAT_TOP_P = float(os.getenv("GIGACHAT_TOP_P", 1))
    
    # Langfuse (опционально)
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    # Пути к данным
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')
    
    # Настройки бота
    MAX_PRODUCTS_DISPLAY = 10  # Максимум товаров для отображения в Telegram
    ENABLE_LANGFUSE = bool(LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY)
    
    @classmethod
    def validate(cls):
        """Валидация обязательных настроек"""
        errors = []
        
        if cls.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            errors.append("❌ TELEGRAM_BOT_TOKEN не установлен в .env")
        
        if not cls.GIGACHAT_API_KEY:
            errors.append("❌ GIGACHAT_API_KEY не установлен в .env")
        
        if errors:
            return False, errors
        
        return True, []
    
    @classmethod
    def get_info(cls):
        """Информация о текущей конфигурации"""
        return f"""
🤖 Конфигурация Telegram бота:
├── Модель: {cls.GIGACHAT_MODEL}
├── Temperature: {cls.GIGACHAT_TEMPERATURE}
├── Top-p: {cls.GIGACHAT_TOP_P}
├── Langfuse: {'✅ Включен' if cls.ENABLE_LANGFUSE else '❌ Отключен'}
└── Макс. товаров: {cls.MAX_PRODUCTS_DISPLAY}
        """


# Создаём экземпляр конфигурации
config = Config()
