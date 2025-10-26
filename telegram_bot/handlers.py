"""
Обработчики команд и сообщений Telegram бота
"""

import telebot
from telebot import types
from typing import Optional

from .config import config
from .utils import get_product_info, search_products, format_product_data
from .gigachat_service import GigaChatService


class BotHandlers:
    """Класс с обработчиками команд и сообщений бота"""
    
    def __init__(self, bot: telebot.TeleBot, products_df, gigachat_service: GigaChatService):
        """
        Инициализация обработчиков.
        
        Args:
            bot: Экземпляр Telegram бота
            products_df: DataFrame с каталогом товаров
            gigachat_service: Сервис для работы с GigaChat
        """
        self.bot = bot
        self.products_df = products_df
        self.gigachat = gigachat_service
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация всех обработчиков"""
        self.bot.message_handler(commands=['start'])(self.cmd_start)
        self.bot.message_handler(commands=['help'])(self.cmd_help)
        self.bot.message_handler(commands=['info'])(self.cmd_info)
        self.bot.message_handler(commands=['list'])(self.cmd_list)
        self.bot.message_handler(func=lambda message: True)(self.handle_text)
    
    def cmd_start(self, message):
        """Обработчик команды /start"""
        welcome_text = """
🛍️ <b>Добро пожаловать в AI Product Cards Bot!</b>

Я помогу создать профессиональные карточки товаров для маркетплейсов.

<b>Что я умею:</b>
• Генерировать карточки товаров с описанием
• Искать товары по категориям
• Создавать SEO-оптимизированные тексты

<b>Как использовать:</b>
Просто отправьте название товара или категорию:
• "наушники"
• "laptop"
• "Sony Speaker"

<b>Команды:</b>
/list - показать примеры товаров
/help - справка
/info - информация о боте

🚀 Готов к работе!
        """
        
        # Клавиатура с быстрыми командами
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("📋 Список товаров"),
            types.KeyboardButton("ℹ️ Справка"),
            types.KeyboardButton("🎧 Наушники"),
            types.KeyboardButton("💻 Ноутбуки")
        )
        
        self.bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    def cmd_help(self, message):
        """Обработчик команды /help"""
        help_text = """
📚 <b>Справка по использованию бота</b>

<b>Поиск товаров:</b>
Отправьте название или категорию:
• "наушники" - найдёт все наушники
• "Sony Speaker" - точный поиск
• "laptop" - найдёт ноутбуки

<b>Запрос списка товаров:</b>
Можете указать количество:
• "выведи 5 ноутбуков"
• "покажи 15 наушников"
• "первых 20 laptop"
• "список 10 колонок"

<b>Генерация карточки:</b>
После поиска я автоматически создам карточку с:
• Названием товара
• Кратким описанием
• Полным описанием
• Преимуществами
• Характеристиками
• SEO-ключевыми словами

<b>Команды:</b>
/start - главное меню
/list - показать 10 случайных товаров
/info - информация о системе

<b>Технологии:</b>
• GigaChat {model} для генерации
• Каталог: {products_count} товаров
• Langfuse трейсинг: {langfuse_status}

💡 Совет: используйте конкретные запросы для лучших результатов!
        """.format(
            model=config.GIGACHAT_MODEL,
            products_count=len(self.products_df),
            langfuse_status="✅" if config.ENABLE_LANGFUSE else "❌"
        )
        
        self.bot.send_message(message.chat.id, help_text, parse_mode='HTML')
    
    def cmd_info(self, message):
        """Обработчик команды /info"""
        info_text = f"""
🤖 <b>Информация о боте</b>

<b>Конфигурация:</b>
• Модель: {config.GIGACHAT_MODEL}
• Temperature: {config.GIGACHAT_TEMPERATURE}
• Top-p: {config.GIGACHAT_TOP_P}
• Langfuse: {'✅ Включен' if config.ENABLE_LANGFUSE else '❌ Отключен'}

<b>Каталог товаров:</b>
• Всего товаров: {len(self.products_df)}
• Колонок данных: {len(self.products_df.columns)}
• Размер данных: ~{len(self.products_df) * len(self.products_df.columns) // 1000} KB

<b>Возможности:</b>
✅ Умный поиск с синонимами
✅ Генерация продающих текстов
✅ SEO-оптимизация
✅ Retry механизм при ошибках
✅ Отслеживание токенов

<b>Версия:</b> 1.0.0
<b>GitHub:</b> Jeff555max/AI-Product-Cards
        """
        
        self.bot.send_message(message.chat.id, info_text, parse_mode='HTML')
    
    def cmd_list(self, message):
        """Обработчик команды /list"""
        try:
            # Получаем случайные товары
            sample_products = self.products_df.sample(
                min(config.MAX_PRODUCTS_DISPLAY, len(self.products_df))
            )
            
            name_col = 'name' if 'name' in self.products_df.columns else self.products_df.columns[0]
            
            products_list = "\n".join([
                f"{idx + 1}. {row[name_col]}"
                for idx, (_, row) in enumerate(sample_products.iterrows())
            ])
            
            response = f"""
📋 <b>Примеры товаров из каталога:</b>

{products_list}

💡 Отправьте название любого товара для генерации карточки!
            """
            
            self.bot.send_message(message.chat.id, response, parse_mode='HTML')
            
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при загрузке списка: {str(e)}"
            )
    
    def handle_text(self, message):
        """Обработчик текстовых сообщений"""
        user_input = message.text.strip()
        
        # Обработка кнопок клавиатуры
        if user_input == "📋 Список товаров":
            self.show_random_products(message, limit=10)
            return
        elif user_input == "ℹ️ Справка":
            self.cmd_help(message)
            return
        elif user_input == "🔍 Создать ещё карточку":
            self.bot.send_message(
                message.chat.id,
                "✏️ <b>Отлично!</b>\n\nОтправьте название товара или категорию:\n• наушники\n• laptop\n• Sony Speaker",
                parse_mode='HTML'
            )
            return
        elif user_input == "🎧 Наушники":
            self.show_category_products(message, "наушники", "🎧 Наушники")
            return
        elif user_input == "💻 Ноутбуки":
            self.show_category_products(message, "ноутбук", "💻 Ноутбуки")
            return
        
        # Проверка на команды с числами (например: "выведи 5 ноутбуков", "покажи 15 наушников")
        parsed_command = self.parse_quantity_command(user_input)
        if parsed_command:
            quantity, category, category_title = parsed_command
            self.show_category_products(message, category, category_title, limit=quantity)
            return
        
        # Отправляем статус "печатает..."
        self.bot.send_chat_action(message.chat.id, 'typing')
        
        # Поиск товара
        self.bot.send_message(message.chat.id, "🔍 Ищу товар в каталоге...")
        
        product_info = get_product_info(user_input, self.products_df)
        
        if not product_info:
            # Товар не найден - предлагаем похожие
            self.handle_not_found(message, user_input)
            return
        
        # Товар найден - показываем краткую информацию
        name_col = 'name' if 'name' in self.products_df.columns else self.products_df.columns[0]
        product_name = product_info.get(name_col, "Неизвестный товар")
        
        self.bot.send_message(
            message.chat.id,
            f"✅ Найден товар: <b>{product_name}</b>\n\n⏳ Генерирую карточку...",
            parse_mode='HTML'
        )
        
        # Генерация карточки
        self.generate_and_send_card(message, user_input, product_info)
    
    def parse_quantity_command(self, text: str):
        """
        Парсит команды вида: "выведи 5 ноутбуков", "покажи 15 наушников", "первых 10 laptop"
        
        Returns:
            Tuple (quantity, category, category_title) или None
        """
        import re
        
        text_lower = text.lower()
        
        # Словарь категорий с вариантами написания
        categories = {
            'ноутбук': ('ноутбук', '💻 Ноутбуки'),
            'ноутбуков': ('ноутбук', '💻 Ноутбуки'),
            'ноутбука': ('ноутбук', '💻 Ноутбуки'),
            'ноутбуки': ('ноутбук', '💻 Ноутбуки'),
            'laptop': ('ноутбук', '💻 Laptops'),
            'laptops': ('ноутбук', '💻 Laptops'),
            'notebook': ('ноутбук', '💻 Notebooks'),
            'notebooks': ('ноутбук', '💻 Notebooks'),
            'наушники': ('наушники', '🎧 Наушники'),
            'наушник': ('наушники', '🎧 Наушники'),
            'наушников': ('наушники', '🎧 Наушники'),
            'наушника': ('наушники', '🎧 Наушники'),
            'headphone': ('наушники', '🎧 Headphones'),
            'headphones': ('наушники', '🎧 Headphones'),
            'earphone': ('наушники', '🎧 Earphones'),
            'earphones': ('наушники', '🎧 Earphones'),
            'earbud': ('наушники', '🎧 Earbuds'),
            'earbuds': ('наушники', '🎧 Earbuds'),
            'колонка': ('колонка', '🔊 Колонки'),
            'колонки': ('колонка', '🔊 Колонки'),
            'колонок': ('колонка', '🔊 Колонки'),
            'speaker': ('колонка', '🔊 Speakers'),
            'speakers': ('колонка', '🔊 Speakers'),
            'телефон': ('телефон', '📱 Телефоны'),
            'телефона': ('телефон', '📱 Телефоны'),
            'телефонов': ('телефон', '📱 Телефоны'),
            'phone': ('телефон', '📱 Phones'),
            'phones': ('телефон', '📱 Phones'),
            'smartphone': ('телефон', '📱 Smartphones'),
            'smartphones': ('телефон', '📱 Smartphones'),
        }
        
        # Паттерны для поиска числа и категории
        patterns = [
            r'выведи\s+(\d+)\s+(\w+)',  # "выведи 10 наушников"
            r'покажи\s+(\d+)\s+(\w+)',  # "покажи 15 laptop"
            r'первых\s+(\d+)\s+(\w+)',  # "первых 5 ноутбуков"
            r'список\s+(\d+)\s+(\w+)',  # "список 20 товаров"
            r'(\d+)\s+(\w+)',  # "5 ноутбуков", "10 наушников"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                quantity = int(match.group(1))
                category_word = match.group(2)
                
                # Проверяем, есть ли это слово в словаре категорий
                if category_word in categories:
                    cat, title = categories[category_word]
                    # Ограничиваем максимальное количество
                    quantity = min(quantity, 50)
                    return (quantity, cat, title)
        
        return None
    
    def show_random_products(self, message, limit: int = 10):
        """Показать случайные товары из всего каталога"""
        try:
            # Получаем случайные товары
            sample_products = self.products_df.sample(min(limit, len(self.products_df)))
            
            name_col = 'name' if 'name' in self.products_df.columns else self.products_df.columns[0]
            
            products_list = "\n".join([
                f"{idx + 1}. {row[name_col]}"
                for idx, (_, row) in enumerate(sample_products.iterrows())
            ])
            
            response = f"""
📋 <b>Случайные {limit} товаров из каталога:</b>

{products_list}

💡 Отправьте название любого товара для генерации карточки!
            """
            
            self.bot.send_message(message.chat.id, response, parse_mode='HTML')
            
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при загрузке списка: {str(e)}"
            )
    
    def show_category_products(self, message, category: str, category_title: str, limit: int = 10):
        """Показать случайные товары из категории"""
        try:
            # Используем функцию поиска товаров по категории
            category_products = search_products(category, self.products_df, limit=100)
            
            if not category_products:
                self.bot.send_message(
                    message.chat.id,
                    f"❌ Товары категории '{category_title}' не найдены."
                )
                return
            
            # Берём случайные из найденных
            import random
            selected = random.sample(category_products, min(limit, len(category_products)))
            
            name_col = 'name' if 'name' in self.products_df.columns else self.products_df.columns[0]
            
            products_list = "\n".join([
                f"{idx + 1}. {item.get(name_col, 'N/A')}"
                for idx, item in enumerate(selected)
            ])
            
            response = f"""
{category_title} - <b>Случайные {len(selected)} товаров:</b>

{products_list}

💡 Отправьте название товара для создания карточки!
            """
            
            self.bot.send_message(message.chat.id, response, parse_mode='HTML')
            
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при загрузке категории: {str(e)}"
            )
    
    def handle_not_found(self, message, query: str):
        """Обработка случая, когда товар не найден"""
        # Пытаемся найти похожие товары
        similar = search_products(query, self.products_df, limit=5)
        
        if similar:
            name_col = 'name' if 'name' in self.products_df.columns else self.products_df.columns[0]
            similar_list = "\n".join([
                f"{idx + 1}. {item.get(name_col, 'N/A')}"
                for idx, item in enumerate(similar)
            ])
            
            response = f"""
❌ Точного совпадения не найдено.

<b>Возможно, вы искали:</b>
{similar_list}

💡 Попробуйте уточнить запрос!
            """
        else:
            response = """
❌ Товар не найден в каталоге.

<b>Попробуйте:</b>
• Использовать другие ключевые слова
• Команду /list для просмотра товаров
• Категории: наушники, ноутбук, колонка, телефон

💡 Примеры: "Sony Speaker", "laptop", "headphone"
            """
        
        self.bot.send_message(message.chat.id, response, parse_mode='HTML')
    
    def generate_and_send_card(self, message, user_input: str, product_info: dict):
        """Генерация и отправка карточки товара"""
        try:
            # Форматируем данные товара
            product_data_str = format_product_data(product_info)
            
            # Генерируем карточку
            response = self.gigachat.generate_card(user_input, product_data_str)
            
            if not response:
                self.bot.send_message(
                    message.chat.id,
                    "❌ Не удалось сгенерировать карточку. Попробуйте позже."
                )
                return
            
            # Извлекаем текст ответа
            card_text = response.get('text', response.get('output', ''))
            
            # Извлекаем информацию о токенах
            token_info = self.gigachat.extract_token_info(response)
            
            # Формируем финальный ответ
            final_response = f"""
{card_text}

━━━━━━━━━━━━━━━━━━━━
💰 <b>Расход токенов:</b>
• Входных: {token_info['input_tokens']}
• Выходных: {token_info['output_tokens']}
• Всего: {token_info['total_tokens']}
            """
            
            if token_info['cached_tokens'] > 0:
                final_response += f"\n• Кэшированных: {token_info['cached_tokens']}"
            
            # Отправляем карточку (разбиваем если слишком длинная)
            self.send_long_message(message.chat.id, final_response)
            
            # Предлагаем продолжить работу
            self.prompt_continue(message.chat.id)
            
        except Exception as e:
            self.bot.send_message(
                message.chat.id,
                f"❌ Ошибка при генерации: {str(e)}"
            )
    
    def prompt_continue(self, chat_id: int):
        """
        Предлагает пользователю продолжить работу с интерактивной клавиатурой.
        """
        # Создаём клавиатуру с вариантами
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🔍 Создать ещё карточку"),
            types.KeyboardButton("📋 Список товаров"),
            types.KeyboardButton("🎧 Наушники"),
            types.KeyboardButton("💻 Ноутбуки"),
            types.KeyboardButton("ℹ️ Справка"),
        )
        
        continue_message = """
━━━━━━━━━━━━━━━━━━━━
✅ <b>Карточка готова!</b>

<b>Что дальше?</b>
• 🔍 Создайте карточку для другого товара
• 📋 Посмотрите список доступных товаров
• Или просто отправьте название товара

💡 Например: "Sony Speaker", "laptop", "колонка"
        """
        
        self.bot.send_message(
            chat_id,
            continue_message,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    def send_long_message(self, chat_id: int, text: str, max_length: int = 4096):
        """
        Отправка длинных сообщений с разбивкой.
        
        Telegram ограничивает длину сообщения в 4096 символов.
        """
        if len(text) <= max_length:
            self.bot.send_message(chat_id, text, parse_mode='HTML')
        else:
            # Разбиваем на части
            parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            for part in parts:
                self.bot.send_message(chat_id, part, parse_mode='HTML')
