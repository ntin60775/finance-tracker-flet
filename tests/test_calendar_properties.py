"""
Property-based тесты для логики календаря (Flet версия).

Тестирует:
- Property 4: Индикаторы дней календаря (расчет статистики по дням)
- Property 5: Отображение транзакций дня (фильтрация по дате)
- Property 9: Навигация между месяцами (корректность выборки данных за период)
"""

from datetime import date, timedelta
from contextlib import contextmanager
from decimal import Decimal

from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    TransactionDB,
    CategoryDB,
    TransactionType,
)
from services.transaction_service import (
    get_month_stats,
    get_transactions_by_date
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
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()

# --- Strategies ---

dates_strategy = st.dates(
    min_value=date(2023, 1, 1),
    max_value=date(2025, 12, 31)
)

amounts_strategy = st.decimals(
    min_value=Decimal('0.01'),
    max_value=Decimal('10000.00'),
    places=2
)

# Стратегия для генерации списка транзакций
@st.composite
def transactions_list_strategy(draw):
    # Сначала создаем дату, вокруг которой будем генерировать транзакции
    base_date = draw(dates_strategy)
    
    # Генерируем список транзакций (данные)
    # Некоторые будут в ту же дату, некоторые в другие дни того же месяца, некоторые в другие месяцы
    transactions_data = []
    num_tx = draw(st.integers(min_value=0, max_value=20))
    
    for _ in range(num_tx):
        # Смещаем дату случайно: 
        # 50% вероятность - тот же месяц
        # 50% вероятность - +/- 2 месяца
        offset_days = draw(st.integers(min_value=-60, max_value=60))
        tx_date = base_date + timedelta(days=offset_days)
        
        amount = draw(amounts_strategy)
        t_type = draw(st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]))
        
        transactions_data.append({
            "date": tx_date,
            "amount": amount,
            "type": t_type
        })
        
    return base_date, transactions_data


class TestCalendarProperties:
    """Property-based тесты для логики календаря."""

    @given(data=transactions_list_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_4_calendar_indicators(self, data):
        """
        Property 4: Индикаторы дней календаря.
        
        Validates: Requirements 3.2, 3.7
        
        Проверяет, что get_month_stats корректно агрегирует суммы
        доходов и расходов для каждого дня указанного месяца.
        """
        base_date, tx_list = data
        year, month = base_date.year, base_date.month
        
        with get_test_session() as session:
            # Arrange: Создаем категории
            cat_inc = CategoryDB(name="Inc", type=TransactionType.INCOME)
            cat_exp = CategoryDB(name="Exp", type=TransactionType.EXPENSE)
            session.add_all([cat_inc, cat_exp])
            session.commit()
            
            # Arrange: Вставляем транзакции
            for item in tx_list:
                cat_id = cat_inc.id if item["type"] == TransactionType.INCOME else cat_exp.id
                tx = TransactionDB(
                    amount=item["amount"],
                    type=item["type"],
                    category_id=cat_id,
                    transaction_date=item["date"],
                    description="Test"
                )
                session.add(tx)
            session.commit()
            
            # Act: Запрашиваем статистику за месяц
            stats = get_month_stats(session, year, month)
            
            # Assert: Проверяем корректность подсчета
            # Считаем ожидаемые значения вручную
            expected_stats = {}
            for item in tx_list:
                d = item["date"]
                if d.year == year and d.month == month:
                    day = d.day
                    if day not in expected_stats:
                        expected_stats[day] = {"income": Decimal('0.0'), "expense": Decimal('0.0')}
                    
                    if item["type"] == TransactionType.INCOME:
                        expected_stats[day]["income"] += item["amount"]
                    else:
                        expected_stats[day]["expense"] += item["amount"]
            
            # Сравниваем
            assert len(stats) == len(expected_stats)
            
            for day, (inc, exp) in stats.items():
                assert day in expected_stats
                assert inc == expected_stats[day]["income"]
                assert exp == expected_stats[day]["expense"]

    @given(data=transactions_list_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_5_day_transactions(self, data):
        """
        Property 5: Отображение транзакций дня.
        
        Validates: Requirements 3.3
        
        Проверяет, что get_transactions_by_date возвращает ровно те транзакции,
        которые принадлежат указанной дате.
        """
        target_date, tx_list = data
        
        with get_test_session() as session:
            # Arrange
            cat_inc = CategoryDB(name="Inc", type=TransactionType.INCOME)
            cat_exp = CategoryDB(name="Exp", type=TransactionType.EXPENSE)
            session.add_all([cat_inc, cat_exp])
            session.commit()
            
            # Вставляем
            inserted_ids_for_target = []
            for item in tx_list:
                cat_id = cat_inc.id if item["type"] == TransactionType.INCOME else cat_exp.id
                tx = TransactionDB(
                    amount=item["amount"],
                    type=item["type"],
                    category_id=cat_id,
                    transaction_date=item["date"],
                    description="Test"
                )
                session.add(tx)
                session.flush() # чтобы получить id
                if item["date"] == target_date:
                    inserted_ids_for_target.append(tx.id)
            session.commit()
            
            # Act
            results = get_transactions_by_date(session, target_date)
            result_ids = [t.id for t in results]
            
            # Assert
            assert len(results) == len(inserted_ids_for_target)
            assert set(result_ids) == set(inserted_ids_for_target)
            
            # Проверяем, что нет транзакций за другие даты
            for t in results:
                assert t.transaction_date == target_date

    @given(data=transactions_list_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_9_navigation_logic(self, data):
        """
        Property 9: Навигация между месяцами.
        
        Validates: Requirements 3.7
        
        Проверяет корректность выборки данных при смене месяца/года.
        Имитирует переход на следующий месяц.
        """
        base_date, tx_list = data
        
        # Имитация навигации: следующий месяц
        if base_date.month == 12:
            next_month_year = base_date.year + 1
            next_month_month = 1
        else:
            next_month_year = base_date.year
            next_month_month = base_date.month + 1
            
        with get_test_session() as session:
            # Arrange
            cat = CategoryDB(name="Cat", type=TransactionType.INCOME)
            session.add(cat)
            session.commit()
            
            for item in tx_list:
                tx = TransactionDB(
                    amount=item["amount"],
                    type=item["type"],
                    category_id=cat.id,
                    transaction_date=item["date"]
                )
                session.add(tx)
            session.commit()
            
            # Act: Получаем статистику за "следующий" месяц
            stats = get_month_stats(session, next_month_year, next_month_month)
            
            # Assert
            # Проверяем, что в статистику попали только транзакции следующего месяца
            for day in stats.keys():
                # Проверяем, что действительно есть транзакции за этот день в исходных данных
                # (хотя бы одна)
                has_tx = False
                for item in tx_list:
                    d = item["date"]
                    if d.year == next_month_year and d.month == next_month_month and d.day == day:
                        has_tx = True
                        break
                assert has_tx, f"В статистике есть день {day}, но нет транзакций в данных"
