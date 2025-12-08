"""
Сервис управления категорями транзакций.

Предоставляет функции для работы со справочником категорий:
- Получение списка категорий с фильтрацией
- Создание пользовательских категорий
- Удаление пользовательских категорий (системные защищены)
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from finance_tracker.models import CategoryDB, TransactionType
from finance_tracker.utils.cache import cache

# Настройка логирования
logger = logging.getLogger(__name__)


def get_all_categories(
    session: Session,
    transaction_type: Optional[TransactionType] = None
) -> List[CategoryDB]:
    """
    Получает список всех категорий с опциональной фильтрацией по типу.
    Использует кэширование.
    """
    try:
        # Пробуем получить из кэша
        all_categories = cache.categories.get_all()
        
        if all_categories is None:
            # Если нет в кэше, загружаем из БД
            all_categories = session.query(CategoryDB).order_by(CategoryDB.name).all()
            # Сохраняем в кэш
            cache.categories.set_all(all_categories, key_extractor=lambda c: c.id)
            logger.info(f"Загружено {len(all_categories)} категорий из БД и сохранено в кэш")
        else:
            logger.debug("Категории получены из кэша")

        # Фильтрация (выполняется уже в памяти над закэшированными данными)
        if transaction_type is not None:
            result = [c for c in all_categories if c.type == transaction_type]
            logger.info(f"Отфильтровано {len(result)} категорий типа {transaction_type.value}")
            return result
        
        return all_categories
        
    except SQLAlchemyError as e:
        error_msg = (
            f"Ошибка при получении категорий"
            f"{f' типа {transaction_type.value}' if transaction_type else ''}: {e}"
        )
        logger.error(error_msg)
        raise


def create_category(
    session: Session,
    name: str,
    transaction_type: TransactionType
) -> CategoryDB:
    """
    Создаёт новую пользовательскую категорию с валидацией.
    Инвалидирует кэш категорий.
    """
    # Валидация входных данных (Fail Fast)
    if not name or not name.strip():
        error_msg = "Название категории не может быть пустым"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Очищаем название от пробелов
    name = name.strip()
    
    try:
        # Проверка уникальности названия
        existing = session.query(CategoryDB).filter_by(name=name).first()
        if existing:
            error_msg = f"Категория с названием '{name}' уже существует"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Создание категории
        category = CategoryDB(
            name=name,
            type=transaction_type,
            is_system=False  # Пользовательская категория
        )
        
        session.add(category)
        session.commit()
        session.refresh(category)
        
        # Инвалидация кэша
        cache.categories.invalidate()
        
        logger.info(
            f"Создана пользовательская категория '{name}' "
            f"типа {transaction_type.value} с ID {category.id}"
        )
        
        return category
        
    except IntegrityError as e:
        # Обработка нарушения уникальности на уровне БД
        session.rollback()
        error_msg = f"Категория с названием '{name}' уже существует (constraint violation)"
        logger.error(f"{error_msg}: {e}")
        raise ValueError(error_msg)
        
    except SQLAlchemyError as e:
        # Логируем с контекстом и откатываем транзакцию
        session.rollback()
        error_msg = f"Ошибка при создании категории '{name}': {e}"
        logger.error(error_msg)
        raise


def update_category(
    session: Session,
    category_id: int,
    name: str
) -> CategoryDB:
    """
    Обновляет название пользовательской категории.
    Инвалидирует кэш категорий.
    """
    # Валидация входных данных (Fail Fast)
    if not name or not name.strip():
        error_msg = "Название категории не может быть пустым"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Очищаем название от пробелов
    name = name.strip()

    try:
        # Получаем категорию
        category = session.query(CategoryDB).filter_by(id=category_id).first()

        # Проверка существования (Fail Fast)
        if not category:
            error_msg = f"Категория с ID {category_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка, что категория не системная (Fail Fast)
        if category.is_system:
            error_msg = (
                f"Невозможно изменить системную категорию '{category.name}' "
                f"(ID {category_id})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка уникальности нового названия (если оно изменилось)
        if category.name != name:
            existing = session.query(CategoryDB).filter_by(name=name).first()
            if existing:
                error_msg = f"Категория с названием '{name}' уже существует"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Обновляем название
            old_name = category.name
            category.name = name
            session.commit()
            session.refresh(category)

            # Инвалидация кэша
            cache.categories.invalidate()

            logger.info(
                f"Категория '{old_name}' переименована в '{name}' (ID {category_id})"
            )
        else:
            logger.info(f"Название категории '{name}' не изменилось (ID {category_id})")

        return category

    except IntegrityError as e:
        # Обработка нарушения уникальности на уровне БД
        session.rollback()
        error_msg = f"Категория с названием '{name}' уже существует (constraint violation)"
        logger.error(f"{error_msg}: {e}")
        raise ValueError(error_msg)

    except SQLAlchemyError as e:
        # Логируем с контекстом и откатываем транзакцию
        session.rollback()
        error_msg = f"Ошибка при обновлении категории ID {category_id}: {e}"
        logger.error(error_msg)
        raise


def delete_category(
    session: Session,
    category_id: int
) -> bool:
    """
    Удаляет пользовательскую категорию с проверкой is_system.
    Инвалидирует кэш категорий.
    """
    try:
        # Получаем категорию
        category = session.query(CategoryDB).filter_by(id=category_id).first()
        
        # Проверка существования (Fail Fast)
        if not category:
            error_msg = f"Категория с ID {category_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверка, что категория не системная (Fail Fast)
        if category.is_system:
            error_msg = (
                f"Невозможно удалить системную категорию '{category.name}' "
                f"(ID {category_id})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверка на наличие связанных транзакций
        from finance_tracker.models import TransactionDB, PlannedTransactionDB, PendingPaymentDB
        
        transactions_count = session.query(TransactionDB).filter_by(category_id=category_id).count()
        if transactions_count > 0:
            error_msg = (
                f"Невозможно удалить категорию '{category.name}': "
                f"существует {transactions_count} транзакций с этой категорией. "
                f"Сначала удалите или измените категорию у этих транзакций."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        planned_transactions_count = session.query(PlannedTransactionDB).filter_by(category_id=category_id).count()
        if planned_transactions_count > 0:
            error_msg = (
                f"Невозможно удалить категорию '{category.name}': "
                f"существует {planned_transactions_count} плановых транзакций с этой категорией. "
                f"Сначала удалите или измените категорию у этих плановых транзакций."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Проверка на наличие связанных отложенных платежей
        pending_payments_count = session.query(PendingPaymentDB).filter_by(category_id=category_id).count()
        if pending_payments_count > 0:
            error_msg = (
                f"Невозможно удалить категорию '{category.name}': "
                f"существует {pending_payments_count} отложенных платежей с этой категорией. "
                f"Сначала удалите или измените категорию у этих отложенных платежей."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Удаление категории
        category_name = category.name
        session.delete(category)
        session.commit()

        # Инвалидация кэша
        cache.categories.invalidate()

        logger.info(f"Удалена пользовательская категория '{category_name}' (ID {category_id})")

        return True

    except SQLAlchemyError as e:
        # Логируем с контекстом и откатываем транзакцию
        session.rollback()
        error_msg = f"Ошибка при удалении категории ID {category_id}: {e}"
        logger.error(error_msg)
        raise


def init_loan_categories(session: Session) -> None:
    """
    Создаёт системные категории для кредитов и займов.

    Функция создаёт три системные категории для работы с кредитами:
    - "Выплата кредита (основной долг)" (EXPENSE)
    - "Выплата процентов по кредиту" (EXPENSE)
    - "Получение кредита" (INCOME)

    Функция идемпотентна: если категории уже существуют, они не дублируются.
    Все созданные категории имеют флаг is_system=True и не могут быть удалены
    через delete_category().

    Args:
        session: Активная сессия БД для создания категорий

    Raises:
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        # Список категорий для создания
        loan_categories = [
            {
                "name": "Выплата кредита (основной долг)",
                "type": TransactionType.EXPENSE,
                "is_system": True
            },
            {
                "name": "Выплата процентов по кредиту",
                "type": TransactionType.EXPENSE,
                "is_system": True
            },
            {
                "name": "Получение кредита",
                "type": TransactionType.INCOME,
                "is_system": True
            }
        ]

        # Создаём категории, если их ещё нет
        created_count = 0
        for cat_data in loan_categories:
            # Проверяем, существует ли уже такая категория
            existing = session.query(CategoryDB).filter_by(name=cat_data["name"]).first()

            if existing is None:
                # Создаём новую категорию
                category = CategoryDB(**cat_data)
                session.add(category)
                created_count += 1
                logger.debug(f"Создана категория: {cat_data['name']}")

        # Коммитим все созданные категории
        if created_count > 0:
            session.commit()
            logger.info(f"Инициализировано {created_count} системных категорий для кредитов")
        else:
            logger.info("Системные категории для кредитов уже существуют")

    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при инициализации категорий кредитов: {e}"
        logger.error(error_msg)
        raise
