"""
Property-based тесты для конфигурации и настроек.
Проверяют корректность сохранения и загрузки параметров приложения.
"""

import os
import tempfile
import json
from hypothesis import given, strategies as st
from config import Config

# Получаем экземпляр конфигурации (Singleton)
config = Config()

def test_config_singleton():
    """Проверка того, что Config является Singleton."""
    c1 = Config()
    c2 = Config()
    assert c1 is c2

@given(
    db_path=st.text(min_size=1, max_size=100).filter(lambda x: all(c.isprintable() for c in x)),
    theme=st.sampled_from(["light", "dark"]),
    date_fmt=st.sampled_from(["%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"]),
    log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"])
)
def test_settings_persistence_general(db_path, theme, date_fmt, log_level):
    """
    Property 52: Персистентность основных настроек (путь к БД, тема, форматы).
    Feature: Settings
    """
    # Создаем временный файл для конфига
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
    
    original_config_file = config.config_file
    config.config_file = tmp_path
    
    try:
        # 1. Устанавливаем значения
        config.db_path = db_path
        config.theme_mode = theme
        config.date_format = date_fmt
        config.log_level = log_level
        
        # 2. Сохраняем
        config.save()
        
        # 3. Сбрасываем значения в памяти (имитация "забывания")
        config.db_path = "default_path"
        config.theme_mode = "system"
        config.date_format = "default_fmt"
        
        # 4. Загружаем обратно
        config.load()
        
        # 5. Проверяем
        assert config.db_path == db_path
        assert config.theme_mode == theme
        assert config.date_format == date_fmt
        assert config.log_level == log_level
        
        # 6. Проверяем физическое наличие файла и JSON валидность
        with open(tmp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['db_path'] == db_path
            assert data['theme_mode'] == theme
            
    finally:
        # Восстанавливаем путь и удаляем временный файл
        config.config_file = original_config_file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass

@given(
    width=st.integers(min_value=100, max_value=3840),
    height=st.integers(min_value=100, max_value=2160),
    top=st.integers(min_value=0, max_value=1000),
    left=st.integers(min_value=0, max_value=1000),
    last_idx=st.integers(min_value=0, max_value=10)
)
def test_window_geometry_persistence(width, height, top, left, last_idx):
    """
    Property 53: Персистентность геометрии окна и состояния.
    Feature: Settings
    """
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
    
    original_config_file = config.config_file
    config.config_file = tmp_path
    
    try:
        config.window_width = width
        config.window_height = height
        config.window_top = top
        config.window_left = left
        config.last_selected_index = last_idx
        
        config.save()
        
        # Сброс
        config.window_width = 0
        config.window_top = -1
        config.load()
        
        assert config.window_width == width
        assert config.window_height == height
        assert config.window_top == top
        assert config.window_left == left
        assert config.last_selected_index == last_idx
        
    finally:
        config.config_file = original_config_file
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass
