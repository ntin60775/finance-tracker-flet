"""
Property-based тесты для прогноза баланса (Flet версия).

Тестирует:
- Property 21: Расчёт прогнозируемого баланса
- Property 22: Учёт компонентов в прогнозе
"""

from datetime import date, timedelta
from contextlib import contextmanager
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models.models import (
    Base,
    CategoryDB,
    TransactionDB,
    PlannedTransactionDB,
    RecurrenceRuleDB,
    LoanPaymentDB,
    PendingPaymentDB,
    LoanDB,
    LenderDB
)
from models.enums import (
    TransactionType,
    RecurrenceType,
    EndConditionType,
    PaymentStatus,
    PendingPaymentStatus,
    PendingPaymentPriority
)
from services.balance_forecast_service import (
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
        session.query(PendingPaymentDB).delete()
        session.query(LoanPaymentDB).delete()
        session.query(LoanDB).delete()
        session.query(LenderDB).delete()
        session.query(RecurrenceRuleDB).delete()
        session.query(PlannedTransactionDB).delete()
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()

# --- Strategies ---
dates = st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31))
amounts = st.decimals(min_value=Decimal('1.00'), max_value=Decimal('10000.00'), places=2)
transaction_types = st.sampled_from(TransactionType)

class TestBalanceForecastProperties:
    """Property-based тесты для прогноза баланса."""

    @given(
        initial_balance=st.decimals(min_value=Decimal('0.00'), max_value=Decimal('100000.00'), places=2),
        planned_txs=st.lists(
            st.fixed_dictionaries({
                'amount': amounts,
                'type': transaction_types,
                'day_offset': st.integers(min_value=1, max_value=30) # Days from today
            }),
            min_size=1,
            max_size=10
        ),
        forecast_days=st.integers(min_value=31, max_value=60), # Forecast horizon
        unique_suffix=st.uuids()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_21_forecast_calculation(self, initial_balance, planned_txs, forecast_days, unique_suffix):
        """
        Property 21: Расчёт прогнозируемого баланса.
        
        Validates: Requirements 6.1
        
        Проверяет, что прогноз корректно суммирует текущий баланс и все плановые транзакции до целевой даты.
        Используем простые однократные плановые транзакции для верификации математики.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            target_date = today + timedelta(days=forecast_days)

            # 1. Setup Initial Balance (via past transaction)
            # Create Income Category
            inc_cat = CategoryDB(name=f"Initial_{unique_suffix}", type=TransactionType.INCOME, is_system=True)
            session.add(inc_cat)
            session.flush()
            
            # Create Initial Transaction
            session.add(TransactionDB(
                amount=initial_balance,
                type=TransactionType.INCOME,
                category_id=inc_cat.id,
                transaction_date=today - timedelta(days=1),
                description="Initial Balance"
            ))

            # Create Categories for Planned Txs
            exp_cat = CategoryDB(name=f"Planned Exp_{unique_suffix}", type=TransactionType.EXPENSE, is_system=True)
            session.add(exp_cat)
            session.commit() # Commit categories
            
            # 2. Setup Planned Transactions (One-time)
            expected_forecast = initial_balance
            
            for pt_data in planned_txs:
                pt_date = today + timedelta(days=pt_data['day_offset'])
                
                # Only include if before or on target_date
                if pt_date <= target_date:
                    if pt_data['type'] == TransactionType.INCOME:
                        cat_id = inc_cat.id
                        expected_forecast += pt_data['amount']
                    else:
                        cat_id = exp_cat.id
                        expected_forecast -= pt_data['amount']

                pt = PlannedTransactionDB(
                    amount=pt_data['amount'],
                    category_id=cat_id,
                    description="Planned",
                    type=pt_data['type'],
                    start_date=pt_date,
                    is_active=True
                )
                session.add(pt)
                # Create ONE_TIME recurrence rule (implicitly handled by service if no rule, 
                # or explicit NONE type. Service usually needs a rule or handles single occurrence logic.
                # Based on models, RecurrenceRule is optional 1-to-1? No, usually 1-to-1.
                # Let's check models. PlannedTransactionDB has relationship to RecurrenceRuleDB.
                # If recurrence type is NONE, it's one time.
                
                recurrence = RecurrenceRuleDB(
                    planned_transaction=pt,
                    recurrence_type=RecurrenceType.NONE,
                    interval=1,
                    end_condition_type=EndConditionType.NEVER # Not used for NONE
                )
                session.add(recurrence)

            session.commit()

            # Act
            calculated_forecast = calculate_forecast_balance(session, target_date)

            # Assert
            assert calculated_forecast == expected_forecast


    @given(
        initial_balance=st.decimals(min_value=Decimal('10000.00'), max_value=Decimal('100000.00'), places=2),
        loan_payments=st.lists(
            st.fixed_dictionaries({
                'amount': amounts,
                'day_offset': st.integers(min_value=1, max_value=30)
            }),
            min_size=1,
            max_size=5
        ),
        pending_payments=st.lists(
            st.fixed_dictionaries({
                'amount': amounts,
                'day_offset': st.integers(min_value=1, max_value=30)
            }),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_22_component_inclusion(self, initial_balance, loan_payments, pending_payments):
        """
        Property 22: Учёт компонентов в прогнозе.
        
        Validates: Requirements 6.2
        
        Проверяет, что платежи по кредитам и отложенные платежи (с датой) 
        корректно вычитаются из прогноза.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            target_date = today + timedelta(days=40) # Cover all offsets (max 30)

            # Setup Initial Balance
            inc_cat = CategoryDB(name="Initial", type=TransactionType.INCOME, is_system=True)
            session.add(inc_cat)
            session.flush()
            
            session.add(TransactionDB(
                amount=initial_balance,
                type=TransactionType.INCOME,
                category_id=inc_cat.id,
                transaction_date=today - timedelta(days=1),
                description="Initial Balance"
            ))
            
            exp_cat = CategoryDB(name="Expense", type=TransactionType.EXPENSE, is_system=True)
            session.add(exp_cat)
            session.commit()

            expected_forecast = initial_balance

            # 1. Add Loan Payments
            # Note: Need a LoanDB parent, but maybe can insert LoanPaymentDB directly if FK is nullable or we mock?
            # Models usually require FK. Let's check models. LoanPaymentDB needs loan_id.
            # Let's create a dummy Loan.
            
            # Need Lender first?
            # Let's simplify: Assume we can insert LoanPaymentDB if we create minimal requirements.
            # Lender -> Loan -> LoanPayment.
            from models.models import LenderDB, LoanDB
            from models.enums import LenderType, LoanType, LoanStatus

            lender = LenderDB(name="Bank", lender_type=LenderType.BANK)
            session.add(lender)
            session.flush()

            loan = LoanDB(
                lender_id=lender.id,
                name="My Loan",
                amount=Decimal('100000.00'),
                interest_rate=Decimal('10.00'),
                issue_date=today,
                term_months=12,
                loan_type=LoanType.CONSUMER,
                status=LoanStatus.ACTIVE
            )
            session.add(loan)
            session.flush()

            for lp_data in loan_payments:
                pay_date = today + timedelta(days=lp_data['day_offset'])
                
                # Logic: All these are PENDING by default in strategy
                expected_forecast -= lp_data['amount']

                lp = LoanPaymentDB(
                    loan_id=loan.id,
                    scheduled_date=pay_date,
                    total_amount=lp_data['amount'], # total_amount is required
                    principal_amount=lp_data['amount'], # Simplified
                    interest_amount=Decimal('0.00'),
                    status=PaymentStatus.PENDING
                )
                session.add(lp)

            # 2. Add Pending Payments
            for pp_data in pending_payments:
                pay_date = today + timedelta(days=pp_data['day_offset'])
                
                expected_forecast -= pp_data['amount']

                pp = PendingPaymentDB(
                    amount=pp_data['amount'],
                    category_id=exp_cat.id,
                    priority=PendingPaymentPriority.MEDIUM,
                    planned_date=pay_date, # Set date so it's included
                    status=PendingPaymentStatus.ACTIVE,
                    description="Test pending payment" # Required field
                )
                session.add(pp)

            session.commit()

            # Act
            calculated_forecast = calculate_forecast_balance(session, target_date)

            # Assert
            assert calculated_forecast == expected_forecast

