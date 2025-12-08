"""
Сервис управления займодателями.

Предоставляет функции для работы с справочником займодателей:
- Получение списка займодателей с фильтрацией
- Создание новых займодателей с валидацией
- Обновление информации о займодателе
- Удаление займодателя с проверкой активных кредитов
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from finance_tracker.models import LenderDB, LenderType, LoanDB, LoanStatus
from finance_tracker.utils.cache import cache

# Настройка логирования
logger = logging.getLogger(__name__)


def get_all_lenders(
    session: Session,
    lender_type: Optional[LenderType] = None
) -> List[LenderDB]:
    """
    Получает список всех займодателей с опциональной фильтрацией по типу.
    Использует кэширование.
    """
    try:
        # Пробуем получить из кэша
        all_lenders = cache.lenders.get_all()

        if all_lenders is None:
            # Если нет в кэше, загружаем из БД
            all_lenders = session.query(LenderDB).order_by(LenderDB.name).all()
            # Сохраняем в кэш
            cache.lenders.set_all(all_lenders, key_extractor=lambda lender: lender.id)
            logger.info(f"Загружено {len(all_lenders)} займодателей из БД и сохранено в кэш")
        else:
            logger.debug("Займодатели получены из кэша")

        # Фильтрация (выполняется уже в памяти над закэшированными данными)
        if lender_type is not None:
            result = [lender for lender in all_lenders if lender.lender_type == lender_type]
            logger.info(f"Отфильтровано {len(result)} займодателей типа {lender_type.value}")
            return result
        
        return all_lenders

    except SQLAlchemyError as e:
        error_msg = (
            f"Ошибка при получении займодателей"
            f"{f' типа {lender_type.value}' if lender_type else ''}: {e}"
        )
        logger.error(error_msg)
        raise


def get_lender_by_id(session: Session, lender_id: int) -> Optional[LenderDB]:
    """
    Получает займодателя по ID.

    Args:
        session: Активная сессия БД
        lender_id: ID займодателя

    Returns:
        Объект LenderDB или None, если займодатель не найден
    """
    try:
        return session.query(LenderDB).filter_by(id=lender_id).first()
    except SQLAlchemyError as e:
        error_msg = f"Ошибка при получении займодателя ID {lender_id}: {e}"
        logger.error(error_msg)
        raise


def create_lender(
    session: Session,
    name: str,
    lender_type: LenderType,
    description: Optional[str] = None,
    contact_info: Optional[str] = None,
    notes: Optional[str] = None
) -> LenderDB:
    """
    Создаёт нового займодателя с валидацией.
    Инвалидирует кэш займодателей.
    """
    try:
        # Валидация
        if not name or name.strip() == "":
            raise ValueError("Название займодателя не может быть пустым")

        # Проверяем уникальность названия
        existing = session.query(LenderDB).filter_by(name=name).first()
        if existing is not None:
            raise ValueError(f"Займодатель '{name}' уже существует")

        # Создание займодателя
        lender = LenderDB(
            name=name.strip(),
            lender_type=lender_type,
            description=description,
            contact_info=contact_info,
            notes=notes
        )
        session.add(lender)
        session.commit()
        session.refresh(lender)

        # Инвалидация кэша
        cache.lenders.invalidate()

        logger.info(f"Создан займодатель '{name}' (ID {lender.id})")

        return lender

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        error_msg = f"Ошибка уникальности при создании займодателя: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при создании займодателя: {e}"
        logger.error(error_msg)
        raise


def update_lender(
    session: Session,
    lender_id: int,
    name: Optional[str] = None,
    lender_type: Optional[LenderType] = None,
    description: Optional[str] = None,
    contact_info: Optional[str] = None,
    notes: Optional[str] = None
) -> LenderDB:
    """
    Обновляет информацию о займодателе.
    Инвалидирует кэш займодателей.
    """
    try:
        # Получаем займодателя
        lender = session.query(LenderDB).filter_by(id=lender_id).first()
        if lender is None:
            raise ValueError(f"Займодатель ID {lender_id} не найден")

        # Обновляем поля, если переданы
        if name is not None:
            if not name or name.strip() == "":
                raise ValueError("Название займодателя не может быть пустым")
            # Проверяем уникальность нового названия (исключая текущего займодателя)
            existing = session.query(LenderDB).filter(
                LenderDB.name == name.strip(),
                LenderDB.id != lender_id
            ).first()
            if existing is not None:
                raise ValueError(f"Займодатель '{name}' уже существует")
            lender.name = name.strip()

        if lender_type is not None:
            lender.lender_type = lender_type

        if description is not None:
            lender.description = description

        if contact_info is not None:
            lender.contact_info = contact_info

        if notes is not None:
            lender.notes = notes

        session.commit()
        session.refresh(lender)

        # Инвалидация кэша
        cache.lenders.invalidate()

        logger.info(f"Обновлён займодатель '{lender.name}' (ID {lender_id})")

        return lender

    except ValueError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        error_msg = f"Ошибка уникальности при обновлении займодателя: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при обновлении займодателя ID {lender_id}: {e}"
        logger.error(error_msg)
        raise


def delete_lender(session: Session, lender_id: int) -> bool:
    """
    Удаляет займодателя после проверки активных кредитов.
    Инвалидирует кэш займодателей.
    """
    try:
        # Получаем займодателя
        lender = session.query(LenderDB).filter_by(id=lender_id).first()
        if lender is None:
            raise ValueError(f"Займодатель ID {lender_id} не найден")

        # Проверяем активные кредиты
        active_loans = session.query(LoanDB).filter(
            LoanDB.lender_id == lender_id,
            LoanDB.status == LoanStatus.ACTIVE
        ).all()

        if active_loans:
            loan_names = ", ".join([f"'{loan.name}'" for loan in active_loans])
            raise ValueError(
                f"Невозможно удалить займодателя '{lender.name}': "
                f"есть активные кредиты: {loan_names}"
            )

        # Удаление займодателя
        lender_name = lender.name

        # Удаляем все кредиты, связанные с займодателем
        # (они должны быть либо погашены, либо просроченных не быть)
        all_loans = session.query(LoanDB).filter(
            LoanDB.lender_id == lender_id
        ).all()
        for loan in all_loans:
            session.delete(loan)

        session.delete(lender)
        session.commit()

        # Инвалидация кэша
        cache.lenders.invalidate()

        logger.info(f"Удалён займодатель '{lender_name}' (ID {lender_id})")

        return True

    except ValueError:
        session.rollback()
        raise
    except SQLAlchemyError as e:
        session.rollback()
        error_msg = f"Ошибка при удалении займодателя ID {lender_id}: {e}"
        logger.error(error_msg)
        raise
