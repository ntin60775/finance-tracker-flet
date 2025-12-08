"""
Property-based тесты для системы логирования.
Проверяют формат и структуру логов.
"""

import json
import logging
from hypothesis import given, strategies as st
from finance_tracker.utils.logger import JsonFormatter

@given(
    message=st.text(),
    level=st.sampled_from([logging.INFO, logging.WARNING, logging.ERROR]),
    module=st.text(min_size=1),
    func=st.text(min_size=1)
)
def test_json_formatter_structure(message, level, module, func):
    """
    Property 61: Язык логов (поддержка unicode) и структура JSON.
    Property 62: Контекст в логах.
    Feature: Logging
    """
    formatter = JsonFormatter()
    
    # Создаем LogRecord вручную
    record = logging.LogRecord(
        name="test_logger",
        level=level,
        pathname="test_path.py",
        lineno=10,
        msg=message,
        args=(),
        exc_info=None,
        func=func
    )
    record.module = module
    
    # Форматируем
    log_output = formatter.format(record)
    
    # Проверяем, что это валидный JSON
    data = json.loads(log_output)
    
    # Проверяем наличие обязательных полей
    assert "timestamp" in data
    assert data["level"] == logging.getLevelName(level)
    assert data["module"] == module
    assert data["function"] == func
    assert data["message"] == message
    
    # Проверяем поддержку Unicode (message должен совпадать)
    assert data["message"] == message

def test_json_formatter_exception():
    """
    Property 60: Логирование важных событий (ошибок с трейсбеком).
    Feature: Logging
    """
    formatter = JsonFormatter()
    
    try:
        raise ValueError("Test exception")
    except ValueError:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None, # Будет заполнен logging системой в реальной жизни, здесь эмулируем
        )
        # Эмуляция exc_info
        import sys
        record.exc_info = sys.exc_info()
        
        log_output = formatter.format(record)
        data = json.loads(log_output)
        
        assert "exception" in data
        assert "ValueError: Test exception" in data["exception"]
