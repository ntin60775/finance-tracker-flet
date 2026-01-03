"""
Unit тесты для функции get_loans_by_current_holder.

Тестирует получение кредитов по текущему держателю долга.
"""

import unittest
from datetime import date
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models.models import Base, LenderDB, LoanDB
from finance_tracker.models.enums import LenderType, LoanType, LoanStatus
from finance_tracker.services.lender_service import create_lender
from finance_tracker.services.loan_service import create_loan, get_loans_by_current_holder


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
        session.query(LoanDB).delete()
        session.query(LenderDB).delete()
        session.commit()
        session.close()


class TestGetLoansByCurrentHolder(unittest.TestCase):
    """Тесты для функции get_loans_by_current_holder."""

    def test_get_loans_by_original_lender(self):
        """Тест получения кредитов по исходному кредитору (без передачи)."""
        with get_test_session() as session:
            # Создаём кредитора
            lender = create_lender(
                session=session,
                name="Тестовый банк",
                lender_type=LenderType.BANK
            )
            
            # Создаём кредит без передачи
            loan = create_loan(
                session=session,
                name="Тестовый кредит",
                lender_id=lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Получаем кредиты по исходному кредитору
            loans = get_loans_by_current_holder(session, lender.id)
            
            # Проверяем результат
            self.assertEqual(len(loans), 1)
            self.assertEqual(loans[0].id, loan.id)
            self.assertEqual(loans[0].name, "Тестовый кредит")

    def test_get_loans_by_current_holder_after_transfer(self):
        """Тест получения кредитов по текущему держателю после передачи."""
        with get_test_session() as session:
            # Создаём исходного кредитора
            original_lender = create_lender(
                session=session,
                name="МФО",
                lender_type=LenderType.MFO
            )
            
            # Создаём нового держателя
            new_holder = create_lender(
                session=session,
                name="Коллектор",
                lender_type=LenderType.COLLECTOR
            )
            
            # Создаём кредит
            loan = create_loan(
                session=session,
                name="Переданный кредит",
                lender_id=original_lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('50000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Симулируем передачу долга (обновляем current_holder_id)
            loan.current_holder_id = new_holder.id
            session.commit()
            
            # Получаем кредиты по новому держателю
            loans_new_holder = get_loans_by_current_holder(session, new_holder.id)
            
            # Получаем кредиты по исходному кредитору
            loans_original = get_loans_by_current_holder(session, original_lender.id)
            
            # Проверяем результаты
            self.assertEqual(len(loans_new_holder), 1)
            self.assertEqual(loans_new_holder[0].id, loan.id)
            
            # Исходный кредитор больше не должен видеть этот кредит
            self.assertEqual(len(loans_original), 0)

    def test_get_loans_with_filters(self):
        """Тест получения кредитов с фильтрацией по типу и статусу."""
        with get_test_session() as session:
            # Создаём кредитора
            lender = create_lender(
                session=session,
                name="Банк",
                lender_type=LenderType.BANK
            )
            
            # Создаём несколько кредитов разных типов и статусов
            loan1 = create_loan(
                session=session,
                name="Потребительский кредит",
                lender_id=lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            loan2 = create_loan(
                session=session,
                name="Ипотека",
                lender_id=lender.id,
                loan_type=LoanType.MORTGAGE,
                amount=Decimal('5000000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Изменяем статус второго кредита
            loan2.status = LoanStatus.PAID_OFF
            session.commit()
            
            # Получаем все кредиты
            all_loans = get_loans_by_current_holder(session, lender.id)
            self.assertEqual(len(all_loans), 2)
            
            # Получаем только потребительские кредиты
            consumer_loans = get_loans_by_current_holder(
                session, 
                lender.id, 
                loan_type=LoanType.CONSUMER
            )
            self.assertEqual(len(consumer_loans), 1)
            self.assertEqual(consumer_loans[0].loan_type, LoanType.CONSUMER)
            
            # Получаем только активные кредиты
            active_loans = get_loans_by_current_holder(
                session, 
                lender.id, 
                status=LoanStatus.ACTIVE
            )
            self.assertEqual(len(active_loans), 1)
            self.assertEqual(active_loans[0].status, LoanStatus.ACTIVE)

    def test_get_loans_empty_result(self):
        """Тест получения пустого списка для держателя без кредитов."""
        with get_test_session() as session:
            # Создаём кредитора без кредитов
            lender = create_lender(
                session=session,
                name="Новый банк",
                lender_type=LenderType.BANK
            )
            
            # Получаем кредиты
            loans = get_loans_by_current_holder(session, lender.id)
            
            # Проверяем пустой результат
            self.assertEqual(len(loans), 0)
            self.assertIsInstance(loans, list)


class TestGetDebtByHolderStatistics(unittest.TestCase):
    """Тесты для функции get_debt_by_holder_statistics."""

    def test_statistics_single_holder(self):
        """Тест статистики для одного держателя."""
        with get_test_session() as session:
            # Создаём кредитора
            lender = create_lender(
                session=session,
                name="Банк",
                lender_type=LenderType.BANK
            )
            
            # Создаём кредит
            loan = create_loan(
                session=session,
                name="Кредит 1",
                lender_id=lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Получаем статистику
            from finance_tracker.services.loan_service import get_debt_by_holder_statistics
            stats = get_debt_by_holder_statistics(session)
            
            # Проверяем результат
            self.assertEqual(len(stats), 1)
            self.assertIn(lender.id, stats)
            
            holder_stat = stats[lender.id]
            self.assertEqual(holder_stat["holder_name"], "Банк")
            self.assertEqual(holder_stat["loan_count"], 1)
            self.assertEqual(holder_stat["total_debt"], Decimal('100000.00'))
            self.assertEqual(len(holder_stat["loans"]), 1)

    def test_statistics_multiple_holders(self):
        """Тест статистики для нескольких держателей."""
        with get_test_session() as session:
            # Создаём двух кредиторов
            lender1 = create_lender(
                session=session,
                name="Банк 1",
                lender_type=LenderType.BANK
            )
            
            lender2 = create_lender(
                session=session,
                name="Банк 2",
                lender_type=LenderType.BANK
            )
            
            # Создаём кредиты для каждого
            loan1 = create_loan(
                session=session,
                name="Кредит 1",
                lender_id=lender1.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            loan2 = create_loan(
                session=session,
                name="Кредит 2",
                lender_id=lender2.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('200000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Получаем статистику
            from finance_tracker.services.loan_service import get_debt_by_holder_statistics
            stats = get_debt_by_holder_statistics(session)
            
            # Проверяем результат
            self.assertEqual(len(stats), 2)
            self.assertIn(lender1.id, stats)
            self.assertIn(lender2.id, stats)
            
            # Проверяем статистику первого держателя
            self.assertEqual(stats[lender1.id]["holder_name"], "Банк 1")
            self.assertEqual(stats[lender1.id]["loan_count"], 1)
            self.assertEqual(stats[lender1.id]["total_debt"], Decimal('100000.00'))
            
            # Проверяем статистику второго держателя
            self.assertEqual(stats[lender2.id]["holder_name"], "Банк 2")
            self.assertEqual(stats[lender2.id]["loan_count"], 1)
            self.assertEqual(stats[lender2.id]["total_debt"], Decimal('200000.00'))

    def test_statistics_with_transferred_loans(self):
        """Тест статистики с учётом переданных кредитов."""
        with get_test_session() as session:
            # Создаём исходного кредитора и коллектора
            original_lender = create_lender(
                session=session,
                name="МФО",
                lender_type=LenderType.MFO
            )
            
            collector = create_lender(
                session=session,
                name="Коллектор",
                lender_type=LenderType.COLLECTOR
            )
            
            # Создаём кредит
            loan = create_loan(
                session=session,
                name="Переданный кредит",
                lender_id=original_lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('50000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Передаём долг коллектору
            loan.current_holder_id = collector.id
            session.commit()
            
            # Получаем статистику
            from finance_tracker.services.loan_service import get_debt_by_holder_statistics
            stats = get_debt_by_holder_statistics(session)
            
            # Проверяем результат
            self.assertEqual(len(stats), 1)
            self.assertIn(collector.id, stats)
            self.assertNotIn(original_lender.id, stats)
            
            # Проверяем статистику коллектора
            self.assertEqual(stats[collector.id]["holder_name"], "Коллектор")
            self.assertEqual(stats[collector.id]["loan_count"], 1)
            self.assertEqual(stats[collector.id]["total_debt"], Decimal('50000.00'))

    def test_statistics_with_status_filter(self):
        """Тест статистики с фильтрацией по статусу."""
        with get_test_session() as session:
            # Создаём кредитора
            lender = create_lender(
                session=session,
                name="Банк",
                lender_type=LenderType.BANK
            )
            
            # Создаём активный кредит
            loan1 = create_loan(
                session=session,
                name="Активный кредит",
                lender_id=lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date(2024, 1, 1)
            )
            
            # Создаём погашенный кредит
            loan2 = create_loan(
                session=session,
                name="Погашенный кредит",
                lender_id=lender.id,
                loan_type=LoanType.CONSUMER,
                amount=Decimal('200000.00'),
                issue_date=date(2024, 1, 1)
            )
            loan2.status = LoanStatus.PAID_OFF
            session.commit()
            
            # Получаем статистику только по активным кредитам
            from finance_tracker.services.loan_service import get_debt_by_holder_statistics
            stats = get_debt_by_holder_statistics(session, status=LoanStatus.ACTIVE)
            
            # Проверяем результат
            self.assertEqual(len(stats), 1)
            self.assertIn(lender.id, stats)
            
            # Проверяем, что учтён только активный кредит
            self.assertEqual(stats[lender.id]["loan_count"], 1)
            self.assertEqual(stats[lender.id]["total_debt"], Decimal('100000.00'))

    def test_statistics_empty_result(self):
        """Тест статистики при отсутствии кредитов."""
        with get_test_session() as session:
            # Получаем статистику без кредитов
            from finance_tracker.services.loan_service import get_debt_by_holder_statistics
            stats = get_debt_by_holder_statistics(session)
            
            # Проверяем пустой результат
            self.assertEqual(len(stats), 0)
            self.assertIsInstance(stats, dict)


if __name__ == '__main__':
    unittest.main()
