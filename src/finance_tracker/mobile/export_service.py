"""
Сервис экспорта данных в файлы.

Публичный функционал - доступен всем пользователям.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """
    Сервис для экспорта данных приложения в JSON файлы.
    
    Экспортирует:
    - Транзакции
    - Категории
    - Кредиты
    - Настройки
    """
    
    @staticmethod
    def export_to_file(filepath: Optional[str] = None) -> str:
        """
        Экспортирует все данные в JSON файл.
        
        Args:
            filepath: Путь к файлу экспорта. Если None - создаётся автоматически
                     в директории ~/.finance_tracker_data/exports/
            
        Returns:
            str: Путь к созданному файлу
            
        Raises:
            IOError: Ошибка записи файла
        """
        if filepath is None:
            # Создаём директорию для экспортов (уже создана в config.py, но проверим)
            export_dir = settings.user_data_dir / "exports"
            export_dir.mkdir(exist_ok=True)
            
            # Генерируем имя файла с датой
            timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
            filepath = str(export_dir / f"backup_{timestamp}.json")
        
        logger.info(f"Начало экспорта данных в {filepath}")
        
        # TODO: Реализовать экспорт данных из БД
        # Пока создаём структуру для будущей реализации
        data = {
            "version": "2.0.0",
            "export_date": datetime.now().isoformat(),
            "transactions": [],
            "categories": [],
            "loans": [],
            "settings": {},
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Экспорт завершён: {filepath}")
            return filepath
            
        except IOError as e:
            logger.error(f"Ошибка при записи файла экспорта {filepath}: {e}")
            raise
