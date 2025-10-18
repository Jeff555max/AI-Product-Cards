
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
    
    # Поиск по ключевым словам
    keywords = query.lower().split()
    for keyword in keywords:
        if len(keyword) > 2:  # Игнорируем короткие слова
            # Экранируем специальные символы regex
            escaped_keyword = re.escape(keyword)
            try:
                matches = df[df[name_col].astype(str).str.lower().str.contains(escaped_keyword, na=False, regex=True)]
                if not matches.empty:
                    print(f"✓ Найдено {len(matches)} товаров по запросу '{keyword}'. Беру первый.")
                    return matches.iloc[0].to_dict()
            except Exception as e:
                print(f"⚠️ Ошибка поиска по слову '{keyword}': {e}")
                continue
    
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
        verify_ssl_certs=False
    )
    chain = LLMChain(llm=llm, prompt=prompt)

    print("\n=== Диалог с ассистентом по каталогу товаров ===")
    print("(Для выхода введите 'exit' или 'выход')\n")
    while True:
        user_input = input("User: ")
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
        response = chain(user_input=user_input, product_data=product_data_str)
        print("\n• Входной запрос:")
        print(user_input)
        print("\n• Ответ ассистента:")
        print(response['text'] if 'text' in response else response)
        # Расход токенов (если поддерживается)
        usage = response.get('llm_output', {}).get('token_usage') if isinstance(response, dict) else None
        if usage:
            print("\n• Расход токенов:")
            print(usage)


if __name__ == "__main__":
    main()
