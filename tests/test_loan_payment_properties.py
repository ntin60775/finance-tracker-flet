"""
Property-based тесты для платежей по кредитам (Flet версия).

Тестирует:
- Property 41: Создание транзакции при исполнении платежа
- Property 42: Автоматическое обновление статуса просроченных платежей
- Property 43: Расчёт дней просрочки
"""

from datetime import date, timedelta
from contextlib import contextmanager
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
import uuid

from models.models import (
    Base,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    TransactionDB,
    CategoryDB,
)
from models.enums import (
    LenderType,
    LoanType,
    PaymentStatus,
    TransactionType,
)
from services.lender_service import create_lender
from services.loan_service import create_loan
from services.loan_payment_service import (
    create_payment,
    execute_payment,
    update_overdue_payments,
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

# Глобальный ID системной категории для переиспользования между тестами
_system_category_id = None

def _ensure_system_category(session):
    """
    Гарантирует наличие системной категории для платежей по кредитам.

    Создаёт категорию один раз и переиспользует её во всех тестах.
    Это необходимо, потому что execute_payment() требует системную категорию.
    """
    global _system_category_id

    if _system_category_id is None:
        # Категория ещё не создана - создаём
        category = CategoryDB(
            name="Выплата кредита (основной долг)",
            type=TransactionType.EXPENSE,
            is_system=True
        )
        session.add(category)
        session.flush()
        _system_category_id = category.id

    return _system_category_id

@contextmanager
def get_test_session():
    """
    Контекстный менеджер для создания тестовой сессии БД.

    Автоматически создаёт системную категорию при первом вызове
    и очищает только тестовые данные (не системную категорию).
    """
    session = TestSessionLocal()
    try:
        # Гарантируем наличие системной категории
        _ensure_system_category(session)
        session.commit()

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем ТОЛЬКО тестовые данные (не системную категорию)
        try:
            session.query(TransactionDB).delete(synchronize_session=False)
            session.query(LoanPaymentDB).delete(synchronize_session=False)
            session.query(LoanDB).delete(synchronize_session=False)
            # НЕ удаляем CategoryDB - системная категория должна остаться
            session.query(LenderDB).delete(synchronize_session=False)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

# --- Strategies ---
# Используем UUID для гарантии уникальности имён между итерациями Hypothesis
lender_names = st.builds(lambda: f"Lender-{uuid.uuid4().hex[:8]}")
loan_names = st.builds(lambda: f"Loan-{uuid.uuid4().hex[:8]}")
loan_types = st.sampled_from(LoanType)
loan_amounts = st.decimals(min_value=Decimal('1000.00'), max_value=Decimal('100000.00'), places=2)
payment_amounts = st.decimals(min_value=Decimal('100.00'), max_value=Decimal('10000.00'), places=2)
dates_past = st.dates(min_value=date(2020, 1, 1), max_value=date.today())
dates_future = st.dates(min_value=date.today(), max_value=date(2030, 12, 31))


class TestLoanPaymentProperties:
    """Property-based тесты для платежей по кредитам."""

    @given(
        lender_name=lender_names,
        loan_name=loan_names,
        loan_type=loan_types,
        amount=loan_amounts,
        payment_amount=payment_amounts,
        scheduled_date=dates_past,
    )
    @settings(max_examples=20, deadline=None)
    def test_property_41_transaction_created_on_payment_execution(
        self,
        lender_name,
        loan_name,
        loan_type,
        amount,
        payment_amount,
        scheduled_date,
    ):
        """
        Property 41: Создание транзакции при исполнении платежа.

        Проверяет, что при исполнении платежа по кредиту автоматически
        создаётся транзакция расхода с соответствующей суммой.

        Feature: flet-finance-tracker
        Property 41: При исполнении платежа по кредиту должна автоматически
        создаваться транзакция расхода
        Validates: Requirements 11.1
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=lender_name,
                lender_type=LenderType.BANK
            )

            # Получаем ID системной категории (уже создана в get_test_session)
            category_id = _system_category_id

            # Создаём кредит
            loan = create_loan(
                session,
                lender_id=lender.id,
                name=loan_name,
                loan_type=loan_type,
                amount=amount,
                issue_date=scheduled_date - timedelta(days=30),
                interest_rate=Decimal('10.00'),
                end_date=scheduled_date + timedelta(days=365),
            )

            # Создаём платёж
            payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=scheduled_date,
                principal_amount=payment_amount * Decimal('0.9'),
                interest_amount=payment_amount * Decimal('0.1'),
                total_amount=payment_amount
            )

            # Запоминаем количество транзакций до исполнения
            transactions_before = session.query(TransactionDB).count()

            # Исполняем платёж
            executed_payment = execute_payment(
                session,
                payment_id=payment.id,
                transaction_date=date.today()
            )

            # Проверяем, что транзакция создана
            transactions_after = session.query(TransactionDB).count()
            assert transactions_after == transactions_before + 1, \
                "Должна быть создана одна транзакция"

            # Получаем созданную транзакцию
            transaction = session.query(TransactionDB).filter_by(
                description=f"Платёж по кредиту: {loan.name}"
            ).first()

            assert transaction is not None, "Транзакция должна быть найдена"
            assert transaction.type == TransactionType.EXPENSE, \
                "Транзакция должна быть расходом"
            assert transaction.amount == payment_amount, \
                "Сумма транзакции должна соответствовать сумме платежа"
            assert transaction.category_id == category_id, \
                "Транзакция должна быть привязана к категории платежей по кредитам"

            # Проверяем, что статус платежа обновлён
            assert executed_payment.status in (PaymentStatus.EXECUTED, PaymentStatus.EXECUTED_LATE), \
                "Статус платежа должен быть EXECUTED или EXECUTED_LATE"

    @given(
        lender_name=lender_names,
        loan_name=loan_names,
        loan_type=loan_types,
        amount=loan_amounts,
        payment_amount=payment_amounts,
        days_overdue=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=20, deadline=None)
    def test_property_42_automatic_overdue_status_update(
        self,
        lender_name,
        loan_name,
        loan_type,
        amount,
        payment_amount,
        days_overdue,
    ):
        """
        Property 42: Автоматическое обновление статуса просроченных платежей.

        Проверяет, что платежи со статусом PENDING автоматически меняют
        статус на OVERDUE, если текущая дата больше scheduled_date.

        Feature: flet-finance-tracker
        Property 42: Платежи со статусом PENDING должны автоматически
        менять статус на OVERDUE после даты платежа
        Validates: Requirements 11.3
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=lender_name,
                lender_type=LenderType.BANK
            )

            # Вычисляем дату платежа в прошлом
            scheduled_date = date.today() - timedelta(days=days_overdue)

            # Создаём кредит
            loan = create_loan(
                session,
                lender_id=lender.id,
                name=loan_name,
                loan_type=loan_type,
                amount=amount,
                issue_date=scheduled_date - timedelta(days=30),
                interest_rate=Decimal('10.00'),
                end_date=scheduled_date + timedelta(days=365),
            )

            # Создаём просроченный платёж (дата в прошлом)
            payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=scheduled_date,
                principal_amount=payment_amount * Decimal('0.9'),
                interest_amount=payment_amount * Decimal('0.1'),
                total_amount=payment_amount
            )

            # Проверяем начальный статус
            assert payment.status == PaymentStatus.PENDING, \
                "Начальный статус должен быть PENDING"

            # Запускаем автоматическое обновление просроченных
            updated_count = update_overdue_payments(session)

            # Проверяем, что платёж был обновлён
            assert updated_count >= 1, \
                "Хотя бы один платёж должен быть обновлён"

            # Обновляем объект payment из БД
            session.refresh(payment)

            # Проверяем, что статус изменился на OVERDUE
            assert payment.status == PaymentStatus.OVERDUE, \
                "Статус должен измениться на OVERDUE для просроченных платежей"

    @given(
        lender_name=lender_names,
        loan_name=loan_names,
        loan_type=loan_types,
        amount=loan_amounts,
        payment_amount=payment_amounts,
        scheduled_date=dates_past,
        days_late=st.integers(min_value=1, max_value=90),
    )
    @settings(max_examples=20, deadline=None)
    def test_property_43_days_overdue_calculation(
        self,
        lender_name,
        loan_name,
        loan_type,
        amount,
        payment_amount,
        scheduled_date,
        days_late,
    ):
        """
        Property 43: Расчёт дней просрочки.

        Проверяет, что при исполнении просроченного платежа корректно
        рассчитывается количество дней просрочки.

        Feature: flet-finance-tracker
        Property 43: При исполнении просроченного платежа должны корректно
        рассчитываться дни просрочки
        Validates: Requirements 11.4
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=lender_name,
                lender_type=LenderType.BANK
            )

            # Создаём кредит
            loan = create_loan(
                session,
                lender_id=lender.id,
                name=loan_name,
                loan_type=loan_type,
                amount=amount,
                issue_date=scheduled_date - timedelta(days=30),
                interest_rate=Decimal('10.00'),
                end_date=scheduled_date + timedelta(days=365),
            )

            # Создаём платёж
            payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=scheduled_date,
                principal_amount=payment_amount * Decimal('0.9'),
                interest_amount=payment_amount * Decimal('0.1'),
                total_amount=payment_amount
            )

            # Исполняем платёж с опозданием
            execution_date = scheduled_date + timedelta(days=days_late)
            executed_payment = execute_payment(
                session,
                payment_id=payment.id,
                transaction_date=execution_date
            )

            # Проверяем расчёт дней просрочки
            expected_days_overdue = (execution_date - scheduled_date).days

            assert executed_payment.overdue_days == expected_days_overdue, \
                f"Дни просрочки должны быть {expected_days_overdue}, " \
                f"получено {executed_payment.overdue_days}"

            # Проверяем статус
            if expected_days_overdue > 0:
                assert executed_payment.status == PaymentStatus.EXECUTED_LATE, \
                    "Статус должен быть EXECUTED_LATE для просроченных платежей"
            else:
                assert executed_payment.status == PaymentStatus.EXECUTED, \
                    "Статус должен быть EXECUTED для платежей вовремя"

    @given(
        lender_name=lender_names,
        loan_name=loan_names,
        loan_type=loan_types,
        amount=loan_amounts,
        payment_amount=payment_amounts,
        scheduled_date=dates_future,
    )
    @settings(max_examples=10, deadline=None)
    def test_property_41_payment_on_time(
        self,
        lender_name,
        loan_name,
        loan_type,
        amount,
        payment_amount,
        scheduled_date,
    ):
        """
        Property 41 (дополнительный): Исполнение платежа вовремя.

        Проверяет, что при исполнении платежа вовремя статус
        устанавливается в EXECUTED и days_overdue = 0.

        Feature: flet-finance-tracker
        Property 41: При исполнении платежа вовремя статус должен быть EXECUTED
        Validates: Requirements 11.1
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=lender_name,
                lender_type=LenderType.BANK
            )

            # Создаём кредит
            loan = create_loan(
                session,
                lender_id=lender.id,
                name=loan_name,
                loan_type=loan_type,
                amount=amount,
                issue_date=scheduled_date - timedelta(days=60),
                interest_rate=Decimal('10.00'),
                end_date=scheduled_date + timedelta(days=365),
            )

            # Создаём платёж
            payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=scheduled_date,
                principal_amount=payment_amount * Decimal('0.9'),
                interest_amount=payment_amount * Decimal('0.1'),
                total_amount=payment_amount
            )

            # Исполняем платёж в день платежа
            executed_payment = execute_payment(
                session,
                payment_id=payment.id,
                transaction_date=scheduled_date
            )

            # Проверяем статус
            assert executed_payment.status == PaymentStatus.EXECUTED, \
                "Статус должен быть EXECUTED для платежей вовремя"

            # Проверяем дни просрочки
            assert executed_payment.overdue_days == 0, \
                "Дни просрочки должны быть 0 для платежей вовремя"

            # Проверяем дату исполнения
            assert executed_payment.executed_date == scheduled_date, \
                "Дата исполнения должна совпадать с датой платежа"
