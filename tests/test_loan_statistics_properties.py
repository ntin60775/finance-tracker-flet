"""
Property-based тесты для статистики кредитов (Flet версия).

Тестирует:
- Property 46: Расчёт общей суммы активных кредитов
- Property 47: Расчёт среднемесячных платежей
- Property 48: Расчёт кредитной нагрузки
- Property 49: Расчёт просроченной задолженности
- Property 50: Фильтрация статистики по периоду
- Property 51: Распределение кредитов по типам
"""

from datetime import date, timedelta
from contextlib import contextmanager
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
import uuid

from finance_tracker.models.models import (
    Base,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    TransactionDB,
    CategoryDB,
)
from finance_tracker.models.enums import (
    LenderType,
    LoanType,
    LoanStatus,
    PaymentStatus,
    TransactionType,
)
from finance_tracker.services.lender_service import create_lender
from finance_tracker.services.loan_service import create_loan
from finance_tracker.services.loan_payment_service import create_payment
from finance_tracker.services.category_service import create_category
from finance_tracker.services.transaction_service import create_transaction
from finance_tracker.services.loan_statistics_service import (
    get_summary_statistics,
    get_monthly_burden_statistics,
    get_overdue_statistics,
    get_period_statistics,
)

# Глобальные переменные для управления БД
_test_engine = None
_TestSessionLocal = None

def _get_test_engine():
    """Получает или создаёт тестовый движок БД."""
    global _test_engine
    if _test_engine is None:
        _test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )

        @event.listens_for(_test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Включает поддержку foreign keys в SQLite."""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(_test_engine)

    return _test_engine

def _get_test_session_local():
    """Получает или создаёт SessionLocal для тестов."""
    global _TestSessionLocal
    if _TestSessionLocal is None:
        _TestSessionLocal = sessionmaker(bind=_get_test_engine())
    return _TestSessionLocal

test_engine = _get_test_engine()
TestSessionLocal = _get_test_session_local()

# Глобальные ID системных категорий для переиспользования между тестами
_system_categories = {}

def _ensure_system_categories(session):
    """
    Гарантирует наличие системных категорий для доходов и расходов.

    Создаёт категории один раз и переиспользует их во всех тестах.
    """
    global _system_categories

    if "income" not in _system_categories:
        # Создаём категорию доходов
        income_cat = CategoryDB(
            name="Зарплата",
            type=TransactionType.INCOME,
            is_system=True
        )
        session.add(income_cat)
        session.flush()
        _system_categories["income"] = income_cat.id

    if "expense" not in _system_categories:
        # Создаём категорию расходов
        expense_cat = CategoryDB(
            name="Выплата кредита (основной долг)",
            type=TransactionType.EXPENSE,
            is_system=True
        )
        session.add(expense_cat)
        session.flush()
        _system_categories["expense"] = expense_cat.id

    return _system_categories

@contextmanager
def get_test_session():
    """
    Контекстный менеджер для создания тестовой сессии БД.

    Автоматически создаёт системные категории при первом вызове
    и очищает только тестовые данные (не системные категории).
    """
    session = TestSessionLocal()
    try:
        # Очищаем тестовые данные перед началом теста
        try:
            session.query(TransactionDB).delete(synchronize_session=False)
            session.query(LoanPaymentDB).delete(synchronize_session=False)
            session.query(LoanDB).delete(synchronize_session=False)
            session.query(LenderDB).delete(synchronize_session=False)
            session.commit()
        except Exception:
            session.rollback()

        # Гарантируем наличие системных категорий
        _ensure_system_categories(session)
        session.commit()

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем ТОЛЬКО тестовые данные (не системные категории)
        try:
            session.query(TransactionDB).delete(synchronize_session=False)
            session.query(LoanPaymentDB).delete(synchronize_session=False)
            session.query(LoanDB).delete(synchronize_session=False)
            session.query(LenderDB).delete(synchronize_session=False)
            # НЕ удаляем CategoryDB - системные категории должны остаться
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
interest_rates = st.decimals(min_value=Decimal('0.00'), max_value=Decimal('30.00'), places=2)
dates_past = st.dates(min_value=date(2020, 1, 1), max_value=date.today())
dates_future = st.dates(min_value=date.today(), max_value=date(2030, 12, 31))


class TestLoanStatisticsProperties:
    """Property-based тесты для статистики кредитов."""

    @given(
        num_loans=st.integers(min_value=1, max_value=10),
        lender_name=lender_names,
        loan_type=loan_types,
        amount=loan_amounts,
        interest_rate=interest_rates,
    )
    @settings(max_examples=20, deadline=None)
    def test_property_46_total_active_loans_sum(
        self,
        num_loans,
        lender_name,
        loan_type,
        amount,
        interest_rate,
    ):
        """
        Property 46: Расчёт общей суммы активных кредитов.

        Проверяет, что общая сумма активных кредитов равняется сумме
        amount всех кредитов со статусом ACTIVE.

        Feature: flet-finance-tracker
        Property 46: Общая сумма активных кредитов должна равняться
        сумме amount всех кредитов со статусом ACTIVE
        Validates: Requirements 12.1
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=lender_name,
                lender_type=LenderType.BANK
            )

            # Создаём несколько активных кредитов
            total_expected = Decimal('0.00')
            for i in range(num_loans):
                loan = create_loan(
                    session,
                    lender_id=lender.id,
                    name=f"Loan-{i}",
                    loan_type=loan_type,
                    amount=amount,
                    issue_date=date.today() - timedelta(days=30),
                    interest_rate=interest_rate,
                    end_date=date.today() + timedelta(days=365),
                )
                assert loan.status == LoanStatus.ACTIVE, \
                    "Новый кредит должен быть в статусе ACTIVE"
                total_expected += amount

            # Получаем статистику
            stats = get_summary_statistics(session)

            # Проверяем количество активных кредитов
            assert stats["total_active_loans"] == num_loans, \
                f"Должно быть {num_loans} активных кредитов, " \
                f"получено {stats['total_active_loans']}"

            # Проверяем общую сумму
            assert Decimal(str(stats["total_active_amount"])) == total_expected, \
                f"Общая сумма должна быть {total_expected}, " \
                f"получено {stats['total_active_amount']}"

    def test_property_47_monthly_payments_calculation(self):
        """
        Property 47: Расчёт среднемесячных платежей.

        Проверяет, что среднемесячные платежи равняются сумме всех
        ожидаемых платежей со статусом PENDING.

        Feature: flet-finance-tracker
        Property 47: Среднемесячные платежи должны равняться сумме
        всех ожидаемых платежей со статусом PENDING
        Validates: Requirements 12.2
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name="TestLender",
                lender_type=LenderType.BANK
            )

            today = date.today()
            amount = Decimal('10000.00')
            interest_rate = Decimal('10.00')
            total_expected_payments = Decimal('0.00')

            # Создаём 2 кредита с платежами
            for i in range(2):
                loan = create_loan(
                    session,
                    lender_id=lender.id,
                    name=f"Loan-{i}",
                    loan_type=LoanType.CONSUMER,
                    amount=amount,
                    issue_date=today - timedelta(days=30),
                    interest_rate=interest_rate,
                    end_date=today + timedelta(days=365),
                )

                # Создаём один платёж
                principal = amount / 12
                interest = (amount * interest_rate / 100) / 12
                total_payment = principal + interest

                payment = create_payment(
                    session,
                    loan_id=loan.id,
                    scheduled_date=today,
                    principal_amount=principal,
                    interest_amount=interest,
                    total_amount=total_payment
                )
                total_expected_payments += total_payment

            # Получаем статистику
            stats = get_summary_statistics(session)

            # Проверяем сумму ежемесячных платежей
            actual_payments = Decimal(str(stats["monthly_payments_sum"]))
            difference = abs(actual_payments - total_expected_payments)
            assert difference < Decimal('1.00'), \
                f"Сумма платежей должна быть примерно {total_expected_payments}, " \
                f"получено {actual_payments}, разница {difference}"

    def test_property_48_credit_burden_calculation(self):
        """
        Property 48: Расчёт кредитной нагрузки.

        Проверяет, что кредитная нагрузка = (среднемесячные платежи / 
        среднемесячный доход) * 100%.

        Feature: flet-finance-tracker
        Property 48: Кредитная нагрузка должна равняться
        (среднемесячные платежи / среднемесячный доход) * 100%
        Validates: Requirements 12.3
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=f"TestLender-{uuid.uuid4().hex[:8]}",
                lender_type=LenderType.BANK
            )

            today = date.today()
            income_amount = Decimal('50000.00')
            income_category_id = _system_categories["income"]

            # Создаём доходные транзакции за последние 6 месяцев
            from finance_tracker.models.models import TransactionCreate
            for month_offset in range(6):
                transaction_date = today - timedelta(days=30*month_offset)
                transaction_data = TransactionCreate(
                    amount=income_amount,
                    type=TransactionType.INCOME,
                    category_id=income_category_id,
                    transaction_date=transaction_date,
                    description="Зарплата"
                )
                create_transaction(session, transaction_data)

            # Создаём кредит с платежом
            amount = Decimal('10000.00')
            interest_rate = Decimal('10.00')
            loan = create_loan(
                session,
                lender_id=lender.id,
                name="TestLoan",
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=today - timedelta(days=30),
                interest_rate=interest_rate,
                end_date=today + timedelta(days=365),
            )

            # Создаём платёж
            principal = amount / 12
            interest = (amount * interest_rate / 100) / 12
            total_payment = principal + interest

            create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=today,
                principal_amount=principal,
                interest_amount=interest,
                total_amount=total_payment
            )

            # Получаем статистику
            burden_stats = get_monthly_burden_statistics(session)

            # Проверяем расчёт кредитной нагрузки
            expected_monthly_income = income_amount  # За 6 месяцев / 6
            monthly_payments = Decimal(str(burden_stats["monthly_payments"]))
            expected_burden = (monthly_payments / expected_monthly_income * 100) if expected_monthly_income > 0 else 0

            actual_burden = Decimal(str(burden_stats["burden_percent"]))
            difference = abs(actual_burden - expected_burden)

            # Допускаем погрешность из-за округления
            assert difference < Decimal('1.00'), \
                f"Кредитная нагрузка должна быть примерно {expected_burden}%, " \
                f"получено {actual_burden}%, разница {difference}"

    def test_property_49_overdue_debt_calculation(self):
        """
        Property 49: Расчёт просроченной задолженности.

        Проверяет, что просроченная задолженность равняется сумме
        total_amount всех платежей со статусом OVERDUE.

        Feature: flet-finance-tracker
        Property 49: Просроченная задолженность должна равняться
        сумме total_amount всех платежей со статусом OVERDUE
        Validates: Requirements 12.4
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=f"TestLender-{uuid.uuid4().hex[:8]}",
                lender_type=LenderType.BANK
            )

            today = date.today()
            amount = Decimal('10000.00')
            interest_rate = Decimal('10.00')
            total_expected_overdue = Decimal('0.00')

            # Создаём кредит с просроченными платежами
            loan = create_loan(
                session,
                lender_id=lender.id,
                name="TestLoan",
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=today - timedelta(days=90),
                interest_rate=interest_rate,
                end_date=today + timedelta(days=365),
            )

            # Создаём 3 просроченных платежа
            for j in range(3):
                payment_date = today - timedelta(days=30 + j*10)
                principal = amount / 12
                interest = (amount * interest_rate / 100) / 12
                total_payment = principal + interest

                payment = create_payment(
                    session,
                    loan_id=loan.id,
                    scheduled_date=payment_date,
                    principal_amount=principal,
                    interest_amount=interest,
                    total_amount=total_payment
                )
                # Устанавливаем статус OVERDUE вручную
                payment.status = PaymentStatus.OVERDUE
                total_expected_overdue += total_payment

            session.commit()

            # Получаем статистику
            overdue_stats = get_overdue_statistics(session)

            # Проверяем количество просроченных платежей
            assert overdue_stats["total_overdue_payments"] == 3, \
                f"Должно быть 3 просроченных платежа, " \
                f"получено {overdue_stats['total_overdue_payments']}"

            # Проверяем общую сумму просрочки
            actual_overdue = Decimal(str(overdue_stats["total_overdue_amount"]))
            difference = abs(actual_overdue - total_expected_overdue)
            assert difference < Decimal('1.00'), \
                f"Сумма просрочки должна быть примерно {total_expected_overdue}, " \
                f"получено {actual_overdue}, разница {difference}"

    def test_property_50_period_statistics_filtering(self):
        """
        Property 50: Фильтрация статистики по периоду.

        Проверяет, что статистика учитывает только кредиты и платежи
        в указанном диапазоне дат.

        Feature: flet-finance-tracker
        Property 50: Статистика должна учитывать только платежи
        в указанном диапазоне дат
        Validates: Requirements 12.5
        """
        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=f"TestLender-{uuid.uuid4().hex[:8]}",
                lender_type=LenderType.BANK
            )

            today = date.today()
            period_start = today.replace(day=1)
            period_end = today
            amount = Decimal('10000.00')
            interest_rate = Decimal('10.00')

            # Создаём кредит
            loan = create_loan(
                session,
                lender_id=lender.id,
                name="TestLoan",
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=period_start - timedelta(days=30),
                interest_rate=interest_rate,
                end_date=period_end + timedelta(days=365),
            )

            # Создаём платежи в периоде
            principal = amount / 12
            interest = (amount * interest_rate / 100) / 12
            total_payment = principal + interest

            # Сначала создаём фиктивную транзакцию для foreign key
            from finance_tracker.models.models import TransactionCreate
            expense_category_id = _system_categories["expense"]
            transaction_data = TransactionCreate(
                amount=total_payment,
                type=TransactionType.EXPENSE,
                category_id=expense_category_id,
                transaction_date=period_start,
                description="Платёж по кредиту"
            )
            transaction = create_transaction(session, transaction_data)
            session.flush()

            payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=period_start,
                principal_amount=principal,
                interest_amount=interest,
                total_amount=total_payment
            )
            # Отмечаем как исполненный
            payment.status = PaymentStatus.EXECUTED
            payment.actual_transaction_id = transaction.id

            # Создаём фиктивную транзакцию для второго платежа
            transaction_data2 = TransactionCreate(
                amount=total_payment,
                type=TransactionType.EXPENSE,
                category_id=expense_category_id,
                transaction_date=period_end + timedelta(days=10),
                description="Платёж по кредиту"
            )
            transaction2 = create_transaction(session, transaction_data2)
            session.flush()

            # Создаём платёж ВНЕ периода
            outside_payment = create_payment(
                session,
                loan_id=loan.id,
                scheduled_date=period_end + timedelta(days=10),
                principal_amount=principal,
                interest_amount=interest,
                total_amount=total_payment
            )
            outside_payment.status = PaymentStatus.EXECUTED
            outside_payment.actual_transaction_id = transaction2.id

            session.commit()

            # Получаем статистику за период
            period_stats = get_period_statistics(session, period_start, period_end)

            # Проверяем, что учтён только платёж в периоде
            assert period_stats["total_payments_count"] == 1, \
                f"Должно быть 1 платёж в периоде, " \
                f"получено {period_stats['total_payments_count']}"

            # Проверяем, что платежи вне периода не учтены
            period_stats_extended = get_period_statistics(
                session,
                period_start,
                period_end + timedelta(days=20)
            )
            assert period_stats_extended["total_payments_count"] == 2, \
                f"При расширении периода должно быть 2 платежа, " \
                f"получено {period_stats_extended['total_payments_count']}"

    def test_property_51_loan_distribution_by_type(self):
        """
        Property 51: Распределение кредитов по типам.

        Проверяет, что распределение показывает количество и сумму
        кредитов для каждого типа.

        Feature: flet-finance-tracker
        Property 51: Распределение должно показывать количество и сумму
        кредитов для каждого типа
        Validates: Requirements 12.6
        """
        # Явно очищаем БД перед тестом (в правильном порядке)
        cleanup_session = TestSessionLocal()
        try:
            cleanup_session.query(LoanPaymentDB).delete(synchronize_session=False)
            cleanup_session.query(TransactionDB).delete(synchronize_session=False)
            cleanup_session.query(LoanDB).delete(synchronize_session=False)
            cleanup_session.query(LenderDB).delete(synchronize_session=False)
            cleanup_session.commit()
        finally:
            cleanup_session.close()

        with get_test_session() as session:
            # Создаём займодателя
            lender = create_lender(
                session,
                name=f"TestLender-{uuid.uuid4().hex[:8]}",
                lender_type=LenderType.BANK
            )

            today = date.today()
            amount = Decimal('10000.00')
            interest_rate = Decimal('10.00')
            expected_distribution = {}

            # Создаём кредиты разных типов (3 типа)
            loan_types_list = [LoanType.CONSUMER, LoanType.MORTGAGE, LoanType.MICROLOAN]
            for i, loan_type in enumerate(loan_types_list):
                loan = create_loan(
                    session,
                    lender_id=lender.id,
                    name=f"Loan-{loan_type.value}",
                    loan_type=loan_type,
                    amount=amount,
                    issue_date=today - timedelta(days=30),
                    interest_rate=interest_rate,
                    end_date=today + timedelta(days=365),
                )

                # Отслеживаем ожидаемое распределение
                if loan_type not in expected_distribution:
                    expected_distribution[loan_type] = {
                        "count": 0,
                        "total_amount": Decimal('0.00')
                    }
                expected_distribution[loan_type]["count"] += 1
                expected_distribution[loan_type]["total_amount"] += amount

            # Получаем статистику
            stats = get_summary_statistics(session)

            # Проверяем, что все типы кредитов учтены
            assert stats["total_active_loans"] == len(loan_types_list), \
                f"Должно быть {len(loan_types_list)} активных кредитов, " \
                f"получено {stats['total_active_loans']}"

            # Проверяем общую сумму
            total_expected = sum(
                info["total_amount"]
                for info in expected_distribution.values()
            )
            actual_total = Decimal(str(stats["total_active_amount"]))
            assert actual_total == total_expected, \
                f"Общая сумма должна быть {total_expected}, " \
                f"получено {actual_total}"
