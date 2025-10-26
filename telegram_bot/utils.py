"""
Утилиты для работы с каталогом товаров
Переиспользование логики из generate_card.py
"""

import os
import re
import pandas as pd
import requests
from typing import Optional, Dict, List


def download_yadisk_file(yadisk_url: str, out_path: str) -> None:
    """
    Скачивает файл с Яндекс.Диска по публичной ссылке.
    
    Args:
        yadisk_url: Публичная ссылка на файл
        out_path: Путь для сохранения
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


def load_products(data_dir: str, force_download: bool = False) -> pd.DataFrame:
    """
    Загружает каталог товаров.
    
    Args:
        data_dir: Путь к директории с данными
        force_download: Принудительно скачать с Яндекс.Диска
        
    Returns:
        DataFrame с каталогом товаров
    """
    os.makedirs(data_dir, exist_ok=True)
    local_path = os.path.join(data_dir, 'products.csv')
    
    # Проверяем наличие локального файла
    if not os.path.exists(local_path) or force_download:
        print("📥 Скачиваю каталог товаров с Яндекс.Диска...")
        download_yadisk_file(
            'https://disk.yandex.ru/d/3Y1rogh78wVtAw',
            local_path
        )
        print(f"✅ Каталог сохранён: {local_path}")
    else:
        print(f"✅ Каталог загружен: {local_path}")
    
    return pd.read_csv(local_path)


def get_product_info(query: str, df: pd.DataFrame) -> Optional[Dict]:
    """
    Умный поиск товара в каталоге с синонимами.
    
    Args:
        query: Поисковый запрос
        df: DataFrame с товарами
        
    Returns:
        Словарь с данными товара или None
    """
    # Словарь синонимов
    synonyms = {
        'ноутбук': ['laptop', 'notebook', 'ноутбук'],
        'наушники': ['headphone', 'earphone', 'earbud', 'наушники'],
        'колонка': ['speaker', 'колонка'],
        'телефон': ['phone', 'smartphone', 'телефон'],
        'камера': ['camera', 'камера'],
        'планшет': ['tablet', 'ipad', 'планшет'],
    }
    
    # Определяем колонку с названием товара
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
        for col in df.columns:
            if df[col].dtype == 'object' and col.lower() != 'id':
                name_col = col
                break
    
    if not name_col:
        name_col = df.columns[0]
    
    # Шаг 1: Точное совпадение
    row = df[df[name_col].astype(str).str.lower() == query.lower()]
    if not row.empty:
        return row.iloc[0].to_dict()
    
    # Шаг 2: Поиск по ключевым словам с синонимами
    search_keywords = []
    keywords = query.lower().split()
    
    for keyword in keywords:
        search_keywords.append(keyword)
        if keyword in synonyms:
            search_keywords.extend(synonyms[keyword])
    
    # Шаг 3: Regex поиск
    for keyword in search_keywords:
        if len(keyword) > 2:
            escaped_keyword = re.escape(keyword)
            try:
                matches = df[df[name_col].astype(str).str.lower().str.contains(
                    escaped_keyword, na=False, regex=True
                )]
                if not matches.empty:
                    return matches.iloc[0].to_dict()
            except Exception:
                continue
    
    return None


def search_products(query: str, df: pd.DataFrame, limit: int = 10) -> List[Dict]:
    """
    Поиск нескольких товаров по категории.
    
    Args:
        query: Категория или ключевое слово
        df: DataFrame с товарами
        limit: Максимальное количество результатов
        
    Returns:
        Список найденных товаров
    """
    synonyms = {
        'ноутбук': ['laptop', 'notebook'],
        'наушники': ['headphone', 'earphone', 'earbud'],
        'колонка': ['speaker'],
        'телефон': ['phone', 'smartphone'],
        'камера': ['camera'],
        'планшет': ['tablet', 'ipad']
    }
    
    # Определяем колонку
    name_col = 'name' if 'name' in df.columns else df.columns[0]
    
    # Собираем ключевые слова
    search_keywords = []
    for key, values in synonyms.items():
        if key in query.lower():
            search_keywords.extend(values)
            break
    
    if not search_keywords:
        search_keywords = query.lower().split()
    
    # Поиск
    results = []
    for keyword in search_keywords:
        if len(keyword) > 2:
            escaped_keyword = re.escape(keyword)
            try:
                matches = df[df[name_col].astype(str).str.lower().str.contains(
                    escaped_keyword, na=False, regex=False
                )]
                if not matches.empty:
                    results = matches.head(limit).to_dict('records')
                    break
            except Exception:
                continue
    
    return results


def format_product_data(product_info: Dict) -> str:
    """
    Форматирует данные товара для промпта.
    
    Args:
        product_info: Словарь с данными товара
        
    Returns:
        Отформатированная строка
    """
    return "\n".join([f"{k}: {v}" for k, v in product_info.items()])
