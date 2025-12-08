"""
Модуль настройки логирования для Finance Tracker Flet.

Обеспечивает:
- Структурированное логирование (JSON формат)
- Ротацию логов
- Вывод в консоль и файл
- Поддержку русского языка в сообщениях
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from finance_tracker.config import settings

class JsonFormatter(logging.Formatter):
    """
    Форматтер для вывода логов в формате JSON.
    Соответствует требованиям структурированного логирования.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирует запись лога в JSON строку.
        
        Args:
            record: Запись лога
            
        Returns:
            str: JSON строка
        """
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Добавляем дополнительные поля из extra, если они есть
        # Пример: logger.info("message", extra={"user_id": 1})
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                          "funcName", "levelname", "levelno", "lineno", "module",
                          "msecs", "message", "msg", "name", "pathname", "process",
                          "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                log_record[key] = value

        # Обработка исключений
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logging() -> None:
    """
    Настраивает систему логирования приложения.
    
    - Создаёт директорию для логов
    - Создаёт новый файл лога для каждого сеанса (формат: finance_tracker_YYYYMMDD_HHMMSS.log)
    - Настраивает JSON форматирование для файла
    - Настраивает текстовый формат для консоли
    """
    log_file = Path(settings.log_file)
    log_dir = log_file.parent
    
    # Создаем директорию, если нет
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать директорию логов: {e}")
            return

    # Создаём уникальное имя файла для текущего сеанса
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_log_file = log_dir / f"finance_tracker_{timestamp}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Удаляем существующие хендлеры
    root_logger.handlers = []

    formatter = JsonFormatter()

    # 1. Файловый хендлер для текущего сеанса
    try:
        file_handler = logging.FileHandler(
            session_log_file,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось настроить файл логов: {e}")

    # 2. Консольный хендлер с текстовым форматом для удобства разработки
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Для консоли используем более читаемый формат
    console_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    logging.info("Система логирования инициализирована")
    logging.info(f"Логи записываются в: {session_log_file}")

def get_logger(name: str) -> logging.Logger:
    """
    Возвращает логгер с указанным именем.
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    return logging.getLogger(name)
