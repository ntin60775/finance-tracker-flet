"""
Property-based тесты для визуализации прогноза и кассовых разрывов.

Тестирует:
- Property 23: Визуализация кассового разрыва (логика обнаружения)
- Property 24: Отображение баланса и прогноза (логика расчёта)
"""

from datetime import date, timedelta
from contextlib import contextmanager
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models.models import (
    Base,
    CategoryDB,
    TransactionDB,
    PlannedTransactionDB,
    RecurrenceRuleDB,
)
from finance_tracker.models.enums import (
    TransactionType,
)
from finance_tracker.services.balance_forecast_service import (
    detect_cash_gaps,
    calculate_forecast_balance
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
        session.query(RecurrenceRuleDB).delete()
        session.query(PlannedTransactionDB).delete()
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()

class TestForecastVisualizationProperties:
    """
    Тесты для логики, лежащей в основе визуализации прогноза.
    Проверяет корректность данных, передаваемых в UI компоненты.
    """

    @given(
        initial_balance=st.decimals(min_value=Decimal('1000.00'), max_value=Decimal('5000.00'), places=2),
        expense_amount=st.decimals(min_value=Decimal('6000.00'), max_value=Decimal('10000.00'), places=2), # Больше баланса -> разрыв
        days_offset=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_23_cash_gap_detection(self, initial_balance, expense_amount, days_offset):
        """
        Property 23: Визуализация кассового разрыва.
        
        Validates: Requirements 6.3
        
        Если плановый расход превышает текущий баланс, система должна обнаружить кассовый разрыв
        на дату расхода. Это состояние используется UI для окрашивания дня в календаре.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            gap_date = today + timedelta(days=days_offset)
            
            # 1. Initial Balance
            inc_cat = CategoryDB(name="Income", type=TransactionType.INCOME, is_system=True)
            session.add(inc_cat)
            session.flush()
            
            session.add(TransactionDB(
                amount=initial_balance,
                type=TransactionType.INCOME,
                category_id=inc_cat.id,
                transaction_date=today,
                description="Init"
            ))
            
            # 2. Planned Expense causing gap
            exp_cat = CategoryDB(name="Expense", type=TransactionType.EXPENSE, is_system=True)
            session.add(exp_cat)
            session.commit()
            
            planned_tx = PlannedTransactionDB(
                amount=expense_amount,
                category_id=exp_cat.id,
                type=TransactionType.EXPENSE,
                start_date=gap_date,
                is_active=True,
                description="Big Expense"
            )
            session.add(planned_tx)
            session.commit()

            # Act
            # Проверяем диапазон вокруг даты разрыва
            gaps = detect_cash_gaps(session, today, gap_date + timedelta(days=1))

            # Assert
            # Разрыв должен быть обнаружен именно на дату расхода
            assert gap_date in gaps
            
            # Проверяем, что до расхода разрыва нет (если баланс > 0)
            if initial_balance >= 0:
                days_before = [today + timedelta(days=i) for i in range(days_offset)]
                for day in days_before:
                    assert day not in gaps

    @given(
        balance=st.decimals(min_value=Decimal('-1000.00'), max_value=Decimal('1000.00'), places=2),
        has_transactions=st.booleans()
    )
    @settings(max_examples=30, deadline=None)
    def test_property_24_balance_display_logic(self, balance, has_transactions):
        """
        Property 24: Отображение баланса и прогноза.
        
        Validates: Requirements 6.4
        
        Проверяет логику, определяющую значение прогноза для отображения в TransactionsPanel.
        UI использует это значение для показа суммы и выбора цвета (красный/обычный).
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            
            # Setup balance via transaction
            cat = CategoryDB(name="Cat", type=TransactionType.INCOME if balance >= 0 else TransactionType.EXPENSE, is_system=True)
            session.add(cat)
            session.flush()
            
            amount = abs(balance)
            if amount > 0:
                 session.add(TransactionDB(
                    amount=amount,
                    type=TransactionType.INCOME if balance >= 0 else TransactionType.EXPENSE,
                    category_id=cat.id,
                    transaction_date=today,
                    description="Balance setter"
                ))
            session.commit()

            # Act
            forecast = calculate_forecast_balance(session, today)

            # Assert
            # Прогноз на сегодня должен совпадать с фактическим балансом
            assert forecast == balance
            
            # Логика UI (эмуляция):
            is_cash_gap = forecast < Decimal('0')
            expected_gap = balance < Decimal('0')
            
            assert is_cash_gap == expected_gap
