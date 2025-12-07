"""
Модуль конфигурации приложения Finance Tracker Flet.

Содержит настройки:
- Основные параметры приложения (название, версия)
- Настройки базы данных (путь)
- Настройки интерфейса (тема, размеры окна)
- Настройки логирования
- Персистентность настроек (загрузка/сохранение)
"""

import os
import json
import logging
from typing import Optional

from database import get_database_path

logger = logging.getLogger(__name__)

class Config:
    """
    Класс конфигурации приложения.
    Реализует паттерн Singleton для доступа к настройкам из любой части приложения.
    """
    
    _instance = None
    
    # Константы приложения
    APP_NAME = "Finance Tracker"
    VERSION = "2.0.0"
    
    # Пути по умолчанию
    DEFAULT_DB_PATH = get_database_path()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Определение пути к файлу конфигурации
        # Используем ту же директорию, что и для БД
        self.config_dir = os.path.dirname(self.DEFAULT_DB_PATH)
        
        # Создаём директорию конфигурации, если её нет (для режима .exe)
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            logger.info(f"Создана директория конфигурации: {self.config_dir}")
        
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # Значения по умолчанию
        self.db_path: str = self.DEFAULT_DB_PATH
        self.theme_mode: str = "light"  # light, dark, system
        self.window_width: int = 1200
        self.window_height: int = 800
        self.window_top: Optional[int] = None
        self.window_left: Optional[int] = None
        
        # Настройки логирования
        self.log_level: str = "INFO"
        self.log_file: str = os.path.join(self.config_dir, "finance_tracker.log")
        
        # Настройки форматов
        self.date_format: str = "%d.%m.%Y"
        self.currency_symbol: str = "₽"
        
        # Состояние приложения
        self.last_selected_index: int = 0
        
        # Загрузка настроек при инициализации
        self.load()

    def load(self) -> None:
        """Загружает настройки из файла конфигурации."""
        if not os.path.exists(self.config_file):
            logger.info(f"Файл конфигурации не найден, используются значения по умолчанию: {self.config_file}")
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.db_path = data.get("db_path", self.DEFAULT_DB_PATH)
            self.theme_mode = data.get("theme_mode", "light")
            self.window_width = data.get("window_width", 1200)
            self.window_height = data.get("window_height", 800)
            self.window_top = data.get("window_top")
            self.window_left = data.get("window_left")
            self.log_level = data.get("log_level", "INFO")
            self.date_format = data.get("date_format", "%d.%m.%Y")
            self.last_selected_index = data.get("last_selected_index", 0)
            
            logger.info(f"Конфигурация загружена из {self.config_file}")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")

    def save(self) -> None:
        """Сохраняет текущие настройки в файл конфигурации."""
        data = {
            "db_path": self.db_path,
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
