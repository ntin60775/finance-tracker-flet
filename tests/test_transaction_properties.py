"""
Property-based тесты для TransactionDB (Flet версия).

Тестирует:
- Property 6: Сохранение транзакции
- Property 7: Обновление транзакции
- Property 8: Удаление транзакции
"""

from datetime import date
from contextlib import contextmanager
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    TransactionDB,
    CategoryDB,
    TransactionType,
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

# Стратегии для генерации тестовых данных
dates_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31)
)

amounts_strategy = st.decimals(
    min_value=Decimal('0.01'),
    max_value=Decimal('1000000.00'),
    places=2
)

text_strategy = st.text(min_size=1, max_size=100)


class TestTransactionProperties:
    """Property-based тесты для CRUD операций транзакций."""

    @given(
        transaction_date=dates_strategy,
        amount=amounts_strategy,
        description=text_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_property_6_transaction_persistence(self, transaction_date, amount, description):
        """
        Property 6: Сохранение транзакции.
        
        Validates: Requirements 3.4, 3.5
        
        Для любого набора валидных данных, транзакция должна успешно сохраняться в БД
        и извлекаться с теми же значениями полей.
        """
        with get_test_session() as session:
            # Arrange
            category = CategoryDB(
                name=f"Cat_{description[:10]}",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Act
            transaction = TransactionDB(
                amount=amount,
                type=TransactionType.INCOME,
                category_id=category.id,
                transaction_date=transaction_date,
                description=description
            )
            session.add(transaction)
            session.commit()
            
            # Assert
            saved_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
            assert saved_transaction is not None
            assert saved_transaction.amount == amount
            assert saved_transaction.transaction_date == transaction_date
            assert saved_transaction.description == description
            assert saved_transaction.category_id == category.id

    @given(
        initial_amount=amounts_strategy,
        new_amount=amounts_strategy,
        initial_desc=text_strategy,
        new_desc=text_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_property_7_transaction_update(self, initial_amount, new_amount, initial_desc, new_desc):
        """
        Property 7: Обновление транзакции.
        
        Validates: Requirements 3.6
        
        При обновлении полей транзакции, изменения должны сохраняться в БД,
        а неизмененные поля должны оставаться прежними.
        """
        with get_test_session() as session:
            # Arrange
            category = CategoryDB(name="Update Category", type=TransactionType.EXPENSE)
            session.add(category)
            session.commit()
            
            transaction = TransactionDB(
                amount=initial_amount,
                type=TransactionType.EXPENSE,
                category_id=category.id,
                transaction_date=date.today(),
                description=initial_desc
            )
            session.add(transaction)
            session.commit()
            
            # Act
            transaction.amount = new_amount
            transaction.description = new_desc
            session.commit()
            
            # Assert
            updated_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
            assert updated_transaction.amount == new_amount
            assert updated_transaction.description == new_desc
            # Проверка, что другие поля не изменились
            assert updated_transaction.category_id == category.id
            assert updated_transaction.type == TransactionType.EXPENSE

    @given(amount=amounts_strategy)
    @settings(max_examples=50, deadline=None)
    def test_property_8_transaction_deletion(self, amount):
        """
        Property 8: Удаление транзакции.
        
        Validates: Requirements 3.6
        
        После удаления транзакции она не должна быть доступна в БД.
        """
        with get_test_session() as session:
            # Arrange
            category = CategoryDB(name="Delete Category", type=TransactionType.INCOME)
            session.add(category)
            session.commit()
            
            transaction = TransactionDB(
                amount=amount,
                type=TransactionType.INCOME,
                category_id=category.id,
                transaction_date=date.today(),
                description="To be deleted"
            )
            session.add(transaction)
            session.commit()
            tx_id = transaction.id
            
            # Act
            session.delete(transaction)
            session.commit()
            
            # Assert
            deleted_transaction = session.query(TransactionDB).filter_by(id=tx_id).first()
            assert deleted_transaction is None
