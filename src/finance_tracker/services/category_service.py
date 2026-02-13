"""
Сервис управления категорями транзакций.

Предоставляет функции для работы со справочником категорий:
- Получение списка категорий с фильтрацией
- Создание пользовательских категорий
- Удаление пользовательских категорий (системные защищены)
"""

import logging
from typing import Any, Dict, List, Optional, cast
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm.exc import DetachedInstanceError

from finance_tracker.models import CategoryDB, TransactionType
from finance_tracker.utils.cache import cache
from finance_tracker.utils.validation import validate_uuid_format

# Настройка логирования
logger = logging.getLogger(__name__)


def _normalize_parent_id(parent_id: Optional[str]) -> Optional[str]:
    if parent_id is None:
        return None

    normalized = parent_id.strip()
    if not normalized:
        return None

    return normalized


def _get_category_usage_counts(session: Session, category_id: str) -> Dict[str, int]:
    from finance_tracker.models import TransactionDB, PlannedTransactionDB, PendingPaymentDB

    return {
        "transactions": session.query(TransactionDB).filter_by(category_id=category_id).count(),
        "planned_transactions": session.query(PlannedTransactionDB)
        .filter_by(category_id=category_id)
        .count(),
        "pending_payments": session.query(PendingPaymentDB)
        .filter_by(category_id=category_id)
        .count(),
    }


def _validate_parent_constraints(
    session: Session,
    parent_id: Optional[str],
    child_type: TransactionType,
    child_id: Optional[str] = None,
) -> Optional[str]:
    normalized_parent_id = _normalize_parent_id(parent_id)
    if normalized_parent_id is None:
        return None

    validate_uuid_format(normalized_parent_id, "parent_id")

    if child_type != TransactionType.EXPENSE:
        error_msg = "Подкатегории разрешены только для категорий типа EXPENSE"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if child_id is not None and normalized_parent_id == child_id:
        error_msg = "Категория не может быть родителем сама себе"
        logger.error(error_msg)
        raise ValueError(error_msg)

    parent = session.query(CategoryDB).filter_by(id=normalized_parent_id).first()
    if parent is None:
        error_msg = f"Родительская категория с ID {normalized_parent_id} не найдена"
        logger.error(error_msg)
        raise ValueError(error_msg)

    parent_type = cast(TransactionType, cast(Any, parent).type)
    if parent_type != TransactionType.EXPENSE:
        error_msg = "Родительская категория должна быть типа EXPENSE"
        logger.error(error_msg)
        raise ValueError(error_msg)

    parent_parent_id = cast(Optional[str], cast(Any, parent).parent_id)
    if parent_parent_id is not None:
        error_msg = "Родительская категория должна быть корневой (one-level only)"
        logger.error(error_msg)
        raise ValueError(error_msg)

    parent_id_value = cast(str, cast(Any, parent).id)
    usage_counts = _get_category_usage_counts(session, parent_id_value)
    if any(usage_counts.values()):
        parent_name = cast(str, cast(Any, parent).name)
        error_msg = (
            f"Нельзя добавлять подкатегории к категории '{parent_name}': "
            "категория уже используется в транзакциях/планах/отложенных платежах"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    return normalized_parent_id


def get_all_categories(
    session: Session, transaction_type: Optional[TransactionType] = None
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

            # ORM-объекты из кэша могут стать detached/expired между сессиями.
            # В этом случае инвалидируем кэш и перечитываем категории из текущей сессии.
            try:
                _ = [c.id for c in all_categories]
                _ = [c.type for c in all_categories]
            except DetachedInstanceError:
                logger.warning("Кэш категорий содержит detached объекты, выполняем перезагрузку")
                cache.categories.invalidate()
                all_categories = session.query(CategoryDB).order_by(CategoryDB.name).all()
                cache.categories.set_all(all_categories, key_extractor=lambda c: c.id)

        # Фильтрация (выполняется уже в памяти над закэшированными данными)
        if transaction_type is not None:
            result: List[CategoryDB] = []
            for category in all_categories:
                category_type = cast(TransactionType, cast(Any, category).type)
                if category_type == transaction_type:
                    result.append(category)
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
    transaction_type: TransactionType,
    parent_id: Optional[str] = None,
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
        if existing is not None:
            error_msg = f"Категория с названием '{name}' уже существует"
            logger.error(error_msg)
            raise ValueError(error_msg)

        validated_parent_id = _validate_parent_constraints(
            session,
            parent_id,
            transaction_type,
        )

        # Создание категории
        category = CategoryDB(
            name=name,
            type=transaction_type,
            parent_id=validated_parent_id,
            is_system=False,  # Пользовательская категория
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
    category_id: str,
    name: str,
    parent_id: Optional[str] = None,
) -> CategoryDB:
    """
    Обновляет название пользовательской категории.
    Инвалидирует кэш категорий.
    """
    try:
        validate_uuid_format(category_id, "category_id")

        # Валидация входных данных (Fail Fast)
        if not name or not name.strip():
            error_msg = "Название категории не может быть пустым"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Очищаем название от пробелов
        name = name.strip()

        # Получаем категорию
        category = session.query(CategoryDB).filter_by(id=category_id).first()

        # Проверка существования (Fail Fast)
        if category is None:
            error_msg = f"Категория с ID {category_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка, что категория не системная (Fail Fast)
        if bool(cast(Any, category).is_system):
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно изменить системную категорию '{category_name}' (ID {category_id})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        current_parent_id = cast(Optional[str], cast(Any, category).parent_id)
        target_parent_id = (
            current_parent_id if parent_id is None else _normalize_parent_id(parent_id)
        )

        if target_parent_id is not None and len(category.children) > 0:
            error_msg = (
                "Категория с дочерними категориями должна оставаться корневой (one-level only)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        validated_parent_id = _validate_parent_constraints(
            session,
            target_parent_id,
            cast(TransactionType, cast(Any, category).type),
            child_id=cast(str, cast(Any, category).id),
        )

        current_name = cast(str, cast(Any, category).name)

        # Проверка уникальности нового названия (если оно изменилось)
        if current_name != name:
            existing = session.query(CategoryDB).filter_by(name=name).first()
            if existing is not None:
                error_msg = f"Категория с названием '{name}' уже существует"
                logger.error(error_msg)
                raise ValueError(error_msg)

        old_name = current_name
        old_parent_id = current_parent_id

        has_name_changes = current_name != name
        has_parent_changes = current_parent_id != validated_parent_id

        if has_name_changes or has_parent_changes:
            category_obj = cast(Any, category)
            category_obj.name = name
            category_obj.parent_id = validated_parent_id
            session.commit()
            session.refresh(category)

            # Инвалидация кэша
            cache.categories.invalidate()

            logger.info(
                f"Категория '{old_name}' обновлена (ID {category_id}): "
                f"name='{name}', parent_id: {old_parent_id} -> {validated_parent_id}"
            )
        else:
            logger.info(
                f"Категория '{name}' не изменилась (ID {category_id}, parent_id={current_parent_id})"
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
        error_msg = f"Ошибка при обновлении категории ID {category_id}: {e}"
        logger.error(error_msg)
        raise


def delete_category(session: Session, category_id: str) -> bool:
    """
    Удаляет пользовательскую категорию с проверкой is_system.
    Инвалидирует кэш категорий.
    """
    try:
        validate_uuid_format(category_id, "category_id")

        # Получаем категорию
        category = session.query(CategoryDB).filter_by(id=category_id).first()

        # Проверка существования (Fail Fast)
        if category is None:
            error_msg = f"Категория с ID {category_id} не найдена"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка, что категория не системная (Fail Fast)
        if bool(cast(Any, category).is_system):
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно удалить системную категорию '{category_name}' (ID {category_id})"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        children_count = session.query(CategoryDB).filter_by(parent_id=category_id).count()
        if children_count > 0:
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно удалить категорию '{category_name}': "
                f"у категории есть {children_count} дочерних категорий"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка на наличие связанных транзакций
        from finance_tracker.models import TransactionDB, PlannedTransactionDB, PendingPaymentDB

        transactions_count = session.query(TransactionDB).filter_by(category_id=category_id).count()
        if transactions_count > 0:
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно удалить категорию '{category_name}': "
                f"существует {transactions_count} транзакций с этой категорией. "
                f"Сначала удалите или измените категорию у этих транзакций."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        planned_transactions_count = (
            session.query(PlannedTransactionDB).filter_by(category_id=category_id).count()
        )
        if planned_transactions_count > 0:
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно удалить категорию '{category_name}': "
                f"существует {planned_transactions_count} плановых транзакций с этой категорией. "
                f"Сначала удалите или измените категорию у этих плановых транзакций."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка на наличие связанных отложенных платежей
        pending_payments_count = (
            session.query(PendingPaymentDB).filter_by(category_id=category_id).count()
        )
        if pending_payments_count > 0:
            category_name = cast(str, cast(Any, category).name)
            error_msg = (
                f"Невозможно удалить категорию '{category_name}': "
                f"существует {pending_payments_count} отложенных платежей с этой категорией. "
                f"Сначала удалите или измените категорию у этих отложенных платежей."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Удаление категории
        category_name = cast(str, cast(Any, category).name)
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
                "is_system": True,
            },
            {
                "name": "Выплата процентов по кредиту",
                "type": TransactionType.EXPENSE,
                "is_system": True,
            },
            {"name": "Получение кредита", "type": TransactionType.INCOME, "is_system": True},
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


def get_expense_tree(session: Session) -> List[Dict[str, object]]:
    expense_categories = get_all_categories(session, TransactionType.EXPENSE)

    roots: List[CategoryDB] = []
    for category in expense_categories:
        category_parent_id = cast(Optional[str], cast(Any, category).parent_id)
        if category_parent_id is None:
            roots.append(category)

    children_by_parent: Dict[str, List[CategoryDB]] = {}
    for root in roots:
        root_id = cast(str, cast(Any, root).id)
        children_by_parent[root_id] = []

    for category in expense_categories:
        category_parent_id = cast(Optional[str], cast(Any, category).parent_id)
        if category_parent_id is not None and category_parent_id in children_by_parent:
            children_by_parent[category_parent_id].append(category)

    result: List[Dict[str, object]] = []
    for root in roots:
        root_id = cast(str, cast(Any, root).id)
        result.append(
            {
                "category": root,
                "children": children_by_parent.get(root_id, []),
            }
        )

    return result


def get_selectable_leaf_categories(
    session: Session,
    transaction_type: TransactionType,
) -> List[CategoryDB]:
    categories = get_all_categories(session, transaction_type)

    if transaction_type == TransactionType.INCOME:
        return categories

    parent_ids: set[str] = set()
    for category in categories:
        category_parent_id = cast(Optional[str], cast(Any, category).parent_id)
        if category_parent_id is not None:
            parent_ids.add(category_parent_id)

    leaf_categories: List[CategoryDB] = []
    for category in categories:
        category_id = cast(str, cast(Any, category).id)
        if category_id not in parent_ids:
            leaf_categories.append(category)

    return leaf_categories
