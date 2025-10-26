"""
Главный файл Telegram бота для генерации карточек товаров
"""

import sys
import telebot
from telebot import logger
import logging

from telegram_bot.config import Config
from telegram_bot.utils import load_products
from telegram_bot.gigachat_service import GigaChatService
from telegram_bot.handlers import BotHandlers


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger.setLevel(logging.INFO)


def main():
    """Главная функция запуска бота"""
    
    print("=" * 60)
    print("🤖 AI Product Cards - Telegram Bot")
    print("=" * 60)
    
    # Валидация конфигурации
    is_valid, errors = Config.validate()
    if not is_valid:
        print("\n❌ Ошибка конфигурации:")
        for error in errors:
            print(f"   {error}")
        print("\n💡 Проверьте файл .env и установите необходимые переменные")
        sys.exit(1)
    
    # Вывод конфигурации
    print(Config.get_info())
    
    try:
        # Инициализация бота
        print("\n🔧 Инициализация компонентов...")
        bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, parse_mode='HTML')
        print("✅ Telegram бот инициализирован")
        
        # Загрузка каталога товаров
        print("\n📦 Загрузка каталога товаров...")
        products_df = load_products(Config.DATA_DIR)
        print(f"✅ Загружено товаров: {len(products_df)}")
        
        # Инициализация GigaChat
        print("\n🧠 Инициализация GigaChat...")
        gigachat_service = GigaChatService()
        
        # Регистрация обработчиков
        print("\n⚙️  Регистрация обработчиков...")
        handlers = BotHandlers(bot, products_df, gigachat_service)
        print("✅ Обработчики зарегистрированы")
        
        # Запуск бота
        print("\n" + "=" * 60)
        print("✅ Бот успешно запущен и готов к работе!")
        print("=" * 60)
        print("\n💬 Ожидание сообщений...\n")
        
        # Polling
        bot.infinity_polling(
            timeout=10,
            long_polling_timeout=5,
            logger_level=logging.INFO
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Остановка бота...")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
