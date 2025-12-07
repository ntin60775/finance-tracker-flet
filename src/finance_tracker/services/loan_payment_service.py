"""
Сервис управления платежами по кредитам.

Предоставляет функции для работы с графиком платежей:
- Получение графика платежей
- Создание платежей в графике
- Обновление платежей
- Удаление платежей
- Автоматическое обновление просроченных платежей
- Импорт платежей из CSV
- Досрочное погашение (полное и частичное)
"""

import logging
import csv
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from io import StringIO
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import (
    LoanPaymentDB, LoanDB, TransactionDB, CategoryDB,
    PaymentStatus, TransactionType, LoanStatus
)

# Настройка логирования
logger = logging.getLogger(__name__)


def get_payments_by_loan(
    session: Session,
    loan_id: int,
    status: Optional[PaymentStatus] = None
) -> List[LoanPaymentDB]:
    """
    Получает график платежей по кредиту с опциональной фильтрацией по статусу.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита
        status: Статус платежа для фильтрации (опциональное)

    Returns:
        Список объектов LoanPaymentDB, отсортированных по дате платежа

    Raises:
        ValueError: Если кредит не найден
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payments = get_payments_by_loan(session, loan_id=1)
        ...     pending = get_payments_by_loan(session, 1, PaymentStatus.PENDING)
    """
    try:
        # Проверяем существование кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Базовый запрос
        query = session.query(LoanPaymentDB).filter_by(loan_id=loan_id)

        # Применяем фильтр по статусу
        if status is not None:
            query = query.filter(LoanPaymentDB.status == status)

        # Сортируем по дате платежа
        query = query.order_by(LoanPaymentDB.scheduled_date)

        # Выполняем запрос
        payments = query.all()

        logger.info(
            f"Получено {len(payments)} платежей по кредиту ID {loan_id}"
            f"{f' статуса {status.value}' if status else ''}"
        )

        return payments

    except ValueError:
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении платежей кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def create_payment(
    session: Session,
    loan_id: int,
    scheduled_date: date,
    principal_amount: Decimal,
    interest_amount: Decimal,
    total_amount: Decimal
) -> LoanPaymentDB:
    """
    Создаёт новый платёж в графике кредита.

    Args:
        session: Активная сессия БД
        loan_id: ID кредита
        scheduled_date: Запланированная дата платежа
        principal_amount: Сумма основного долга (>= 0)
        interest_amount: Сумма процентов (>= 0)
        total_amount: Общая сумма платежа (> 0)

    Returns:
        Созданный объект LoanPaymentDB

    Raises:
        ValueError: Если валидация не прошла
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payment = create_payment(
        ...         session, loan_id=1,
        ...         scheduled_date=date(2025, 2, 15),
        ...         principal_amount=Decimal('10000.00'),
        ...         interest_amount=Decimal('500.00'),
        ...         total_amount=Decimal('10500.00')
        ...     )
    """
    try:
        # Валидация кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Валидация сумм
        if principal_amount < Decimal('0'):
            raise ValueError("Сумма основного долга не может быть отрицательной")
        if interest_amount < Decimal('0'):
            raise ValueError("Сумма процентов не может быть отрицательной")
        if total_amount <= Decimal('0'):
            raise ValueError("Общая сумма платежа должна быть больше 0")

        # Валидация суммы
        expected_total = principal_amount + interest_amount
        if abs(total_amount - expected_total) > Decimal('0.01'):
            raise ValueError(
                f"Общая сумма должна равняться сумме основного долга и процентов "
                f"({expected_total:.2f})"
            )

        # Создание платежа
        payment = LoanPaymentDB(
            loan_id=loan_id,
            scheduled_date=scheduled_date,
            principal_amount=principal_amount,
            interest_amount=interest_amount,
            total_amount=total_amount
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)

        logger.info(
            f"Создан платёж по кредиту ID {loan_id} "
            f"на дату {scheduled_date} (ID {payment.id})"
        )

        return payment

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании платежа по кредиту ID {loan_id}: {e}"
        logger.error(error_msg)
        raise


def update_payment(
    session: Session,
    payment_id: int,
    scheduled_date: Optional[date] = None,
    principal_amount: Optional[Decimal] = None,
    interest_amount: Optional[Decimal] = None,
    total_amount: Optional[Decimal] = None
) -> LoanPaymentDB:
    """
    Обновляет платёж (только если статус PENDING).

    Args:
        session: Активная сессия БД
        payment_id: ID платежа
        scheduled_date: Новая дата платежа (опциональное)
        principal_amount: Новая сумма основного долга (опциональное)
        interest_amount: Новая сумма процентов (опциональное)
        total_amount: Новая общая сумма (опциональное)

    Returns:
        Обновлённый объект LoanPaymentDB

    Raises:
        ValueError: Если платёж не найден, статус не PENDING, или валидация не прошла
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        # Получаем платёж
        payment = session.query(LoanPaymentDB).filter_by(id=payment_id).first()
        if payment is None:
            raise ValueError(f"Платёж ID {payment_id} не найден")

        # Проверяем статус
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(
                f"Можно редактировать только платежи со статусом PENDING, "
                f"текущий статус: {payment.status.value}"
            )

        # Обновляем поля
        if scheduled_date is not None:
            payment.scheduled_date = scheduled_date

        if principal_amount is not None:
            payment.principal_amount = principal_amount

        if interest_amount is not None:
            payment.interest_amount = interest_amount

        if total_amount is not None:
            payment.total_amount = total_amount

        session.commit()
        session.refresh(payment)

        logger.info(f"Обновлён платёж ID {payment_id}")

        return payment

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении платежа ID {payment_id}: {e}"
        logger.error(error_msg)
        raise


def delete_payment(session: Session, payment_id: int) -> bool:
    """
    Удаляет платёж (только если статус PENDING или CANCELLED).

    Args:
        session: Активная сессия БД
        payment_id: ID платежа для удаления

    Returns:
        True, если платёж успешно удалён

    Raises:
        ValueError: Если платёж не найден или статус не позволяет удаление
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        # Получаем платёж
        payment = session.query(LoanPaymentDB).filter_by(id=payment_id).first()
        if payment is None:
            raise ValueError(f"Платёж ID {payment_id} не найден")

        # Проверяем статус
        if payment.status not in (PaymentStatus.PENDING, PaymentStatus.CANCELLED):
            raise ValueError(
                f"Можно удалять только платежи со статусом PENDING или CANCELLED, "
                f"текущий статус: {payment.status.value}"
            )

        session.delete(payment)
        session.commit()

        logger.info(f"Удалён платёж ID {payment_id}")

        return True

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при удалении платежа ID {payment_id}: {e}"
        logger.error(error_msg)
        raise


def update_overdue_payments(session: Session) -> int:
    """
    Автоматически обновляет статус просроченных платежей.

    Функция меняет статус платежей со статусом PENDING на OVERDUE,
    если текущая дата > scheduled_date.

    Args:
        session: Активная сессия БД

    Returns:
        Количество обновленных платежей

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     count = update_overdue_payments(session)
        ...     print(f"Обновлено {count} просроченных платежей")
    """
    try:
        today = date.today()

        # Получаем все платежи со статусом PENDING, у которых дата прошла
        overdue_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.status == PaymentStatus.PENDING,
            LoanPaymentDB.scheduled_date < today
        ).all()

        # Обновляем статус
        for payment in overdue_payments:
            payment.status = PaymentStatus.OVERDUE
            logger.debug(f"Платёж ID {payment.id} отмечен как просрочен")

        if overdue_payments:
            session.commit()
            logger.info(f"Обновлено {len(overdue_payments)} просроченных платежей")

        return len(overdue_payments)

    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении просроченных платежей: {e}"
        logger.error(error_msg)
        raise


def get_overdue_statistics(session: Session) -> dict:
    """
    Получает статистику по просроченным платежам.

    Returns:
        Словарь со статистикой:
        - total_overdue: общее количество просроченных платежей
        - total_overdue_amount: общая сумма просроченных платежей
        - overdue_by_loan: количество просроченных платежей по каждому кредиту
    """
    try:
        # Получаем все просроченные платежи
        overdue = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.status == PaymentStatus.OVERDUE
        ).all()

        total_amount = sum((p.total_amount for p in overdue), Decimal('0.0'))

        # Группируем по кредитам
        overdue_by_loan = {}
        for payment in overdue:
            loan = payment.loan
            if loan.id not in overdue_by_loan:
                overdue_by_loan[loan.id] = {
                    "loan_name": loan.name,
                    "count": 0,
                    "total_amount": Decimal('0.0')
                }
            overdue_by_loan[loan.id]["count"] += 1
            overdue_by_loan[loan.id]["total_amount"] += payment.total_amount

        logger.info(
            f"Статистика просроченных платежей: "
            f"всего={len(overdue)}, сумма={total_amount}"
        )

        return {
            "total_overdue": len(overdue),
            "total_overdue_amount": total_amount,
            "overdue_by_loan": overdue_by_loan
        }

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении статистики просроченных платежей: {e}"
        logger.error(error_msg)
        raise


def import_payments_from_csv(
    session: Session,
    loan_id: int,
    csv_content: str
) -> Dict[str, Any]:
    """
    Импортирует платежи по кредиту из CSV контента.

    Ожидаемый формат CSV:
    - scheduled_date: дата платежа (YYYY-MM-DD)
    - principal_amount: сумма основного долга
    - interest_amount: сумма процентов
    - total_amount: общая сумма (или будет вычислена)

    Args:
        session: Активная сессия БД
        loan_id: ID кредита для импорта платежей
        csv_content: Содержимое CSV файла в виде строки

    Returns:
        Словарь со статистикой импорта:
        - success_count: количество успешно импортированных платежей
        - error_count: количество ошибок
        - errors: список ошибок с детализацией
        - warnings: список предупреждений
        - payment_ids: список ID созданных платежей

    Raises:
        ValueError: Если кредит не найден или формат CSV некорректный
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> csv_data = '''scheduled_date,principal_amount,interest_amount
        ... 2025-02-15,10000,500
        ... 2025-03-15,10000,450'''
        >>> with get_db_session() as session:
        ...     result = import_payments_from_csv(session, 1, csv_data)
        ...     print(f"Импортировано: {result['success_count']}")
    """
    try:
        # Проверяем существование кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        result = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "warnings": [],
            "payment_ids": []
        }

        # Парсим CSV
        try:
            csv_reader = csv.DictReader(StringIO(csv_content))
            if not csv_reader.fieldnames:
                raise ValueError("CSV файл пуст или не содержит заголовков")

            # Проверяем обязательные поля
            required_fields = {"scheduled_date", "principal_amount", "interest_amount"}
            missing_fields = required_fields - set(csv_reader.fieldnames or [])
            if missing_fields:
                raise ValueError(
                    f"CSV не содержит обязательные поля: {', '.join(missing_fields)}"
                )

            # Импортируем платежи
            for row_num, row in enumerate(csv_reader, start=2):  # start=2 т.к. строка 1 - заголовки
                try:
                    # Валидируем и парсим дату
                    scheduled_date_str = row.get("scheduled_date", "").strip()
                    if not scheduled_date_str:
                        raise ValueError("Пустая дата платежа")

                    try:
                        scheduled_date = datetime.strptime(
                            scheduled_date_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        raise ValueError(
                            f"Некорректный формат даты '{scheduled_date_str}' "
                            f"(ожидается YYYY-MM-DD)"
                        )

                    # Парсим суммы
                    principal_str = row.get("principal_amount", "").strip()
                    interest_str = row.get("interest_amount", "").strip()
                    total_str = row.get("total_amount", "").strip()

                    if not principal_str:
                        raise ValueError("Пустая сумма основного долга")
                    if not interest_str:
                        raise ValueError("Пустая сумма процентов")

                    try:
                        principal_amount = Decimal(principal_str)
                        interest_amount = Decimal(interest_str)
                    except InvalidOperation as e:
                        raise ValueError(f"Некорректное значение суммы: {e}")

                    # Вычисляем или парсим общую сумму
                    if total_str:
                        try:
                            total_amount = Decimal(total_str)
                        except InvalidOperation:
                            raise ValueError(
                                f"Некорректное значение общей суммы '{total_str}'"
                            )
                    else:
                        total_amount = principal_amount + interest_amount

                    # Дополнительная валидация
                    if principal_amount < Decimal('0'):
                        raise ValueError("Сумма основного долга не может быть отрицательной")
                    if interest_amount < Decimal('0'):
                        raise ValueError("Сумма процентов не может быть отрицательной")
                    if total_amount <= Decimal('0'):
                        raise ValueError("Общая сумма должна быть больше 0")

                    # Проверяем соответствие сумм
                    expected_total = principal_amount + interest_amount
                    if abs(total_amount - expected_total) > Decimal('0.01'):
                        warning = (
                            f"Строка {row_num}: общая сумма ({total_amount}) не совпадает с "
                            f"суммой основного долга и процентов ({expected_total}). "
                            f"Используется значение из total_amount."
                        )
                        result["warnings"].append(warning)
                        logger.warning(warning)

                    # Создаём платёж
                    payment = LoanPaymentDB(
                        loan_id=loan_id,
                        scheduled_date=scheduled_date,
                        principal_amount=principal_amount,
                        interest_amount=interest_amount,
                        total_amount=total_amount
                    )
                    session.add(payment)
                    session.flush()  # Получаем ID платежа

                    result["payment_ids"].append(payment.id)
                    result["success_count"] += 1

                    logger.debug(
                        f"Импортирован платёж (строка {row_num}): "
                        f"дата={scheduled_date}, сумма={total_amount}"
                    )

                except ValueError as e:
                    result["error_count"] += 1
                    error_msg = f"Строка {row_num}: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.warning(error_msg)
                except Exception as e:
                    result["error_count"] += 1
                    error_msg = f"Строка {row_num}: неожиданная ошибка: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.warning(error_msg)

        except ValueError as e:
            raise ValueError(f"Ошибка парсинга CSV: {str(e)}")
        except Exception as e:
            raise ValueError(f"Неожиданная ошибка при чтении CSV: {str(e)}")

        # Коммитим успешно импортированные платежи
        if result["success_count"] > 0:
            session.commit()
            logger.info(
                f"Успешно импортировано {result['success_count']} платежей "
                f"по кредиту ID {loan_id}"
            )

        if result["error_count"] > 0:
            logger.warning(
                f"При импорте платежей произошло {result['error_count']} ошибок"
            )

        return result

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при импорте платежей по кредиту ID {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        session.rollback()
        error_msg = f"Неожиданная ошибка при импорте платежей: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def early_repayment_full(
    session: Session,
    loan_id: int,
    repayment_amount: Decimal,
    repayment_date: date
) -> dict:
    """
    Реализует полное досрочное погашение кредита.

    При полном досрочном погашении:
    1. Создается транзакция типа EXPENSE (расход средств)
    2. Все будущие платежи отменяются
    3. Связанные плановые транзакции деактивируются
    4. Статус кредита изменяется на PAID_OFF

    Args:
        session: Активная сессия БД
        loan_id: ID кредита для полного погашения
        repayment_amount: Сумма полного погашения (> 0)
        repayment_date: Дата внесения полного погашения

    Returns:
        Словарь со статистикой операции:
        - loan_id: ID кредита
        - repayment_amount: сумма погашения
        - cancelled_payments_count: количество отменённых платежей
        - transaction_id: ID созданной транзакции расхода

    Raises:
        ValueError: Если кредит не найден, сумма недействительна
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     result = early_repayment_full(
        ...         session, loan_id=1, repayment_amount=Decimal('50000.00'), repayment_date=date.today()
        ...     )
        ...     print(f"Отменено платежей: {result['cancelled_payments_count']}")
    """
    try:
        # Валидация входных данных
        # Проверяем существование кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Проверяем сумму погашения
        if repayment_amount <= Decimal('0'):
            raise ValueError("Сумма погашения должна быть больше 0")

        result = {
            "loan_id": loan_id,
            "repayment_amount": repayment_amount,
            "cancelled_payments_count": 0,
            "transaction_id": None
        }

        # Отмена всех будущих платежей
        # Получаем все платежи со статусом PENDING и будущей датой
        future_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.loan_id == loan_id,
            LoanPaymentDB.status == PaymentStatus.PENDING,
            LoanPaymentDB.scheduled_date > repayment_date
        ).all()

        # Отменяем будущие платежи
        for payment in future_payments:
            payment.status = PaymentStatus.CANCELLED
            result["cancelled_payments_count"] += 1
            logger.debug(f"Платёж ID {payment.id} отменён при полном погашении кредита ID {loan_id}")

        # Примечание: деактивирование плановых транзакций требует наличия поля related_loan_id
        # в модели PlannedTransactionDB, которое в настоящее время отсутствует.
        # Это будет реализовано в будущих версиях при расширении связей между кредитами и плановыми транзакциями.

        # Создание транзакции расхода для полного погашения
        # Получаем категорию "Выплата кредита (основной долг)" для расходов по погашению
        expense_category = session.query(CategoryDB).filter(
            CategoryDB.name.like("%Выплата кредита%"),
            CategoryDB.type == "expense"
        ).first()

        # Создаём транзакцию расхода для полного погашения
        transaction = TransactionDB(
            date=repayment_date,
            type=TransactionType.EXPENSE,
            amount=repayment_amount,
            category_id=expense_category.id if expense_category else None,
            description=f"Полное досрочное погашение кредита '{loan.name}'"
        )
        session.add(transaction)
        session.flush()  # Получаем ID транзакции
        result["transaction_id"] = transaction.id
        logger.debug(f"Создана транзакция расхода ID {transaction.id} для полного погашения кредита ID {loan_id}")

        # Обновление статуса кредита на PAID_OFF
        loan.status = LoanStatus.PAID_OFF
        logger.debug(f"Статус кредита ID {loan_id} изменён на PAID_OFF")

        # Коммитим все изменения
        session.commit()
        logger.info(
            f"Полное досрочное погашение кредита ID {loan_id}: "
            f"сумма={repayment_amount}, отменено платежей={result['cancelled_payments_count']}"
        )

        return result

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при полном досрочном погашении кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        session.rollback()
        error_msg = f"Неожиданная ошибка при полном досрочном погашении: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def early_repayment_partial(
    session: Session,
    loan_id: int,
    repayment_amount: Decimal,
    repayment_date: date
) -> dict:
    """
    Реализует частичное досрочное погашение кредита.

    При частичном досрочном погашении:
    1. Создается транзакция типа EXPENSE (расход средств)
    2. Платежи остаются без изменений
    3. Пользователю выводится предупреждение о необходимости обновить график
    4. Остаток долга пересчитывается

    Args:
        session: Активная сессия БД
        loan_id: ID кредита для частичного погашения
        repayment_amount: Сумма частичного погашения (> 0)
        repayment_date: Дата внесения частичного погашения

    Returns:
        Словарь со статистикой операции:
        - loan_id: ID кредита
        - repayment_amount: сумма погашения
        - new_balance: новый остаток долга (после пересчёта)
        - transaction_id: ID созданной транзакции расхода
        - warning: предупреждение о необходимости обновить график

    Raises:
        ValueError: Если кредит не найден, сумма недействительна
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     result = early_repayment_partial(
        ...         session, loan_id=1, repayment_amount=Decimal('5000.00'), repayment_date=date.today()
        ...     )
        ...     print(f"Новый остаток: {result['new_balance']}")
    """
    try:
        # Валидация входных данных
        # Проверяем существование кредита
        loan = session.query(LoanDB).filter_by(id=loan_id).first()
        if loan is None:
            raise ValueError(f"Кредит ID {loan_id} не найден")

        # Проверяем сумму погашения
        if repayment_amount <= Decimal('0'):
            raise ValueError("Сумма погашения должна быть больше 0")

        result = {
            "loan_id": loan_id,
            "repayment_amount": repayment_amount,
            "new_balance": Decimal('0.0'),
            "transaction_id": None,
            "warning": "Внимание! После частичного досрочного погашения необходимо обновить график платежей по кредиту."
        }

        # Расчет текущего и нового остатка долга
        # Получаем сумму всех будущих платежей (остаток долга)
        future_payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.loan_id == loan_id,
            LoanPaymentDB.status == PaymentStatus.PENDING,
            LoanPaymentDB.scheduled_date >= repayment_date
        ).all()

        current_balance = sum((p.total_amount for p in future_payments), Decimal('0.0'))
        new_balance = max(Decimal('0'), current_balance - repayment_amount)
        result["new_balance"] = new_balance
        logger.debug(
            f"Расчёт остатка для кредита ID {loan_id}: "
            f"текущий={current_balance}, новый={new_balance}"
        )

        # Создание транзакции расхода для частичного погашения
        # Получаем категорию "Выплата кредита (основной долг)" для расходов по погашению
        expense_category = session.query(CategoryDB).filter(
            CategoryDB.name.like("%Выплата кредита%"),
            CategoryDB.type == "expense"
        ).first()

        # Создаём транзакцию расхода для частичного погашения
        transaction = TransactionDB(
            date=repayment_date,
            type=TransactionType.EXPENSE,
            amount=repayment_amount,
            category_id=expense_category.id if expense_category else None,
            description=f"Частичное досрочное погашение кредита '{loan.name}' (новый остаток: {new_balance:.2f})"
        )
        session.add(transaction)
        session.flush()  # Получаем ID транзакции
        result["transaction_id"] = transaction.id
        logger.debug(f"Создана транзакция расхода ID {transaction.id} для частичного погашения кредита ID {loan_id}")

        # Коммитим все изменения
        session.commit()
        logger.info(
            f"Частичное досрочное погашение кредита ID {loan_id}: "
            f"сумма={repayment_amount}, новый остаток={new_balance}"
        )

        return result

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при частичном досрочном погашении кредита ID {loan_id}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        session.rollback()
        error_msg = f"Неожиданная ошибка при частичном досрочном погашении: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def get_payments_by_date(
    session: Session,
    target_date: date
) -> List[LoanPaymentDB]:
    """
    Получает все платежи по кредитам для конкретной даты.

    Args:
        session: Активная сессия БД
        target_date: Дата для поиска платежей

    Returns:
        Список объектов LoanPaymentDB с запланированной датой равной target_date

    Raises:
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payments = get_payments_by_date(session, date(2025, 2, 15))
        ...     print(f"Найдено {len(payments)} платежей")
    """
    try:
        # Получаем все платежи на указанную дату
        payments = session.query(LoanPaymentDB).filter(
            LoanPaymentDB.scheduled_date == target_date
        ).order_by(LoanPaymentDB.loan_id).all()

        logger.info(
            f"Получено {len(payments)} платежей по кредитам на дату {target_date}"
        )

        return payments

    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении платежей на дату {target_date}: {e}"
        logger.error(error_msg)
        raise


def execute_payment(
    session: Session,
    payment_id: int,
    transaction_date: Optional[date] = None
) -> LoanPaymentDB:
    """
    Исполняет платёж по кредиту (обёртка для loan_service.execute_payment).

    Получает сумму платежа из LoanPaymentDB.total_amount и создаёт фактическую транзакцию.
    Функция автоматически рассчитывает количество дней просрочки и обновляет статус.

    Args:
        session: Активная сессия БД
        payment_id: ID платежа в графике
        transaction_date: Дата исполнения (по умолчанию сегодня)

    Returns:
        Обновленный объект LoanPaymentDB со статусом EXECUTED или EXECUTED_LATE

    Raises:
        ValueError: Если платёж не найден, неверный статус или другие ошибки валидации
        SQLAlchemyError: При ошибках работы с БД

    Example:
        >>> with get_db_session() as session:
        ...     payment = execute_payment(session, payment_id=1)
        ...     print(f"Платёж исполнен: {payment.executed_amount}")
    """
    try:
        # Получаем платёж для получения суммы
        payment = session.query(LoanPaymentDB).filter_by(id=payment_id).first()
        if payment is None:
            raise ValueError(f"Платёж ID {payment_id} не найден")

        # Используем total_amount как transaction_amount
        from .loan_service import execute_payment as execute_payment_loan_service
        executed_payment, transaction = execute_payment_loan_service(
            session,
            payment_id=payment_id,
            transaction_amount=payment.total_amount,
            transaction_date=transaction_date
        )

        logger.info(f"Исполнен платёж ID {payment_id} на сумму {payment.total_amount}")
        return executed_payment

    except ValueError:
        raise
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при исполнении платежа ID {payment_id}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Неожиданная ошибка при исполнении платежа ID {payment_id}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
