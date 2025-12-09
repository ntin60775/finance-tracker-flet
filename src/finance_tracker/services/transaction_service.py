"""
Модуль сервисного слоя для Finance Tracker Flet.

Содержит бизнес-логику и CRUD операции для работы с транзакциями:
- get_transactions_by_date: получение транзакций по дате
- get_by_date_range: получение транзакций за период
- add_transaction: создание новой транзакции с валидацией
- update_transaction: обновление существующей транзакции
- delete_transaction: удаление транзакции с проверкой существования
- get_month_stats: получение статистики по месяцу для календаря

Все функции принимают сессию БД как параметр (Dependency Injection).
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from finance_tracker.models import TransactionDB, TransactionCreate, TransactionType, TransactionUpdate
from finance_tracker.utils.validation import validate_uuid_format


# Настройка логирования
logger = logging.getLogger(__name__)


def get_total_balance(session: Session) -> Decimal:
    """
    Рассчитывает текущий общий баланс (Доходы - Расходы).
    
    Args:
        session: Активная сессия БД
        
    Returns:
        Decimal: Текущий баланс
        
    Raises:
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        logger.debug("Расчёт текущего баланса")
        
        # Получаем все транзакции
        transactions = session.query(TransactionDB).all()
        
        total_income = sum((t.amount for t in transactions if t.type == TransactionType.INCOME), Decimal('0.0'))
        total_expense = sum((t.amount for t in transactions if t.type == TransactionType.EXPENSE), Decimal('0.0'))
        
        balance = total_income - total_expense
        logger.info(f"Текущий баланс: {balance}")
        return balance
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при расчёте баланса: {e}")
        raise


def get_transactions_by_date(session: Session, target_date: date) -> List[TransactionDB]:
    """
    Получает все транзакции для указанной даты.
    
    Args:
        session: Активная сессия БД
        target_date: Дата для фильтрации транзакций
        
    Returns:
        Список транзакций для указанной даты (может быть пустым)
        
    Raises:
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        logger.debug(f"Получение транзакций для даты: {target_date}")
        
        transactions = session.query(TransactionDB).filter(
            TransactionDB.transaction_date == target_date
        ).all()
        
        logger.info(f"Найдено {len(transactions)} транзакций для {target_date}")
        return transactions
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении транзакций для {target_date}: {e}")
        raise


def get_by_date_range(session: Session, start_date: date, end_date: date) -> List[TransactionDB]:
    """
    Получает транзакции за указанный период (включительно).

    Args:
        session: Активная сессия БД
        start_date: Дата начала периода
        end_date: Дата окончания периода

    Returns:
        Список транзакций за период
        
    Raises:
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        logger.debug(f"Получение транзакций за период: {start_date} - {end_date}")
        
        transactions = session.query(TransactionDB).filter(
            TransactionDB.transaction_date >= start_date,
            TransactionDB.transaction_date <= end_date
        ).order_by(TransactionDB.transaction_date).all()
        
        logger.info(f"Найдено {len(transactions)} транзакций за период {start_date} - {end_date}")
        return transactions
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении транзакций за период: {e}")
        raise


def create_transaction(session: Session, transaction: TransactionCreate) -> TransactionDB:
    """
    Создаёт новую транзакцию с валидацией данных.
    
    Args:
        session: Активная сессия БД
        transaction: Данные для создания транзакции (Pydantic модель)
        
    Returns:
        Созданная транзакция с заполненным ID и created_at
        
    Raises:
        ValidationError: Если данные не прошли валидацию Pydantic
        ValueError: Если данные невалидны на уровне бизнес-логики
        SQLAlchemyError: При ошибках записи в базу данных
    """
    try:
        logger.debug(f"Создание новой транзакции: {transaction.amount}, cat_id={transaction.category_id}")
        
        # Дополнительная валидация на уровне сервиса
        if transaction.amount <= Decimal('0'):
            error_msg = "Сумма должна быть положительным числом"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        validate_uuid_format(transaction.category_id, "category_id")
        
        # Создаём объект БД из Pydantic модели
        db_transaction = TransactionDB(**transaction.model_dump())
        
        # Добавляем в сессию и сохраняем
        session.add(db_transaction)
        session.commit()
        session.refresh(db_transaction)
        
        logger.info(f"Транзакция успешно создана с ID: {db_transaction.id}")
        return db_transaction
        
    except ValidationError as e:
        logger.error(f"Ошибка валидации данных транзакции: {e}")
        session.rollback()
        raise
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при сохранении транзакции в БД: {e}")
        session.rollback()
        raise ValueError(f"Ошибка при сохранении транзакции: {e}")
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании транзакции: {e}")
        session.rollback()
        raise


def update_transaction(
    session: Session, 
    transaction_id: str, 
    transaction: TransactionUpdate
) -> Optional[TransactionDB]:
    """
    Обновляет существующую транзакцию.
    
    Args:
        session: Активная сессия БД
        transaction_id: ID транзакции для обновления (UUID)
        transaction: Новые данные транзакции (Pydantic модель)
        
    Returns:
        Обновлённая транзакция или None, если транзакция не найдена
        
    Raises:
        ValidationError: Если данные не прошли валидацию Pydantic
        ValueError: Если данные невалидны на уровне бизнес-логики
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        validate_uuid_format(transaction_id, "transaction_id")
        logger.debug(f"Обновление транзакции ID: {transaction_id}")
        
        # Ищем транзакцию
        db_transaction = session.query(TransactionDB).filter_by(
            id=transaction_id
        ).first()
        
        if not db_transaction:
            logger.warning(f"Транзакция с ID {transaction_id} не найдена")
            return None
        
        # Обновляем поля, если они предоставлены
        if transaction.amount is not None:
            if transaction.amount <= Decimal('0'):
                raise ValueError("Сумма должна быть положительной")
            db_transaction.amount = transaction.amount
            
        if transaction.category_id is not None:
            validate_uuid_format(transaction.category_id, "category_id")
            db_transaction.category_id = transaction.category_id
            
        if transaction.description is not None:
            db_transaction.description = transaction.description
            
        if transaction.type is not None:
            db_transaction.type = transaction.type
            
        if transaction.transaction_date is not None:
            db_transaction.transaction_date = transaction.transaction_date
        
        # Сохраняем изменения
        session.commit()
        session.refresh(db_transaction)
        
        logger.info(f"Транзакция ID {transaction_id} успешно обновлена")
        return db_transaction
        
    except ValidationError as e:
        logger.error(f"Ошибка валидации данных при обновлении: {e}")
        session.rollback()
        raise
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при обновлении транзакции в БД: {e}")
        session.rollback()
        raise ValueError(f"Ошибка при обновлении транзакции: {e}")
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обновлении транзакции: {e}")
        session.rollback()
        raise


def delete_transaction(session: Session, transaction_id: str) -> bool:
    """
    Удаляет транзакцию с проверкой существования.
    
    Args:
        session: Активная сессия БД
        transaction_id: ID транзакции для удаления (UUID)
        
    Returns:
        True если транзакция успешно удалена, False если не найдена
        
    Raises:
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        validate_uuid_format(transaction_id, "transaction_id")
        logger.debug(f"Удаление транзакции ID: {transaction_id}")
        
        # Ищем транзакцию
        db_transaction = session.query(TransactionDB).filter_by(
            id=transaction_id
        ).first()
        
        if not db_transaction:
            logger.warning(f"Транзакция с ID {transaction_id} не найдена для удаления")
            return False
        
        # Удаляем транзакцию
        session.delete(db_transaction)
        session.commit()
        
        logger.info(f"Транзакция ID {transaction_id} успешно удалена")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при удалении транзакции из БД: {e}")
        session.rollback()
        raise


def get_month_stats(session: Session, year: int, month: int) -> Dict[int, Tuple[Decimal, Decimal]]:
    """
    Получает статистику транзакций по дням месяца для отображения в календаре.
    
    Для каждого дня месяца вычисляет суммарные доходы и расходы.
    Используется для визуальных индикаторов в календаре.
    
    Args:
        session: Активная сессия БД
        year: Год (например, 2024)
        month: Месяц (1-12)
        
    Returns:
        Словарь {день: (доходы, расходы)}, где:
        - день: номер дня месяца (1-31)
        - доходы: суммарные доходы за день
        - расходы: суммарные расходы за день
        
    Raises:
        ValueError: Если месяц не в диапазоне 1-12
        SQLAlchemyError: При ошибках работы с базой данных
    """
    try:
        # Валидация входных параметров
        if not 1 <= month <= 12:
            error_msg = f"Месяц должен быть в диапазоне 1-12, получено: {month}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Получение статистики для {year}-{month:02d}")
        
        # Определяем границы месяца
        start_date = date(year, month, 1)
        
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Получаем все транзакции месяца
        transactions = session.query(TransactionDB).filter(
            TransactionDB.transaction_date >= start_date,
            TransactionDB.transaction_date < end_date
        ).all()
        
        # Группируем по дням
        stats: Dict[int, Tuple[Decimal, Decimal]] = {}
        
        for transaction in transactions:
            day = transaction.transaction_date.day
            
            # Инициализируем день, если его ещё нет
            if day not in stats:
                stats[day] = (Decimal('0.0'), Decimal('0.0'))
            
            # Добавляем сумму к доходам или расходам
            income, expense = stats[day]
            
            if transaction.type == TransactionType.INCOME:
                stats[day] = (income + transaction.amount, expense)
            else:  # TransactionType.EXPENSE
                stats[day] = (income, expense + transaction.amount)
        
        logger.info(f"Статистика для {year}-{month:02d}: {len(stats)} дней с транзакциями")
        return stats
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении статистики месяца: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении статистики: {e}")
        raise
