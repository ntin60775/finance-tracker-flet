"""
Тесты для проверки работы фикстур из conftest.py.
"""
import pytest
from datetime import date, datetime
from decimal import Decimal
import uuid

from finance_tracker.models.models import CategoryDB, TransactionDB
from finance_tracker.models.enums import TransactionType


def test_mock_page_fixture(mock_page):
    """Тест фикстуры mock_page."""
    # Проверяем, что все необходимые атрибуты присутствуют
    assert hasattr(mock_page, 'overlay')
    assert hasattr(mock_page, 'update')
    assert hasattr(mock_page, 'open')
    assert hasattr(mock_page, 'close')
    assert hasattr(mock_page, 'show_snack_bar')
    
    # Проверяем начальные значения
    assert mock_page.overlay == []
    assert mock_page.width == 1200
    assert mock_page.height == 800


def test_mock_session_fixture(mock_session):
    """Тест фикстуры mock_session."""
    # Проверяем, что все необходимые методы присутствуют
    assert hasattr(mock_session, 'commit')
    assert hasattr(mock_session, 'rollback')
    assert hasattr(mock_session, 'close')
    assert hasattr(mock_session, 'query')
    assert hasattr(mock_session, 'add')
    assert hasattr(mock_session, 'delete')
    
    # Проверяем работу context manager
    assert hasattr(mock_session, '__enter__')
    assert hasattr(mock_session, '__exit__')


def test_sample_categories_fixture(sample_categories):
    """Тест фикстуры sample_categories."""
    # Проверяем структуру возвращаемых данных
    assert 'expense' in sample_categories
    assert 'income' in sample_categories
    assert 'all' in sample_categories
    
    # Проверяем количество категорий
    assert len(sample_categories['expense']) == 3
    assert len(sample_categories['income']) == 2
    assert len(sample_categories['all']) == 5
    
    # Проверяем типы категорий
    for category in sample_categories['expense']:
        assert isinstance(category, CategoryDB)
        assert category.type == TransactionType.EXPENSE
        assert category.id is not None
        assert category.name is not None
    
    for category in sample_categories['income']:
        assert isinstance(category, CategoryDB)
        assert category.type == TransactionType.INCOME
        assert category.id is not None
        assert category.name is not None
    
    # Проверяем, что первая категория доходов системная
    assert sample_categories['income'][0].is_system == True


def test_sample_transactions_fixture(sample_transactions):
    """Тест фикстуры sample_transactions."""
    # Проверяем, что возвращается список транзакций
    assert isinstance(sample_transactions, list)
    assert len(sample_transactions) == 3
    
    # Проверяем каждую транзакцию
    for transaction in sample_transactions:
        assert isinstance(transaction, TransactionDB)
        assert transaction.id is not None
        assert isinstance(transaction.amount, Decimal)
        assert transaction.amount > Decimal('0')
        assert transaction.type in [TransactionType.INCOME, TransactionType.EXPENSE]
        assert transaction.category_id is not None
        assert isinstance(transaction.transaction_date, date)
        assert isinstance(transaction.created_at, datetime)
        
        # Проверяем, что это валидный UUID
        uuid.UUID(transaction.id)
        uuid.UUID(transaction.category_id)


def test_db_session_fixture(db_session):
    """Тест фикстуры db_session."""
    # Проверяем, что сессия создана и работает
    assert db_session is not None
    
    # Создаем тестовую категорию
    test_category = CategoryDB(
        id=str(uuid.uuid4()),
        name="Тестовая категория",
        type=TransactionType.EXPENSE,
        is_system=False,
        created_at=datetime.now()
    )
    
    # Добавляем в БД
    db_session.add(test_category)
    db_session.commit()
    
    # Проверяем, что категория сохранилась
    saved_category = db_session.query(CategoryDB).filter_by(id=test_category.id).first()
    assert saved_category is not None
    assert saved_category.name == "Тестовая категория"
    assert saved_category.type == TransactionType.EXPENSE


def test_fixtures_integration(db_session, sample_categories, sample_transactions, mock_page, mock_session):
    """Тест интеграции всех фикстур."""
    # Проверяем, что все фикстуры работают вместе
    assert db_session is not None
    assert sample_categories is not None
    assert sample_transactions is not None
    assert mock_page is not None
    assert mock_session is not None
    
    # Проверяем, что данные из sample_categories доступны в БД
    categories_count = db_session.query(CategoryDB).count()
    assert categories_count == len(sample_categories['all'])
    
    # Проверяем, что данные из sample_transactions доступны в БД
    transactions_count = db_session.query(TransactionDB).count()
    assert transactions_count == len(sample_transactions)