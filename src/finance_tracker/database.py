"""
Модуль управления базой данных для Finance Tracker Flet.

Содержит функции для:
- Инициализации базы данных и создания таблиц
- Управления сессиями БД через контекстный менеджер
- Обработки ошибок с автоматическим откатом транзакций

Путь к базе данных определяется в config.py через settings.db_path
"""

from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.config import settings

# Imports will be available after Task 2.1 and 3.2
# from models import Base, CategoryDB, TransactionType
# from services.category_service import init_loan_categories

# Настройка логирования
logger = logging.getLogger(__name__)


# Глобальные переменные для engine и session factory
_engine: Engine = None
_SessionLocal: sessionmaker = None


def init_default_categories(session: Session) -> None:
    """
    Создаёт предопределённые категории при первом запуске.
    """
    # Import inside function to avoid circular imports or early import errors
    from finance_tracker.models import CategoryDB, TransactionType

    try:
        # Проверяем, есть ли уже категории в БД
        existing_count = session.query(CategoryDB).count()
        
        if existing_count > 0:
            logger.info(f"Категории уже существуют ({existing_count} шт.), пропускаем инициализацию")
            return
        
        logger.info("Инициализация предопределённых категорий...")
        
        # Категории доходов
        income_categories = [
            "Зарплата",
            "Фриланс",
            "Инвестиции",
            "Прочие доходы"
        ]
        
        # Категории расходов
        expense_categories = [
            "Продукты",
            "Транспорт",
            "Жильё",
            "Связь",
            "Развлечения",
            "Здоровье",
            "Прочие расходы"
        ]
        
        # Создаём категории доходов
        for name in income_categories:
            category = CategoryDB(
                name=name,
                type=TransactionType.INCOME,
                is_system=True
            )
            session.add(category)
            logger.debug(f"Добавлена категория дохода: {name}")
        
        # Создаём категории расходов
        for name in expense_categories:
            category = CategoryDB(
                name=name,
                type=TransactionType.EXPENSE,
                is_system=True
            )
            session.add(category)
            logger.debug(f"Добавлена категория расхода: {name}")
        
        # Сохраняем все категории
        session.commit()
        
        total_created = len(income_categories) + len(expense_categories)
        logger.info(f"Успешно создано {total_created} предопределённых категорий")
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при инициализации категорий: {e}")
        session.rollback()
        raise


def init_db() -> Engine:
    """
    Инициализирует подключение к базе данных и создаёт таблицы.
    
    Путь к базе данных берётся из settings.db_path (определён в config.py).
    """
    global _engine, _SessionLocal
    
    # Import inside function
    from finance_tracker.models import Base
    # from finance_tracker.services.category_service import init_loan_categories
    
    try:
        # Получаем путь к БД из конфигурации
        db_path = settings.db_path
        database_url = f"sqlite:///{db_path}"
        
        logger.info(f"Инициализация базы данных: {database_url}")
        
        # Создаём engine с настройками для SQLite
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},  # Для SQLite
            echo=False
        )
        
        # Создаём все таблицы на основе моделей
        Base.metadata.create_all(bind=_engine)
        logger.info("Таблицы базы данных успешно созданы/проверены")
        
        # Создаём фабрику сессий
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine
        )
        
        # Инициализируем предопределённые категории
        with get_db_session() as session:
            init_default_categories(session)
            # init_loan_categories(session) # Will be uncommented when service exists

        logger.info("База данных успешно инициализирована")
        return _engine
        
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при инициализации БД: {e}")
        raise


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией базы данных.
    """
    if _SessionLocal is None:
        error_msg = "База данных не инициализирована. Вызовите init_db() перед использованием."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Создаём новую сессию
    session: Session = _SessionLocal()
    
    try:
        logger.debug("Создана новая сессия БД")
        yield session
        
    except SQLAlchemyError as e:
        # Откатываем транзакцию при ошибке БД
        logger.error(f"Ошибка SQLAlchemy, откат транзакции: {e}")
        session.rollback()
        raise
        
    except Exception as e:
        # Откатываем транзакцию при любой другой ошибке
        logger.error(f"Неожиданная ошибка, откат транзакции: {e}")
        session.rollback()
        raise
        
    finally:
        # Всегда закрываем сессию
        session.close()
        logger.debug("Сессия БД закрыта")


# Алиас для обратной совместимости
get_db = get_db_session
