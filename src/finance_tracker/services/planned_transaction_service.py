"""
Сервис управления плановыми транзакциями.

Предоставляет функции для работы с плановыми транзакциями:
- Создание плановых транзакций (однократных и периодических)
- Обновление шаблонов с применением изменений к будущим вхождениям
- Деактивация плановых транзакций
- Удаление плановых транзакций с опцией удаления связанных фактических транзакций
- Получение списка плановых транзакций с фильтрацией
"""

import logging
from typing import List, Optional
from datetime import date
from calendar import monthrange
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.models.models import (
    PlannedTransactionDB,
    PlannedTransactionCreate,
    RecurrenceRuleDB,
    PlannedOccurrenceDB,
    TransactionDB,
    CategoryDB
)
from finance_tracker.models.enums import (
    TransactionType,
    OccurrenceStatus
)
from finance_tracker.utils.validation import validate_uuid_format
from finance_tracker.services.recurrence_service import generate_occurrences_for_period

# Настройка логирования
logger = logging.getLogger(__name__)


def create_planned_transaction(
    session: Session,
    planned_tx: PlannedTransactionCreate,
    target_month: Optional[date] = None
) -> PlannedTransactionDB:
    """
    Создаёт плановую транзакцию (однократную или периодическую) с валидацией.
    
    Функция создаёт шаблон плановой транзакции в БД и автоматически создаёт вхождения
    от start_date до target_month (или до текущего месяца, если target_month не указан).
    Если указано правило повторения, создаётся периодическая транзакция, иначе — однократная.
    
    Выполняется валидация:
    - Категория должна существовать в справочнике
    - Сумма должна быть положительной (проверяется Pydantic)
    - Дата начала не может быть в прошлом (опционально)
    
    Args:
        session: Активная сессия БД для выполнения операций
        planned_tx: Данные для создания плановой транзакции (Pydantic модель)
        target_month: Дата, определяющая до какого месяца создавать вхождения.
                     Если None, используется текущий месяц.
    
    Returns:
        Созданный объект PlannedTransactionDB с заполненным id
    
    Raises:
        ValueError: Если категория не найдена или данные некорректны
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     # Создать однократную плановую транзакцию
        ...     planned_tx_data = PlannedTransactionCreate(
        ...         amount=5000.0,
        ...         category_id=1,
        ...         description="Премия",
        ...         type=TransactionType.INCOME,
        ...         start_date=date(2025, 2, 1)
        ...     )
        ...     planned_tx = create_planned_transaction(session, planned_tx_data)
        ...     print(f"Создана плановая транзакция ID {planned_tx.id}")
        ...     
        ...     # Создать с указанием целевого месяца
        ...     planned_tx = create_planned_transaction(
        ...         session, 
        ...         planned_tx_data,
        ...         target_month=date(2025, 3, 1)
        ...     )
    """
    # Валидация: проверка существования категории (Fail Fast)
    validate_uuid_format(planned_tx.category_id, "category_id")
    category = session.query(CategoryDB).filter_by(id=planned_tx.category_id).first()
    if not category:
        error_msg = f"Категория с ID {planned_tx.category_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Создание плановой транзакции
        new_planned_tx = PlannedTransactionDB(
            amount=planned_tx.amount,
            category_id=planned_tx.category_id,
            description=planned_tx.description,
            type=planned_tx.type,
            start_date=planned_tx.start_date,
            end_date=planned_tx.end_date,
            is_active=True
        )
        
        session.add(new_planned_tx)
        session.flush()  # Получаем ID для создания правила повторения
        
        # Если есть правило повторения, создаём его
        if planned_tx.recurrence_rule:
            recurrence_rule = RecurrenceRuleDB(
                planned_transaction_id=new_planned_tx.id,
                recurrence_type=planned_tx.recurrence_rule.recurrence_type,
                interval=planned_tx.recurrence_rule.interval,
                interval_unit=planned_tx.recurrence_rule.interval_unit,
                weekdays=None,  # TODO: сериализация списка дней недели
                only_workdays=planned_tx.recurrence_rule.only_workdays,
                end_condition_type=planned_tx.recurrence_rule.end_condition_type,
                end_date=planned_tx.recurrence_rule.end_date,
                occurrences_count=planned_tx.recurrence_rule.occurrences_count
            )
            session.add(recurrence_rule)
            session.flush()  # Сохраняем правило повторения для генерации вхождений
        
        # Определяем период для создания вхождений
        if target_month is None:
            # Используем текущий месяц
            today = date.today()
            target_month = date(today.year, today.month, 1)
        
        # Определяем конец периода (последний день целевого месяца)
        last_day = monthrange(target_month.year, target_month.month)[1]
        period_end = date(target_month.year, target_month.month, last_day)
        
        # Определяем начало периода
        # Если start_date в прошлом, создаём вхождения начиная с start_date
        # Если start_date в будущем, создаём вхождения начиная с start_date до целевого месяца
        period_start = planned_tx.start_date
        
        # Если есть end_date и он раньше period_end, используем его
        if planned_tx.end_date and planned_tx.end_date < period_end:
            period_end = planned_tx.end_date
        
        # Генерируем даты вхождений для периода
        occurrence_dates = generate_occurrences_for_period(
            session,
            new_planned_tx,
            period_start,
            period_end
        )
        
        # Создаём вхождения в БД
        created_occurrences_count = 0
        for scheduled_date in occurrence_dates:
            # Проверяем, существует ли уже вхождение (для идемпотентности)
            existing_occurrence = session.query(PlannedOccurrenceDB).filter_by(
                planned_transaction_id=new_planned_tx.id,
                occurrence_date=scheduled_date
            ).first()
            
            if not existing_occurrence:
                new_occurrence = PlannedOccurrenceDB(
                    planned_transaction_id=new_planned_tx.id,
                    occurrence_date=scheduled_date,
                    amount=new_planned_tx.amount,
                    status=OccurrenceStatus.PENDING
                )
                session.add(new_occurrence)
                created_occurrences_count += 1
        
        session.commit()
        session.refresh(new_planned_tx)
        
        logger.info(
            f"Создана {'периодическая' if planned_tx.recurrence_rule else 'однократная'} "
            f"плановая транзакция ID {new_planned_tx.id}, "
            f"сумма {planned_tx.amount}, категория ID {planned_tx.category_id}, "
            f"создано {created_occurrences_count} вхождений для периода {period_start} - {period_end}"
        )
        
        return new_planned_tx
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании плановой транзакции: {e}"
        logger.error(error_msg)
        raise


def update_planned_transaction(
    session: Session,
    planned_tx_id: str,
    planned_tx: PlannedTransactionCreate
) -> Optional[PlannedTransactionDB]:
    """
    Обновляет шаблон плановой транзакции с применением изменений к будущим вхождениям.
    
    Функция обновляет параметры шаблона плановой транзакции. Изменения применяются
    только к будущим неисполненным вхождениям. Исполненные и пропущенные вхождения
    остаются без изменений для сохранения истории.
    
    Args:
        session: Активная сессия БД для выполнения операций
        planned_tx_id: ID плановой транзакции для обновления (UUID)
        planned_tx: Новые данные для плановой транзакции
    
    Returns:
        Обновлённый объект PlannedTransactionDB или None, если транзакция не найдена
    
    Raises:
        ValueError: Если плановая транзакция не найдена или категория не существует
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     updated_data = PlannedTransactionCreate(
        ...         amount=6000.0,  # Новая сумма
        ...         category_id=1,
        ...         description="Обновлённое описание",
        ...         type=TransactionType.INCOME,
        ...         start_date=date(2025, 2, 1)
        ...     )
        ...     updated_tx = update_planned_transaction(session, 1, updated_data)
    """
    validate_uuid_format(planned_tx_id, "planned_tx_id")
    
    # Валидация: проверка существования плановой транзакции (Fail Fast)
    existing_tx = session.query(PlannedTransactionDB).filter_by(id=planned_tx_id).first()
    if not existing_tx:
        error_msg = f"Плановая транзакция с ID {planned_tx_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Валидация: проверка существования категории (Fail Fast)
    validate_uuid_format(planned_tx.category_id, "category_id")
    category = session.query(CategoryDB).filter_by(id=planned_tx.category_id).first()
    if not category:
        error_msg = f"Категория с ID {planned_tx.category_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Обновляем поля шаблона
        existing_tx.amount = planned_tx.amount
        existing_tx.category_id = planned_tx.category_id
        existing_tx.description = planned_tx.description
        existing_tx.type = planned_tx.type
        existing_tx.start_date = planned_tx.start_date
        existing_tx.end_date = planned_tx.end_date
        
        # Обновляем правило повторения, если оно есть
        if planned_tx.recurrence_rule and existing_tx.recurrence_rule:
            existing_tx.recurrence_rule.recurrence_type = planned_tx.recurrence_rule.recurrence_type
            existing_tx.recurrence_rule.interval = planned_tx.recurrence_rule.interval
            existing_tx.recurrence_rule.interval_unit = planned_tx.recurrence_rule.interval_unit
            existing_tx.recurrence_rule.only_workdays = planned_tx.recurrence_rule.only_workdays
            existing_tx.recurrence_rule.end_condition_type = planned_tx.recurrence_rule.end_condition_type
            existing_tx.recurrence_rule.end_date = planned_tx.recurrence_rule.end_date
            existing_tx.recurrence_rule.occurrences_count = planned_tx.recurrence_rule.occurrences_count
        
        # Примечание: будущие неисполненные вхождения будут пересчитаны при следующей генерации
        # Исполненные вхождения остаются без изменений
        
        session.commit()
        session.refresh(existing_tx)
        
        logger.info(
            f"Обновлена плановая транзакция ID {planned_tx_id}, "
            f"новая сумма {planned_tx.amount}"
        )
        
        return existing_tx
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении плановой транзакции ID {planned_tx_id}: {e}"
        logger.error(error_msg)
        raise


def deactivate_planned_transaction(
    session: Session,
    planned_tx_id: str
) -> bool:
    """
    Деактивирует плановую транзакцию (прекращает генерацию вхождений).
    
    Функция устанавливает флаг is_active=False для плановой транзакции.
    Деактивированная транзакция не будет генерировать новые вхождения,
    но сохранит историю исполненных вхождений.
    
    Args:
        session: Активная сессия БД для выполнения операций
        planned_tx_id: ID плановой транзакции для деактивации (UUID)
    
    Returns:
        True, если транзакция успешно деактивирована
    
    Raises:
        ValueError: Если плановая транзакция не найдена
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     success = deactivate_planned_transaction(session, 1)
        ...     if success:
        ...         print("Плановая транзакция деактивирована")
    """
    validate_uuid_format(planned_tx_id, "planned_tx_id")
    
    # Валидация: проверка существования плановой транзакции (Fail Fast)
    planned_tx = session.query(PlannedTransactionDB).filter_by(id=planned_tx_id).first()
    if not planned_tx:
        error_msg = f"Плановая транзакция с ID {planned_tx_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Деактивируем транзакцию
        planned_tx.is_active = False
        
        session.commit()
        
        logger.info(f"Деактивирована плановая транзакция ID {planned_tx_id}")
        
        return True
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при деактивации плановой транзакции ID {planned_tx_id}: {e}"
        logger.error(error_msg)
        raise


def delete_planned_transaction(
    session: Session,
    planned_tx_id: str,
    delete_actual_transactions: bool = False
) -> bool:
    """
    Удаляет плановую транзакцию с опцией удаления связанных фактических транзакций.
    
    Функция удаляет плановую транзакцию и все её вхождения из БД.
    Можно выбрать, удалять ли связанные фактические транзакции:
    - delete_actual_transactions=False: фактические транзакции сохраняются,
      но ссылка на плановое вхождение очищается
    - delete_actual_transactions=True: фактические транзакции удаляются вместе с планом
    
    Args:
        session: Активная сессия БД для выполнения операций
        planned_tx_id: ID плановой транзакции для удаления (UUID)
        delete_actual_transactions: Удалять ли связанные фактические транзакции
    
    Returns:
        True, если транзакция успешно удалена
    
    Raises:
        ValueError: Если плановая транзакция не найдена
        SQLAlchemyError: При ошибках работы с БД
    
    Example:
        >>> with get_db_session() as session:
        ...     # Удалить план, но сохранить фактические транзакции
        ...     success = delete_planned_transaction(session, 1, delete_actual_transactions=False)
        ...     
        ...     # Удалить план И все фактические транзакции
        ...     success = delete_planned_transaction(session, 2, delete_actual_transactions=True)
    """
    validate_uuid_format(planned_tx_id, "planned_tx_id")
    
    # Валидация: проверка существования плановой транзакции (Fail Fast)
    planned_tx = session.query(PlannedTransactionDB).filter_by(id=planned_tx_id).first()
    if not planned_tx:
        error_msg = f"Плановая транзакция с ID {planned_tx_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Получаем все вхождения плановой транзакции
        occurrences = session.query(PlannedOccurrenceDB).filter_by(
            planned_transaction_id=planned_tx_id
        ).all()
        
        # Получаем все фактические транзакции, связанные с вхождениями
        occurrence_ids = [occ.id for occ in occurrences]
        actual_transactions = session.query(TransactionDB).filter(
            TransactionDB.planned_occurrence_id.in_(occurrence_ids)
        ).all()
        
        # Обрабатываем связанные фактические транзакции
        for actual_tx in actual_transactions:
            if delete_actual_transactions:
                # Удаляем фактическую транзакцию
                session.delete(actual_tx)
                logger.debug(f"Удалена фактическая транзакция ID {actual_tx.id}")
            else:
                # Очищаем ссылку на плановое вхождение
                actual_tx.planned_occurrence_id = None
                logger.debug(f"Очищена ссылка на плановое вхождение для транзакции ID {actual_tx.id}")
        
        # Удаляем все вхождения
        for occurrence in occurrences:
            session.delete(occurrence)
        
        # Удаляем правило повторения, если есть
        if planned_tx.recurrence_rule:
            session.delete(planned_tx.recurrence_rule)
        
        # Удаляем саму плановую транзакцию
        session.delete(planned_tx)
        
        session.commit()
        
        logger.info(
            f"Удалена плановая транзакция ID {planned_tx_id}, "
            f"{'с удалением' if delete_actual_transactions else 'с сохранением'} "
            f"фактических транзакций"
        )
        
        return True
        
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при удалении плановой транзакции ID {planned_tx_id}: {e}"
        logger.error(error_msg)
        raise


def get_all_planned_transactions(
    session: Session,
    active_only: bool = True,
    transaction_type: Optional[TransactionType] = None
) -> List[PlannedTransactionDB]:
    """
    Получает список всех плановых транзакций с фильтрацией.
    
    Функция возвращает список плановых транзакций с возможностью фильтрации
    по статусу активности и типу транзакции.
    
    Args:
        session: Активная сессия БД для выполнения запросов
        active_only: Возвращать только активные транзакции (по умолчанию True)
        transaction_type: Фильтр по типу транзакции (INCOME или EXPENSE).
                         Если None, возвращаются все типы.
    
    Returns:
        Список объектов PlannedTransactionDB, отсортированных по дате начала.
        Список может быть пустым, если транзакций нет.
    
    Raises:
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        # Базовый запрос
        query = session.query(PlannedTransactionDB)
        
        # Применяем фильтр по активности
        if active_only:
            query = query.filter(PlannedTransactionDB.is_active)
        
        # Применяем фильтр по типу, если указан
        if transaction_type is not None:
            query = query.filter(PlannedTransactionDB.type == transaction_type)
        
        # Сортируем по дате начала
        query = query.order_by(PlannedTransactionDB.start_date)
        
        # Выполняем запрос
        transactions = query.all()
        
        logger.info(
            f"Получено {len(transactions)} плановых транзакций "
            f"({'только активные' if active_only else 'все'})"
            f"{f', тип {transaction_type.value}' if transaction_type else ''}"
        )
        
        return transactions
        
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении списка плановых транзакций: {e}"
        logger.error(error_msg)
        raise


def get_occurrences_by_date(
    session: Session,
    occurrence_date: date
) -> List[PlannedOccurrenceDB]:
    """
    Получает список плановых вхождений на конкретную дату.

    Args:
        session: Активная сессия БД
        occurrence_date: Дата для поиска вхождений

    Returns:
        Список объектов PlannedOccurrenceDB
    """
    try:
        occurrences = session.query(PlannedOccurrenceDB).filter_by(
            occurrence_date=occurrence_date
        ).all()
        return occurrences
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении вхождений на дату {occurrence_date}: {e}")
        return []


def get_pending_occurrences(
    session: Session,
    limit: int = 5
) -> List[PlannedOccurrenceDB]:
    """
    Получает список ближайших ожидающих исполнения вхождений.
    
    Возвращает вхождения со статусом PENDING, отсортированные по дате (сначала старые).
    
    Args:
        session: Активная сессия БД
        limit: Максимальное количество возвращаемых записей
        
    Returns:
        Список объектов PlannedOccurrenceDB
    """
    try:
        occurrences = session.query(PlannedOccurrenceDB).filter(
            PlannedOccurrenceDB.status == OccurrenceStatus.PENDING
        ).order_by(
            PlannedOccurrenceDB.occurrence_date
        ).limit(limit).all()
        
        return occurrences
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении ожидающих вхождений: {e}")
        return []


def execute_occurrence(
    session: Session,
    occurrence_id: str,
    execution_date: date,
    amount: Decimal
) -> TransactionDB:
    """
    Исполняет плановое вхождение, создавая фактическую транзакцию.
    
    Args:
        session: Активная сессия БД
        occurrence_id: ID вхождения (UUID)
        execution_date: Дата фактического исполнения
        amount: Фактическая сумма
        
    Returns:
        Созданная транзакция (TransactionDB)
    """
    validate_uuid_format(occurrence_id, "occurrence_id")
    
    occurrence = session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
    if not occurrence:
        raise ValueError(f"Вхождение {occurrence_id} не найдено")
        
    if occurrence.status == OccurrenceStatus.EXECUTED:
        raise ValueError(f"Вхождение {occurrence_id} уже исполнено")
        
    planned_tx = occurrence.planned_transaction
    
    # Создаем транзакцию
    transaction = TransactionDB(
        amount=amount,
        category_id=planned_tx.category_id,
        description=f"{planned_tx.description} (Плановый)",
        type=planned_tx.type,
        date=execution_date,
        planned_occurrence_id=occurrence.id
    )
    session.add(transaction)
    session.flush()  # Get ID
    
    # Обновляем статус вхождения
    occurrence.status = OccurrenceStatus.EXECUTED
    occurrence.executed_date = execution_date
    occurrence.executed_amount = amount
    occurrence.actual_transaction_id = transaction.id
    
    session.commit()
    session.refresh(transaction)
    session.refresh(occurrence)
    
    # Если это было однократное вхождение без повторений, можно пометить саму транзакцию как завершенную?
    # Пока оставляем как есть, is_active влияет на генерацию новых.
    
    logger.info(f"Исполнено плановое вхождение {occurrence_id}, создана транзакция")
    return transaction


def skip_occurrence(
    session: Session,
    occurrence_id: str
) -> PlannedOccurrenceDB:
    """
    Пропускает плановое вхождение.
    
    Args:
        session: Активная сессия БД
        occurrence_id: ID вхождения (UUID)
        
    Returns:
        Обновленное вхождение
    """
    validate_uuid_format(occurrence_id, "occurrence_id")
    
    occurrence = session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
    if not occurrence:
        raise ValueError(f"Вхождение {occurrence_id} не найдено")
        
    occurrence.status = OccurrenceStatus.SKIPPED
    occurrence.skipped_date = date.today()
    
    logger.info(f"Пропущено плановое вхождение {occurrence_id}")
    return occurrence


def get_occurrences_by_date_range(
    session: Session,
    start_date: date,
    end_date: date
) -> List[PlannedOccurrenceDB]:
    """
    Получает список плановых вхождений за период.

    Args:
        session: Активная сессия БД
        start_date: Начало периода
        end_date: Конец периода

    Returns:
        Список объектов PlannedOccurrenceDB
    """
    try:
        occurrences = session.query(PlannedOccurrenceDB).filter(
            PlannedOccurrenceDB.occurrence_date >= start_date,
            PlannedOccurrenceDB.occurrence_date <= end_date
        ).all()
        return occurrences
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении вхождений за период {start_date} - {end_date}: {e}")
        return []