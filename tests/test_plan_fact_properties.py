"""
Property-based тесты для план-факт анализа.

Тестирует:
- Property 25: Фильтрация по периоду
- Property 26: Фильтрация по категории
- Property 27: Расчёт отклонений
- Property 28: Расчёт статистики исполнения
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
    PlannedTransactionDB,
    PlannedOccurrenceDB,
)
from models.enums import (
    TransactionType,
    OccurrenceStatus,
)
from services.plan_fact_service import get_plan_fact_analysis

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
        session.query(PlannedOccurrenceDB).delete()
        session.query(PlannedTransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()

class TestPlanFactProperties:
    """Property-based тесты для план-факт анализа."""

    @given(
        offsets=st.lists(st.integers(min_value=-10, max_value=10), min_size=1, max_size=20)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_25_filter_by_period(self, offsets):
        """
        Property 25: Фильтрация по периоду.
        
        Validates: Requirements 7.2
        
        Проверяет, что в анализ попадают только вхождения, дата которых находится внутри заданного периода.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            start_date = today - timedelta(days=5)
            end_date = today + timedelta(days=5)
            
            cat = CategoryDB(name="Test", type=TransactionType.EXPENSE, is_system=True)
            session.add(cat)
            session.flush()
            
            planned_tx = PlannedTransactionDB(
                amount=Decimal('100.00'), category_id=cat.id, type=TransactionType.EXPENSE,
                start_date=today, is_active=True, description="Test"
            )
            session.add(planned_tx)
            session.flush()
            
            expected_count = 0
            for offset in offsets:
                occ_date = today + timedelta(days=offset)
                if start_date <= occ_date <= end_date:
                    expected_count += 1
                    
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=planned_tx.id,
                    occurrence_date=occ_date,
                    amount=Decimal('100.00'), # Fixed: required field
                    status=OccurrenceStatus.PENDING
                ))
            session.commit()

            # Act
            analysis = get_plan_fact_analysis(session, start_date, end_date)

            # Assert
            assert analysis['total_occurrences'] == expected_count

    @given(
        cat1_count=st.integers(min_value=0, max_value=10),
        cat2_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_26_filter_by_category(self, cat1_count, cat2_count):
        """
        Property 26: Фильтрация по категории.
        
        Validates: Requirements 7.3
        
        Проверяет фильтрацию по category_id.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            cat1 = CategoryDB(name="Cat1", type=TransactionType.EXPENSE, is_system=True)
            cat2 = CategoryDB(name="Cat2", type=TransactionType.EXPENSE, is_system=True)
            session.add_all([cat1, cat2])
            session.flush()
            
            pt1 = PlannedTransactionDB(amount=Decimal('100.00'), category_id=cat1.id, type=TransactionType.EXPENSE, start_date=today, is_active=True)
            pt2 = PlannedTransactionDB(amount=Decimal('100.00'), category_id=cat2.id, type=TransactionType.EXPENSE, start_date=today, is_active=True)
            session.add_all([pt1, pt2])
            session.flush()
            
            for _ in range(cat1_count):
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=pt1.id, occurrence_date=today, 
                    amount=Decimal('100.00'), status=OccurrenceStatus.PENDING
                ))
            for _ in range(cat2_count):
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=pt2.id, occurrence_date=today, 
                    amount=Decimal('100.00'), status=OccurrenceStatus.PENDING
                ))
            session.commit()

            # Act
            analysis_cat1 = get_plan_fact_analysis(session, today, today, category_id=cat1.id)
            analysis_cat2 = get_plan_fact_analysis(session, today, today, category_id=cat2.id)

            # Assert
            assert analysis_cat1['total_occurrences'] == cat1_count
            assert analysis_cat2['total_occurrences'] == cat2_count

    @given(
        plan=st.decimals(min_value=Decimal('100.00'), max_value=Decimal('1000.00'), places=2),
        fact=st.decimals(min_value=Decimal('50.00'), max_value=Decimal('1500.00'), places=2)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_27_deviation_calculation(self, plan, fact):
        """
        Property 27: Расчёт отклонений.
        
        Validates: Requirements 7.4
        
        Проверяет правильность расчёта отклонения по сумме (Факт - План).
        Сервис возвращает avg_amount_deviation.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            cat = CategoryDB(name="Test", type=TransactionType.EXPENSE, is_system=True)
            session.add(cat)
            session.flush()
            
            pt = PlannedTransactionDB(
                amount=plan, category_id=cat.id, type=TransactionType.EXPENSE,
                start_date=today, is_active=True, description="Test"
            )
            session.add(pt)
            session.flush()
            
            deviation = fact - plan
            occ = PlannedOccurrenceDB(
                planned_transaction_id=pt.id,
                occurrence_date=today,
                amount=plan, # Fixed: required field
                status=OccurrenceStatus.EXECUTED,
                executed_amount=fact,
                # amount_deviation - computed property, cannot set
                executed_date=today,
                # date_deviation - computed property, cannot set
            )
            session.add(occ)
            session.commit()

            # Act
            analysis = get_plan_fact_analysis(session, today, today)

            # Assert
            assert analysis['avg_amount_deviation'] == deviation

    @given(
        executed=st.integers(min_value=0, max_value=10),
        skipped=st.integers(min_value=0, max_value=10),
        pending=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_28_execution_statistics(self, executed, skipped, pending):
        """
        Property 28: Расчёт статистики исполнения.
        
        Validates: Requirements 7.5
        
        Проверяет правильность подсчёта количества исполненных, пропущенных и ожидающих вхождений.
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            cat = CategoryDB(name="Test", type=TransactionType.EXPENSE, is_system=True)
            session.add(cat)
            session.flush()
            
            pt = PlannedTransactionDB(amount=Decimal('100.00'), category_id=cat.id, type=TransactionType.EXPENSE, start_date=today, is_active=True)
            session.add(pt)
            session.flush()
            
            for _ in range(executed):
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=pt.id, occurrence_date=today, amount=Decimal('100.00'),
                    status=OccurrenceStatus.EXECUTED, executed_amount=Decimal('100.00'), executed_date=today
                ))
            for _ in range(skipped):
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=pt.id, occurrence_date=today, amount=Decimal('100.00'),
                    status=OccurrenceStatus.SKIPPED
                ))
            for _ in range(pending):
                session.add(PlannedOccurrenceDB(
                    planned_transaction_id=pt.id, occurrence_date=today, amount=Decimal('100.00'),
                    status=OccurrenceStatus.PENDING
                ))
            
            session.commit()

            # Act
            analysis = get_plan_fact_analysis(session, today, today)

            # Assert
            assert analysis['total_occurrences'] == executed + skipped + pending
            assert analysis['executed_count'] == executed
            assert analysis['skipped_count'] == skipped
            assert analysis['pending_count'] == pending