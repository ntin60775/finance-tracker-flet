"""
Сервис план-факт анализа.

Предоставляет функции для работы с исполнением плановых транзакций
и анализом отклонений между планом и фактом:
- Исполнение плановых вхождений с созданием фактических транзакций
- Пропуск плановых вхождений
- Получение статистики отклонений
- Детальное план-факт сравнение
"""

from typing import Dict, Any, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from models.models import (
    PlannedOccurrenceDB,
    PlannedTransactionDB,
    TransactionDB,
)
from models.enums import (
    OccurrenceStatus
)
from utils.logger import get_logger

# Настройка логирования
logger = get_logger(__name__)


def execute_planned_occurrence(
    session: Session,
    occurrence_id: int,
    actual_amount: Decimal,
    actual_date: date,
    actual_category_id: Optional[int] = None,
    actual_description: Optional[str] = None
) -> Tuple[TransactionDB, PlannedOccurrenceDB]:
    """
    Исполняет плановое вхождение, создавая фактическую транзакцию.
    
    Функция создаёт фактическую транзакцию на основе планового вхождения,
    рассчитывает и сохраняет отклонения от плана (по сумме и дате).
    Статус вхождения изменяется на EXECUTED.
    
    Пользователь может изменить параметры при исполнении:
    - Сумму (отклонение сохраняется в amount_deviation)
    - Дату (отклонение сохраняется в date_deviation)
    - Категорию (если actual_category_id указан)
    - Описание (если actual_description указано)
    
    Args:
        session: Активная сессия БД для выполнения операций
        occurrence_id: ID планового вхождения для исполнения
        actual_amount: Фактическая сумма транзакции
        actual_date: Фактическая дата транзакции
        actual_category_id: ID категории (если отличается от плана)
        actual_description: Описание (если отличается от плана)
    
    Returns:
        Кортеж (созданная фактическая транзакция, обновлённое вхождение)
    
    Raises:
        ValueError: Если вхождение не найдено, уже исполнено, или сумма <= 0
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     # Исполнить вхождение без отклонений
        ...     tx, occ = execute_planned_occurrence(
        ...         session,
        ...         occurrence_id=1,
        ...         actual_amount=Decimal('1000.00'),
        ...         actual_date=date.today()
        ...     )
        ...     
        ...     # Исполнить с отклонением по сумме
        ...     tx, occ = execute_planned_occurrence(
        ...         session,
        ...         occurrence_id=2,
        ...         actual_amount=Decimal('1200.00'),  # План был 1000
        ...         actual_date=date.today()
        ...     )
    """
    # Валидация: сумма должна быть положительной (Fail Fast)
    if actual_amount <= Decimal('0'):
        error_msg = "Сумма должна быть положительной"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Получаем вхождение
        occurrence = session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
        
        # Проверка существования (Fail Fast)
        if not occurrence:
            error_msg = f"Вхождение с ID {occurrence_id} не найдено"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверка статуса (Fail Fast)
        if occurrence.status != OccurrenceStatus.PENDING:
            error_msg = (
                f"Вхождение уже исполнено или пропущено "
                f"(статус: {occurrence.status.value})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Получаем плановую транзакцию для параметров по умолчанию
        planned_tx = occurrence.planned_transaction
        
        # Определяем параметры фактической транзакции
        final_category_id = actual_category_id if actual_category_id else planned_tx.category_id
        final_description = actual_description if actual_description else planned_tx.description
        
        # Создаём фактическую транзакцию
        transaction = TransactionDB(
            amount=actual_amount,
            category_id=final_category_id,
            description=final_description,
            type=planned_tx.type,
            transaction_date=actual_date,
            planned_occurrence_id=occurrence_id
        )
        
        session.add(transaction)
        session.flush()  # Получаем ID транзакции
        
        # Рассчитываем отклонения (они вычисляются автоматически через @property)
        # amount_deviation = actual_amount - planned_tx.amount
        # date_deviation = (actual_date - occurrence.occurrence_date).days
        
        # Обновляем вхождение
        occurrence.status = OccurrenceStatus.EXECUTED
        occurrence.actual_transaction_id = transaction.id
        occurrence.executed_amount = actual_amount
        occurrence.executed_date = actual_date
        # amount_deviation и date_deviation вычисляются автоматически через @property
        
        session.commit()
        session.refresh(transaction)
        session.refresh(occurrence)
        
        logger.info(
            f"Вхождение ID {occurrence_id} исполнено, "
            f"создана транзакция ID {transaction.id}, "
            f"отклонение по сумме: {occurrence.amount_deviation}, "
            f"отклонение по дате: {occurrence.date_deviation} дней"
        )
        
        return transaction, occurrence
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при исполнении вхождения ID {occurrence_id}: {e}"
        logger.error(error_msg)
        raise


def skip_planned_occurrence(
    session: Session,
    occurrence_id: int,
    skip_reason: Optional[str] = None
) -> PlannedOccurrenceDB:
    """
    Отмечает плановое вхождение как пропущенное.
    
    Функция изменяет статус вхождения на SKIPPED и сохраняет причину пропуска
    (если указана). Фактическая транзакция не создаётся.
    
    Args:
        session: Активная сессия БД для выполнения операций
        occurrence_id: ID планового вхождения для пропуска
        skip_reason: Причина пропуска (опционально)
    
    Returns:
        Обновлённое плановое вхождение со статусом SKIPPED
    
    Raises:
        ValueError: Если вхождение не найдено или уже исполнено/пропущено
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     # Пропустить без причины
        ...     occ = skip_planned_occurrence(session, occurrence_id=1)
        ...     
        ...     # Пропустить с причиной
        ...     occ = skip_planned_occurrence(
        ...         session,
        ...         occurrence_id=2,
        ...         skip_reason="Не получил зарплату вовремя"
        ...     )
    """
    try:
        # Получаем вхождение
        occurrence = session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
        
        # Проверка существования (Fail Fast)
        if not occurrence:
            error_msg = f"Вхождение с ID {occurrence_id} не найдено"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверка статуса (Fail Fast)
        if occurrence.status != OccurrenceStatus.PENDING:
            error_msg = (
                f"Вхождение уже исполнено или пропущено "
                f"(статус: {occurrence.status.value})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Обновляем вхождение
        occurrence.status = OccurrenceStatus.SKIPPED
        occurrence.skip_reason = skip_reason
        
        session.commit()
        session.refresh(occurrence)
        
        logger.info(
            f"Вхождение ID {occurrence_id} пропущено"
            f"{f', причина: {skip_reason}' if skip_reason else ''}"
        )
        
        return occurrence
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при пропуске вхождения ID {occurrence_id}: {e}"
        logger.error(error_msg)
        raise


def get_plan_fact_analysis(
    session: Session,
    start_date: date,
    end_date: date,
    category_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Возвращает план-факт анализ за период с статистикой отклонений.
    
    Функция анализирует все плановые вхождения в указанном периоде
    и рассчитывает статистику:
    - Общее количество вхождений
    - Количество исполненных, пропущенных, ожидающих
    - Средние отклонения по сумме и дате
    - Процент исполненных вовремя
    - Процент пропущенных
    
    Можно отфильтровать по категории.
    
    Args:
        session: Активная сессия БД для выполнения запросов
        start_date: Начало периода анализа
        end_date: Конец периода анализа
        category_id: ID категории для фильтрации (опционально)
    
    Returns:
        Словарь с ключами:
        - total_occurrences: общее количество вхождений
        - executed_count: количество исполненных
        - skipped_count: количество пропущенных
        - pending_count: количество ожидающих
        - avg_amount_deviation: среднее отклонение по сумме
        - avg_date_deviation_days: среднее отклонение по дате (в днях)
        - on_time_percentage: процент исполненных вовремя (без отклонения по дате)
        - skipped_percentage: процент пропущенных
        - occurrences: список вхождений с деталями
    
    Raises:
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     # Анализ за последний месяц
        ...     analysis = get_plan_fact_analysis(
        ...         session,
        ...         start_date=date.today() - timedelta(days=30),
        ...         end_date=date.today()
        ...     )
        ...     print(f"Исполнено: {analysis['executed_count']}")
        ...     print(f"Среднее отклонение: {analysis['avg_amount_deviation']}")
    """
    try:
        # Базовый запрос с eager loading связанных данных
        query = session.query(PlannedOccurrenceDB).options(
            joinedload(PlannedOccurrenceDB.planned_transaction).joinedload(PlannedTransactionDB.category)
        ).filter(
            PlannedOccurrenceDB.occurrence_date >= start_date,
            PlannedOccurrenceDB.occurrence_date <= end_date
        )
        
        # Применяем фильтр по категории, если указан
        if category_id is not None:
            query = query.join(PlannedTransactionDB).filter(
                PlannedTransactionDB.category_id == category_id
            )
        
        # Получаем все вхождения
        occurrences = query.all()
        
        # Инициализация статистики
        total_occurrences = len(occurrences)
        executed_count = 0
        skipped_count = 0
        pending_count = 0
        
        total_amount_deviation = Decimal('0.0')
        total_date_deviation_days = 0
        on_time_count = 0
        executed_with_deviation_count = 0
        
        occurrences_list = []
        
        # Обрабатываем каждое вхождение
        for occurrence in occurrences:
            # Подсчёт по статусам
            if occurrence.status == OccurrenceStatus.EXECUTED:
                executed_count += 1
                
                # Суммируем отклонения
                if occurrence.amount_deviation is not None:
                    total_amount_deviation += occurrence.amount_deviation
                    executed_with_deviation_count += 1
                
                if occurrence.date_deviation is not None:
                    total_date_deviation_days += occurrence.date_deviation
                    
                    # Считаем исполненные вовремя (без отклонения по дате)
                    if occurrence.date_deviation == 0:
                        on_time_count += 1
                        
            elif occurrence.status == OccurrenceStatus.SKIPPED:
                skipped_count += 1
            elif occurrence.status == OccurrenceStatus.PENDING:
                pending_count += 1
            
            # Добавляем в список для детального просмотра
            occurrences_list.append({
                "occurrence_id": occurrence.id,
                "planned_transaction_id": occurrence.planned_transaction_id,
                "scheduled_date": occurrence.occurrence_date.isoformat(),
                "status": occurrence.status.value,
                "planned_amount": occurrence.planned_transaction.amount,
                "actual_amount": occurrence.executed_amount,
                "amount_deviation": occurrence.amount_deviation,
                "executed_date": occurrence.executed_date.isoformat() if occurrence.executed_date else None,
                "date_deviation": occurrence.date_deviation,
                "skip_reason": occurrence.skip_reason,
                # Дополнительные поля для детального просмотра
                "category_name": occurrence.planned_transaction.category.name if occurrence.planned_transaction.category else "Без категории",
                "category_id": occurrence.planned_transaction.category_id,
                "description": occurrence.planned_transaction.description,
                "transaction_type": occurrence.planned_transaction.type.value
            })
        
        # Рассчитываем средние значения
        avg_amount_deviation = (
            total_amount_deviation / executed_with_deviation_count
            if executed_with_deviation_count > 0
            else Decimal('0.0')
        )
        
        avg_date_deviation_days = (
            total_date_deviation_days / executed_count
            if executed_count > 0
            else 0.0
        )
        
        # Рассчитываем проценты
        on_time_percentage = (
            (on_time_count / executed_count * 100)
            if executed_count > 0
            else 0.0
        )
        
        skipped_percentage = (
            (skipped_count / total_occurrences * 100)
            if total_occurrences > 0
            else 0.0
        )
        
        # Формируем результат
        analysis = {
            "total_occurrences": total_occurrences,
            "executed_count": executed_count,
            "skipped_count": skipped_count,
            "pending_count": pending_count,
            "avg_amount_deviation": avg_amount_deviation,
            "avg_date_deviation_days": avg_date_deviation_days,
            "on_time_percentage": on_time_percentage,
            "skipped_percentage": skipped_percentage,
            "occurrences": occurrences_list
        }
        
        logger.info(
            f"План-факт анализ за период {start_date} - {end_date}: "
            f"всего {total_occurrences}, исполнено {executed_count}, "
            f"пропущено {skipped_count}, ожидается {pending_count}"
        )
        
        return analysis
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении план-факт анализа: {e}"
        logger.error(error_msg)
        raise


def get_occurrence_details(
    session: Session,
    occurrence_id: int
) -> Dict[str, Any]:
    """
    Возвращает детальную информацию о вхождении с план-факт сравнением.
    
    Функция предоставляет полную информацию о плановом вхождении:
    - Запланированные параметры (сумма, дата, категория)
    - Фактические параметры (если исполнено)
    - Отклонения от плана
    - Статус и причина пропуска (если пропущено)
    
    Args:
        session: Активная сессия БД для выполнения запросов
        occurrence_id: ID планового вхождения
    
    Returns:
        Словарь с ключами:
        - occurrence_id: ID вхождения
        - planned_transaction_id: ID плановой транзакции
        - status: статус вхождения
        - scheduled_date: запланированная дата
        - planned_amount: запланированная сумма
        - category_id: ID категории
        - description: описание
        - executed_date: фактическая дата (если исполнено)
        - actual_amount: фактическая сумма (если исполнено)
        - amount_deviation: отклонение по сумме
        - date_deviation: отклонение по дате в днях
        - skip_reason: причина пропуска (если пропущено)
    
    Raises:
        ValueError: Если вхождение не найдено
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     details = get_occurrence_details(session, occurrence_id=1)
        ...     print(f"Статус: {details['status']}")
        ...     print(f"Отклонение: {details['amount_deviation']}")
    """
    try:
        # Получаем вхождение
        occurrence = session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
        
        # Проверка существования (Fail Fast)
        if not occurrence:
            error_msg = f"Вхождение с ID {occurrence_id} не найдено"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Получаем плановую транзакцию
        planned_tx = occurrence.planned_transaction
        
        # Формируем детали
        details = {
            "occurrence_id": occurrence.id,
            "planned_transaction_id": planned_tx.id,
            "status": occurrence.status.value,
            "scheduled_date": occurrence.occurrence_date.isoformat(),
            "planned_amount": planned_tx.amount,
            "category_id": planned_tx.category_id,
            "description": planned_tx.description,
            "executed_date": occurrence.executed_date.isoformat() if occurrence.executed_date else None,
            "actual_amount": occurrence.executed_amount,
            "amount_deviation": occurrence.amount_deviation,
            "date_deviation": occurrence.date_deviation,
            "skip_reason": occurrence.skip_reason
        }
        
        logger.info(f"Получены детали вхождения ID {occurrence_id}")
        
        return details
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении деталей вхождения ID {occurrence_id}: {e}"
        logger.error(error_msg)
        raise
