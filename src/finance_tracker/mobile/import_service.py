"""
Сервис импорта данных из файлов.

Публичный функционал - доступен всем пользователям.
"""

import json
from typing import Dict

from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ImportService:
    """
    Сервис для импорта данных из JSON файлов.
    """
    
    @staticmethod
    def import_from_file(filepath: str) -> Dict[str, int]:
        """
        Импортирует данные из JSON файла.
        
        Args:
            filepath: Путь к файлу импорта
            
        Returns:
            Dict[str, int]: Статистика импорта (количество импортированных записей)
            
        Raises:
            FileNotFoundError: Файл не найден
            ValueError: Некорректный формат файла
        """
        logger.info(f"Начало импорта данных из {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл импорта не найден: {filepath}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Некорректный формат JSON в файле {filepath}: {e}")
            raise ValueError(f"Некорректный формат файла: {e}")
        
        # Проверка версии
        file_version = data.get("version")
        if file_version != "2.0.0":
            error_msg = f"Неподдерживаемая версия файла: {file_version}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # TODO: Реализовать импорт данных в БД
        # Пока возвращаем пустую статистику
        stats = {
            "transactions": 0,
            "categories": 0,
            "loans": 0,
        }
        
        logger.info(f"Импорт завершён: {stats}")
        return stats
