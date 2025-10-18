import os
import pandas as pd
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

# Загрузка переменных окружения
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

# Загрузка каталога товаров (пример: data/products.csv)
PRODUCTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.csv')
products_df = pd.read_csv(PRODUCTS_PATH)

def get_product_info(query, df):
    # Поиск товара по названию (можно доработать под свои нужды)
    row = df[df['name'].str.lower() == query.lower()]
    if not row.empty:
        return row.iloc[0].to_dict()
    return None

def main():
    # Ввод запроса пользователя
    user_input = input("Введите запрос для генерации карточки товара: ")

    # Пример: берём первый товар для теста
    query = user_input
    product_info = get_product_info(query, products_df)
    if not product_info:
        print("Товар не найден в каталоге.")
        return
    product_data_str = "\n".join([f"{k}: {v}" for k, v in product_info.items()])

    # Загрузка системного промпта
    with open(os.path.join(os.path.dirname(__file__), '..', 'prompts', 'system_prompt.txt'), encoding='utf-8') as f:
        prompt_template = f.read()

    prompt = PromptTemplate(
        input_variables=["user_input", "product_data"],
        template=prompt_template
    )

    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0.2,
        openai_api_key=API_KEY
    )
    chain = LLMChain(llm=llm, prompt=prompt)

    # Генерация карточки
    response = chain.run(user_input=user_input, product_data=product_data_str)

    # Вывод в консоль
    print("\nВходной запрос:")
    print(user_input)
    print("\nОтвет ассистента:")
    print(response)
    # Попытка вывести расход токенов (если поддерживается)
    if hasattr(response, 'llm_output') and 'token_usage' in response.llm_output:
        print("\nРасход токенов:")
        print(response.llm_output['token_usage'])

if __name__ == "__main__":
    main()
