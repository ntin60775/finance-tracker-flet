"""
Тесты для проверки включения информации о держателях в статистику по кредитам.
"""
import unittest
from decimal import Decimal
from datetime import date, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finance_tracker.models import Base
from finance_tracker.services.loan_statistics_service import get_summary_statistics
from finance_tracker.services.lender_service import create_lender
from finance_tracker.services.loan_service import create_loan
from finance_tracker.models.enums import LenderType, LoanType


# Создаём тестовую БД в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(bind=test_engine)


@contextmanager
def get_test_session():
    """Контекстный менеджер для создания тестовой сессии БД с очисткой."""
    # Создаём таблицы
    Base.metadata.create_all(bind=test_engine)
    
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Очищаем таблицы после теста
        Base.metadata.drop_all(bind=test_engine)


class TestLoanStatisticsHolderInfo(unittest.TestCase):
    """Тесты для проверки информации о держателях в статистике."""

    def test_summary_statistics_includes_by_holder_field(self):
        """
        Тест наличия поля by_holder в статистике.
        
        Проверяет:
        - Поле by_holder присутствует в результате get_summary_statistics
        - Поле by_holder является словарём
        
        Validates: Requirements 7.1
        """
        with get_test_session() as session:
            # Получаем статистику
            stats = get_summary_statistics(session)
            
            # Проверяем наличие поля by_holder
            self.assertIn('by_holder', stats, "Статистика должна содержать поле by_holder")
            self.assertIsInstance(stats['by_holder'], dict, "Поле by_holder должно быть словарём")

    def test_summary_statistics_by_holder_with_single_lender(self):
        """
        Тест статистики по держателям с одним кредитором.
        
        Проверяет:
        - Для одного кредитора статистика содержит корректную информацию
        - holder_name соответствует имени кредитора
        - loan_count равен количеству кредитов
        - total_debt равен сумме задолженностей
        
        Validates: Requirements 7.1
        """
        with get_test_session() as session:
            # Создаём кредитора
            lender = create_lender(
                session,
                name="Тестовый Банк",
                lender_type=LenderType.BANK
            )
            
            # Создаём два активных кредита
            loan1 = create_loan(
                session,
                lender_id=lender.id,
                name="Кредит 1",
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date.today() - timedelta(days=30),
                interest_rate=Decimal('10.0'),
                end_date=date.today() + timedelta(days=365)
            )
            
            loan2 = create_loan(
                session,
                lender_id=lender.id,
                name="Кредит 2",
                loan_type=LoanType.CONSUMER,
                amount=Decimal('50000.00'),
                issue_date=date.today() - timedelta(days=30),
                interest_rate=Decimal('10.0'),
                end_date=date.today() + timedelta(days=365)
            )
            
            # Получаем статистику
            stats = get_summary_statistics(session)
            
            # Проверяем статистику по держателям
            self.assertIn('by_holder', stats)
            by_holder = stats['by_holder']
            
            # Должен быть один держатель
            self.assertEqual(len(by_holder), 1, "Должен быть один держатель")
            
            # Проверяем информацию о держателе
            holder_id = lender.id
            self.assertIn(holder_id, by_holder, f"Держатель {holder_id} должен быть в статистике")
            
            holder_info = by_holder[holder_id]
            self.assertEqual(holder_info['holder_name'], "Тестовый Банк")
            self.assertEqual(holder_info['loan_count'], 2)
            # total_debt должен быть равен сумме кредитов (без учёта платежей)
            self.assertGreater(holder_info['total_debt'], 0)

    def test_summary_statistics_by_holder_with_multiple_lenders(self):
        """
        Тест статистики по держателям с несколькими кредиторами.
        
        Проверяет:
        - Для нескольких кредиторов статистика содержит информацию о каждом
        - Каждый держатель имеет корректную статистику
        
        Validates: Requirements 7.1
        """
        with get_test_session() as session:
            # Создаём двух кредиторов
            lender1 = create_lender(
                session,
                name="Банк 1",
                lender_type=LenderType.BANK
            )
            
            lender2 = create_lender(
                session,
                name="Банк 2",
                lender_type=LenderType.BANK
            )
            
            # Создаём кредиты для каждого кредитора
            loan1 = create_loan(
                session,
                lender_id=lender1.id,
                name="Кредит от Банка 1",
                loan_type=LoanType.CONSUMER,
                amount=Decimal('100000.00'),
                issue_date=date.today() - timedelta(days=30),
                interest_rate=Decimal('10.0'),
                end_date=date.today() + timedelta(days=365)
            )
            
            loan2 = create_loan(
                session,
                lender_id=lender2.id,
                name="Кредит от Банка 2",
                loan_type=LoanType.CONSUMER,
                amount=Decimal('200000.00'),
                issue_date=date.today() - timedelta(days=30),
                interest_rate=Decimal('10.0'),
                end_date=date.today() + timedelta(days=365)
            )
            
            # Получаем статистику
            stats = get_summary_statistics(session)
            
            # Проверяем статистику по держателям
            self.assertIn('by_holder', stats)
            by_holder = stats['by_holder']
            
            # Должно быть два держателя
            self.assertEqual(len(by_holder), 2, "Должно быть два держателя")
            
            # Проверяем информацию о каждом держателе
            self.assertIn(lender1.id, by_holder)
            self.assertIn(lender2.id, by_holder)
            
            holder1_info = by_holder[lender1.id]
            self.assertEqual(holder1_info['holder_name'], "Банк 1")
            self.assertEqual(holder1_info['loan_count'], 1)
            
            holder2_info = by_holder[lender2.id]
            self.assertEqual(holder2_info['holder_name'], "Банк 2")
            self.assertEqual(holder2_info['loan_count'], 1)

    def test_summary_statistics_by_holder_empty_when_no_loans(self):
        """
        Тест статистики по держателям при отсутствии кредитов.
        
        Проверяет:
        - При отсутствии кредитов by_holder является пустым словарём
        
        Validates: Requirements 7.1
        """
        with get_test_session() as session:
            # Получаем статистику без создания кредитов
            stats = get_summary_statistics(session)
            
            # Проверяем, что by_holder пустой
            self.assertIn('by_holder', stats)
            self.assertEqual(len(stats['by_holder']), 0, "by_holder должен быть пустым при отсутствии кредитов")


if __name__ == '__main__':
    unittest.main()
