"""
Property-based тесты для передачи долга между кредиторами.

Тестирует:
- Property 1: Консистентность текущего держателя после передачи
- Property 2: Неизменность исходного кредитора
- Property 3: Корректность вычисления разницы сумм
- Property 4: Валидация источника передачи
- Property 5: Хронологический порядок истории передач
- Property 8: Запрет передачи погашенного кредита
- Property 9: Запрет передачи самому себе
- Property 10: Запрет отрицательной или нулевой суммы
"""

from datetime import date
from contextlib import contextmanager
import uuid
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck, Verbosity, Phase
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models.models import (
    Base,
    LenderDB,
    LoanDB,
    DebtTransferDB,
    LoanPaymentDB,
)
from finance_tracker.models.enums import (
    LenderType,
    LoanType,
    LoanStatus,
    PaymentStatus
)
from finance_tracker.services.lender_service import create_lender
from finance_tracker.services.loan_service import create_loan
from finance_tracker.services.debt_transfer_service import (
    validate_transfer,
    create_debt_transfer,
    get_remaining_debt,
    get_transfer_history,
    update_payments_on_transfer
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
    """Контекстный менеджер для создания тестовой сессии БД с очисткой."""
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем данные после использования
        session.query(LoanDB).delete()
        session.query(LenderDB).delete()
        session.commit()
        session.close()

# --- Strategies ---
lender_names = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=['Cc', 'Cs'])).filter(lambda x: len(x.strip()) > 0)
loan_names = st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=['Cc', 'Cs'])).filter(lambda x: len(x.strip()) > 0)
loan_amounts = st.decimals(min_value=Decimal('1000.00'), max_value=Decimal('10000000.00'), places=2)
transfer_amounts = st.decimals(min_value=Decimal('0.01'), max_value=Decimal('10000000.00'), places=2)
invalid_transfer_amounts = st.one_of(
    st.just(Decimal('0')),
    st.decimals(min_value=Decimal('-10000000.00'), max_value=Decimal('-0.01'), places=2)
)
dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))


class TestDebtTransferValidationProperties:
    """Property-based тесты для валидации передачи долга."""

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_4_validate_transfer_source(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date
    ):
        """
        Property 4: Валидация источника передачи.

        Feature: debt-transfer, Property 4: Для любой попытки создания передачи,
        если from_lender_id не равен loan.effective_holder_id, передача должна
        быть отклонена с ошибкой

        Validates: Requirements 2.5

        Проверяет, что передача возможна только от текущего держателя долга.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act & Assert: валидация передачи от текущего держателя должна пройти
            is_valid, error = validate_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_amount=transfer_amount
            )

            # Передача от текущего держателя (original_lender) должна быть валидна
            assert is_valid is True, f"Ошибка валидации: {error}"
            assert error is None
            assert loan.effective_holder_id == original_lender_id

    @given(
        lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_8_reject_paid_off_loan_transfer(
        self,
        lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date
    ):
        """
        Property 8: Запрет передачи погашенного кредита.

        Feature: debt-transfer, Property 8: Для любого кредита со статусом PAID_OFF,
        попытка создания передачи должна быть отклонена с соответствующей ошибкой

        Validates: Requirements 6.1

        Проверяет, что нельзя передать погашенный кредит.
        """
        # Убедимся, что имена разные
        assume(lender_name != new_lender_name)
        assume(lender_name != loan_name)
        assume(new_lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём кредитора
            lender = create_lender(
                session=session,
                name=lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            lender_id = lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Arrange: помечаем кредит как погашенный
            loan.status = LoanStatus.PAID_OFF
            session.flush()

            # Act: пытаемся передать погашенный кредит
            is_valid, error = validate_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_amount=transfer_amount
            )

            # Assert: передача должна быть отклонена
            assert is_valid is False
            assert error is not None
            assert "погашенный" in error.lower() or "paid_off" in error.lower()

    @given(
        lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_9_reject_transfer_to_self(
        self,
        lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date
    ):
        """
        Property 9: Запрет передачи самому себе.

        Feature: debt-transfer, Property 9: Для любой попытки передачи,
        где to_lender_id равен текущему держателю (loan.effective_holder_id),
        передача должна быть отклонена

        Validates: Requirements 6.2

        Проверяет, что нельзя передать долг тому же кредитору.
        """
        # Убедимся, что имена разные
        assume(lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём кредитора
            lender = create_lender(
                session=session,
                name=lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            lender_id = lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: пытаемся передать долг тому же кредитору
            is_valid, error = validate_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=lender_id,  # Тот же кредитор!
                transfer_amount=transfer_amount
            )

            # Assert: передача должна быть отклонена
            assert is_valid is False
            assert error is not None
            assert "тому же" in error.lower() or "same" in error.lower()

    @given(
        lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        invalid_amount=invalid_transfer_amounts,
        issue_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_10_reject_invalid_transfer_amount(
        self,
        lender_name,
        new_lender_name,
        loan_name,
        amount,
        invalid_amount,
        issue_date
    ):
        """
        Property 10: Запрет отрицательной или нулевой суммы передачи.

        Feature: debt-transfer, Property 10: Для любой попытки передачи
        с transfer_amount <= 0, передача должна быть отклонена с ошибкой валидации

        Validates: Requirements 6.3

        Проверяет, что сумма передачи должна быть положительной.
        """
        # Убедимся, что имена разные
        assume(lender_name != new_lender_name)
        assume(lender_name != loan_name)
        assume(new_lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём кредитора
            lender = create_lender(
                session=session,
                name=lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            lender_id = lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: пытаемся передать с невалидной суммой
            is_valid, error = validate_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_amount=invalid_amount
            )

            # Assert: передача должна быть отклонена
            assert is_valid is False
            assert error is not None
            assert "положительн" in error.lower() or "positive" in error.lower()


class TestDebtTransferCreationProperties:
    """Property-based тесты для создания передачи долга."""

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates,
        transfer_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_1_current_holder_consistency_after_transfer(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date,
        transfer_date
    ):
        """
        Property 1: Консистентность текущего держателя после передачи.

        Feature: debt-transfer, Property 1: Для любого кредита и валидной передачи долга,
        после создания передачи loan.current_holder_id должен равняться transfer.to_lender_id,
        и все новые платежи должны быть привязаны к этому держателю

        Validates: Requirements 2.2, 4.3

        Проверяет, что после передачи долга текущий держатель обновляется корректно.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)
        # Убедимся, что transfer_amount положительная
        assume(transfer_amount > Decimal('0'))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: создаём передачу долга
            transfer = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_date=transfer_date,
                transfer_amount=transfer_amount
            )

            # Assert: проверяем консистентность текущего держателя
            # После передачи loan.current_holder_id должен равняться to_lender_id
            assert loan.current_holder_id == new_lender_id
            assert transfer.to_lender_id == new_lender_id
            assert loan.effective_holder_id == new_lender_id
        finally:
            session.close()
            test_engine.dispose()

    @given(
        original_lender_name=lender_names,
        new_lender_name_1=lender_names,
        new_lender_name_2=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount_1=transfer_amounts,
        transfer_amount_2=transfer_amounts,
        issue_date=dates,
        transfer_date_1=dates,
        transfer_date_2=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_2_original_lender_immutability(
        self,
        original_lender_name,
        new_lender_name_1,
        new_lender_name_2,
        loan_name,
        amount,
        transfer_amount_1,
        transfer_amount_2,
        issue_date,
        transfer_date_1,
        transfer_date_2
    ):
        """
        Property 2: Неизменность исходного кредитора.

        Feature: debt-transfer, Property 2: Для любого кредита с историей передач,
        loan.original_lender_id должен равняться loan.lender_id (исходному кредитору)
        и не должен меняться при последующих передачах

        Validates: Requirements 2.3

        Проверяет, что исходный кредитор не меняется при множественных передачах.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name_1)
        assume(original_lender_name != new_lender_name_2)
        assume(new_lender_name_1 != new_lender_name_2)
        assume(original_lender_name != loan_name)
        # Убедимся, что суммы положительные
        assume(transfer_amount_1 > Decimal('0'))
        assume(transfer_amount_2 > Decimal('0'))
        # Убедимся, что даты разные
        assume(transfer_date_1 != transfer_date_2)

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём первого нового кредитора
            new_lender_1 = create_lender(
                session=session,
                name=new_lender_name_1,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_1_id = new_lender_1.id

            # Arrange: создаём второго нового кредитора
            new_lender_2 = create_lender(
                session=session,
                name=new_lender_name_2,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_2_id = new_lender_2.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: первая передача долга
            transfer_1 = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_1_id,
                transfer_date=transfer_date_1,
                transfer_amount=transfer_amount_1
            )

            # Assert: после первой передачи original_lender_id должен быть установлен
            assert loan.original_lender_id == original_lender_id
            assert loan.original_lender_id == loan.lender_id

            # Act: вторая передача долга (от первого коллектора ко второму)
            transfer_2 = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_2_id,
                transfer_date=transfer_date_2,
                transfer_amount=transfer_amount_2
            )

            # Assert: после второй передачи original_lender_id не должен измениться
            assert loan.original_lender_id == original_lender_id
            assert loan.original_lender_id == loan.lender_id
            # Текущий держатель должен измениться на второго коллектора
            assert loan.current_holder_id == new_lender_2_id
        finally:
            session.close()
            test_engine.dispose()

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates,
        transfer_date=dates
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_3_amount_difference_calculation(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date,
        transfer_date
    ):
        """
        Property 3: Корректность вычисления разницы сумм.

        Feature: debt-transfer, Property 3: Для любой передачи долга,
        transfer.amount_difference должен равняться
        transfer.transfer_amount - transfer.previous_amount

        Validates: Requirements 2.4, 8.5

        Проверяет, что разница сумм вычисляется корректно.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)
        # Убедимся, что transfer_amount положительная
        assume(transfer_amount > Decimal('0'))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: получаем остаток долга до передачи
            previous_amount = get_remaining_debt(session, loan_id)

            # Act: создаём передачу долга
            transfer = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_date=transfer_date,
                transfer_amount=transfer_amount
            )

            # Assert: проверяем корректность вычисления разницы
            # amount_difference = transfer_amount - previous_amount
            expected_difference = transfer_amount - previous_amount
            assert transfer.amount_difference == expected_difference
            assert transfer.transfer_amount == transfer_amount
            assert transfer.previous_amount == previous_amount
        finally:
            session.close()
            test_engine.dispose()


class TestDebtTransferHistoryProperties:
    """Property-based тесты для истории передачи долга."""

    @given(
        original_lender_name=lender_names,
        new_lender_names=st.lists(
            lender_names,
            min_size=1,
            max_size=5,
            unique=True
        ),
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amounts_list=st.lists(
            transfer_amounts,
            min_size=1,
            max_size=5
        ),
        issue_date=dates,
        transfer_dates=st.lists(
            dates,
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_5_transfer_history_chronological_order(
        self,
        original_lender_name,
        new_lender_names,
        loan_name,
        amount,
        transfer_amounts_list,
        issue_date,
        transfer_dates
    ):
        """
        Property 5: Хронологический порядок истории передач.

        Feature: debt-transfer, Property 5: Для любого кредита с историей передач,
        список передач должен быть отсортирован по transfer_date в порядке возрастания

        Validates: Requirements 3.3

        Проверяет, что история передач всегда возвращается в хронологическом порядке.
        """
        # Убедимся, что у нас есть кредиторы для передачи
        assume(len(new_lender_names) >= 1)
        # Убедимся, что суммы положительные
        assume(all(amount > Decimal('0') for amount in transfer_amounts_list))
        # Убедимся, что имена разные
        assume(original_lender_name not in new_lender_names)
        assume(original_lender_name != loan_name)
        assume(len(set(new_lender_names)) == len(new_lender_names))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём новых кредиторов
            new_lenders = []
            for new_lender_name in new_lender_names:
                new_lender = create_lender(
                    session=session,
                    name=new_lender_name,
                    lender_type=LenderType.COLLECTOR
                )
                session.flush()
                new_lenders.append(new_lender)

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Act: создаём несколько передач долга с разными датами
            # Используем только столько передач, сколько у нас есть кредиторов и дат
            num_transfers = min(len(new_lenders), len(transfer_dates), len(transfer_amounts_list))
            
            for i in range(num_transfers):
                transfer_date = transfer_dates[i]
                transfer_amount = transfer_amounts_list[i]
                new_lender = new_lenders[i]
                
                # Убедимся, что сумма положительная
                if transfer_amount > Decimal('0'):
                    create_debt_transfer(
                        session=session,
                        loan_id=loan_id,
                        to_lender_id=new_lender.id,
                        transfer_date=transfer_date,
                        transfer_amount=transfer_amount
                    )

            # Act: получаем историю передач
            history = get_transfer_history(session, loan_id)

            # Assert: проверяем, что история отсортирована по дате в порядке возрастания
            if len(history) > 1:
                # Проверяем, что каждая дата не меньше предыдущей
                for i in range(1, len(history)):
                    assert history[i].transfer_date >= history[i-1].transfer_date, \
                        f"История передач не отсортирована: {history[i-1].transfer_date} > {history[i].transfer_date}"
            
            # Assert: проверяем, что все даты в истории совпадают с созданными передачами
            assert len(history) == num_transfers
            
            # Assert: проверяем, что история содержит все созданные передачи
            for transfer in history:
                assert transfer.loan_id == loan_id
        finally:
            session.close()
            test_engine.dispose()



class TestDebtTransferPaymentUpdateProperties:
    """Property-based тесты для обновления платежей при передаче долга."""

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates,
        transfer_date=dates,
        payment_dates=st.lists(dates, min_size=1, max_size=5),
        payment_amounts=st.lists(
            st.decimals(min_value=Decimal('100.00'), max_value=Decimal('5000.00'), places=2),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_6_executed_payments_immutability_on_transfer(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date,
        transfer_date,
        payment_dates,
        payment_amounts
    ):
        """
        Property 6: Неизменность исполненных платежей при передаче.

        Feature: debt-transfer, Property 6: Для любой передачи долга,
        платежи со статусом EXECUTED или EXECUTED_LATE не должны изменяться
        (их привязка к кредитору сохраняется)

        Validates: Requirements 4.2

        Проверяет, что исполненные платежи не обновляются при передаче долга.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)
        # Убедимся, что transfer_amount положительная
        assume(transfer_amount > Decimal('0'))
        # Убедимся, что у нас есть платежи
        assume(len(payment_dates) >= 1)
        assume(len(payment_amounts) >= 1)
        # Убедимся, что суммы платежей положительные
        assume(all(amount > Decimal('0') for amount in payment_amounts))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Arrange: создаём исполненные платежи (EXECUTED и EXECUTED_LATE)
            executed_payments = []
            num_payments = min(len(payment_dates), len(payment_amounts))
            
            for i in range(num_payments):
                payment_date = payment_dates[i]
                payment_amount = payment_amounts[i]
                
                # Создаём платёж со статусом EXECUTED
                payment = LoanPaymentDB(
                    id=str(uuid.uuid4()),
                    loan_id=loan_id,
                    holder_id=original_lender_id,  # Привязан к исходному кредитору
                    scheduled_date=payment_date,
                    principal_amount=payment_amount,
                    interest_amount=Decimal('0'),
                    total_amount=payment_amount,
                    status=PaymentStatus.EXECUTED if i % 2 == 0 else PaymentStatus.EXECUTED_LATE,
                    executed_date=payment_date,
                    executed_amount=payment_amount
                )
                session.add(payment)
                executed_payments.append(payment)
            
            session.flush()

            # Arrange: сохраняем исходные holder_id для исполненных платежей
            original_holder_ids = {p.id: p.holder_id for p in executed_payments}

            # Act: создаём передачу долга
            transfer = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_date=transfer_date,
                transfer_amount=transfer_amount
            )

            # Assert: проверяем, что исполненные платежи не изменились
            for payment in executed_payments:
                session.refresh(payment)
                # holder_id исполненных платежей должен остаться прежним
                assert payment.holder_id == original_holder_ids[payment.id], \
                    f"Исполненный платёж {payment.id} был изменён: " \
                    f"было {original_holder_ids[payment.id]}, стало {payment.holder_id}"
                # Статус платежа не должен измениться
                assert payment.status in [PaymentStatus.EXECUTED, PaymentStatus.EXECUTED_LATE]
        finally:
            session.close()
            test_engine.dispose()

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates,
        transfer_date=dates,
        payment_dates=st.lists(dates, min_size=1, max_size=5),
        payment_amounts=st.lists(
            st.decimals(min_value=Decimal('100.00'), max_value=Decimal('5000.00'), places=2),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_7_pending_payments_update_on_transfer(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date,
        transfer_date,
        payment_dates,
        payment_amounts
    ):
        """
        Property 7: Обновление ожидающих платежей при передаче.

        Feature: debt-transfer, Property 7: Для любой передачи долга,
        все платежи со статусом PENDING должны быть обновлены для привязки
        к новому держателю долга

        Validates: Requirements 4.1

        Проверяет, что ожидающие платежи обновляются при передаче долга.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)
        # Убедимся, что transfer_amount положительная
        assume(transfer_amount > Decimal('0'))
        # Убедимся, что у нас есть платежи
        assume(len(payment_dates) >= 1)
        assume(len(payment_amounts) >= 1)
        # Убедимся, что суммы платежей положительные
        assume(all(amount > Decimal('0') for amount in payment_amounts))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Arrange: создаём ожидающие платежи (PENDING)
            pending_payments = []
            num_payments = min(len(payment_dates), len(payment_amounts))
            
            for i in range(num_payments):
                payment_date = payment_dates[i]
                payment_amount = payment_amounts[i]
                
                # Создаём платёж со статусом PENDING
                payment = LoanPaymentDB(
                    id=str(uuid.uuid4()),
                    loan_id=loan_id,
                    holder_id=original_lender_id,  # Привязан к исходному кредитору
                    scheduled_date=payment_date,
                    principal_amount=payment_amount,
                    interest_amount=Decimal('0'),
                    total_amount=payment_amount,
                    status=PaymentStatus.PENDING
                )
                session.add(payment)
                pending_payments.append(payment)
            
            session.flush()

            # Act: создаём передачу долга
            transfer = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_date=transfer_date,
                transfer_amount=transfer_amount
            )

            # Assert: проверяем, что ожидающие платежи обновлены
            for payment in pending_payments:
                session.refresh(payment)
                # holder_id ожидающих платежей должен быть обновлён на нового держателя
                assert payment.holder_id == new_lender_id, \
                    f"Ожидающий платёж {payment.id} не был обновлён: " \
                    f"ожидалось {new_lender_id}, получено {payment.holder_id}"
                # Статус платежа должен остаться PENDING
                assert payment.status == PaymentStatus.PENDING
        finally:
            session.close()
            test_engine.dispose()

    @given(
        original_lender_name=lender_names,
        new_lender_name=lender_names,
        loan_name=loan_names,
        amount=loan_amounts,
        transfer_amount=transfer_amounts,
        issue_date=dates,
        transfer_date=dates,
        payment_dates=st.lists(dates, min_size=1, max_size=5),
        payment_amounts=st.lists(
            st.decimals(min_value=Decimal('100.00'), max_value=Decimal('5000.00'), places=2),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        verbosity=Verbosity.verbose,
        phases=[Phase.generate, Phase.target, Phase.shrink]
    )
    def test_property_6_7_mixed_payment_statuses_on_transfer(
        self,
        original_lender_name,
        new_lender_name,
        loan_name,
        amount,
        transfer_amount,
        issue_date,
        transfer_date,
        payment_dates,
        payment_amounts
    ):
        """
        Property 6 & 7 Combined: Смешанные статусы платежей при передаче.

        Feature: debt-transfer, Property 6 & 7: Для любой передачи долга,
        платежи со статусом PENDING должны быть обновлены, а платежи со статусами
        EXECUTED и EXECUTED_LATE должны остаться без изменений

        Validates: Requirements 4.1, 4.2

        Проверяет, что при передаче долга обновляются только PENDING платежи,
        а исполненные платежи остаются без изменений.
        """
        # Убедимся, что имена разные
        assume(original_lender_name != new_lender_name)
        assume(original_lender_name != loan_name)
        assume(new_lender_name != loan_name)
        # Убедимся, что transfer_amount положительная
        assume(transfer_amount > Decimal('0'))
        # Убедимся, что у нас есть платежи
        assume(len(payment_dates) >= 2)
        assume(len(payment_amounts) >= 2)
        # Убедимся, что суммы платежей положительные
        assume(all(amount > Decimal('0') for amount in payment_amounts))

        # Создаём отдельный engine для каждого теста
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        
        @event.listens_for(test_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine)
        session = TestSession()
        
        try:
            # Arrange: создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name=original_lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            original_lender_id = original_lender.id

            # Arrange: создаём нового кредитора
            new_lender = create_lender(
                session=session,
                name=new_lender_name,
                lender_type=LenderType.COLLECTOR
            )
            session.flush()
            new_lender_id = new_lender.id

            # Arrange: создаём кредит
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=original_lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date
            )
            session.flush()
            loan_id = loan.id

            # Arrange: создаём платежи с разными статусами
            pending_payments = []
            executed_payments = []
            num_payments = min(len(payment_dates), len(payment_amounts))
            
            for i in range(num_payments):
                payment_date = payment_dates[i]
                payment_amount = payment_amounts[i]
                
                if i % 2 == 0:
                    # Создаём PENDING платёж
                    payment = LoanPaymentDB(
                        id=str(uuid.uuid4()),
                        loan_id=loan_id,
                        holder_id=original_lender_id,
                        scheduled_date=payment_date,
                        principal_amount=payment_amount,
                        interest_amount=Decimal('0'),
                        total_amount=payment_amount,
                        status=PaymentStatus.PENDING
                    )
                    pending_payments.append(payment)
                else:
                    # Создаём EXECUTED платёж
                    payment = LoanPaymentDB(
                        id=str(uuid.uuid4()),
                        loan_id=loan_id,
                        holder_id=original_lender_id,
                        scheduled_date=payment_date,
                        principal_amount=payment_amount,
                        interest_amount=Decimal('0'),
                        total_amount=payment_amount,
                        status=PaymentStatus.EXECUTED,
                        executed_date=payment_date,
                        executed_amount=payment_amount
                    )
                    executed_payments.append(payment)
                
                session.add(payment)
            
            session.flush()

            # Arrange: сохраняем исходные holder_id для исполненных платежей
            original_executed_holder_ids = {p.id: p.holder_id for p in executed_payments}

            # Act: создаём передачу долга
            transfer = create_debt_transfer(
                session=session,
                loan_id=loan_id,
                to_lender_id=new_lender_id,
                transfer_date=transfer_date,
                transfer_amount=transfer_amount
            )

            # Assert: проверяем PENDING платежи (должны быть обновлены)
            for payment in pending_payments:
                session.refresh(payment)
                assert payment.holder_id == new_lender_id, \
                    f"PENDING платёж {payment.id} не был обновлён"
                assert payment.status == PaymentStatus.PENDING

            # Assert: проверяем EXECUTED платежи (не должны быть обновлены)
            for payment in executed_payments:
                session.refresh(payment)
                assert payment.holder_id == original_executed_holder_ids[payment.id], \
                    f"EXECUTED платёж {payment.id} был неправильно обновлён"
                assert payment.status == PaymentStatus.EXECUTED
        finally:
            session.close()
            test_engine.dispose()
