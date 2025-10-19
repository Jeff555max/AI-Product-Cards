
import os
import pandas as pd
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_gigachat.chat_models import GigaChat
import requests

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение настроек GigaChat из переменных окружения
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-Pro")  # По умолчанию GigaChat-Pro
GIGACHAT_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", 0.2))  # Температура для контроля креативности
GIGACHAT_TOP_P = float(os.getenv("GIGACHAT_TOP_P", 1))  # Top-p sampling для разнообразия ответов


def download_yadisk_file(yadisk_url, out_path):
    """
    Скачивает файл с Яндекс.Диска по публичной ссылке.
    
    Использует API Яндекс.Диска для получения прямой ссылки на скачивание,
    затем загружает файл по частям (chunks) для экономии памяти.
    
    Args:
        yadisk_url (str): Публичная ссылка на файл на Яндекс.Диске
        out_path (str): Путь для сохранения скачанного файла
    """
    api_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download'
    params = {'public_key': yadisk_url}
    r = requests.get(api_url, params=params)
    r.raise_for_status()
    download_url = r.json()['href']
    with requests.get(download_url, stream=True) as f:
        f.raise_for_status()
        with open(out_path, 'wb') as out_file:
            for chunk in f.iter_content(chunk_size=8192):
                out_file.write(chunk)

def load_products():
    """
    Загружает каталог товаров из локального файла или с Яндекс.Диска.
    
    Пользователь выбирает способ загрузки:
    1 - из локального файла data/products.csv
    2 - скачать с Яндекс.Диска
    
    Returns:
        pandas.DataFrame: Загруженный каталог товаров
    """
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    local_path = os.path.join(data_dir, 'products.csv')
    print("Выберите способ загрузки каталога товаров:")
    print("1. Загрузить локальный файл (products.csv в папке data)")
    print("2. Скачать с Яндекс.Диска по ссылке (https://disk.yandex.ru/d/3Y1rogh78wVtAw)")
    choice = input("Введите 1 или 2: ").strip()
    if choice == '1':
        if not os.path.exists(local_path):
            print(f"Файл {local_path} не найден. Пожалуйста, поместите products.csv в папку data.")
            exit(1)
        print(f"Загружаем каталог из {local_path}")
        return pd.read_csv(local_path)
    elif choice == '2':
        print("Скачиваем файл с Яндекс.Диска...")
        download_yadisk_file('https://disk.yandex.ru/d/3Y1rogh78wVtAw', local_path)
        print(f"Файл сохранён как {local_path}")
        return pd.read_csv(local_path)
    else:
        print("Некорректный выбор. Завершение работы.")
        exit(1)

def get_product_info(query, df):
    """
    Умный поиск товара в каталоге с поддержкой синонимов и нечёткого поиска.
    
    Алгоритм поиска:
    1. Сначала пытается найти точное совпадение по названию
    2. Если не найдено - ищет по ключевым словам с использованием словаря синонимов
    3. Поддерживает русско-английский перевод (ноутбук -> laptop, наушники -> headphone)
    
    Args:
        query (str): Поисковый запрос пользователя
        df (pandas.DataFrame): Каталог товаров для поиска
        
    Returns:
        dict or None: Словарь с информацией о товаре или None, если товар не найден
    """
    import re
    
    # Словарь синонимов для перевода русских запросов на английский
    # и расширения поиска близкими по смыслу терминами
    synonyms = {
        'ноутбук': ['laptop', 'notebook', 'ноутбук'],
        'наушники': ['headphone', 'earphone', 'earbud', 'наушники'],
        'колонка': ['speaker', 'колонка'],
        'телефон': ['phone', 'smartphone', 'телефон'],
        'камера': ['camera', 'камера'],
        'планшет': ['tablet', 'ipad', 'планшет'],
    }
    
    # Автоопределение колонки с названием товара
    # Проверяем типичные варианты названий колонок
    name_col = None
    possible_names = ['name', 'title', 'product', 'description', 'название', 'наименование']
    
    for col in df.columns:
        col_lower = str(col).lower()
        for possible in possible_names:
            if possible in col_lower:
                name_col = col
                break
        if name_col:
            break
    
    # Если стандартная колонка не найдена, берём первую текстовую колонку (кроме ID)
    if not name_col:
        for col in df.columns:
            if df[col].dtype == 'object' and col.lower() != 'id':
                name_col = col
                break
    
    # В крайнем случае - просто первая колонка
    if not name_col:
        name_col = df.columns[0]
    
    print(f"🔍 Поиск в колонке: '{name_col}'")
    
    # Шаг 1: Попытка точного совпадения (case-insensitive)
    row = df[df[name_col].astype(str).str.lower() == query.lower()]
    if not row.empty:
        return row.iloc[0].to_dict()
    
    # Шаг 2: Сборка списка ключевых слов для поиска
    # Включаем оригинальные слова запроса + их синонимы
    search_keywords = []
    keywords = query.lower().split()
    
    for keyword in keywords:
        search_keywords.append(keyword)
        # Добавляем синонимы из словаря, если они есть
        if keyword in synonyms:
            search_keywords.extend(synonyms[keyword])
    
    # Шаг 3: Поиск по ключевым словам с использованием regex
    for keyword in search_keywords:
        if len(keyword) > 2:  # Игнорируем короткие слова (предлоги, артикли)
            # Экранируем специальные символы regex для безопасности
            escaped_keyword = re.escape(keyword)
            try:
                matches = df[df[name_col].astype(str).str.lower().str.contains(escaped_keyword, na=False, regex=True)]
                if not matches.empty:
                    print(f"✓ Найдено {len(matches)} товаров по запросу '{keyword}'.")
                    print(f"📦 Первый товар: {matches.iloc[0][name_col]}")
                    return matches.iloc[0].to_dict()
            except Exception as e:
                print(f"⚠️ Ошибка поиска по слову '{keyword}': {e}")
                continue
    
    # Если ничего не найдено - подсказываем варианты запросов
    print(f"\n❌ Товар не найден в каталоге по запросу: '{query}'")
    print(f"💡 Попробуйте другие варианты: laptop, speaker, camera, headphone, phone, tablet")
    print(f"📋 Или используйте команду 'покажи 10 товаров' для просмотра каталога")
    return None

def main():
    """
    Главная функция для запуска интерактивного диалога с ассистентом.
    
    Основные возможности:
    - Загрузка каталога товаров (локально или с Яндекс.Диска)
    - Просмотр списка товаров по запросу ("покажи 10 товаров")
    - Поиск товара и генерация карточки через GigaChat
    - Отображение расхода токенов на каждый запрос
    - Retry механизм при ошибках подключения (3 попытки с задержками 3, 6, 9 сек)
    
    Команды выхода: 'exit', 'выход', 'quit', 'q' или двойной Enter
    """
    # Загрузка каталога товаров
    products_df = load_products()
    print("\nПервые 5 товаров из каталога:")
    print(products_df.head())
    print("\n=== Колонки в каталоге ===")
    print(products_df.columns.tolist())
    
    # Определяем колонку с названием товара для корректного отображения
    name_columns = [col for col in products_df.columns if any(word in str(col).lower() for word in ['name', 'title', 'product', 'description', 'название'])]
    if name_columns:
        print(f"\n=== Найдены колонки с названиями: {name_columns} ===")
        print(f"Примеры данных из '{name_columns[0]}':")
        print(products_df[name_columns[0]].head())
    else:
        print("\n⚠️ Колонка с названием не найдена. Используется первая колонка.")
        print(f"Первая колонка: {products_df.columns[0]}")
        print(products_df[products_df.columns[0]].head())

    # Загрузка системного промпта из файла
    with open(os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.txt'), encoding='utf-8') as f:
        prompt_template = f.read()

    # Создание шаблона промпта с переменными для подстановки данных о товаре
    prompt = PromptTemplate(
        input_variables=["user_input", "product_data"],
        template=prompt_template
    )

    # Инициализация GigaChat LLM с настройками из .env
    llm = GigaChat(
        credentials=GIGACHAT_API_KEY,
        model=GIGACHAT_MODEL,
        scope=GIGACHAT_SCOPE,
        temperature=GIGACHAT_TEMPERATURE,  # 0.2 для стабильных результатов
        top_p=GIGACHAT_TOP_P,  # 1.0 для полного разнообразия токенов
        profanity_check=True,  # Проверка на нецензурную лексику
        verify_ssl_certs=False,  # Отключаем проверку SSL для dev-контейнеров
        streaming=False,  # Получаем полный ответ целиком
        timeout=120  # Увеличенный timeout до 120 секунд для стабильности
    )
    # Создание LangChain цепочки (LLM + Prompt)
    # return_final_only=False нужен для доступа к полной информации о токенах
    chain = LLMChain(llm=llm, prompt=prompt, return_final_only=False)

    print("\n=== Диалог с ассистентом по каталогу товаров ===")
    print("(Для выхода введите 'exit', 'выход' или нажмите Enter 2 раза подряд)\n")
    
    empty_input_count = 0  # Счётчик пустых вводов для двойного Enter
    while True:
        user_input = input("User: ")
        
        # Обработка пустого ввода - выход после двойного Enter
        if not user_input.strip():
            empty_input_count += 1
            if empty_input_count >= 2:
                print("\n👋 Выход из диалога. До свидания!")
                break
            print("(Нажмите Enter ещё раз для выхода, или введите запрос)")
            continue
        
        empty_input_count = 0  # Сбрасываем счётчик при любом вводе
        
        # Обработка команд выхода
        if user_input.strip().lower() in ['exit', 'выход', 'quit', 'q']:
            print("\n👋 Выход из диалога. До свидания!")
            break
        
        # Обработка запросов на вывод списка товаров
        # Распознаём фразы типа "покажи 10 товаров", "список", "дай первые 5", "выведи первые 5 ноутбуков"
        list_keywords = ['список', 'покажи', 'дай', 'выведи', 'первые', 'все']
        if any(word in user_input.lower() for word in list_keywords):
            import re
            
            # Извлекаем число из запроса, если указано
            numbers = re.findall(r'\d+', user_input)
            count = int(numbers[0]) if numbers else 5
            count = min(count, 20)  # Ограничиваем до 20 товаров для читаемости
            
            # Проверяем, есть ли указание на конкретную категорию товаров
            # Например: "выведи 5 ноутбуков", "покажи наушники"
            name_col = 'name' if 'name' in products_df.columns else products_df.columns[0]
            
            # Собираем ключевые слова из словаря синонимов для поиска категории
            synonyms = {
                'ноутбук': ['laptop', 'notebook'],
                'наушники': ['headphone', 'earphone', 'earbud'],
                'колонка': ['speaker'],
                'телефон': ['phone', 'smartphone'],
                'камера': ['camera'],
                'планшет': ['tablet', 'ipad']
            }
            
            # Ищем категорию в запросе
            category_found = None
            search_keywords = []
            words = user_input.lower().split()
            
            for word in words:
                if word in synonyms:
                    category_found = word
                    search_keywords.extend(synonyms[word])
                    break
            
            # Если категория найдена - фильтруем товары
            if category_found or search_keywords:
                filtered_df = products_df
                for keyword in search_keywords:
                    matches = filtered_df[filtered_df[name_col].astype(str).str.lower().str.contains(keyword, na=False, regex=False)]
                    if not matches.empty:
                        filtered_df = matches
                        break
                
                if filtered_df.empty or len(filtered_df) == 0:
                    print(f"\n❌ Товары по запросу '{user_input}' не найдены в каталоге.")
                    print(f"💡 Попробуйте: laptop, speaker, camera, headphone, phone и т.д.")
                    continue
                
                print(f"\n📋 Найдено {len(filtered_df)} товаров. Показываю первые {min(count, len(filtered_df))}:")
                for idx, row in filtered_df.head(count).iterrows():
                    print(f"{idx+1}. {row[name_col]}")
            else:
                # Если категория не указана - выводим первые N товаров
                print(f"\n📋 Вывожу первые {count} товаров из каталога:")
                for idx, row in products_df.head(count).iterrows():
                    print(f"{idx+1}. {row[name_col]}")
            
            print("\nДля генерации карточки введите название конкретного товара или ключевое слово (например: 'ноутбук', 'наушники')")
            continue
        
        # Поиск товара по запросу пользователя с использованием умного поиска
        product_info = get_product_info(user_input, products_df)
        if not product_info:
            # Сообщение об ошибке уже выведено в функции get_product_info
            continue
        
        # Преобразуем словарь product_info в строку для передачи в промпт
        product_data_str = "\n".join([f"{k}: {v}" for k, v in product_info.items()])
        
        # ========== RETRY МЕХАНИЗМ ==========
        # При ошибках подключения к API делаем 3 попытки с прогрессивными задержками
        max_retries = 3
        retry_count = 0
        response = None
        
        while retry_count < max_retries:
            try:
                # Вызываем цепочку LangChain для генерации карточки товара
                # return_only_outputs=False нужен для доступа к метаинформации (токены)
                response = chain.invoke(
                    {"user_input": user_input, "product_data": product_data_str},
                    return_only_outputs=False
                )
                break  # Успешный запрос - выходим из цикла retry
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # Проверяем, является ли это ошибкой соединения/таймаута
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    "connection reset", "connecttimeout", "timeout", 
                    "timed out", "handshake", "ssl"
                ])
                
                if is_connection_error:
                    if retry_count < max_retries:
                        # Прогрессивная задержка: 3, 6, 9 секунд
                        wait_time = retry_count * 3
                        print(f"\n⚠️  Ошибка соединения (попытка {retry_count}/{max_retries}). Повторяю через {wait_time} сек...")
                        import time
                        time.sleep(wait_time)
                    else:
                        print(f"\n❌ Ошибка при генерации ответа после {max_retries} попыток: {e}")
                        print("   Проверьте подключение к интернету и попробуйте снова.")
                        break
                else:
                    # Другие ошибки (не связанные с сетью) - не повторяем
                    print(f"\n❌ Ошибка при генерации ответа: {e}")
                    break
        
        if response is None:
            continue
            
        # ========== ВЫВОД РЕЗУЛЬТАТА ==========
        print("\n• Входной запрос:")
        print(user_input)
        print("\n• Ответ ассистента:")
        
        # Извлекаем текст ответа из response (может быть в 'text' или 'output')
        response_text = response.get('text', response.get('output', ''))
        print(response_text)
        
        # ========== ДЕТАЛЬНАЯ ОТЛАДКА СТРУКТУРЫ (опционально) ==========
        # Включается через переменную окружения DEBUG_TOKENS=true
        if os.getenv('DEBUG_TOKENS', 'false').lower() == 'true':
            print("\n[DEBUG] Структура ответа:")
            print(f"Ключи верхнего уровня: {list(response.keys())}")
            if 'full_generation' in response:
                full_gen = response['full_generation']
                if isinstance(full_gen, list) and len(full_gen) > 0:
                    gen = full_gen[0]
                    print(f"Тип full_generation[0]: {type(gen)}")
                    if hasattr(gen, 'generation_info'):
                        print(f"generation_info: {gen.generation_info}")
                    if hasattr(gen, 'message'):
                        msg = gen.message
                        print(f"Тип message: {type(msg)}")
                        print(f"Атрибуты message: {[attr for attr in dir(msg) if not attr.startswith('_')]}")
                        if hasattr(msg, 'response_metadata'):
                            print(f"response_metadata: {msg.response_metadata}")
                        if hasattr(msg, 'usage_metadata'):
                            print(f"usage_metadata: {msg.usage_metadata}")
        
        # ========== ИЗВЛЕЧЕНИЕ ТОКЕНОВ ==========
        # Пытаемся получить информацию о токенах из нескольких возможных мест
        token_info_found = False
        
        # ПРИОРИТЕТ 1: full_generation[0].message.usage_metadata (основной для GigaChat)
        # Здесь GigaChat возвращает информацию о токенах в формате:
        # {'input_tokens': X, 'output_tokens': Y, 'total_tokens': Z, 'input_token_details': {'cache_read': N}}
        if 'full_generation' in response:
            full_gen = response['full_generation']
            if isinstance(full_gen, list) and len(full_gen) > 0:
                for gen in full_gen:
                    if hasattr(gen, 'message') and hasattr(gen.message, 'usage_metadata'):
                        usage = gen.message.usage_metadata
                        if usage:
                            print("\n• 💰 Расход токенов:")
                            if isinstance(usage, dict):
                                # Извлекаем токены из словаря
                                input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 'N/A'))
                                output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 'N/A'))
                                total_tokens = usage.get('total_tokens', 'N/A')
                                print(f"  Входных токенов (prompt): {input_tokens}")
                                print(f"  Выходных токенов (completion): {output_tokens}")
                                print(f"  Всего токенов: {total_tokens}")
                                # Дополнительно показываем кэшированные токены, если есть
                                if 'input_token_details' in usage and 'cache_read' in usage['input_token_details']:
                                    cache_read = usage['input_token_details']['cache_read']
                                    if cache_read > 0:
                                        print(f"  Кэшированных токенов: {cache_read}")
                            else:
                                # Если usage - объект, получаем атрибуты
                                input_tokens = getattr(usage, 'input_tokens', None) or getattr(usage, 'prompt_tokens', None)
                                output_tokens = getattr(usage, 'output_tokens', None) or getattr(usage, 'completion_tokens', None)
                                total_tokens = getattr(usage, 'total_tokens', None)
                                print(f"  Входных токенов (prompt): {input_tokens or 'N/A'}")
                                print(f"  Выходных токенов (completion): {output_tokens or 'N/A'}")
                                print(f"  Всего токенов: {total_tokens or 'N/A'}")
                            token_info_found = True
                            break
        
        # ПРИОРИТЕТ 2: generation_info (fallback для старых версий LangChain)
        if not token_info_found and 'generation_info' in response:
            gen_info = response['generation_info']
            # generation_info может быть списком - берём первый элемент
            if gen_info and isinstance(gen_info, list) and len(gen_info) > 0:
                gen_info = gen_info[0]
            if gen_info and isinstance(gen_info, dict) and 'usage' in gen_info:
                usage = gen_info['usage']
                print("\n• 💰 Расход токенов:")
                print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                token_info_found = True
            
        # ПРИОРИТЕТ 3: llm_output (ещё один fallback)
        if not token_info_found and 'llm_output' in response:
            llm_out = response['llm_output']
            if llm_out and 'token_usage' in llm_out:
                usage = llm_out['token_usage']
                print("\n• 💰 Расход токенов:")
                print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                token_info_found = True
        
        # Если токены не найдены нигде - уведомляем пользователя
        if not token_info_found:
            print("\n• 💰 Расход токенов: информация недоступна")


if __name__ == "__main__":
    main()
