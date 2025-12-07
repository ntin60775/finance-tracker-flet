"""
Property-based тесты для займодателей (Flet версия).

Тестирует:
- Property 35: Уникальность названия займодателя
- Property 36: Сохранение данных займодателя
- Property 37: Защита займодателей со связанными кредитами
"""

from datetime import date, timedelta
from contextlib import contextmanager
import pytest
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models.models import (
    Base,
    LenderDB,
    LoanDB,
)
from models.enums import (
    LenderType,
    LoanType,
    LoanStatus
)
from services.lender_service import (
    create_lender,
    update_lender,
    delete_lender
)
from services.loan_service import (
    create_loan
)

# Создаём тестовый движок БД в памяти
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Включает поддержку foreign keys в SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base.metadata.create_all(test_engine)
TestSessionLocal = sessionmaker(bind=test_engine)

@contextmanager
def get_test_session():
    """Контекстный менеджер для создания тестовой сессии БД."""
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем данные после использования
        session.query(LoanDB).delete()
        session.query(LenderDB).delete()
        session.commit()
        session.close()

# --- Strategies ---
lender_names = st.text(min_size=1, max_size=100).map(lambda x: x.strip()).filter(lambda x: len(x) > 0)
lender_types = st.sampled_from(LenderType)
optional_text = st.one_of(st.none(), st.text(min_size=1, max_size=200))
loan_amounts = st.floats(min_value=1000.0, max_value=10000000.0)
interest_rates = st.floats(min_value=0.0, max_value=50.0)


class TestLenderProperties:
    """Property-based тесты для управления займодателями."""

    @given(name=lender_names)
    @settings(max_examples=100, deadline=None)
    def test_property_35_lender_name_uniqueness(self, name):
        """
        Property 35: Уникальность названия займодателя.

        Feature: flet-finance-tracker, Property 35: Для любого нового займодателя,
        если займодатель с таким названием уже существует, то создание должно быть
        отклонено с ошибкой валидации

        Validates: Requirements 9.1

        Проверяет, что система запрещает создание займодателей с дублирующимися названиями.
        """
        with get_test_session() as session:
            # Arrange: создаём первого займодателя
            lender1 = create_lender(
                session=session,
                name=name,
                lender_type=LenderType.BANK
            )
            assert lender1.id is not None
            assert lender1.name == name

            # Act & Assert: попытка создать займодателя с тем же названием должна вызвать ошибку
            with pytest.raises(ValueError, match="уже существует"):
                create_lender(
                    session=session,
                    name=name,
                    lender_type=LenderType.MFO
                )

            # Verify: в БД по-прежнему только один займодатель с таким названием
            all_lenders = session.query(LenderDB).filter_by(name=name).all()
            assert len(all_lenders) == 1
            assert all_lenders[0].id == lender1.id

    @given(
        name=lender_names,
        lender_type=lender_types,
        description=optional_text,
        contact_info=optional_text,
        notes=optional_text
    )
    @settings(max_examples=100, deadline=None)
    def test_property_36_lender_data_persistence(
        self,
        name,
        lender_type,
        description,
        contact_info,
        notes
    ):
        """
        Property 36: Сохранение данных займодателя.

        Feature: flet-finance-tracker, Property 36: Для любого займодателя,
        контактная информация и примечания должны сохраняться в БД и быть
        доступны для чтения

        Validates: Requirements 9.3

        Проверяет, что все данные займодателя корректно сохраняются и читаются из БД.
        """
        with get_test_session() as session:
            # Arrange & Act: создаём займодателя со всеми данными
            lender = create_lender(
                session=session,
                name=name,
                lender_type=lender_type,
                description=description,
                contact_info=contact_info,
                notes=notes
            )

            # Flush чтобы убедиться, что данные записаны в БД
            session.flush()
            lender_id = lender.id

            # Очищаем кэш сессии (detach объект)
            session.expire_all()

            # Assert: читаем займодателя из БД заново
            retrieved_lender = session.query(LenderDB).filter_by(id=lender_id).first()

            assert retrieved_lender is not None
            assert retrieved_lender.name == name
            assert retrieved_lender.lender_type == lender_type
            assert retrieved_lender.description == description
            assert retrieved_lender.contact_info == contact_info
            assert retrieved_lender.notes == notes

    @given(
        lender_name=lender_names,
        loan_name=lender_names,
        amount=loan_amounts,
        interest_rate=interest_rates
    )
    @settings(max_examples=100, deadline=None)
    def test_property_37_protect_lenders_with_loans(
        self,
        lender_name,
        loan_name,
        amount,
        interest_rate
    ):
        """
        Property 37: Защита займодателей со связанными кредитами.

        Feature: flet-finance-tracker, Property 37: Для любого займодателя,
        если существуют кредиты от этого займодателя, то удаление должно быть
        заблокировано

        Validates: Requirements 9.4

        Проверяет, что система запрещает удаление займодателей, у которых есть активные кредиты.
        """
        # Убедимся, что имена уникальны
        assume(lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём займодателя
            lender = create_lender(
                session=session,
                name=lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            lender_id = lender.id

            # Создаём активный кредит от этого займодателя
            issue_date = date.today()
            end_date = issue_date + timedelta(days=365)  # ~12 месяцев
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date,
                interest_rate=interest_rate,
                end_date=end_date
            )
            assert loan.id is not None
            assert loan.lender_id == lender_id
            assert loan.status == LoanStatus.ACTIVE

            # Act & Assert: попытка удалить займодателя с активным кредитом должна вызвать ошибку
            with pytest.raises(ValueError, match="активные кредиты"):
                delete_lender(session, lender_id)

            # Verify: займодатель и кредит по-прежнему существуют в БД
            retrieved_lender = session.query(LenderDB).filter_by(id=lender_id).first()
            assert retrieved_lender is not None

            retrieved_loan = session.query(LoanDB).filter_by(id=loan.id).first()
            assert retrieved_loan is not None
            assert retrieved_loan.status == LoanStatus.ACTIVE

    @given(
        lender_name=lender_names,
        loan_name=lender_names,
        amount=loan_amounts,
        interest_rate=interest_rates
    )
    @settings(max_examples=100, deadline=None)
    def test_property_37_allow_delete_with_paid_loans(
        self,
        lender_name,
        loan_name,
        amount,
        interest_rate
    ):
        """
        Property 37 (расширение): Разрешение удаления займодателей с погашенными кредитами.

        Feature: flet-finance-tracker, Property 37: Для любого займодателя,
        если существуют только погашенные кредиты (PAID_OFF), то удаление разрешено

        Validates: Requirements 9.4

        Проверяет, что система разрешает удаление займодателей, у которых все кредиты погашены.
        """
        # Убедимся, что имена уникальны
        assume(lender_name != loan_name)

        with get_test_session() as session:
            # Arrange: создаём займодателя
            lender = create_lender(
                session=session,
                name=lender_name,
                lender_type=LenderType.BANK
            )
            session.flush()
            lender_id = lender.id

            # Создаём кредит от этого займодателя
            issue_date = date.today() - timedelta(days=365)
            end_date = date.today() - timedelta(days=30)  # уже прошла дата окончания
            loan = create_loan(
                session=session,
                name=loan_name,
                lender_id=lender_id,
                loan_type=LoanType.CONSUMER,
                amount=amount,
                issue_date=issue_date,
                interest_rate=interest_rate,
                end_date=end_date
            )
            assert loan.id is not None

            # Переводим кредит в статус PAID_OFF (погашен)
            loan.status = LoanStatus.PAID_OFF
            session.flush()

            # Act: удаляем займодателя с погашенным кредитом
            result = delete_lender(session, lender_id)

            # Assert: удаление успешно
            assert result is True

            # Verify: займодатель и кредит удалены из БД
            retrieved_lender = session.query(LenderDB).filter_by(id=lender_id).first()
            assert retrieved_lender is None

            # Кредит тоже должен быть удалён (cascade delete)
            retrieved_loan = session.query(LoanDB).filter_by(id=loan.id).first()
            assert retrieved_loan is None

    @given(
        original_name=lender_names,
        new_name=lender_names
    )
    @settings(max_examples=100, deadline=None)
    def test_property_35_update_name_uniqueness(self, original_name, new_name):
        """
        Property 35 (расширение): Уникальность при обновлении названия займодателя.

        Feature: flet-finance-tracker, Property 35: При обновлении названия займодателя,
        новое название также должно быть уникальным

        Validates: Requirements 9.1

        Проверяет, что система запрещает переименование займодателя в название,
        которое уже используется другим займодателем.
        """
        # Убедимся, что имена разные
        assume(original_name != new_name)

        with get_test_session() as session:
            # Arrange: создаём двух займодателей с разными именами
            lender1 = create_lender(
                session=session,
                name=original_name,
                lender_type=LenderType.BANK
            )

            _ = create_lender(
                session=session,
                name=new_name,
                lender_type=LenderType.MFO
            )

            session.flush()
            lender1_id = lender1.id

            # Act & Assert: попытка переименовать lender1 в имя lender2 должна вызвать ошибку
            with pytest.raises(ValueError, match="уже существует"):
                update_lender(
                    session=session,
                    lender_id=lender1_id,
                    name=new_name
                )

            # Verify: имя lender1 не изменилось
            session.expire_all()
            retrieved_lender1 = session.query(LenderDB).filter_by(id=lender1_id).first()
            assert retrieved_lender1.name == original_name
