"""
Интеграционные тесты для отображения платежей по кредитам в TransactionsPanel.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import (
    LenderDB, LoanDB, LoanPaymentDB, CategoryDB, Base
)
from models.enums import (
    LenderType, LoanType, LoanStatus, PaymentStatus, TransactionType
)
from services.loan_payment_service import get_payments_by_date


class TestLoanPaymentIntegration:
    """Тесты интеграции платежей по кредитам с TransactionsPanel."""

    def test_get_payments_by_date_returns_correct_payments(self, db_session):
        """
        Проверяет, что get_payments_by_date возвращает только платежи на указанную дату.
        """
        # Создаём займодателя
        lender = LenderDB(
            name="Тестовый банк",
            lender_type=LenderType.BANK
        )
        db_session.add(lender)
        db_session.flush()

        # Создаём кредит
        loan = LoanDB(
            lender_id=lender.id,
            name="Тестовый кредит",
            loan_type=LoanType.CONSUMER,
            amount=Decimal("100000.00"),
            issue_date=date.today() - timedelta(days=30),
            status=LoanStatus.ACTIVE
        )
        db_session.add(loan)
        db_session.flush()

        # Создаём платежи на разные даты
        target_date = date.today()
        other_date = date.today() + timedelta(days=7)

        payment1 = LoanPaymentDB(
            loan_id=loan.id,
            scheduled_date=target_date,
            principal_amount=Decimal("5000.00"),
            interest_amount=Decimal("500.00"),
            total_amount=Decimal("5500.00"),
            status=PaymentStatus.PENDING
        )
        
        payment2 = LoanPaymentDB(
            loan_id=loan.id,
            scheduled_date=other_date,
            principal_amount=Decimal("5000.00"),
            interest_amount=Decimal("450.00"),
            total_amount=Decimal("5450.00"),
            status=PaymentStatus.PENDING
        )
        
        payment3 = LoanPaymentDB(
            loan_id=loan.id,
            scheduled_date=target_date,
            principal_amount=Decimal("5000.00"),
            interest_amount=Decimal("500.00"),
            total_amount=Decimal("5500.00"),
            status=PaymentStatus.OVERDUE
        )

        db_session.add_all([payment1, payment2, payment3])
        db_session.commit()

        # Получаем платежи на целевую дату
        payments = get_payments_by_date(db_session, target_date)

        # Проверяем результат
        assert len(payments) == 2, "Должно быть 2 платежа на целевую дату"
        assert all(p.scheduled_date == target_date for p in payments), \
            "Все платежи должны быть на целевую дату"
        assert payment1 in payments, "payment1 должен быть в результатах"
        assert payment3 in payments, "payment3 должен быть в результатах"
        assert payment2 not in payments, "payment2 не должен быть в результатах"

    def test_get_payments_by_date_empty_result(self, db_session):
        """
        Проверяет, что get_payments_by_date возвращает пустой список,
        если нет платежей на указанную дату.
        """
        target_date = date.today()
        payments = get_payments_by_date(db_session, target_date)
        
        assert payments == [], "Должен вернуться пустой список"

    def test_get_payments_by_date_with_multiple_loans(self, db_session):
        """
        Проверяет, что get_payments_by_date возвращает платежи от разных кредитов.
        """
        # Создаём займодателя
        lender = LenderDB(
            name="Тестовый банк",
            lender_type=LenderType.BANK
        )
        db_session.add(lender)
        db_session.flush()

        # Создаём два кредита
        loan1 = LoanDB(
            lender_id=lender.id,
            name="Кредит 1",
            loan_type=LoanType.CONSUMER,
            amount=Decimal("100000.00"),
            issue_date=date.today() - timedelta(days=30),
            status=LoanStatus.ACTIVE
        )
        
        loan2 = LoanDB(
            lender_id=lender.id,
            name="Кредит 2",
            loan_type=LoanType.MORTGAGE,
            amount=Decimal("2000000.00"),
            issue_date=date.today() - timedelta(days=60),
            status=LoanStatus.ACTIVE
        )
        
        db_session.add_all([loan1, loan2])
        db_session.flush()

        # Создаём платежи на одну дату от разных кредитов
        target_date = date.today()

        payment1 = LoanPaymentDB(
            loan_id=loan1.id,
            scheduled_date=target_date,
            principal_amount=Decimal("5000.00"),
            interest_amount=Decimal("500.00"),
            total_amount=Decimal("5500.00"),
            status=PaymentStatus.PENDING
        )
        
        payment2 = LoanPaymentDB(
            loan_id=loan2.id,
            scheduled_date=target_date,
            principal_amount=Decimal("20000.00"),
            interest_amount=Decimal("15000.00"),
            total_amount=Decimal("35000.00"),
            status=PaymentStatus.PENDING
        )

        db_session.add_all([payment1, payment2])
        db_session.commit()

        # Получаем платежи на целевую дату
        payments = get_payments_by_date(db_session, target_date)

        # Проверяем результат
        assert len(payments) == 2, "Должно быть 2 платежа от разных кредитов"
        assert payment1 in payments, "payment1 должен быть в результатах"
        assert payment2 in payments, "payment2 должен быть в результатах"
        
        # Проверяем, что платежи отсортированы по loan_id
        assert payments[0].loan_id <= payments[1].loan_id, \
            "Платежи должны быть отсортированы по loan_id"
