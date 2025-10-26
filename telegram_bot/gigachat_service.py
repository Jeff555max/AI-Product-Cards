"""
Сервис для работы с GigaChat LLM
"""

import os
from typing import Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_gigachat.chat_models import GigaChat
from langfuse.langchain import CallbackHandler

from .config import config


class GigaChatService:
    """Сервис для генерации карточек товаров через GigaChat"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.llm = None
        self.chain = None
        self.langfuse_handler = None
        self._initialize_langfuse()
        self._initialize_llm()
        self._load_prompt()
    
    def _initialize_langfuse(self):
        """Инициализация Langfuse для трейсинга"""
        if config.ENABLE_LANGFUSE:
            try:
                self.langfuse_handler = CallbackHandler()
                print("✅ Langfuse трейсинг активирован")
            except Exception as e:
                print(f"⚠️  Langfuse не удалось инициализировать: {e}")
                self.langfuse_handler = None
    
    def _initialize_llm(self):
        """Инициализация GigaChat LLM"""
        try:
            self.llm = GigaChat(
                credentials=config.GIGACHAT_API_KEY,
                model=config.GIGACHAT_MODEL,
                scope=config.GIGACHAT_SCOPE,
                temperature=config.GIGACHAT_TEMPERATURE,
                top_p=config.GIGACHAT_TOP_P,
                profanity_check=True,
                verify_ssl_certs=False,
                streaming=False,
                timeout=120
            )
            print(f"✅ GigaChat инициализирован: {config.GIGACHAT_MODEL}")
        except Exception as e:
            print(f"❌ Ошибка инициализации GigaChat: {e}")
            raise
    
    def _load_prompt(self):
        """Загрузка системного промпта"""
        prompt_path = os.path.join(config.PROMPTS_DIR, 'system_prompt.txt')
        
        try:
            with open(prompt_path, encoding='utf-8') as f:
                prompt_template = f.read()
            
            self.prompt = PromptTemplate(
                input_variables=["user_input", "product_data"],
                template=prompt_template
            )
            
            # Создание цепочки
            self.chain = LLMChain(
                llm=self.llm,
                prompt=self.prompt,
                return_final_only=False
            )
            print("✅ Системный промпт загружен")
        except Exception as e:
            print(f"❌ Ошибка загрузки промпта: {e}")
            raise
    
    def generate_card(
        self,
        user_input: str,
        product_data: str,
        max_retries: int = 3
    ) -> Optional[dict]:
        """
        Генерация карточки товара.
        
        Args:
            user_input: Запрос пользователя
            product_data: Данные товара
            max_retries: Максимум попыток при ошибках
            
        Returns:
            Словарь с ответом или None при ошибке
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Формируем конфигурацию для вызова
                invoke_config = {}
                if self.langfuse_handler:
                    invoke_config["callbacks"] = [self.langfuse_handler]
                
                # Вызов цепочки
                response = self.chain.invoke(
                    {
                        "user_input": user_input,
                        "product_data": product_data
                    },
                    config=invoke_config if invoke_config else None,
                    return_only_outputs=False
                )
                
                return response
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # Проверяем тип ошибки
                is_connection_error = any(
                    keyword in error_msg.lower()
                    for keyword in ["connection reset", "timeout", "ssl"]
                )
                
                if is_connection_error and retry_count < max_retries:
                    import time
                    wait_time = retry_count * 3
                    print(f"⚠️  Ошибка соединения (попытка {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Ошибка генерации: {e}")
                    return None
        
        return None
    
    def extract_token_info(self, response: dict) -> dict:
        """
        Извлечение информации о токенах из ответа.
        
        Args:
            response: Ответ от LLM
            
        Returns:
            Словарь с информацией о токенах
        """
        token_info = {
            'input_tokens': 'N/A',
            'output_tokens': 'N/A',
            'total_tokens': 'N/A',
            'cached_tokens': 0
        }
        
        # Приоритет 1: usage_metadata
        if 'full_generation' in response:
            full_gen = response['full_generation']
            if isinstance(full_gen, list) and len(full_gen) > 0:
                for gen in full_gen:
                    if hasattr(gen, 'message') and hasattr(gen.message, 'usage_metadata'):
                        usage = gen.message.usage_metadata
                        if usage:
                            if isinstance(usage, dict):
                                token_info['input_tokens'] = usage.get('input_tokens', 'N/A')
                                token_info['output_tokens'] = usage.get('output_tokens', 'N/A')
                                token_info['total_tokens'] = usage.get('total_tokens', 'N/A')
                                
                                if 'input_token_details' in usage:
                                    token_info['cached_tokens'] = usage['input_token_details'].get('cache_read', 0)
                            break
        
        return token_info
