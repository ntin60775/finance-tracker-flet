"""
Сервис генерации вхождений для периодических плановых транзакций.

Содержит функции для:
- Проверки рабочих дней
- Вычисления следующей даты вхождения
- Генерации дат вхождений для периода
- Ленивой генерации вхождений
"""

import json
import logging
from datetime import date, timedelta
from typing import List, Optional
from calendar import monthrange

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.models import (
    PlannedTransactionDB,
    RecurrenceRuleDB,
    PlannedOccurrenceDB
)
from models.enums import (
    RecurrenceType,
    IntervalUnit,
    EndConditionType,
    OccurrenceStatus
)

# Настройка логирования
logger = logging.getLogger(__name__)


def is_workday(target_date: date) -> bool:
    """
    Проверяет, является ли дата рабочим днём (понедельник-пятница).
    
    Args:
        target_date: Дата для проверки
        
    Returns:
        True, если дата является рабочим днём (пн-пт), False для выходных (сб-вс)
        
    Example:
        >>> is_workday(date(2025, 1, 6))  # Понедельник
        True
        >>> is_workday(date(2025, 1, 11))  # Суббота
        False
    """
    # weekday() возвращает 0 для понедельника, 6 для воскресенья
    return target_date.weekday() < 5


def calculate_next_occurrence_date(
    current_date: date,
    recurrence_rule: RecurrenceRuleDB
) -> Optional[date]:
    """
    Вычисляет следующую дату вхождения на основе правила повторения.
    
    Функция учитывает тип повторения, интервал, дни недели и опцию "только рабочие дни".
    
    Args:
        current_date: Текущая дата вхождения
        recurrence_rule: Правило повторения с настройками
        
    Returns:
        Следующая дата вхождения или None, если правило не определено
        
    Raises:
        ValueError: Если тип повторения неизвестен
        
    Example:
        >>> rule = RecurrenceRuleDB(recurrence_type=RecurrenceType.DAILY, interval=1)
        >>> calculate_next_occurrence_date(date(2025, 1, 1), rule)
        date(2025, 1, 2)
    """
    if recurrence_rule.recurrence_type == RecurrenceType.DAILY:
        # Ежедневное повторение
        next_date = current_date + timedelta(days=recurrence_rule.interval)
        
        # Если включена опция "только рабочие дни", пропускаем выходные
        if recurrence_rule.only_workdays:
            while not is_workday(next_date):
                next_date += timedelta(days=1)
        
        return next_date
    
    elif recurrence_rule.recurrence_type == RecurrenceType.WEEKLY:
        # Еженедельное повторение
        next_date = current_date + timedelta(weeks=recurrence_rule.interval)
        
        # Если включена опция "только рабочие дни", пропускаем выходные
        if recurrence_rule.only_workdays:
            while not is_workday(next_date):
                next_date += timedelta(days=1)
        
        return next_date
    
    elif recurrence_rule.recurrence_type == RecurrenceType.MONTHLY:
        # Ежемесячное повторение
        # Получаем исходный день из плановой транзакции
        planned_tx = recurrence_rule.planned_transaction
        original_day = planned_tx.start_date.day
        
        # Вычисляем следующий месяц
        year = current_date.year
        month = current_date.month + recurrence_rule.interval
        
        # Корректируем год, если месяц выходит за пределы
        while month > 12:
            month -= 12
            year += 1
        
        # Обрабатываем граничный случай: если день больше количества дней в месяце
        max_day_in_month = monthrange(year, month)[1]
        day = min(original_day, max_day_in_month)
        
        next_date = date(year, month, day)
        
        # Если включена опция "только рабочие дни", пропускаем выходные
        if recurrence_rule.only_workdays:
            while not is_workday(next_date):
                next_date += timedelta(days=1)
        
        return next_date
    
    elif recurrence_rule.recurrence_type == RecurrenceType.YEARLY:
        # Ежегодное повторение
        # Получаем исходный день из плановой транзакции
        planned_tx = recurrence_rule.planned_transaction
        original_day = planned_tx.start_date.day
        original_month = planned_tx.start_date.month
        
        year = current_date.year + recurrence_rule.interval
        month = original_month
        
        # Обрабатываем граничный случай: 29 февраля в невисокосном году
        max_day_in_month = monthrange(year, month)[1]
        day = min(original_day, max_day_in_month)
        
        next_date = date(year, month, day)
        
        # Если включена опция "только рабочие дни", пропускаем выходные
        if recurrence_rule.only_workdays:
            while not is_workday(next_date):
                next_date += timedelta(days=1)
        
        return next_date
    
    elif recurrence_rule.recurrence_type == RecurrenceType.CUSTOM:
        # Кастомное правило повторения
        if recurrence_rule.interval_unit == IntervalUnit.DAYS:
            next_date = current_date + timedelta(days=recurrence_rule.interval)
        elif recurrence_rule.interval_unit == IntervalUnit.WEEKS:
            # Если указаны конкретные дни недели
            if recurrence_rule.weekdays:
                weekdays = json.loads(recurrence_rule.weekdays)
                current_weekday = current_date.weekday()
                
                # Ищем следующий день недели из списка
                next_weekday = None
                for wd in weekdays:
                    if wd > current_weekday:
                        next_weekday = wd
                        break
                
                if next_weekday is not None:
                    # Следующий день в текущей неделе
                    days_ahead = next_weekday - current_weekday
                    next_date = current_date + timedelta(days=days_ahead)
                else:
                    # Переходим к следующей неделе (или через N недель)
                    days_ahead = (7 * recurrence_rule.interval) - current_weekday + weekdays[0]
                    next_date = current_date + timedelta(days=days_ahead)
            else:
                # Просто добавляем N недель
                next_date = current_date + timedelta(weeks=recurrence_rule.interval)
        elif recurrence_rule.interval_unit == IntervalUnit.MONTHS:
            # Аналогично ежемесячному повторению
            planned_tx = recurrence_rule.planned_transaction
            original_day = planned_tx.start_date.day
            
            year = current_date.year
            month = current_date.month + recurrence_rule.interval
            
            while month > 12:
                month -= 12
                year += 1
            
            max_day_in_month = monthrange(year, month)[1]
            day = min(original_day, max_day_in_month)
            
            next_date = date(year, month, day)
        elif recurrence_rule.interval_unit == IntervalUnit.YEARS:
            # Аналогично ежегодному повторению
            planned_tx = recurrence_rule.planned_transaction
            original_day = planned_tx.start_date.day
            original_month = planned_tx.start_date.month
            
            year = current_date.year + recurrence_rule.interval
            month = original_month
            
            max_day_in_month = monthrange(year, month)[1]
            day = min(original_day, max_day_in_month)
            
            next_date = date(year, month, day)
        else:
            error_msg = f"Неизвестная единица интервала: {recurrence_rule.interval_unit}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Если включена опция "только рабочие дни", пропускаем выходные
        if recurrence_rule.only_workdays:
            while not is_workday(next_date):
                next_date += timedelta(days=1)
        
        return next_date
    
    else:
        error_msg = f"Неизвестный тип повторения: {recurrence_rule.recurrence_type}"
        logger.error(error_msg)
        raise ValueError(error_msg)



def generate_occurrences_for_period(
    session: Session,
    planned_tx: PlannedTransactionDB,
    start_date: date,
    end_date: date
) -> List[date]:
    """
    Генерирует даты вхождений для периодической транзакции в указанном периоде.
    
    Функция учитывает правила повторения, рабочие дни, кастомные интервалы
    и условия окончания. Используется для отображения плановых транзакций
    в календаре и для прогноза баланса.
    
    ВАЖНО: Вхождения НЕ создаются раньше start_date плановой транзакции.
    Для бессрочных транзакций генерируются вхождения только от start_date и позже.
    Для транзакций с end_date генерируются вхождения только в диапазоне [start_date, end_date].
    
    Args:
        session: Активная сессия БД для доступа к правилам повторения
        planned_tx: Шаблон плановой транзакции с правилом повторения
        start_date: Начало периода для генерации
        end_date: Конец периода для генерации
        
    Returns:
        Список дат, когда должна быть исполнена плановая транзакция.
        Список может быть пустым, если в периоде нет вхождений.
        
    Raises:
        ValueError: Если start_date > end_date
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     planned_tx = session.query(PlannedTransactionDB).first()
        ...     dates = generate_occurrences_for_period(
        ...         session, 
        ...         planned_tx, 
        ...         date(2025, 1, 1), 
        ...         date(2025, 1, 31)
        ...     )
        ...     print(f"Найдено {len(dates)} вхождений")
    """
    # Валидация входных данных (Fail Fast)
    if start_date > end_date:
        error_msg = f"Дата начала ({start_date}) не может быть позже даты окончания ({end_date})"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # ВАЖНО: Вхождения НЕ должны создаваться раньше start_date плановой транзакции
        # Если запрашиваемый период полностью раньше start_date плановой транзакции, возвращаем пустой список
        if end_date < planned_tx.start_date:
            logger.debug(f"Период ({start_date} - {end_date}) раньше start_date плановой транзакции ({planned_tx.start_date}), вхождения не генерируются")
            return []
        
        # Получаем правило повторения
        recurrence_rule = planned_tx.recurrence_rule
        
        # Если нет правила повторения, это однократная транзакция
        if not recurrence_rule or recurrence_rule.recurrence_type == RecurrenceType.NONE:
            # Проверяем, попадает ли дата начала в период
            if start_date <= planned_tx.start_date <= end_date:
                return [planned_tx.start_date]
            return []
        
        # Для транзакций с end_date: проверяем, что период пересекается с [start_date, end_date] транзакции
        if recurrence_rule.end_condition_type == EndConditionType.UNTIL_DATE and recurrence_rule.end_date:
            # Если запрашиваемый период полностью после end_date транзакции, возвращаем пустой список
            if start_date > recurrence_rule.end_date:
                logger.debug(f"Период ({start_date} - {end_date}) после end_date плановой транзакции ({recurrence_rule.end_date}), вхождения не генерируются")
                return []
        
        occurrences: List[date] = []
        current_date = planned_tx.start_date
        
        # Если дата начала плана позже конца периода, возвращаем пустой список
        if current_date > end_date:
            return []
        
        # Счётчик для условия AFTER_COUNT
        count = 0
        max_count = recurrence_rule.occurrences_count if recurrence_rule.end_condition_type == EndConditionType.AFTER_COUNT else None
        
        # Генерируем вхождения
        while current_date <= end_date:
            # Проверяем условие окончания по дате
            if recurrence_rule.end_condition_type == EndConditionType.UNTIL_DATE:
                if recurrence_rule.end_date and current_date > recurrence_rule.end_date:
                    break
            
            # Проверяем условие окончания по количеству
            if max_count is not None and count >= max_count:
                break
            
            # Добавляем текущую дату, если она в периоде
            if current_date >= start_date:
                occurrences.append(current_date)
                count += 1
            elif current_date < start_date:
                # Увеличиваем счётчик, даже если дата не в периоде
                count += 1
            
            # Вычисляем следующую дату
            next_date = calculate_next_occurrence_date(current_date, recurrence_rule)
            
            if next_date is None or next_date <= current_date:
                # Защита от бесконечного цикла
                logger.warning(f"Невозможно вычислить следующую дату для плановой транзакции ID {planned_tx.id}")
                break
            
            current_date = next_date
        
        logger.info(f"Сгенерировано {len(occurrences)} вхождений для плановой транзакции ID {planned_tx.id} в периоде {start_date} - {end_date}")
        return occurrences
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при генерации вхождений для плановой транзакции ID {planned_tx.id}: {e}")
        raise



def get_or_create_occurrence(
    session: Session,
    planned_tx_id: int,
    scheduled_date: date
) -> PlannedOccurrenceDB:
    """
    Получает существующее вхождение или создаёт новое для указанной даты.
    
    Используется для ленивой генерации вхождений — вхождения создаются
    только когда они нужны (при отображении в календаре или исполнении).
    
    Args:
        session: Активная сессия БД
        planned_tx_id: ID плановой транзакции
        scheduled_date: Запланированная дата вхождения
        
    Returns:
        Объект вхождения (существующий или новый)
        
    Raises:
        ValueError: Если плановая транзакция не найдена
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     occurrence = get_or_create_occurrence(session, 1, date(2025, 1, 15))
        ...     print(f"Вхождение ID {occurrence.id} на дату {occurrence.occurrence_date}")
    """
    # Валидация входных данных (Fail Fast)
    if planned_tx_id <= 0:
        error_msg = f"ID плановой транзакции должен быть положительным, получено: {planned_tx_id}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Проверяем, существует ли плановая транзакция
        planned_tx = session.query(PlannedTransactionDB).filter_by(id=planned_tx_id).first()
        
        if not planned_tx:
            error_msg = f"Плановая транзакция с ID {planned_tx_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Ищем существующее вхождение
        occurrence = session.query(PlannedOccurrenceDB).filter_by(
            planned_transaction_id=planned_tx_id,
            occurrence_date=scheduled_date
        ).first()
        
        if occurrence:
            logger.debug(f"Найдено существующее вхождение ID {occurrence.id} для плановой транзакции ID {planned_tx_id} на дату {scheduled_date}")
            return occurrence
        
        # Создаём новое вхождение
        new_occurrence = PlannedOccurrenceDB(
            planned_transaction_id=planned_tx_id,
            occurrence_date=scheduled_date,
            amount=planned_tx.amount,
            status=OccurrenceStatus.PENDING
        )
        session.add(new_occurrence)
        session.commit()
        session.refresh(new_occurrence)
        
        logger.info(f"Создано новое вхождение ID {new_occurrence.id} для плановой транзакции ID {planned_tx_id} на дату {scheduled_date}")
        return new_occurrence
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении/создании вхождения для плановой транзакции ID {planned_tx_id} на дату {scheduled_date}: {e}")
        session.rollback()
        raise


def ensure_occurrences_for_period(
    session: Session,
    start_date: date,
    end_date: date
) -> int:
    """
    Создаёт вхождения в БД для всех активных плановых транзакций в указанном периоде.
    
    Функция проходит по всем активным плановым транзакциям, генерирует даты вхождений
    для указанного периода и создаёт записи в БД, если их ещё нет. Используется для
    предварительного создания вхождений при инициализации приложения и при переключении
    месяца в календаре.
    
    Вхождения создаются только если их ещё нет (проверка по planned_transaction_id + scheduled_date).
    Это обеспечивает идемпотентность функции — повторный вызов не создаст дубликаты.
    
    Args:
        session: Активная сессия БД для выполнения операций
        start_date: Начало периода для создания вхождений
        end_date: Конец периода для создания вхождений
        
    Returns:
        Количество созданных новых вхождений
        
    Raises:
        ValueError: Если start_date > end_date
        SQLAlchemyError: При ошибках работы с БД
        
    Example:
        >>> with get_db_session() as session:
        ...     # Создаём вхождения для текущего месяца
        ...     today = date.today()
        ...     start = date(today.year, today.month, 1)
        ...     end = date(today.year, today.month, monthrange(today.year, today.month)[1])
        ...     count = ensure_occurrences_for_period(session, start, end)
        ...     print(f"Создано {count} новых вхождений")
    """
    # Валидация входных данных (Fail Fast)
    if start_date > end_date:
        error_msg = f"Дата начала ({start_date}) не может быть позже даты окончания ({end_date})"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Получаем все активные плановые транзакции
        active_planned_txs = session.query(PlannedTransactionDB).filter_by(is_active=True).all()
        
        if not active_planned_txs:
            logger.info("Нет активных плановых транзакций для создания вхождений")
            return 0
        
        created_count = 0
        
        # Для каждой плановой транзакции генерируем вхождения
        for planned_tx in active_planned_txs:
            # Генерируем даты вхождений для периода
            occurrence_dates = generate_occurrences_for_period(
                session,
                planned_tx,
                start_date,
                end_date
            )
            
            # Создаём вхождения в БД, если их ещё нет
            for scheduled_date in occurrence_dates:
                # Проверяем, существует ли уже вхождение
                existing_occurrence = session.query(PlannedOccurrenceDB).filter_by(
                    planned_transaction_id=planned_tx.id,
                    occurrence_date=scheduled_date
                ).first()
                
                if not existing_occurrence:
                    # Создаём новое вхождение
                    new_occurrence = PlannedOccurrenceDB(
                        planned_transaction_id=planned_tx.id,
                        occurrence_date=scheduled_date,
                        amount=planned_tx.amount,
                        status=OccurrenceStatus.PENDING
                    )
                    session.add(new_occurrence)
                    created_count += 1
                    logger.debug(f"Создано вхождение для плановой транзакции ID {planned_tx.id} на дату {scheduled_date}")
        
        # Сохраняем все изменения одной транзакцией
        session.commit()
        
        logger.info(f"Создано {created_count} новых вхождений для периода {start_date} - {end_date}")
        return created_count
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при создании вхождений для периода {start_date} - {end_date}: {e}")
        session.rollback()
        raise
