"""
Конфигурация pytest для тестов finance_tracker_flet.

Добавляет родительскую директорию в sys.path для корректного импорта модулей.
"""
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем после добавления в sys.path
from models import Base


@pytest.fixture
def db_session():
    """
    Централизованная фикстура для создания временной БД и сессии.
    Автоматически закрывает соединение после теста.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # Закрываем сессию и соединение
    session.close()
    engine.dispose()
