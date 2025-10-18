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

    print("\n=== Диалог с ассистентом по каталогу товаров ===\n(Для выхода введите 'exit')\n")
    while True:
        user_input = input("User: ")
        if user_input.strip().lower() == 'exit':
            print("Выход из диалога.")
            break
        # Поиск товара по запросу пользователя
        product_info = get_product_info(user_input, products_df)
        if not product_info:
            print("Ассистент: Товар не найден в каталоге. Попробуйте другой запрос.")
            continue
        product_data_str = "\n".join([f"{k}: {v}" for k, v in product_info.items()])
        response = chain.run(user_input=user_input, product_data=product_data_str)
        print("\n• Входной запрос:")
        print(user_input)
        print("\n• Ответ ассистента:")
        print(response)
        # Попытка вывести расход токенов (если поддерживается)
        if hasattr(response, 'llm_output') and 'token_usage' in response.llm_output:
            print("\n• Расход токенов:")
            print(response.llm_output['token_usage'])


if __name__ == "__main__":
    main()
