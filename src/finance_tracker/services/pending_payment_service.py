"""
Сервис управления отложенными платежами.

<ai:purpose>
Предоставляет функции для работы с отложенными платежами:
- Создание, чтение, обновление, удаление (CRUD)
- Исполнение платежей (создание фактической транзакции)
- Отмена платежей
- История и статистика
</ai:purpose>
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import date as date_type, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

from finance_tracker.models.models import (
    PendingPaymentDB,
    PendingPaymentCreate,
    PendingPaymentUpdate,
    PendingPaymentExecute,
    PendingPaymentCancel,
    PendingPaymentStatus,
    PendingPaymentPriority,
    CategoryDB,
    TransactionDB,
    TransactionType,
)

# Настройка логирования
logger = logging.getLogger(__name__)


# <ai:block name="CRUD Operations">
# <ai:purpose>Базовые операции создания, чтения, обновления и удаления</ai:purpose>


def create_pending_payment(
    session: Session,
    payment_data: PendingPaymentCreate
) -> PendingPaymentDB:
    """
    Создаёт новый отложенный платёж с валидацией.

    <ai:purpose>
    Validates Requirements 1.1-1.6, 7.1-7.3
    </ai:purpose>

    Валидация:
    - Категория должна существовать
    - Категория должна быть типа EXPENSE
    - Сумма должна быть положительной (проверяется Pydantic)
    - Описание не может быть пустым (проверяется Pydantic)

    Args:
        session: Активная сессия БД
        payment_data: Данные для создания платежа

    Returns:
        Созданный объект PendingPaymentDB

    Raises:
        ValueError: Если категория не найдена или имеет тип INCOME
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payment_data = PendingPaymentCreate(
        ...         amount=1000.0,
        ...         category_id=5,
        ...         description="Оплата интернета",
        ...         priority=PendingPaymentPriority.HIGH
        ...     )
        ...     payment = create_pending_payment(session, payment_data)
    """
    try:
        # <ai:step type="validation">Проверка существования категории</ai:step>
        category = session.query(CategoryDB).filter(
            CategoryDB.id == payment_data.category_id
        ).first()

        # <ai:condition test="Категория должна существовать">
        if not category:
            error_msg = f"Категория с ID {payment_data.category_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:condition test="Категория должна быть типа EXPENSE">
        if category.type != TransactionType.EXPENSE:
            error_msg = (
                f"Отложенные платежи должны использовать категории типа EXPENSE. "
                f"Категория '{category.name}' имеет тип {category.type.value}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:step type="create">Создание записи в БД</ai:step>
        db_payment = PendingPaymentDB(
            amount=payment_data.amount,
            category_id=payment_data.category_id,
            description=payment_data.description.strip(),
            priority=payment_data.priority,
            planned_date=payment_data.planned_date,
            status=PendingPaymentStatus.ACTIVE,
        )

        session.add(db_payment)
        session.commit()
        session.refresh(db_payment)

        logger.info(
            f"Создан отложенный платёж ID={db_payment.id}: "
            f"'{db_payment.description}', {db_payment.amount} руб., "
            f"приоритет={db_payment.priority.value}"
        )

        return db_payment

    except ValueError:
        # <ai:exception>Пробрасываем ValueError дальше без изменений</ai:exception>
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании отложенного платежа: {e}"
        logger.error(error_msg)
        raise


def get_pending_payment_by_id(
    session: Session,
    payment_id: int
) -> Optional[PendingPaymentDB]:
    """
    Получает отложенный платёж по ID.

    Args:
        session: Активная сессия БД
        payment_id: ID платежа

    Returns:
        Объект PendingPaymentDB или None, если не найден

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payment = get_pending_payment_by_id(session, 1)
        ...     if payment:
        ...         print(f"Платёж: {payment.description}")
    """
    try:
        payment = session.query(PendingPaymentDB).filter(
            PendingPaymentDB.id == payment_id
        ).first()

        if payment:
            logger.info(f"Получен отложенный платёж ID={payment_id}")
        else:
            logger.warning(f"Отложенный платёж ID={payment_id} не найден")

        return payment

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении отложенного платежа ID={payment_id}: {e}"
        logger.error(error_msg)
        raise


def get_all_pending_payments(
    session: Session,
    status: Optional[PendingPaymentStatus] = None,
    has_planned_date: Optional[bool] = None,
    category_id: Optional[int] = None,
    priority: Optional[PendingPaymentPriority] = None
) -> List[PendingPaymentDB]:
    """
    Получает список отложенных платежей с фильтрацией.

    <ai:purpose>
    По умолчанию возвращает только активные платежи (status=ACTIVE).
    Validates Requirements 2.1, 2.2, 7.1-7.3, 9.1
    </ai:purpose>

    Args:
        session: Активная сессия БД
        status: Фильтр по статусу (None = только ACTIVE)
        has_planned_date: Фильтр по наличию плановой даты
                         (True = только с датой, False = только без даты, None = все)
        category_id: Фильтр по категории
        priority: Фильтр по приоритету

    Returns:
        Список объектов PendingPaymentDB, отсортированный по приоритету и дате

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     # Все активные платежи
        ...     active = get_all_pending_payments(session)
        ...
        ...     # Только платежи с плановой датой
        ...     with_date = get_all_pending_payments(session, has_planned_date=True)
        ...
        ...     # Критические платежи
        ...     critical = get_all_pending_payments(session, priority=PendingPaymentPriority.CRITICAL)
    """
    try:
        # <ai:step type="query">Построение запроса с фильтрами</ai:step>
        query = session.query(PendingPaymentDB)

        # <ai:condition test="Фильтр по статусу (по умолчанию только ACTIVE)">
        if status is None:
            query = query.filter(PendingPaymentDB.status == PendingPaymentStatus.ACTIVE)
        else:
            query = query.filter(PendingPaymentDB.status == status)
        # </ai:condition>

        # <ai:condition test="Фильтр по наличию плановой даты">
        if has_planned_date is not None:
            if has_planned_date:
                query = query.filter(PendingPaymentDB.planned_date.isnot(None))
            else:
                query = query.filter(PendingPaymentDB.planned_date.is_(None))
        # </ai:condition>

        # <ai:condition test="Фильтр по категории">
        if category_id is not None:
            query = query.filter(PendingPaymentDB.category_id == category_id)
        # </ai:condition>

        # <ai:condition test="Фильтр по приоритету">
        if priority is not None:
            query = query.filter(PendingPaymentDB.priority == priority)
        # </ai:condition>

        # <ai:step type="sorting">Сортировка по приоритету (CRITICAL первые) и дате</ai:step>
        # Порядок приоритетов: CRITICAL > HIGH > MEDIUM > LOW
        priority_order = {
            PendingPaymentPriority.CRITICAL: 0,
            PendingPaymentPriority.HIGH: 1,
            PendingPaymentPriority.MEDIUM: 2,
            PendingPaymentPriority.LOW: 3,
        }

        payments = query.all()

        # Сортировка в Python для учёта кастомного порядка приоритетов
        payments.sort(
            key=lambda p: (
                priority_order.get(p.priority, 999),
                p.planned_date if p.planned_date else date_type.max,
                p.created_at
            )
        )

        logger.info(
            f"Получено {len(payments)} отложенных платежей "
            f"(status={status or 'ACTIVE'}, "
            f"has_planned_date={has_planned_date}, "
            f"category_id={category_id}, "
            f"priority={priority.value if priority else 'все'})"
        )

        return payments

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении списка отложенных платежей: {e}"
        logger.error(error_msg)
        raise


def update_pending_payment(
    session: Session,
    payment_id: int,
    payment_data: PendingPaymentUpdate
) -> PendingPaymentDB:
    """
    Обновляет отложенный платёж.

    <ai:purpose>
    Можно обновлять только активные платежи (status=ACTIVE).
    Validates Requirements 3.1-3.4, 5.1, 5.3
    </ai:purpose>

    Args:
        session: Активная сессия БД
        payment_id: ID платежа для обновления
        payment_data: Новые данные (только указанные поля)

    Returns:
        Обновлённый объект PendingPaymentDB

    Raises:
        ValueError: Если платёж не найден или не активен
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     update_data = PendingPaymentUpdate(
        ...         amount=1500.0,
        ...         priority=PendingPaymentPriority.CRITICAL
        ...     )
        ...     payment = update_pending_payment(session, 1, update_data)
    """
    try:
        # <ai:step type="validation">Получение и проверка платежа</ai:step>
        payment = get_pending_payment_by_id(session, payment_id)

        # <ai:condition test="Платёж должен существовать">
        if not payment:
            error_msg = f"Отложенный платёж ID={payment_id} не найден"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:condition test="Платёж должен быть активным">
        if payment.status != PendingPaymentStatus.ACTIVE:
            error_msg = (
                f"Нельзя обновить платёж ID={payment_id} со статусом {payment.status.value}. "
                f"Обновлять можно только активные платежи."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:step type="validation">Проверка новой категории, если указана</ai:step>
        if payment_data.category_id is not None:
            category = session.query(CategoryDB).filter(
                CategoryDB.id == payment_data.category_id
            ).first()

            if not category:
                error_msg = f"Категория с ID {payment_data.category_id} не найдена"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if category.type != TransactionType.EXPENSE:
                error_msg = (
                    f"Отложенные платежи должны использовать категории типа EXPENSE. "
                    f"Категория '{category.name}' имеет тип {category.type.value}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        # <ai:step type="update">Обновление полей (только указанные)</ai:step>
        # Используем model_dump(exclude_unset=True) для определения явно установленных полей
        update_dict = payment_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == 'description' and value is not None:
                # Очищаем описание от пробелов
                setattr(payment, field, value.strip())
            else:
                # Устанавливаем значение напрямую (включая None для planned_date)
                setattr(payment, field, value)

        payment.updated_at = datetime.now()

        session.commit()
        session.refresh(payment)

        logger.info(f"Обновлён отложенный платёж ID={payment_id}")

        return payment

    except ValueError:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении отложенного платежа ID={payment_id}: {e}"
        logger.error(error_msg)
        raise


def delete_pending_payment(
    session: Session,
    payment_id: int
) -> bool:
    """
    Удаляет отложенный платёж.

    <ai:purpose>
    Можно удалять только активные платежи (status=ACTIVE).
    Выполненные и отменённые платежи нельзя удалить (только через историю).
    Validates Requirements 5.1, 5.3
    </ai:purpose>

    Args:
        session: Активная сессия БД
        payment_id: ID платежа для удаления

    Returns:
        True, если удаление успешно

    Raises:
        ValueError: Если платёж не найден или не активен
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     success = delete_pending_payment(session, 1)
        ...     print(f"Удалено: {success}")
    """
    try:
        # <ai:step type="validation">Получение и проверка платежа</ai:step>
        payment = get_pending_payment_by_id(session, payment_id)

        # <ai:condition test="Платёж должен существовать">
        if not payment:
            error_msg = f"Отложенный платёж ID={payment_id} не найден"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:condition test="Платёж должен быть активным">
        if payment.status != PendingPaymentStatus.ACTIVE:
            error_msg = (
                f"Нельзя удалить платёж ID={payment_id} со статусом {payment.status.value}. "
                f"Удалять можно только активные платежи."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:step type="delete">Удаление записи из БД</ai:step>
        session.delete(payment)
        session.commit()

        logger.info(f"Удалён отложенный платёж ID={payment_id}")

        return True

    except ValueError:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при удалении отложенного платежа ID={payment_id}: {e}"
        logger.error(error_msg)
        raise


# </ai:block>


# <ai:block name="Execute and Cancel Operations">
# <ai:purpose>Операции исполнения и отмены платежей</ai:purpose>


def execute_pending_payment(
    session: Session,
    payment_id: int,
    execute_data: PendingPaymentExecute
) -> Tuple[TransactionDB, PendingPaymentDB]:
    """
    Исполняет отложенный платёж, создавая фактическую транзакцию.

    <ai:purpose>
    Validates Requirements 4.1-4.5
    </ai:purpose>

    Процесс:
    1. Проверка, что платёж активен
    2. Создание фактической транзакции (тип EXPENSE)
    3. Обновление статуса платежа на EXECUTED
    4. Сохранение ссылки на транзакцию и факта исполнения

    После исполнения платёж исчезает из основного списка (фильтр по status=ACTIVE).

    Args:
        session: Активная сессия БД
        payment_id: ID платежа для исполнения
        execute_data: Данные исполнения (дата, сумма)

    Returns:
        Кортеж (созданная транзакция, обновлённый платёж)

    Raises:
        ValueError: Если платёж не найден или не активен
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     execute_data = PendingPaymentExecute(
        ...         executed_date=date.today(),
        ...         executed_amount=1000.0
        ...     )
        ...     transaction, payment = execute_pending_payment(session, 1, execute_data)
    """
    try:
        # <ai:step type="validation">Получение и проверка платежа</ai:step>
        payment = get_pending_payment_by_id(session, payment_id)

        # <ai:condition test="Платёж должен существовать">
        if not payment:
            error_msg = f"Отложенный платёж ID={payment_id} не найден"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:condition test="Платёж должен быть активным">
        if payment.status != PendingPaymentStatus.ACTIVE:
            error_msg = (
                f"Нельзя исполнить платёж ID={payment_id} со статусом {payment.status.value}. "
                f"Исполнять можно только активные платежи."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:step type="create">Создание фактической транзакции</ai:step>
        # Используем executed_amount, если указан, иначе оригинальную сумму
        actual_amount = execute_data.executed_amount if execute_data.executed_amount is not None else payment.amount

        transaction = TransactionDB(
            transaction_date=execute_data.executed_date,
            type=TransactionType.EXPENSE,
            category_id=payment.category_id,
            amount=actual_amount,
            description=f"{payment.description} (исполнение отложенного платежа)",
        )

        session.add(transaction)
        session.flush()  # Получаем ID транзакции до commit

        # <ai:step type="update">Обновление статуса платежа</ai:step>
        payment.status = PendingPaymentStatus.EXECUTED
        payment.actual_transaction_id = transaction.id
        payment.executed_date = execute_data.executed_date
        payment.executed_amount = actual_amount
        payment.updated_at = datetime.now()

        session.commit()
        session.refresh(transaction)
        session.refresh(payment)

        logger.info(
            f"Исполнен отложенный платёж ID={payment_id}, "
            f"создана транзакция ID={transaction.id}, сумма={actual_amount} руб."
        )

        return transaction, payment

    except ValueError:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при исполнении отложенного платежа ID={payment_id}: {e}"
        logger.error(error_msg)
        raise


def cancel_pending_payment(
    session: Session,
    payment_id: int,
    cancel_data: PendingPaymentCancel
) -> PendingPaymentDB:
    """
    Отменяет отложенный платёж.

    <ai:purpose>
    Можно отменять только активные платежи (status=ACTIVE).
    После отмены платёж исчезает из основного списка.
    Validates Requirements 5.1, 5.2
    </ai:purpose>

    Args:
        session: Активная сессия БД
        payment_id: ID платежа для отмены
        cancel_data: Данные отмены (причина)

    Returns:
        Обновлённый объект PendingPaymentDB

    Raises:
        ValueError: Если платёж не найден или не активен
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     cancel_data = PendingPaymentCancel(cancel_reason="Больше не актуально")
        ...     payment = cancel_pending_payment(session, 1, cancel_data)
    """
    try:
        # <ai:step type="validation">Получение и проверка платежа</ai:step>
        payment = get_pending_payment_by_id(session, payment_id)

        # <ai:condition test="Платёж должен существовать">
        if not payment:
            error_msg = f"Отложенный платёж ID={payment_id} не найден"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:condition test="Платёж должен быть активным">
        if payment.status != PendingPaymentStatus.ACTIVE:
            error_msg = (
                f"Нельзя отменить платёж ID={payment_id} со статусом {payment.status.value}. "
                f"Отменять можно только активные платежи."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        # </ai:condition>

        # <ai:step type="update">Обновление статуса платежа</ai:step>
        payment.status = PendingPaymentStatus.CANCELLED
        payment.cancelled_date = date_type.today()
        payment.cancel_reason = cancel_data.cancel_reason
        payment.updated_at = datetime.now()

        session.commit()
        session.refresh(payment)

        logger.info(f"Отменён отложенный платёж ID={payment_id}")

        return payment

    except ValueError:
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при отмене отложенного платежа ID={payment_id}: {e}"
        logger.error(error_msg)
        raise


# </ai:block>


# <ai:block name="History and Statistics">
# <ai:purpose>Функции для получения истории и статистики</ai:purpose>


def get_pending_payments_history(
    session: Session,
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None
) -> List[PendingPaymentDB]:
    """
    Получает историю выполненных и отменённых платежей.

    <ai:purpose>
    Validates Requirements 10.1, 10.2
    </ai:purpose>

    Args:
        session: Активная сессия БД
        start_date: Начало периода (по executed_date или cancelled_date)
        end_date: Конец периода

    Returns:
        Список платежей со статусом EXECUTED или CANCELLED

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     from datetime import date, timedelta
        ...     start = date.today() - timedelta(days=30)
        ...     history = get_pending_payments_history(session, start_date=start)
    """
    try:
        # <ai:step type="query">Построение запроса для истории</ai:step>
        query = session.query(PendingPaymentDB).filter(
            PendingPaymentDB.status.in_([
                PendingPaymentStatus.EXECUTED,
                PendingPaymentStatus.CANCELLED
            ])
        )

        # <ai:condition test="Фильтр по дате начала">
        if start_date:
            query = query.filter(
                or_(
                    PendingPaymentDB.executed_date >= start_date,
                    PendingPaymentDB.cancelled_date >= start_date
                )
            )
        # </ai:condition>

        # <ai:condition test="Фильтр по дате окончания">
        if end_date:
            query = query.filter(
                or_(
                    PendingPaymentDB.executed_date <= end_date,
                    PendingPaymentDB.cancelled_date <= end_date
                )
            )
        # </ai:condition>

        # <ai:step type="sorting">Сортировка по дате исполнения/отмены (новые первые)</ai:step>
        history = query.all()
        history.sort(
            key=lambda p: p.executed_date or p.cancelled_date or datetime.min.date(),
            reverse=True
        )

        logger.info(f"Получена история: {len(history)} платежей")

        return history

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении истории отложенных платежей: {e}"
        logger.error(error_msg)
        raise


def get_pending_payments_statistics(
    session: Session
) -> Dict[str, Any]:
    """
    Получает статистику по отложенным платежам.

    <ai:purpose>
    Validates Requirements 11.1, 11.2
    </ai:purpose>

    Returns:
        Словарь со статистикой:
        - total_active: Количество активных платежей
        - total_amount: Общая сумма активных платежей
        - by_priority: Статистика по приоритетам
        - with_planned_date: Количество платежей с плановой датой
        - without_planned_date: Количество платежей без плановой даты

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     stats = get_pending_payments_statistics(session)
        ...     print(f"Активных платежей: {stats['total_active']}")
        ...     print(f"Общая сумма: {stats['total_amount']} руб.")
    """
    try:
        # <ai:step type="query">Получение всех активных платежей</ai:step>
        active_payments = get_all_pending_payments(session)

        # <ai:step type="calculation">Расчёт общей статистики</ai:step>
        total_active = len(active_payments)
        total_amount = sum((p.amount for p in active_payments), Decimal('0.0'))

        # <ai:step type="calculation">Статистика по приоритетам</ai:step>
        by_priority = {}
        for priority in PendingPaymentPriority:
            payments = [p for p in active_payments if p.priority == priority]
            by_priority[priority.value] = {
                "count": len(payments),
                "total_amount": sum((p.amount for p in payments), Decimal('0.0'))
            }

        # <ai:step type="calculation">Статистика по наличию плановой даты</ai:step>
        with_planned_date = len([p for p in active_payments if p.planned_date is not None])
        without_planned_date = len([p for p in active_payments if p.planned_date is None])

        statistics = {
            "total_active": total_active,
            "total_amount": total_amount,
            "by_priority": by_priority,
            "with_planned_date": with_planned_date,
            "without_planned_date": without_planned_date,
        }

        logger.info(
            f"Статистика отложенных платежей: {total_active} активных, "
            f"сумма {total_amount} руб."
        )

        return statistics

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении статистики отложенных платежей: {e}"
        logger.error(error_msg)
        raise


def get_pending_payments_by_date(
    session: Session,
    target_date: date_type
) -> List[PendingPaymentDB]:
    """
    Получает активные отложенные платежи для указанной даты.

    <ai:purpose>
    Возвращает только активные платежи с planned_date = target_date.
    Используется для отображения в календаре.
    Validates Requirements 8.1, 8.2
    </ai:purpose>

    Args:
        session: Активная сессия БД
        target_date: Дата для фильтрации

    Returns:
        Список активных отложенных платежей с указанной плановой датой

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payments = get_pending_payments_by_date(session, date(2025, 2, 15))
        ...     print(f"Найдено {len(payments)} платежей на 2025-02-15")
    """
    try:
        # <ai:step type="query">Получение активных платежей с указанной датой</ai:step>
        payments = session.query(PendingPaymentDB).filter(
            PendingPaymentDB.status == PendingPaymentStatus.ACTIVE,
            PendingPaymentDB.planned_date == target_date
        ).order_by(
            # Сортировка по приоритету (CRITICAL первые)
            PendingPaymentDB.priority.desc(),
            PendingPaymentDB.created_at.asc()
        ).all()

        logger.info(
            f"Найдено {len(payments)} активных отложенных платежей "
            f"для даты {target_date}"
        )

        return payments

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении платежей для даты {target_date}: {e}"
        logger.error(error_msg)
        raise


# </ai:block>
