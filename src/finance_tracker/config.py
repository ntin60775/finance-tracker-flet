"""
Модуль конфигурации приложения Finance Tracker Flet.

Содержит настройки:
- Основные параметры приложения (название, версия)
- Настройки базы данных (путь)
- Настройки интерфейса (тема, размеры окна)
- Настройки логирования
- Персистентность настроек (загрузка/сохранение)
- Управление пользовательской директорией данных
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    """
    Класс конфигурации приложения.
    Реализует паттерн Singleton для доступа к настройкам из любой части приложения.
    
    Все пользовательские данные (БД, логи, настройки, экспорты) хранятся в
    директории ~/.finance_tracker_data/ независимо от режима запуска (разработка/.exe).
    """
    
    _instance = None
    
    # Константы приложения
    APP_NAME = "Finance Tracker"
    VERSION = "2.0.0"
    
    @staticmethod
    def get_user_data_dir() -> Path:
        """
        Возвращает путь к директории пользовательских данных.
        
        Создаёт директорию ~/.finance_tracker_data/ и необходимые поддиректории:
        - logs/ - для файлов логов
        - exports/ - для экспортированных данных
        
        Returns:
            Path: Путь к ~/.finance_tracker_data/
        """
        # Получаем домашнюю директорию пользователя
        home = Path.home()
        data_dir = home / ".finance_tracker_data"
        
        # Создаём основную директорию, если не существует
        data_dir.mkdir(exist_ok=True)
        logger.info(f"Директория пользовательских данных: {data_dir}")
        
        # Создаём поддиректорию для логов
        logs_dir = data_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        logger.debug(f"Директория логов: {logs_dir}")
        
        # Создаём поддиректорию для экспортов
        exports_dir = data_dir / "exports"
        exports_dir.mkdir(exist_ok=True)
        logger.debug(f"Директория экспортов: {exports_dir}")
        
        return data_dir
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Получаем директорию пользовательских данных
        self.user_data_dir = self.get_user_data_dir()
        
        # Определяем пути к файлам
        self.db_path: str = str(self.user_data_dir / "finance.db")
        self.config_file: str = str(self.user_data_dir / "config.json")
        self.log_file: str = str(self.user_data_dir / "logs" / "finance_tracker.log")
        
        # Значения по умолчанию для UI
        self.theme_mode: str = "light"  # light, dark, system
        self.window_width: int = 1200
        self.window_height: int = 800
        self.window_top: Optional[int] = None
        self.window_left: Optional[int] = None
        
        # Настройки логирования
        self.log_level: str = "INFO"
        
        # Настройки форматов
        self.date_format: str = "%d.%m.%Y"
        self.currency_symbol: str = "₽"
        
        # Состояние приложения
        self.last_selected_index: int = 0
        
        # Загрузка настроек при инициализации
        self.load()

    def load(self) -> None:
        """
        Загружает настройки из файла конфигурации.
        
        Если файл не существует, используются значения по умолчанию.
        Путь к БД не загружается из конфигурации - всегда используется
        ~/.finance_tracker_data/finance.db
        """
        if not os.path.exists(self.config_file):
            logger.info(f"Файл конфигурации не найден, используются значения по умолчанию: {self.config_file}")
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Настройки UI
            self.theme_mode = data.get("theme_mode", "light")
            self.window_width = data.get("window_width", 1200)
            self.window_height = data.get("window_height", 800)
            self.window_top = data.get("window_top")
            self.window_left = data.get("window_left")
            
            # Настройки логирования
            self.log_level = data.get("log_level", "INFO")
            
            # Настройки форматов
            self.date_format = data.get("date_format", "%d.%m.%Y")
            
            # Состояние приложения
            self.last_selected_index = data.get("last_selected_index", 0)
            
            logger.info(f"Конфигурация загружена из {self.config_file}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")

    def save(self) -> None:
        """
        Сохраняет текущие настройки в файл конфигурации.
        
        Путь к БД не сохраняется - он всегда фиксирован как
        ~/.finance_tracker_data/finance.db
        """
        data = {
            "theme_mode": self.theme_mode,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_top": self.window_top,
            "window_left": self.window_left,
            "log_level": self.log_level,
            "date_format": self.date_format,
            "last_selected_index": self.last_selected_index
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Конфигурация сохранена в {self.config_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")

# Глобальный экземпляр конфигурации
settings = Config()
