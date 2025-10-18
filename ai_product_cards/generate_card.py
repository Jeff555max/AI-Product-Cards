
import os
import pandas as pd
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_gigachat.chat_models import GigaChat
import requests

# Загрузка переменных окружения
load_dotenv()

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat-Pro")
GIGACHAT_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", 0.2))
GIGACHAT_TOP_P = float(os.getenv("GIGACHAT_TOP_P", 1))


def download_yadisk_file(yadisk_url, out_path):
    """
    Скачивает файл с Яндекс.Диска по публичной ссылке через сервис https://cloud-api.yandex.net/v1/disk/public/resources/download
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
    Улучшенный поиск товара: сначала точное совпадение, затем поиск по ключевым словам
    """
    import re
    
    # Словарь синонимов для перевода и расширения поиска
    synonyms = {
        'ноутбук': ['laptop', 'notebook', 'ноутбук'],
        'наушники': ['headphone', 'earphone', 'earbud', 'наушники'],
        'колонка': ['speaker', 'колонка'],
        'телефон': ['phone', 'smartphone', 'телефон'],
        'камера': ['camera', 'камера'],
        'планшет': ['tablet', 'ipad', 'планшет'],
    }
    
    # Проверяем, есть ли колонка 'name' (может называться по-другому)
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
    
    if not name_col:
        # Если колонка не найдена, берём первую текстовую колонку
        for col in df.columns:
            if df[col].dtype == 'object' and col.lower() != 'id':
                name_col = col
                break
    
    if not name_col:
        name_col = df.columns[0]
    
    print(f"🔍 Поиск в колонке: '{name_col}'")
    
    # Попытка точного совпадения
    row = df[df[name_col].astype(str).str.lower() == query.lower()]
    if not row.empty:
        return row.iloc[0].to_dict()
    
    # Собираем все ключевые слова для поиска (оригинальные + синонимы)
    search_keywords = []
    keywords = query.lower().split()
    
    for keyword in keywords:
        search_keywords.append(keyword)
        # Добавляем синонимы, если есть
        if keyword in synonyms:
            search_keywords.extend(synonyms[keyword])
    
    # Поиск по ключевым словам
    for keyword in search_keywords:
        if len(keyword) > 2:  # Игнорируем короткие слова
            # Экранируем специальные символы regex
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
    
    print(f"❌ Товар не найден по запросу: {query}")
    print(f"💡 Попробуйте: laptop, speaker, camera, headphone и т.д.")
    return None

def main():
    # Загрузка каталога товаров
    products_df = load_products()
    print("\nПервые 5 товаров из каталога:")
    print(products_df.head())
    print("\n=== Колонки в каталоге ===")
    print(products_df.columns.tolist())
    
    # Определяем колонку с названием товара
    name_columns = [col for col in products_df.columns if any(word in str(col).lower() for word in ['name', 'title', 'product', 'description', 'название'])]
    if name_columns:
        print(f"\n=== Найдены колонки с названиями: {name_columns} ===")
        print(f"Примеры данных из '{name_columns[0]}':")
        print(products_df[name_columns[0]].head())
    else:
        print("\n⚠️ Колонка с названием не найдена. Используется первая колонка.")
        print(f"Первая колонка: {products_df.columns[0]}")
        print(products_df[products_df.columns[0]].head())

    # Загрузка системного промпта
    with open(os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.txt'), encoding='utf-8') as f:
        prompt_template = f.read()


    prompt = PromptTemplate(
        input_variables=["user_input", "product_data"],
        template=prompt_template
    )

    llm = GigaChat(
        credentials=GIGACHAT_API_KEY,
        model=GIGACHAT_MODEL,
        scope=GIGACHAT_SCOPE,
        temperature=GIGACHAT_TEMPERATURE,
        top_p=GIGACHAT_TOP_P,
        profanity_check=True,
        verify_ssl_certs=False,
        streaming=False,
        timeout=120  # Увеличенный timeout до 120 секунд
    )
    chain = LLMChain(llm=llm, prompt=prompt, return_final_only=False)

    print("\n=== Диалог с ассистентом по каталогу товаров ===")
    print("(Для выхода введите 'exit', 'выход' или нажмите Enter 2 раза подряд)\n")
    
    empty_input_count = 0
    while True:
        user_input = input("User: ")
        
        # Обработка пустого ввода
        if not user_input.strip():
            empty_input_count += 1
            if empty_input_count >= 2:
                print("\n👋 Выход из диалога. До свидания!")
                break
            print("(Нажмите Enter ещё раз для выхода, или введите запрос)")
            continue
        
        empty_input_count = 0  # Сбрасываем счётчик при любом вводе
        
        if user_input.strip().lower() in ['exit', 'выход', 'quit', 'q']:
            print("\n👋 Выход из диалога. До свидания!")
            break
        
        # Обработка запросов на вывод списка товаров
        if any(word in user_input.lower() for word in ['список', 'покажи', 'дай', 'выведи', 'первые', 'все']):
            # Извлекаем число, если есть
            import re
            numbers = re.findall(r'\d+', user_input)
            count = int(numbers[0]) if numbers else 5
            count = min(count, 20)  # Ограничиваем до 20 товаров
            
            print(f"\n📋 Вывожу первые {count} товаров:")
            name_col = 'name' if 'name' in products_df.columns else products_df.columns[0]
            for idx, row in products_df.head(count).iterrows():
                print(f"{idx+1}. {row[name_col]}")
            print("\nДля генерации карточки введите название конкретного товара или ключевое слово (например: 'ноутбук', 'наушники')")
            continue
        
        # Поиск товара по запросу пользователя
        product_info = get_product_info(user_input, products_df)
        if not product_info:
            print("Ассистент: Товар не найден в каталоге. Попробуйте другой запрос.")
            continue
        product_data_str = "\n".join([f"{k}: {v}" for k, v in product_info.items()])
        
        # Повторные попытки при ошибках соединения
        max_retries = 3
        retry_count = 0
        response = None
        
        while retry_count < max_retries:
            try:
                # Используем invoke для вызова chain
                response = chain.invoke(
                    {"user_input": user_input, "product_data": product_data_str},
                    return_only_outputs=False
                )
                break  # Успешный запрос - выходим из цикла
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # Проверяем различные типы ошибок соединения и таймаута
                is_connection_error = any(keyword in error_msg.lower() for keyword in [
                    "connection reset", "connecttimeout", "timeout", 
                    "timed out", "handshake", "ssl"
                ])
                
                if is_connection_error:
                    if retry_count < max_retries:
                        wait_time = retry_count * 3  # Увеличиваем паузу с каждой попыткой: 3, 6, 9 сек
                        print(f"\n⚠️  Ошибка соединения (попытка {retry_count}/{max_retries}). Повторяю через {wait_time} сек...")
                        import time
                        time.sleep(wait_time)
                    else:
                        print(f"\n❌ Ошибка при генерации ответа после {max_retries} попыток: {e}")
                        print("   Проверьте подключение к интернету и попробуйте снова.")
                        break
                else:
                    # Другие ошибки - не повторяем
                    print(f"\n❌ Ошибка при генерации ответа: {e}")
                    break
        
        if response is None:
            continue
            
        # Обработка успешного ответа
        print("\n• Входной запрос:")
        print(user_input)
        print("\n• Ответ ассистента:")
        
        # Извлекаем текст ответа
        response_text = response.get('text', response.get('output', ''))
        print(response_text)
        
        # Попытка получить информацию о токенах из разных мест
        token_info_found = False
        
        # Вариант 1: из generation_info
        if 'generation_info' in response:
            gen_info = response['generation_info']
            if gen_info and isinstance(gen_info, list) and len(gen_info) > 0:
                gen_info = gen_info[0]
            if gen_info and isinstance(gen_info, dict) and 'usage' in gen_info:
                usage = gen_info['usage']
                print("\n• 💰 Расход токенов:")
                print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                token_info_found = True
            
            # Вариант 2: из llm_output (если есть)
            if not token_info_found and 'llm_output' in response:
                llm_out = response['llm_output']
                if llm_out and 'token_usage' in llm_out:
                    usage = llm_out['token_usage']
                    print("\n• 💰 Расход токенов:")
                    print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                    print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                    print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                    token_info_found = True
            
            # Вариант 3: из full_generation (для GigaChat)
            if not token_info_found and 'full_generation' in response:
                full_gen = response['full_generation']
                if isinstance(full_gen, list) and len(full_gen) > 0:
                    gen = full_gen[0]
                    if hasattr(gen, 'generation_info') and gen.generation_info:
                        if 'usage' in gen.generation_info:
                            usage = gen.generation_info['usage']
                            print("\n• 💰 Расход токенов:")
                            print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                            print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                            print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                            token_info_found = True
            
            # Если токены не найдены, пробуем отладку
            if not token_info_found:
                # Попробуем извлечь из full_generation детально
                if 'full_generation' in response:
                    full_gen = response['full_generation']
                    if isinstance(full_gen, list) and len(full_gen) > 0:
                        gen = full_gen[0]
                        # Выводим доступные атрибуты для отладки
                        print("\n• 💰 Расход токенов:")
                        if hasattr(gen, 'generation_info'):
                            gen_info = gen.generation_info
                            if isinstance(gen_info, dict):
                                if 'usage' in gen_info:
                                    usage = gen_info['usage']
                                    print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                                    print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                                    print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                                    token_info_found = True
                                elif 'token_usage' in gen_info:
                                    usage = gen_info['token_usage']
                                    print(f"  Входных токенов (prompt): {usage.get('prompt_tokens', 'N/A')}")
                                    print(f"  Выходных токенов (completion): {usage.get('completion_tokens', 'N/A')}")
                                    print(f"  Всего токенов: {usage.get('total_tokens', 'N/A')}")
                                    token_info_found = True
                                else:
                                    print(f"  Информация недоступна (ключи в generation_info: {list(gen_info.keys())})")
                        
                        if not token_info_found:
                            print("  Информация недоступна")
                else:
                    print("\n• 💰 Расход токенов: информация недоступна")


if __name__ == "__main__":
    main()
