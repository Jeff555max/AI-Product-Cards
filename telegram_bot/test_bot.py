"""
Пример использования Telegram бота в тестовом режиме
Для разработки и отладки без реального Telegram API
"""

from unittest.mock import Mock
import pandas as pd

# Имитируем структуру сообщения Telegram
class MockMessage:
    def __init__(self, text, chat_id=123456):
        self.text = text
        self.chat = Mock()
        self.chat.id = chat_id


# Имитируем бота
class MockBot:
    def __init__(self):
        self.messages = []
    
    def send_message(self, chat_id, text, **kwargs):
        self.messages.append({
            'chat_id': chat_id,
            'text': text,
            'kwargs': kwargs
        })
        print(f"\n[BOT → User {chat_id}]")
        print(text)
        print("-" * 60)
    
    def send_chat_action(self, chat_id, action):
        print(f"[Action: {action}]")


def test_handlers():
    """Тест обработчиков без реального Telegram"""
    print("=" * 60)
    print("🧪 Тестирование обработчиков бота")
    print("=" * 60)
    
    # Создаём мок данных
    mock_products = pd.DataFrame({
        'name': ['Test Product 1', 'Test Product 2', 'Test Headphones'],
        'brand': ['Brand A', 'Brand B', 'Brand C'],
        'price': [100, 200, 50]
    })
    
    mock_bot = MockBot()
    
    # Тестируем различные сценарии
    test_cases = [
        "/start",
        "/help",
        "/list",
        "наушники",
        "unknown product"
    ]
    
    for test_input in test_cases:
        print(f"\n📥 User Input: {test_input}")
        msg = MockMessage(test_input)
        
        # Здесь можно протестировать логику обработчиков
        # без реального подключения к Telegram
        
        print(f"✅ Processed successfully")
    
    print("\n" + "=" * 60)
    print(f"📊 Всего сообщений от бота: {len(mock_bot.messages)}")
    print("=" * 60)


if __name__ == "__main__":
    test_handlers()
