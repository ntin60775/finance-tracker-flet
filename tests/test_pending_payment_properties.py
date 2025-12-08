"""
Property-based тесты для отложенных платежей.

Использует Hypothesis для генерации тестовых данных и проверки инвариантов.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import date, timedelta
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models import (
    Base,
    PendingPaymentDB,
    PendingPaymentCreate,
    PendingPaymentExecute,
    PendingPaymentCancel,
    TransactionType,
    CategoryDB,
    TransactionDB
)
from finance_tracker.models.enums import PendingPaymentPriority, PendingPaymentStatus
from finance_tracker.services.pending_payment_service import (
    create_pending_payment,
    get_all_pending_payments,
    execute_pending_payment,
    cancel_pending_payment,
    get_pending_payments_statistics
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
        # Порядок важен из-за foreign keys: сначала зависимые, потом родительские
        session.query(PendingPaymentDB).delete()
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()


# Стратегии генерации данных
amounts = st.decimals(min_value=Decimal('1.00'), max_value=Decimal('1000000.00'), places=2)
descriptions = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
priorities = st.sampled_from(list(PendingPaymentPriority))
dates = st.dates(min_value=date.today(), max_value=date.today() + timedelta(days=365))


class TestPendingPaymentProperties:
    """
    Property-based тесты для отложенных платежей.

    Проверяют инварианты системы согласно Requirements 8.1-8.7.
    """

    # Feature: flet-finance-tracker, Property 30: Валидация категории отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_30_category_validation(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        Property 30: Валидация категории отложенного платежа.

        Инвариант: Категория отложенного платежа ДОЛЖНА быть типа EXPENSE.
        Попытка создать платёж с категорией типа INCOME ДОЛЖНА приводить к ValueError.
        """
        with get_test_session() as session:
            # Создаём тестовые категории
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            income_category = CategoryDB(
                name=f"Income_{description[:10]}",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(expense_category)
            session.add(income_category)
            session.commit()

            # Успешное создание с EXPENSE категорией
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            payment = create_pending_payment(session, payment_data)

            assert payment.amount == amount
            assert payment.category_id == expense_category.id
            assert payment.status == PendingPaymentStatus.ACTIVE

            # Попытка создать платёж с INCOME категорией должна вызвать ошибку
            invalid_payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=income_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            with pytest.raises(ValueError, match="EXPENSE"):
                create_pending_payment(session, invalid_payment_data)

    # Feature: flet-finance-tracker, Property 31: Исполнение отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        executed_amount=amounts
    )
    @settings(max_examples=100, deadline=None)
    def test_property_31_execute_payment(
        self,
        amount,
        description,
        executed_amount
    ):
        """
        Property 31: Исполнение отложенного платежа.

        Инвариант: При исполнении платежа:
        - Создаётся транзакция типа EXPENSE
        - Статус меняется на EXECUTED
        - Сохраняется executed_amount и executed_date
        - Повторное исполнение того же платежа невозможно
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём платёж
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=PendingPaymentPriority.MEDIUM
            )

            payment = create_pending_payment(session, payment_data)
            payment_id = payment.id

            # Исполняем платёж
            execute_data = PendingPaymentExecute(
                executed_date=date.today(),
                executed_amount=executed_amount
            )

            transaction, updated_payment = execute_pending_payment(
                session,
                payment_id,
                execute_data
            )

            # Проверяем транзакцию
            assert transaction.type == TransactionType.EXPENSE
            assert transaction.amount == executed_amount
            assert transaction.category_id == expense_category.id

            # Проверяем платёж
            assert updated_payment.status == PendingPaymentStatus.EXECUTED
            assert updated_payment.executed_amount == executed_amount
            assert updated_payment.executed_date == date.today()
            assert updated_payment.actual_transaction_id == transaction.id

            # Попытка повторного исполнения должна вызвать ошибку
            with pytest.raises(ValueError, match="активные"):
                execute_pending_payment(session, payment_id, execute_data)

    # Feature: flet-finance-tracker, Property 32: Отмена отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        cancel_reason=st.one_of(st.none(), st.text(min_size=1, max_size=200))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_32_cancel_payment(
        self,
        amount,
        description,
        cancel_reason
    ):
        """
        Property 32: Отмена отложенного платежа.

        Инвариант: При отмене платежа:
        - Статус меняется на CANCELLED
        - Сохраняется cancelled_date и cancel_reason
        - Транзакция НЕ создаётся
        - Повторная отмена невозможна
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём платёж
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=PendingPaymentPriority.MEDIUM
            )

            payment = create_pending_payment(session, payment_data)
            payment_id = payment.id

            # Отменяем платёж
            cancel_data = PendingPaymentCancel(cancel_reason=cancel_reason)
            updated_payment = cancel_pending_payment(session, payment_id, cancel_data)

            # Проверяем платёж
            assert updated_payment.status == PendingPaymentStatus.CANCELLED
            assert updated_payment.cancelled_date == date.today()
            assert updated_payment.cancel_reason == cancel_reason
            assert updated_payment.actual_transaction_id is None  # Транзакция не создана

            # Попытка повторной отмены должна вызвать ошибку
            with pytest.raises(ValueError, match="активные"):
                cancel_pending_payment(session, payment_id, cancel_data)

    # Feature: flet-finance-tracker, Property 33: Сортировка отложенных платежей
    @given(
        payments_count=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_33_payment_sorting(
        self,
        payments_count
    ):
        """
        Property 33: Сортировка отложенных платежей.

        Инвариант: Платежи сортируются:
        1. По приоритету (CRITICAL > HIGH > MEDIUM > LOW)
        2. При равном приоритете - по плановой дате (раньше первыми)
        3. Платежи без даты - в конце
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name="Expense_Sort",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём несколько платежей с разными приоритетами
            priorities_list = [
                PendingPaymentPriority.LOW,
                PendingPaymentPriority.MEDIUM,
                PendingPaymentPriority.HIGH,
                PendingPaymentPriority.CRITICAL
            ]

            created_payments = []
            for i in range(payments_count):
                priority = priorities_list[i % len(priorities_list)]
                planned_date = date.today() + timedelta(days=i) if i % 2 == 0 else None

                payment_data = PendingPaymentCreate(
                    amount=100.0 + i,
                    category_id=expense_category.id,
                    description=f"Payment {i}",
                    priority=priority,
                    planned_date=planned_date
                )

                payment = create_pending_payment(session, payment_data)
                created_payments.append(payment)

            # Получаем отсортированный список
            sorted_payments = get_all_pending_payments(session)

            # Проверяем сортировку по приоритету
            priority_order = {
                PendingPaymentPriority.CRITICAL: 0,
                PendingPaymentPriority.HIGH: 1,
                PendingPaymentPriority.MEDIUM: 2,
                PendingPaymentPriority.LOW: 3,
            }

            for i in range(len(sorted_payments) - 1):
                current = sorted_payments[i]
                next_payment = sorted_payments[i + 1]

                current_priority = priority_order[current.priority]
                next_priority = priority_order[next_payment.priority]

                # Приоритет текущего должен быть <= следующего
                assert current_priority <= next_priority

    # Feature: flet-finance-tracker, Property 34: Статистика отложенных платежей
    @given(
        payments_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_34_payment_statistics(
        self,
        payments_count
    ):
        """
        Property 34: Статистика отложенных платежей.

        Инвариант: Статистика корректно отражает:
        - Количество активных платежей
        - Общую сумму активных платежей
        - Распределение по приоритетам
        - Платежи с датой / без даты
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name="Expense_Stats",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём несколько платежей
            total_amount = Decimal('0.0')
            with_date_count = 0
            without_date_count = 0

            for i in range(payments_count):
                amount = Decimal('100.0') + (i * Decimal('10'))
                total_amount += amount

                has_date = i % 2 == 0
                if has_date:
                    with_date_count += 1
                else:
                    without_date_count += 1

                payment_data = PendingPaymentCreate(
                    amount=amount,
                    category_id=expense_category.id,
                    description=f"Payment {i}",
                    priority=PendingPaymentPriority.MEDIUM,
                    planned_date=date.today() + timedelta(days=i) if has_date else None
                )

                create_pending_payment(session, payment_data)

            # Получаем статистику
            stats = get_pending_payments_statistics(session)

            # Проверяем корректность
            assert stats["total_active"] == payments_count
            assert stats["total_amount"] == total_amount
            assert stats["with_planned_date"] == with_date_count
            assert stats["without_planned_date"] == without_date_count

            # Проверяем статистику по приоритетам
            assert "by_priority" in stats
            assert stats["by_priority"]["medium"]["count"] == payments_count
            assert stats["by_priority"]["medium"]["total_amount"] == total_amount
