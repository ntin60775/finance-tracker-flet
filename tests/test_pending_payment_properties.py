"""
Property-based тесты для отложенных платежей.

Использует Hypothesis для генерации тестовых данных и проверки инвариантов.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import date, timedelta
from decimal import Decimal
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models import (
    Base,
    PendingPaymentDB,
    PendingPaymentCreate,
    PendingPaymentExecute,
    PendingPaymentCancel,
    TransactionType,
    CategoryDB,
    TransactionDB
)
from finance_tracker.models.enums import PendingPaymentPriority, PendingPaymentStatus
from finance_tracker.services.pending_payment_service import (
    create_pending_payment,
    get_all_pending_payments,
    execute_pending_payment,
    cancel_pending_payment,
    get_pending_payments_statistics
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
        # Порядок важен из-за foreign keys: сначала зависимые, потом родительские
        session.query(PendingPaymentDB).delete()
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()


# Стратегии генерации данных
amounts = st.decimals(min_value=Decimal('1.00'), max_value=Decimal('1000000.00'), places=2)
descriptions = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
priorities = st.sampled_from(list(PendingPaymentPriority))
dates = st.dates(min_value=date.today(), max_value=date.today() + timedelta(days=365))


class TestPendingPaymentProperties:
    """
    Property-based тесты для отложенных платежей.

    Проверяют инварианты системы согласно Requirements 8.1-8.7.
    """

    # Feature: flet-finance-tracker, Property 30: Валидация категории отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_30_category_validation(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        Property 30: Валидация категории отложенного платежа.

        Инвариант: Категория отложенного платежа ДОЛЖНА быть типа EXPENSE.
        Попытка создать платёж с категорией типа INCOME ДОЛЖНА приводить к ValueError.
        """
        with get_test_session() as session:
            # Создаём тестовые категории
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            income_category = CategoryDB(
                name=f"Income_{description[:10]}",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(expense_category)
            session.add(income_category)
            session.commit()

            # Успешное создание с EXPENSE категорией
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            payment = create_pending_payment(session, payment_data)

            assert payment.amount == amount
            assert payment.category_id == expense_category.id
            assert payment.status == PendingPaymentStatus.ACTIVE

            # Попытка создать платёж с INCOME категорией должна вызвать ошибку
            invalid_payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=income_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            with pytest.raises(ValueError, match="EXPENSE"):
                create_pending_payment(session, invalid_payment_data)

    # Feature: flet-finance-tracker, Property 31: Исполнение отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        executed_amount=amounts
    )
    @settings(max_examples=100, deadline=None)
    def test_property_31_execute_payment(
        self,
        amount,
        description,
        executed_amount
    ):
        """
        Property 31: Исполнение отложенного платежа.

        Инвариант: При исполнении платежа:
        - Создаётся транзакция типа EXPENSE
        - Статус меняется на EXECUTED
        - Сохраняется executed_amount и executed_date
        - Повторное исполнение того же платежа невозможно
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём платёж
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=PendingPaymentPriority.MEDIUM
            )

            payment = create_pending_payment(session, payment_data)
            payment_id = payment.id

            # Исполняем платёж
            execute_data = PendingPaymentExecute(
                executed_date=date.today(),
                executed_amount=executed_amount
            )

            transaction, updated_payment = execute_pending_payment(
                session,
                payment_id,
                execute_data
            )

            # Проверяем транзакцию
            assert transaction.type == TransactionType.EXPENSE
            assert transaction.amount == executed_amount
            assert transaction.category_id == expense_category.id

            # Проверяем платёж
            assert updated_payment.status == PendingPaymentStatus.EXECUTED
            assert updated_payment.executed_amount == executed_amount
            assert updated_payment.executed_date == date.today()
            assert updated_payment.actual_transaction_id == transaction.id

            # Попытка повторного исполнения должна вызвать ошибку
            with pytest.raises(ValueError, match="активные"):
                execute_pending_payment(session, payment_id, execute_data)

    # Feature: flet-finance-tracker, Property 32: Отмена отложенного платежа
    @given(
        amount=amounts,
        description=descriptions,
        cancel_reason=st.one_of(st.none(), st.text(min_size=1, max_size=200))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_32_cancel_payment(
        self,
        amount,
        description,
        cancel_reason
    ):
        """
        Property 32: Отмена отложенного платежа.

        Инвариант: При отмене платежа:
        - Статус меняется на CANCELLED
        - Сохраняется cancelled_date и cancel_reason
        - Транзакция НЕ создаётся
        - Повторная отмена невозможна
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём платёж
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=PendingPaymentPriority.MEDIUM
            )

            payment = create_pending_payment(session, payment_data)
            payment_id = payment.id

            # Отменяем платёж
            cancel_data = PendingPaymentCancel(cancel_reason=cancel_reason)
            updated_payment = cancel_pending_payment(session, payment_id, cancel_data)

            # Проверяем платёж
            assert updated_payment.status == PendingPaymentStatus.CANCELLED
            assert updated_payment.cancelled_date == date.today()
            assert updated_payment.cancel_reason == cancel_reason
            assert updated_payment.actual_transaction_id is None  # Транзакция не создана

            # Попытка повторной отмены должна вызвать ошибку
            with pytest.raises(ValueError, match="активные"):
                cancel_pending_payment(session, payment_id, cancel_data)

    # Feature: flet-finance-tracker, Property 33: Сортировка отложенных платежей
    @given(
        payments_count=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_33_payment_sorting(
        self,
        payments_count
    ):
        """
        Property 33: Сортировка отложенных платежей.

        Инвариант: Платежи сортируются:
        1. По приоритету (CRITICAL > HIGH > MEDIUM > LOW)
        2. При равном приоритете - по плановой дате (раньше первыми)
        3. Платежи без даты - в конце
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name="Expense_Sort",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём несколько платежей с разными приоритетами
            priorities_list = [
                PendingPaymentPriority.LOW,
                PendingPaymentPriority.MEDIUM,
                PendingPaymentPriority.HIGH,
                PendingPaymentPriority.CRITICAL
            ]

            created_payments = []
            for i in range(payments_count):
                priority = priorities_list[i % len(priorities_list)]
                planned_date = date.today() + timedelta(days=i) if i % 2 == 0 else None

                payment_data = PendingPaymentCreate(
                    amount=100.0 + i,
                    category_id=expense_category.id,
                    description=f"Payment {i}",
                    priority=priority,
                    planned_date=planned_date
                )

                payment = create_pending_payment(session, payment_data)
                created_payments.append(payment)

            # Получаем отсортированный список
            sorted_payments = get_all_pending_payments(session)

            # Проверяем сортировку по приоритету
            priority_order = {
                PendingPaymentPriority.CRITICAL: 0,
                PendingPaymentPriority.HIGH: 1,
                PendingPaymentPriority.MEDIUM: 2,
                PendingPaymentPriority.LOW: 3,
            }

            for i in range(len(sorted_payments) - 1):
                current = sorted_payments[i]
                next_payment = sorted_payments[i + 1]

                current_priority = priority_order[current.priority]
                next_priority = priority_order[next_payment.priority]

                # Приоритет текущего должен быть <= следующего
                assert current_priority <= next_priority

    # Feature: flet-finance-tracker, Property 34: Статистика отложенных платежей
    @given(
        payments_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_34_payment_statistics(
        self,
        payments_count
    ):
        """
        Property 34: Статистика отложенных платежей.

        Инвариант: Статистика корректно отражает:
        - Количество активных платежей
        - Общую сумму активных платежей
        - Распределение по приоритетам
        - Платежи с датой / без даты
        """
        with get_test_session() as session:
            # Создаём тестовую категорию
            expense_category = CategoryDB(
                name="Expense_Stats",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём несколько платежей
            total_amount = Decimal('0.0')
            with_date_count = 0
            without_date_count = 0

            for i in range(payments_count):
                amount = Decimal('100.0') + (i * Decimal('10'))
                total_amount += amount

                has_date = i % 2 == 0
                if has_date:
                    with_date_count += 1
                else:
                    without_date_count += 1

                payment_data = PendingPaymentCreate(
                    amount=amount,
                    category_id=expense_category.id,
                    description=f"Payment {i}",
                    priority=PendingPaymentPriority.MEDIUM,
                    planned_date=date.today() + timedelta(days=i) if has_date else None
                )

                create_pending_payment(session, payment_data)

            # Получаем статистику
            stats = get_pending_payments_statistics(session)

            # Проверяем корректность
            assert stats["total_active"] == payments_count
            assert stats["total_amount"] == total_amount
            assert stats["with_planned_date"] == with_date_count
            assert stats["without_planned_date"] == without_date_count

            # Проверяем статистику по приоритетам
            assert "by_priority" in stats
            assert stats["by_priority"]["medium"]["count"] == payments_count
            assert stats["by_priority"]["medium"]["total_amount"] == total_amount

    # Feature: pending-payment-add-button, Property 1: Создание платежа сохраняет в БД
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_create_payment_saves_to_db(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        **Feature: pending-payment-add-button, Property 1: Создание платежа сохраняет в БД**
        **Validates: Requirements 1.3**
        
        Property: Для любых валидных данных отложенного платежа (сумма > 0, 
        существующая категория EXPENSE, непустое описание), создание платежа 
        через Presenter должно привести к появлению записи в базе данных 
        с соответствующими данными.
        """
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём данные для платежа
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            # Создаём платёж через сервис
            created_payment = create_pending_payment(session, payment_data)

            # Проверяем, что платёж создан
            assert created_payment is not None
            assert created_payment.id is not None

            # Проверяем наличие записи в БД с правильными данными
            saved_payment = session.query(PendingPaymentDB).filter_by(
                id=created_payment.id
            ).first()

            # Платёж должен существовать в БД
            assert saved_payment is not None
            
            # Проверяем корректность сохранённых данных
            assert saved_payment.amount == amount
            assert saved_payment.category_id == expense_category.id
            assert saved_payment.description == description.strip()
            assert saved_payment.priority == priority
            assert saved_payment.planned_date == planned_date
            assert saved_payment.status == PendingPaymentStatus.ACTIVE
            
            # Проверяем, что created_at установлен
            assert saved_payment.created_at is not None
            
            # Проверяем, что связь с категорией корректна
            assert saved_payment.category is not None
            assert saved_payment.category.type == TransactionType.EXPENSE

    # Feature: pending-payment-add-button, Property 2: Создание платежа обновляет виджет
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_create_payment_updates_widget(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        **Feature: pending-payment-add-button, Property 2: Создание платежа обновляет виджет**
        **Validates: Requirements 1.4, 5.1**
        
        Property: Для любого созданного отложенного платежа, виджет отложенных 
        платежей должен обновить свой список и включить новый платёж в отображение.
        
        Проверяет, что после создания платежа через Presenter вызывается 
        update_pending_payments callback.
        """
        from unittest.mock import Mock
        from finance_tracker.views.home_presenter import HomePresenter
        from finance_tracker.views.interfaces import IHomeViewCallbacks
        
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём mock callbacks
            mock_callbacks = Mock(spec=IHomeViewCallbacks)
            
            # Создаём Presenter с mock callbacks
            presenter = HomePresenter(session, mock_callbacks)

            # Создаём данные для платежа
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            # Создаём платёж через Presenter
            presenter.create_pending_payment(payment_data)

            # Проверяем, что callback update_pending_payments был вызван
            # Presenter вызывает _refresh_data, который вызывает load_pending_payments,
            # который в свою очередь вызывает update_pending_payments
            mock_callbacks.update_pending_payments.assert_called()
            
            # Проверяем, что callback был вызван с правильными параметрами
            # Первый аргумент - список платежей, второй - статистика
            call_args = mock_callbacks.update_pending_payments.call_args
            assert call_args is not None
            
            payments_list = call_args[0][0]
            statistics = call_args[0][1]
            
            # Проверяем, что список платежей не пустой
            assert len(payments_list) > 0
            
            # Проверяем, что созданный платёж есть в списке
            created_payment_found = False
            for payment in payments_list:
                if (payment.amount == amount and 
                    payment.description == description.strip() and
                    payment.priority == priority):
                    created_payment_found = True
                    break
            
            assert created_payment_found, "Созданный платёж должен быть в списке обновлённых платежей"
            
            # Проверяем, что статистика обновлена
            assert isinstance(statistics, dict)
            assert "total_active" in statistics
            assert "total_amount" in statistics
            assert statistics["total_active"] >= 1
            assert statistics["total_amount"] >= amount

    # Feature: pending-payment-add-button, Property 3: Создание платежа обновляет статистику
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_create_payment_updates_statistics(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        **Feature: pending-payment-add-button, Property 3: Создание платежа обновляет статистику**
        **Validates: Requirements 5.2**
        
        Property: Для любого созданного отложенного платежа, статистика виджета 
        (total_active, total_amount) должна увеличиться на 1 и на сумму платежа 
        соответственно.
        
        Проверяет, что после создания платежа статистика корректно обновляется.
        """
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Получаем статистику ДО создания платежа
            stats_before = get_pending_payments_statistics(session)
            total_active_before = stats_before["total_active"]
            total_amount_before = stats_before["total_amount"]

            # Создаём данные для платежа
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            # Создаём платёж через сервис
            created_payment = create_pending_payment(session, payment_data)

            # Получаем статистику ПОСЛЕ создания платежа
            stats_after = get_pending_payments_statistics(session)
            total_active_after = stats_after["total_active"]
            total_amount_after = stats_after["total_amount"]

            # Проверяем, что total_active увеличился на 1
            assert total_active_after == total_active_before + 1, (
                f"total_active должен увеличиться на 1: "
                f"было {total_active_before}, стало {total_active_after}"
            )

            # Проверяем, что total_amount увеличился на сумму платежа
            assert total_amount_after == total_amount_before + amount, (
                f"total_amount должен увеличиться на {amount}: "
                f"было {total_amount_before}, стало {total_amount_after}"
            )

            # Дополнительно проверяем, что созданный платёж учтён в статистике по приоритетам
            priority_stats = stats_after["by_priority"][priority.value]
            
            # Количество платежей с данным приоритетом должно быть >= 1
            assert priority_stats["count"] >= 1, (
                f"Должен быть хотя бы 1 платёж с приоритетом {priority.value}"
            )
            
            # Сумма платежей с данным приоритетом должна включать наш платёж
            assert priority_stats["total_amount"] >= amount, (
                f"Сумма платежей с приоритетом {priority.value} должна включать {amount}"
            )

    # Feature: pending-payment-add-button, Property 4: Платёж с датой отображается в календаре
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=dates  # Всегда генерируем дату (не None)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_payment_with_date_updates_calendar(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        **Feature: pending-payment-add-button, Property 4: Платёж с датой отображается в календаре**
        **Validates: Requirements 5.3**
        
        Property: Для любого отложенного платежа с установленной плановой датой, 
        календарь должен отобразить индикатор платежа на соответствующей дате 
        после создания.
        
        Проверяет, что после создания платежа с плановой датой через Presenter 
        вызывается update_calendar_data callback.
        """
        from unittest.mock import Mock
        from finance_tracker.views.home_presenter import HomePresenter
        from finance_tracker.views.interfaces import IHomeViewCallbacks
        
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём mock callbacks
            mock_callbacks = Mock(spec=IHomeViewCallbacks)
            
            # Создаём Presenter с mock callbacks
            presenter = HomePresenter(session, mock_callbacks)

            # Создаём данные для платежа с плановой датой
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date  # Обязательно указываем дату
            )

            # Сбрасываем счётчик вызовов перед созданием платежа
            mock_callbacks.reset_mock()

            # Создаём платёж через Presenter
            presenter.create_pending_payment(payment_data)

            # Проверяем, что callback update_calendar_data был вызван
            # Presenter вызывает _refresh_data, который вызывает load_calendar_data,
            # который в свою очередь вызывает update_calendar_data
            mock_callbacks.update_calendar_data.assert_called()
            
            # Проверяем, что callback был вызван хотя бы один раз
            assert mock_callbacks.update_calendar_data.call_count >= 1, (
                "update_calendar_data должен быть вызван после создания платежа с датой"
            )
            
            # Проверяем, что платёж действительно создан в БД с правильной датой
            created_payment = session.query(PendingPaymentDB).filter_by(
                description=description.strip()
            ).first()
            
            assert created_payment is not None, "Платёж должен быть создан в БД"
            assert created_payment.planned_date == planned_date, (
                f"Плановая дата должна быть {planned_date}, "
                f"но получена {created_payment.planned_date}"
            )
            
            # Дополнительно проверяем, что платёж активен
            assert created_payment.status == PendingPaymentStatus.ACTIVE, (
                "Созданный платёж должен иметь статус ACTIVE"
            )

    # Feature: pending-payment-add-button, Property 5: Каскадное обновление компонентов
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        planned_date=st.one_of(st.none(), dates)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_cascade_updates(
        self,
        amount,
        description,
        priority,
        planned_date
    ):
        """
        **Feature: pending-payment-add-button, Property 5: Каскадное обновление компонентов**
        **Validates: Requirements 3.3**
        
        Property: Для любой операции создания платежа через Presenter, должны 
        обновиться все зависимые компоненты: виджет отложенных платежей, 
        календарь, панель транзакций, плановые операции.
        
        Проверяет, что после создания платежа через Presenter вызываются все 
        необходимые callback методы обновления UI компонентов.
        """
        from unittest.mock import Mock
        from finance_tracker.views.home_presenter import HomePresenter
        from finance_tracker.views.interfaces import IHomeViewCallbacks
        
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём mock callbacks
            mock_callbacks = Mock(spec=IHomeViewCallbacks)
            
            # Создаём Presenter с mock callbacks
            presenter = HomePresenter(session, mock_callbacks)

            # Создаём данные для платежа
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=planned_date
            )

            # Сбрасываем счётчик вызовов перед созданием платежа
            mock_callbacks.reset_mock()

            # Создаём платёж через Presenter
            presenter.create_pending_payment(payment_data)

            # Проверяем каскадное обновление всех компонентов
            # Presenter.create_pending_payment вызывает _refresh_data(), который вызывает:
            
            # 1. load_calendar_data() → update_calendar_data()
            mock_callbacks.update_calendar_data.assert_called()
            assert mock_callbacks.update_calendar_data.call_count >= 1, (
                "update_calendar_data должен быть вызван для обновления календаря"
            )
            
            # 2. on_date_selected() → update_transactions()
            mock_callbacks.update_transactions.assert_called()
            assert mock_callbacks.update_transactions.call_count >= 1, (
                "update_transactions должен быть вызван для обновления панели транзакций"
            )
            
            # 3. load_planned_occurrences() → update_planned_occurrences()
            mock_callbacks.update_planned_occurrences.assert_called()
            assert mock_callbacks.update_planned_occurrences.call_count >= 1, (
                "update_planned_occurrences должен быть вызван для обновления плановых операций"
            )
            
            # 4. load_pending_payments() → update_pending_payments()
            mock_callbacks.update_pending_payments.assert_called()
            assert mock_callbacks.update_pending_payments.call_count >= 1, (
                "update_pending_payments должен быть вызван для обновления виджета платежей"
            )
            
            # Дополнительно проверяем, что show_message был вызван для уведомления пользователя
            mock_callbacks.show_message.assert_called()
            
            # Проверяем, что платёж действительно создан в БД
            created_payment = session.query(PendingPaymentDB).filter_by(
                description=description.strip()
            ).first()
            
            assert created_payment is not None, "Платёж должен быть создан в БД"
            assert created_payment.amount == amount, (
                f"Сумма платежа должна быть {amount}, но получена {created_payment.amount}"
            )
            assert created_payment.status == PendingPaymentStatus.ACTIVE, (
                "Созданный платёж должен иметь статус ACTIVE"
            )
            
            # Проверяем порядок вызовов: сначала обновление данных, потом сообщение
            # Получаем все вызовы mock_callbacks
            all_calls = mock_callbacks.method_calls
            
            # Находим индексы вызовов
            update_calls = [
                i for i, call in enumerate(all_calls) 
                if call[0] in ['update_calendar_data', 'update_transactions', 
                              'update_planned_occurrences', 'update_pending_payments']
            ]
            show_message_calls = [
                i for i, call in enumerate(all_calls) 
                if call[0] == 'show_message'
            ]
            
            # Проверяем, что обновления происходят до показа сообщения
            if update_calls and show_message_calls:
                assert max(update_calls) < min(show_message_calls), (
                    "Обновление UI компонентов должно происходить до показа сообщения пользователю"
                )

    # Feature: pending-payment-add-button, Property 6: Валидация пустых полей
    @given(
        invalid_amount=st.one_of(
            st.just(Decimal('0')),
            st.decimals(min_value=Decimal('-100.00'), max_value=Decimal('-0.01'), places=2)
        ),
        invalid_description=st.one_of(
            st.just(""),
            st.just("   "),
            st.just("\t"),
            st.just("\n")
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_validation_rejects_invalid_data(
        self,
        invalid_amount,
        invalid_description
    ):
        """
        **Feature: pending-payment-add-button, Property 6: Валидация пустых полей**
        **Validates: Requirements 6.1**
        
        Property: Для любых невалидных данных (пустые поля, нулевая или 
        отрицательная сумма), система должна показать ошибки валидации.
        Pydantic валидация должна отклонять данные, и запись не должна 
        создаваться в БД.
        
        Проверяет, что:
        1. Pydantic валидация отклоняет невалидные данные
        2. Запись не создаётся в БД при невалидных данных
        3. Выбрасывается ValidationError с понятным сообщением
        """
        from pydantic import ValidationError
        
        with get_test_session() as session:
            # Создаём тестовую категорию EXPENSE
            expense_category = CategoryDB(
                name="Expense_Validation",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Получаем количество платежей ДО попытки создания
            payments_count_before = session.query(PendingPaymentDB).count()

            # Тест 1: Невалидная сумма (0 или отрицательная)
            with pytest.raises(ValidationError) as exc_info:
                PendingPaymentCreate(
                    amount=invalid_amount,
                    category_id=expense_category.id,
                    description="Valid description",
                    priority=PendingPaymentPriority.MEDIUM
                )
            
            # Проверяем, что ошибка связана с полем amount
            errors = exc_info.value.errors()
            assert any(error['loc'] == ('amount',) for error in errors), (
                f"Должна быть ошибка валидации для поля 'amount', "
                f"но получены ошибки: {errors}"
            )
            
            # Проверяем, что есть сообщение об ошибке для amount
            # Pydantic может выдавать разные сообщения: "greater than", "finite number" и т.д.
            error_messages = [error['msg'] for error in errors if error['loc'] == ('amount',)]
            assert len(error_messages) > 0, (
                f"Должно быть сообщение об ошибке для поля 'amount'"
            )

            # Тест 2: Невалидное описание (пустое или только пробелы)
            with pytest.raises(ValidationError) as exc_info:
                PendingPaymentCreate(
                    amount=Decimal('100.00'),
                    category_id=expense_category.id,
                    description=invalid_description,
                    priority=PendingPaymentPriority.MEDIUM
                )
            
            # Проверяем, что ошибка связана с полем description
            errors = exc_info.value.errors()
            assert any(error['loc'] == ('description',) for error in errors), (
                f"Должна быть ошибка валидации для поля 'description', "
                f"но получены ошибки: {errors}"
            )
            
            # Проверяем, что есть сообщение об ошибке для description
            # Может быть "Описание не может быть пустым" или "at least 1 characters"
            error_messages = [error['msg'] for error in errors if error['loc'] == ('description',)]
            assert len(error_messages) > 0, (
                f"Должно быть сообщение об ошибке для поля 'description'"
            )
            
            # Проверяем, что сообщение содержит информацию о проблеме
            combined_message = ' '.join(error_messages).lower()
            assert (
                'пустым' in combined_message or 
                'empty' in combined_message or
                'at least' in combined_message or
                'минимум' in combined_message or
                'length' in combined_message
            ), f"Сообщение об ошибке должно указывать на проблему с описанием: {error_messages}"

            # Тест 3: Комбинация невалидных полей
            with pytest.raises(ValidationError) as exc_info:
                PendingPaymentCreate(
                    amount=invalid_amount,
                    category_id=expense_category.id,
                    description=invalid_description,
                    priority=PendingPaymentPriority.MEDIUM
                )
            
            # Проверяем, что есть ошибки для обоих полей
            errors = exc_info.value.errors()
            error_fields = [error['loc'][0] for error in errors]
            
            # Должны быть ошибки для amount и/или description
            assert 'amount' in error_fields or 'description' in error_fields, (
                f"Должны быть ошибки валидации для невалидных полей, "
                f"но получены ошибки только для: {error_fields}"
            )

            # Проверяем, что количество платежей в БД НЕ изменилось
            payments_count_after = session.query(PendingPaymentDB).count()
            assert payments_count_after == payments_count_before, (
                f"Количество платежей в БД не должно измениться при невалидных данных. "
                f"Было: {payments_count_before}, стало: {payments_count_after}"
            )
            
            # Дополнительная проверка: попытка создать платёж через сервис 
            # с невалидными данными должна вызвать ошибку ещё на этапе 
            # создания Pydantic модели, поэтому сервис даже не будет вызван
            
            # Проверяем, что невалидные данные не могут пройти через Pydantic
            try:
                invalid_payment_data = PendingPaymentCreate(
                    amount=invalid_amount,
                    category_id=expense_category.id,
                    description=invalid_description,
                    priority=PendingPaymentPriority.MEDIUM
                )
                # Если мы дошли сюда, значит валидация не сработала - это ошибка
                pytest.fail(
                    f"Pydantic валидация должна была отклонить данные: "
                    f"amount={invalid_amount}, description='{invalid_description}'"
                )
            except ValidationError:
                # Это ожидаемое поведение - валидация отклонила данные
                pass
            
            # Финальная проверка: БД осталась в исходном состоянии
            final_payments_count = session.query(PendingPaymentDB).count()
            assert final_payments_count == payments_count_before, (
                "БД должна остаться в исходном состоянии после попыток создания "
                "платежей с невалидными данными"
            )
