"""
Конфигурация pytest для тестов finance_tracker.
"""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
from decimal import Decimal
import uuid
import flet as ft

from finance_tracker.models import Base
from finance_tracker.models.models import CategoryDB, TransactionDB, TransactionCreate
from finance_tracker.models.enums import TransactionType


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


@pytest.fixture
def mock_page():
    """
    Фикстура для создания мока Flet Page.
    
    Использует СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0):
    - page.open(dialog) - для открытия диалогов, SnackBar и других overlay компонентов
    - page.close(dialog) - для закрытия диалогов и overlay компонентов
    
    ВАЖНО: Не используется устаревший API:
    - ❌ page.dialog = dialog; dialog.open = True; page.update()
    - ✅ page.open(dialog)
    
    Returns:
        MagicMock: Полностью настроенный мок объекта page с методами:
            - overlay: пустой список для модальных окон
            - dialog: None (для обратной совместимости, но не используется в новом коде)
            - update(): метод для обновления UI
            - open(): метод для открытия диалогов (СОВРЕМЕННЫЙ API)
            - close(): метод для закрытия диалогов (СОВРЕМЕННЫЙ API)
            - show_snack_bar(): метод для показа SnackBar
    """
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    # Атрибут dialog оставлен для обратной совместимости, но не используется в новом коде
    page.dialog = None
    page.update = MagicMock()
    # Современный Flet API для работы с диалогами
    page.open = MagicMock()
    page.close = MagicMock()
    page.show_snack_bar = MagicMock()
    page.width = 1200
    page.height = 800
    page.theme_mode = "light"
    return page


@pytest.fixture
def mock_session():
    """
    Фикстура для создания мока SQLAlchemy Session.
    
    Returns:
        Mock: Мок объекта session с настроенными методами:
            - commit(): фиксация транзакции
            - rollback(): откат транзакции
            - close(): закрытие сессии
            - query(): создание запроса
            - add(): добавление объекта
            - delete(): удаление объекта
    """
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    session.add = Mock()
    session.delete = Mock()
    
    # Настройка context manager
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=None)
    
    return session


@pytest.fixture
def sample_categories(db_session):
    """
    Фикстура для создания образцов категорий в тестовой БД.
    
    Returns:
        dict: Словарь с категориями по типам:
            - 'expense': список категорий расходов
            - 'income': список категорий доходов
    """
    expense_categories = [
        CategoryDB(
            id=str(uuid.uuid4()),
            name="Еда",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=datetime.now()
        ),
        CategoryDB(
            id=str(uuid.uuid4()),
            name="Транспорт",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=datetime.now()
        ),
        CategoryDB(
            id=str(uuid.uuid4()),
            name="Развлечения",
            type=TransactionType.EXPENSE,
            is_system=False,
            created_at=datetime.now()
        )
    ]
    
    income_categories = [
        CategoryDB(
            id=str(uuid.uuid4()),
            name="Зарплата",
            type=TransactionType.INCOME,
            is_system=True,
            created_at=datetime.now()
        ),
        CategoryDB(
            id=str(uuid.uuid4()),
            name="Подработка",
            type=TransactionType.INCOME,
            is_system=False,
            created_at=datetime.now()
        )
    ]
    
    all_categories = expense_categories + income_categories
    for category in all_categories:
        db_session.add(category)
    db_session.commit()
    
    return {
        'expense': expense_categories,
        'income': income_categories,
        'all': all_categories
    }


@pytest.fixture
def sample_transactions(db_session, sample_categories):
    """
    Фикстура для создания образцов транзакций в тестовой БД.
    
    Returns:
        list: Список созданных транзакций
    """
    categories = sample_categories['all']
    
    transactions = [
        TransactionDB(
            id=str(uuid.uuid4()),
            amount=Decimal('150.50'),
            type=TransactionType.EXPENSE,
            category_id=categories[0].id,  # Еда
            description="Покупки в магазине",
            transaction_date=date.today(),
            created_at=datetime.now()
        ),
        TransactionDB(
            id=str(uuid.uuid4()),
            amount=Decimal('50000.00'),
            type=TransactionType.INCOME,
            category_id=categories[3].id,  # Зарплата
            description="Зарплата за декабрь",
            transaction_date=date.today(),
            created_at=datetime.now()
        ),
        TransactionDB(
            id=str(uuid.uuid4()),
            amount=Decimal('2500.00'),
            type=TransactionType.EXPENSE,
            category_id=categories[1].id,  # Транспорт
            description="Проездной билет",
            transaction_date=date(2024, 12, 1),
            created_at=datetime.now()
        )
    ]
    
    for transaction in transactions:
        db_session.add(transaction)
    db_session.commit()
    
    return transactions
