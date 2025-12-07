"""
Property-based тесты для проверки производительности.
Проверяют время выполнения ключевых операций.
"""

from datetime import date
import time
import pytest
from services.transaction_service import get_total_balance, get_month_stats
from models import TransactionDB, TransactionType

def test_initialization_performance():
    """
    Property 58: Время инициализации приложения (импорт и создание конфигурации).
    Feature: Performance
    """
    start_time = time.time()
    
    # Импортируем основные модули (имитация запуска)
    import config
    import database
    import models
    
    # Создаем конфигурацию
    finance_tracker_flet.config.Config()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Инициализация должна быть быстрее 1 секунды
    assert duration < 1.0, f"Initialization took too long: {duration:.4f}s"

def test_transaction_query_performance(db_session: Session):
    """
    Property 59: Время выполнения запросов к БД (баланс и статистика).
    Feature: Performance
    """
    # Подготовка: создаем 1000 транзакций (если их нет)
    if db_session.query(TransactionDB).count() < 1000:
        transactions = []
        for i in range(1000):
            transactions.append(TransactionDB(
                amount=100.0,
                type=TransactionType.EXPENSE,
                category_id=1,
                transaction_date=date(2023, 1, 1)
            ))
        db_session.add_all(transactions)
        db_session.commit()
    
    # Замер времени получения баланса
    start_time = time.time()
    get_total_balance(db_session)
    balance_duration = time.time() - start_time
    
    # Замер времени получения статистики за месяц
    start_time = time.time()
    get_month_stats(db_session, 2023, 1)
    stats_duration = time.time() - start_time
    
    # Проверки (пороги могут быть настроены под конкретное железо)
    # Баланс должен считаться очень быстро (агрегация)
    assert balance_duration < 0.1, f"Balance calculation too slow: {balance_duration:.4f}s"
    
    # Статистика за месяц тоже должна быть быстрой
    assert stats_duration < 0.2, f"Month stats calculation too slow: {stats_duration:.4f}s"
