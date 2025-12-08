"""
Конфигурация pytest для тестов finance_tracker.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.models import Base


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
