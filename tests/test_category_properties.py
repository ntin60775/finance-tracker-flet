"""
Property-based тесты для категорий (Flet версия).

Тестирует:
- Property 10: Фильтрация категорий по типу
- Property 11: Уникальность названия категории
- Property 12: Защита системных категорий
- Property 13: Защита категорий со связанными транзакциями
"""

from datetime import date
from contextlib import contextmanager
import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models import (
    Base,
    CategoryDB,
    TransactionDB,
    TransactionType,
)
from finance_tracker.services.category_service import (
    get_all_categories,
    create_category,
    delete_category
)

# Создаём тестовый движок БД в памяти
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Включает поддержку foreign keys в SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base.metadata.create_all(test_engine)
TestSessionLocal = sessionmaker(bind=test_engine)

@contextmanager
def get_test_session():
    """Контекстный менеджер для создания тестовой сессии БД."""
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем данные после использования
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()

# --- Strategies ---
category_names = st.text(min_size=1, max_size=50).map(lambda x: x.strip()).filter(lambda x: len(x) > 0)
transaction_types = st.sampled_from(TransactionType)

class TestCategoryProperties:
    """Property-based тесты для управления категориями."""

    @given(
        names_inc=st.lists(category_names, min_size=1, max_size=5, unique=True),
        names_exp=st.lists(category_names, min_size=1, max_size=5, unique=True)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_10_filter_categories(self, names_inc, names_exp):
        """
        Property 10: Фильтрация категорий по типу.
        
        Validates: Requirements 4.2
        
        Проверяет, что фильтр корректно возвращает только категории указанного типа.
        """
        # Убедимся, что имена не пересекаются между списками (hypothesis unique=True работает внутри списка)
        # В редком случае пересечения просто пропустим тест или сделаем имена уникальными префиксами
        names_inc = [f"inc_{x}" for x in names_inc]
        names_exp = [f"exp_{x}" for x in names_exp]
        
        with get_test_session() as session:
            # Arrange
            for name in names_inc:
                create_category(session, name, TransactionType.INCOME)
            for name in names_exp:
                create_category(session, name, TransactionType.EXPENSE)
            
            # Act & Assert for INCOME
            result_inc = get_all_categories(session, TransactionType.INCOME)
            assert len(result_inc) == len(names_inc)
            for cat in result_inc:
                assert cat.type == TransactionType.INCOME
                
            # Act & Assert for EXPENSE
            result_exp = get_all_categories(session, TransactionType.EXPENSE)
            assert len(result_exp) == len(names_exp)
            for cat in result_exp:
                assert cat.type == TransactionType.EXPENSE
                
            # Act & Assert for ALL
            result_all = get_all_categories(session, None)
            assert len(result_all) == len(names_inc) + len(names_exp)

    @given(name=category_names, t_type=transaction_types)
    @settings(max_examples=30, deadline=None)
    def test_property_11_unique_name(self, name, t_type):
        """
        Property 11: Уникальность названия категории.
        
        Validates: Requirements 4.3
        
        Попытка создать категорию с существующим именем должна вызывать ошибку.
        """
        with get_test_session() as session:
            # Arrange
            create_category(session, name, t_type)
            
            # Act & Assert
            with pytest.raises(ValueError, match="уже существует"):
                create_category(session, name, t_type) # Тип не важен, имя уникально глобально

    @given(name=category_names, t_type=transaction_types)
    @settings(max_examples=30, deadline=None)
    def test_property_12_system_category_protection(self, name, t_type):
        """
        Property 12: Защита системных категорий.
        
        Validates: Requirements 4.4
        
        Системные категории нельзя удалить.
        """
        with get_test_session() as session:
            # Arrange: Создаем категорию вручную как системную
            # (через сервис нельзя создать системную)
            cat = CategoryDB(name=name, type=t_type, is_system=True)
            session.add(cat)
            session.commit()
            cat_id = cat.id
            
            # Act & Assert
            with pytest.raises(ValueError, match="системную категорию"):
                delete_category(session, cat_id)

            # Verify it still exists
            assert session.get(CategoryDB, cat_id) is not None

    @given(name=category_names, amount=st.floats(min_value=10, max_value=1000))
    @settings(max_examples=30, deadline=None)
    def test_property_13_linked_transaction_protection(self, name, amount):
        """
        Property 13: Защита категорий со связанными транзакциями.
        
        Validates: Requirements 4.5
        
        Нельзя удалить категорию, если она используется в транзакциях.
        """
        with get_test_session() as session:
            # Arrange
            cat = create_category(session, name, TransactionType.EXPENSE)
            
            tx = TransactionDB(
                amount=amount,
                type=TransactionType.EXPENSE,
                category_id=cat.id,
                transaction_date=date.today(),
                description="Linked tx"
            )
            session.add(tx)
            session.commit()
            cat_id = cat.id
            
            # Act & Assert
            with pytest.raises(ValueError, match="существует .* транзакций"):
                delete_category(session, cat_id)

            # Verify it still exists
            assert session.get(CategoryDB, cat_id) is not None

            # Cleanup: Delete transaction then category should work
            session.delete(tx)
            session.commit()
            assert delete_category(session, cat_id) is True
            assert session.get(CategoryDB, cat_id) is None
