"""
Property-based тесты для план-факт анализа.

Тестирует:
- Property 25: Фильтрация по периоду
- Property 26: Фильтрация по категории
- Property 27: Расчёт отклонений
- Property 28: Расчёт статистики исполнения
- Property: Отклонения должны корректно рассчитываться для любых план-факт данных
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
    PlannedTransactionDB,
    PlannedOccurrenceDB,
)
from finance_tracker.models.enums import (
    TransactionType,
    OccurrenceStatus,
)
from finance_tracker.services.plan_fact_service import get_plan_fact_analysis

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
                    amount=Decimal('100.00'),
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
                amount=plan,
                status=OccurrenceStatus.EXECUTED,
                executed_amount=fact,
                executed_date=today,
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

    @given(
        occurrences_data=st.lists(
            st.tuples(
                st.decimals(min_value=Decimal('100.00'), max_value=Decimal('10000.00'), places=2),  # planned_amount (для вхождения)
                st.decimals(min_value=Decimal('50.00'), max_value=Decimal('15000.00'), places=2),   # executed_amount
                st.integers(min_value=-10, max_value=10)  # date_offset
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_deviation_calculation_for_any_plan_fact_data(self, occurrences_data):
        """
        Property: Отклонения должны корректно рассчитываться для любых план-факт данных.
        
        Feature: ui-testing, Property: Отклонения должны корректно рассчитываться для любых план-факт данных
        Validates: Requirements 12.5
        
        Проверяет, что для любого набора плановых и фактических данных:
        1. Отклонение по сумме = Факт - План (где План = occurrence.amount)
        2. Среднее отклонение рассчитывается корректно
        3. Отклонение по дате рассчитывается корректно (в днях)
        4. Статистика отклонений корректна для всех исполненных вхождений
        """
        with get_test_session() as session:
            # Arrange
            today = date.today()
            cat = CategoryDB(name="Test", type=TransactionType.EXPENSE, is_system=True)
            session.add(cat)
            session.flush()
            
            # Плановая сумма в шаблоне транзакции (используется для отображения в UI)
            template_amount = Decimal('1000.00')
            pt = PlannedTransactionDB(
                amount=template_amount,
                category_id=cat.id,
                type=TransactionType.EXPENSE,
                start_date=today,
                is_active=True,
                description="Test"
            )
            session.add(pt)
            session.flush()
            
            # Создаём вхождения с разными отклонениями
            expected_deviations = []
            expected_date_deviations = []
            
            for planned_amount, executed_amount, date_offset in occurrences_data:
                occurrence_date = today + timedelta(days=date_offset)
                executed_date = today  # Исполняем сегодня
                
                # Рассчитываем ожидаемые отклонения
                # amount_deviation = executed_amount - occurrence.amount (не PlannedTransaction.amount!)
                amount_deviation = executed_amount - planned_amount
                date_deviation = (executed_date - occurrence_date).days
                
                expected_deviations.append(amount_deviation)
                expected_date_deviations.append(date_deviation)
                
                occ = PlannedOccurrenceDB(
                    planned_transaction_id=pt.id,
                    occurrence_date=occurrence_date,
                    amount=planned_amount,  # Индивидуальная плановая сумма вхождения
                    status=OccurrenceStatus.EXECUTED,
                    executed_amount=executed_amount,
                    executed_date=executed_date
                )
                session.add(occ)
            
            session.commit()
            
            # Act
            analysis = get_plan_fact_analysis(session, today - timedelta(days=15), today + timedelta(days=15))
            
            # Assert
            # 1. Проверяем количество исполненных вхождений
            assert analysis['executed_count'] == len(occurrences_data)
            
            # 2. Проверяем среднее отклонение по сумме
            expected_avg_amount_deviation = sum(expected_deviations) / len(expected_deviations)
            assert abs(analysis['avg_amount_deviation'] - expected_avg_amount_deviation) < Decimal('0.01')
            
            # 3. Проверяем среднее отклонение по дате
            expected_avg_date_deviation = sum(expected_date_deviations) / len(expected_date_deviations)
            assert abs(analysis['avg_date_deviation_days'] - expected_avg_date_deviation) < 0.01
            
            # 4. Проверяем, что каждое вхождение имеет правильное отклонение
            # Проверяем инвариант: amount_deviation = actual_amount - planned_amount (из occurrence)
            # Это проверяет корректность формулы расчета отклонения
            for occ_data in analysis['occurrences']:
                if occ_data['status'] == 'executed':
                    # Получаем фактические значения из БД
                    actual_amount = occ_data['actual_amount']
                    amount_deviation = occ_data['amount_deviation']
                    
                    # Проверяем инвариант: отклонение должно быть равно разнице факта и плана
                    # Используем данные из БД для проверки консистентности
                    # Находим соответствующее вхождение в БД для получения его плановой суммы
                    occ_id = occ_data['occurrence_id']
                    occ_from_db = session.query(PlannedOccurrenceDB).filter_by(id=occ_id).first()
                    
                    # Проверяем, что отклонение рассчитано правильно по формуле
                    expected_deviation_from_db = actual_amount - occ_from_db.amount
                    assert abs(amount_deviation - expected_deviation_from_db) <= Decimal('0.01')
                    
                    # planned_amount в анализе берется из PlannedTransactionDB.amount (шаблон), а не из occurrence.amount
                    assert occ_data['planned_amount'] == template_amount
