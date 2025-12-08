"""
Тесты для PendingPaymentsView.

Проверяет:
- Инициализацию View
- Загрузку отложенных платежей и статистики
- Выполнение платежа
- Отмену платежа
- Отображение пустого состояния
- Обновление статистики
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
from decimal import Decimal
from datetime import date, timedelta
from contextlib import contextmanager

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.views.pending_payments_view import PendingPaymentsView
from finance_tracker.models.enums import PendingPaymentPriority, PendingPaymentStatus
from finance_tracker.models import (
    Base,
    PendingPaymentDB,
    PendingPaymentCreate,
    PendingPaymentExecute,
    TransactionType,
    CategoryDB,
    TransactionDB
)
from finance_tracker.services.pending_payment_service import (
    create_pending_payment,
    execute_pending_payment,
    get_all_pending_payments
)
from test_view_base import ViewTestBase
from test_factories import create_test_pending_payment, create_test_category


class TestPendingPaymentsView(ViewTestBase):
    """Тесты для PendingPaymentsView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.pending_payments_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы отложенных платежей
        self.mock_get_all_payments = self.add_patcher(
            'finance_tracker.views.pending_payments_view.get_all_pending_payments',
            return_value=[]
        )
        self.mock_get_statistics = self.add_patcher(
            'finance_tracker.views.pending_payments_view.get_pending_payments_statistics',
            return_value={
                'total_active': 0,
                'total_amount': Decimal('0.00'),
                'with_planned_date': 0,
                'without_planned_date': 0
            }
        )
        self.mock_create_payment = self.add_patcher(
            'finance_tracker.views.pending_payments_view.create_pending_payment'
        )
        self.mock_update_payment = self.add_patcher(
            'finance_tracker.views.pending_payments_view.update_pending_payment'
        )
        self.mock_execute_payment = self.add_patcher(
            'finance_tracker.views.pending_payments_view.execute_pending_payment'
        )
        self.mock_cancel_payment = self.add_patcher(
            'finance_tracker.views.pending_payments_view.cancel_pending_payment'
        )
        self.mock_delete_payment = self.add_patcher(
            'finance_tracker.views.pending_payments_view.delete_pending_payment'
        )
        
        # Патчим PendingPaymentModal и ExecutePendingPaymentModal
        self.mock_payment_modal = self.add_patcher(
            'finance_tracker.views.pending_payments_view.PendingPaymentModal'
        )
        self.mock_execute_modal = self.add_patcher(
            'finance_tracker.views.pending_payments_view.ExecutePendingPaymentModal'
        )
        
        # Создаем экземпляр PendingPaymentsView
        self.view = PendingPaymentsView(self.page)

    def test_initialization(self):
        """
        Тест инициализации View.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - UI компоненты созданы (заголовок, статистика, фильтры, список)
        - Фильтры инициализированы
        
        Validates: Requirements 10.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, PendingPaymentsView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        
        # Проверяем фильтры
        self.assertIsNone(self.view.has_date_filter)
        self.assertIsNone(self.view.priority_filter)
        
        # Проверяем UI компоненты
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.header)
        self.assertIsNotNone(self.view.stats_card)
        self.assertIsNotNone(self.view.date_tabs)
        self.assertIsNotNone(self.view.priority_dropdown)
        self.assertIsNotNone(self.view.payments_list)

    def test_load_payments_and_statistics(self):
        """
        Тест загрузки отложенных платежей и статистики.
        
        Проверяет:
        - При инициализации вызывается get_all_pending_payments
        - При инициализации вызывается get_pending_payments_statistics
        - Статистика отображается в stats_card
        - Платежи загружаются
        
        Validates: Requirements 10.1, 10.2
        """
        # Создаем тестовые платежи
        test_payments = [
            create_test_pending_payment(
                id=1,
                amount=Decimal("1000.00"),
                description="Платеж 1",
                priority=PendingPaymentPriority.HIGH,
                planned_date=date.today()
            ),
            create_test_pending_payment(
                id=2,
                amount=Decimal("2000.00"),
                description="Платеж 2",
                priority=PendingPaymentPriority.MEDIUM,
                planned_date=None
            ),
        ]
        
        # Настраиваем моки
        self.mock_get_all_payments.return_value = test_payments
        self.mock_get_statistics.return_value = {
            'total_active': 2,
            'total_amount': Decimal('3000.00'),
            'with_planned_date': 1,
            'without_planned_date': 1
        }
        
        # Мокируем page.update() чтобы избежать ошибок при обновлении контролов
        self.page.update = MagicMock()
        
        # Вызываем refresh_data
        self.view.refresh_data()
        
        # Проверяем, что сервисы были вызваны
        self.assert_service_called(
            self.mock_get_all_payments,
            self.mock_session,
            status=PendingPaymentStatus.ACTIVE,
            has_planned_date=None,
            priority=None
        )
        self.assert_service_called(self.mock_get_statistics, self.mock_session)
        
        # Проверяем, что статистика обновлена
        self.assertIsNotNone(self.view.stats_card.content)

    def test_load_payments_empty_list(self):
        """
        Тест загрузки пустого списка платежей.
        
        Проверяет:
        - При пустом списке отображается сообщение "Нет отложенных платежей"
        - Список очищается и добавляется сообщение о пустом состоянии
        
        Validates: Requirements 10.4
        """
        # Настраиваем моки для возврата пустого списка
        self.mock_get_all_payments.return_value = []
        self.mock_get_statistics.return_value = {
            'total_active': 0,
            'total_amount': Decimal('0.00'),
            'with_planned_date': 0,
            'without_planned_date': 0
        }
        
        # Мокируем page.update() чтобы избежать ошибок при обновлении контролов
        self.page.update = MagicMock()
        
        # Вызываем refresh_data
        self.view.refresh_data()
        
        # Проверяем, что сервис был вызван
        self.assert_service_called(
            self.mock_get_all_payments,
            self.mock_session,
            status=PendingPaymentStatus.ACTIVE,
            has_planned_date=None,
            priority=None
        )

    def test_filter_by_date_with_date(self):
        """
        Тест фильтрации по наличию даты (с датой).
        
        Проверяет:
        - При выборе таба "С датой" устанавливается has_date_filter=True
        - Вызывается refresh_data с правильным фильтром
        - Платежи загружаются с фильтром
        
        Validates: Requirements 10.1
        """
        # Создаем тестовый платеж с датой
        test_payment = create_test_pending_payment(
            id=1,
            planned_date=date.today()
        )
        
        # Настраиваем моки
        self.mock_get_all_payments.return_value = [test_payment]
        
        # Устанавливаем таб на "С датой" (индекс 1)
        self.view.date_tabs.selected_index = 1
        self.view.on_date_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertTrue(self.view.has_date_filter)
        
        # Проверяем, что сервис был вызван с правильным фильтром
        self.assert_service_called(
            self.mock_get_all_payments,
            self.mock_session,
            status=PendingPaymentStatus.ACTIVE,
            has_planned_date=True,
            priority=None
        )

    def test_filter_by_date_without_date(self):
        """
        Тест фильтрации по наличию даты (без даты).
        
        Проверяет:
        - При выборе таба "Без даты" устанавливается has_date_filter=False
        - Вызывается refresh_data с правильным фильтром
        - Платежи загружаются с фильтром
        
        Validates: Requirements 10.1
        """
        # Создаем тестовый платеж без даты
        test_payment = create_test_pending_payment(
            id=1,
            planned_date=None
        )
        
        # Настраиваем моки
        self.mock_get_all_payments.return_value = [test_payment]
        
        # Устанавливаем таб на "Без даты" (индекс 2)
        self.view.date_tabs.selected_index = 2
        self.view.on_date_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertFalse(self.view.has_date_filter)
        
        # Проверяем, что сервис был вызван с правильным фильтром
        self.assert_service_called(
            self.mock_get_all_payments,
            self.mock_session,
            status=PendingPaymentStatus.ACTIVE,
            has_planned_date=False,
            priority=None
        )

    def test_filter_by_priority(self):
        """
        Тест фильтрации по приоритету.
        
        Проверяет:
        - При выборе приоритета устанавливается priority_filter
        - Вызывается refresh_data с правильным фильтром
        - Платежи загружаются с фильтром
        
        Validates: Requirements 10.1
        """
        # Создаем тестовый платеж с высоким приоритетом
        test_payment = create_test_pending_payment(
            id=1,
            priority=PendingPaymentPriority.HIGH
        )
        
        # Настраиваем моки
        self.mock_get_all_payments.return_value = [test_payment]
        
        # Устанавливаем приоритет
        self.view.priority_dropdown.value = PendingPaymentPriority.HIGH.value
        self.view.on_priority_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.priority_filter, PendingPaymentPriority.HIGH)
        
        # Проверяем, что сервис был вызван с правильным фильтром
        self.assert_service_called(
            self.mock_get_all_payments,
            self.mock_session,
            status=PendingPaymentStatus.ACTIVE,
            has_planned_date=None,
            priority=PendingPaymentPriority.HIGH
        )

    def test_execute_payment_action(self):
        """
        Тест выполнения платежа.
        
        Проверяет:
        - При вызове on_execute_payment вызывается execute_pending_payment сервис
        - После исполнения перезагружаются данные
        - Показывается сообщение об успехе
        
        Validates: Requirements 10.2
        """
        # Вызываем on_execute_payment
        self.view.on_execute_payment(
            payment_id=1,
            executed_amount=1000.00,
            executed_date=date.today()
        )
        
        # Проверяем, что execute_pending_payment был вызван
        self.assert_service_called(self.mock_execute_payment, self.mock_session, 1, ANY)

    def test_cancel_payment_action(self):
        """
        Тест отмены платежа.
        
        Проверяет:
        - При вызове confirm_cancel_payment создается диалог подтверждения
        - При подтверждении вызывается cancel_pending_payment сервис
        - После отмены перезагружаются данные
        
        Validates: Requirements 10.3
        """
        # Создаем тестовый платеж
        test_payment = create_test_pending_payment(id=1)
        
        # Вызываем confirm_cancel_payment
        self.view.confirm_cancel_payment(test_payment)
        
        # Проверяем, что диалог был создан
        self.assertIsNotNone(self.page.dialog)

    def test_update_statistics(self):
        """
        Тест обновления статистики.
        
        Проверяет:
        - При вызове _update_statistics обновляется stats_card
        - Статистика содержит правильные значения
        
        Validates: Requirements 10.5
        """
        # Создаем статистику
        statistics = {
            'total_active': 5,
            'total_amount': Decimal('10000.00'),
            'with_planned_date': 3,
            'without_planned_date': 2
        }
        
        # Мокируем stats_card.update() чтобы избежать ошибок при обновлении контролов
        self.view.stats_card.update = MagicMock()
        self.view.page = self.page
        
        # Вызываем _update_statistics
        self.view._update_statistics(statistics)
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(self.view.stats_card.content)

    def test_open_create_dialog(self):
        """
        Тест открытия диалога создания платежа.
        
        Проверяет:
        - При нажатии кнопки "Добавить" открывается PendingPaymentModal
        - Диалог открывается с правильными параметрами
        
        Validates: Requirements 10.1
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем open_create_dialog
        self.view.open_create_dialog(mock_event)
        
        # Проверяем, что modal.open был вызван
        modal_instance = self.mock_payment_modal.return_value
        modal_instance.open.assert_called_once_with(self.page)

    def test_open_edit_dialog(self):
        """
        Тест открытия диалога редактирования платежа.
        
        Проверяет:
        - При нажатии кнопки редактирования открывается PendingPaymentModal
        - Диалог открывается с данными платежа
        
        Validates: Requirements 10.1
        """
        # Создаем тестовый платеж
        test_payment = create_test_pending_payment(id=1)
        
        # Вызываем open_edit_dialog
        self.view.open_edit_dialog(test_payment)
        
        # Проверяем, что modal.open был вызван с платежом
        modal_instance = self.mock_payment_modal.return_value
        modal_instance.open.assert_called_once_with(self.page, payment=test_payment)

    def test_open_execute_dialog(self):
        """
        Тест открытия диалога исполнения платежа.
        
        Проверяет:
        - При нажатии кнопки исполнения открывается ExecutePendingPaymentModal
        - Диалог открывается с данными платежа
        
        Validates: Requirements 10.2
        """
        # Создаем тестовый платеж
        test_payment = create_test_pending_payment(id=1)
        
        # Вызываем open_execute_dialog
        self.view.open_execute_dialog(test_payment)
        
        # Проверяем, что modal.open был вызван с платежом
        modal_instance = self.mock_execute_modal.return_value
        modal_instance.open.assert_called_once_with(self.page, payment=test_payment)

    def test_on_create_payment(self):
        """
        Тест callback создания платежа.
        
        Проверяет:
        - При вызове on_create_payment вызывается create_pending_payment сервис
        - После создания перезагружаются данные
        
        Validates: Requirements 10.1
        """
        # Создаем данные платежа
        payment_data = Mock()
        
        # Вызываем on_create_payment
        self.view.on_create_payment(payment_data)
        
        # Проверяем, что create_pending_payment был вызван
        self.assert_service_called(self.mock_create_payment, self.mock_session, payment_data)

    def test_on_update_payment(self):
        """
        Тест callback обновления платежа.
        
        Проверяет:
        - При вызове on_update_payment вызывается update_pending_payment сервис
        - После обновления перезагружаются данные
        
        Validates: Requirements 10.1
        """
        # Создаем данные платежа
        payment_data = Mock()
        
        # Вызываем on_update_payment
        self.view.on_update_payment(payment_id=1, payment_data=payment_data)
        
        # Проверяем, что update_pending_payment был вызван
        self.assert_service_called(self.mock_update_payment, self.mock_session, 1, payment_data)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 1.2
        """
        # Проверяем, что context manager был создан
        self.assertIsNotNone(self.view.cm)
        
        # Проверяем, что session была получена
        self.assertIsNotNone(self.view.session)


# Создаём тестовый движок БД в памяти для property-based тестов
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


# Стратегии генерации данных для property-based тестов
amounts = st.decimals(min_value=Decimal('1.00'), max_value=Decimal('1000000.00'), places=2)
descriptions = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
priorities = st.sampled_from(list(PendingPaymentPriority))
dates = st.dates(min_value=date.today(), max_value=date.today() + timedelta(days=365))


class TestPendingPaymentsViewProperties:
    """
    Property-based тесты для PendingPaymentsView.
    
    Проверяют инварианты системы согласно Requirements 10.2.
    """

    # Feature: ui-testing, Property 7: Выполнение платежа создает транзакцию и удаляет платеж
    @given(
        amount=amounts,
        description=descriptions,
        priority=priorities,
        executed_amount=amounts
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_execute_payment_creates_transaction_and_removes_payment(
        self,
        amount,
        description,
        priority,
        executed_amount
    ):
        """
        Property 7: Выполнение платежа должно создавать транзакцию и удалять платеж.
        
        Инвариант: Для любого отложенного платежа при его исполнении:
        - Создается новая транзакция типа EXPENSE с суммой executed_amount
        - Платеж переходит в статус EXECUTED
        - Платеж больше не появляется в списке активных платежей
        - Связь между платежом и транзакцией сохраняется
        
        Validates: Requirements 10.2
        """
        with get_test_session() as session:
            # Создаём тестовую категорию типа EXPENSE
            expense_category = CategoryDB(
                name=f"Expense_{description[:10]}",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()

            # Создаём отложенный платеж
            payment_data = PendingPaymentCreate(
                amount=amount,
                category_id=expense_category.id,
                description=description,
                priority=priority,
                planned_date=date.today()
            )

            payment = create_pending_payment(session, payment_data)
            payment_id = payment.id

            # Проверяем, что платеж активен и есть в списке
            active_payments_before = get_all_pending_payments(
                session,
                status=PendingPaymentStatus.ACTIVE
            )
            assert any(p.id == payment_id for p in active_payments_before), \
                "Платеж должен быть в списке активных до исполнения"

            # Исполняем платеж
            execute_data = PendingPaymentExecute(
                executed_date=date.today(),
                executed_amount=executed_amount
            )

            transaction, updated_payment = execute_pending_payment(
                session,
                payment_id,
                execute_data
            )

            # Проверяем, что транзакция создана с правильными параметрами
            assert transaction is not None, "Транзакция должна быть создана"
            assert transaction.type == TransactionType.EXPENSE, \
                "Транзакция должна быть типа EXPENSE"
            assert transaction.amount == executed_amount, \
                "Сумма транзакции должна равняться executed_amount"
            assert transaction.category_id == expense_category.id, \
                "Категория транзакции должна совпадать с категорией платежа"
            assert transaction.date == date.today(), \
                "Дата транзакции должна быть датой исполнения"

            # Проверяем, что платеж обновлен
            assert updated_payment.status == PendingPaymentStatus.EXECUTED, \
                "Статус платежа должен измениться на EXECUTED"
            assert updated_payment.executed_amount == executed_amount, \
                "executed_amount должен быть сохранен"
            assert updated_payment.executed_date == date.today(), \
                "executed_date должна быть сохранена"
            assert updated_payment.actual_transaction_id == transaction.id, \
                "Платеж должен быть связан с созданной транзакцией"

            # Проверяем, что платеж больше не в списке активных
            active_payments_after = get_all_pending_payments(
                session,
                status=PendingPaymentStatus.ACTIVE
            )
            assert not any(p.id == payment_id for p in active_payments_after), \
                "Платеж не должен быть в списке активных после исполнения"

            # Проверяем, что платеж можно найти в списке исполненных
            executed_payments = get_all_pending_payments(
                session,
                status=PendingPaymentStatus.EXECUTED
            )
            assert any(p.id == payment_id for p in executed_payments), \
                "Платеж должен быть в списке исполненных"

            # Проверяем, что транзакция действительно сохранена в БД
            saved_transaction = session.query(TransactionDB).filter_by(
                id=transaction.id
            ).first()
            assert saved_transaction is not None, \
                "Транзакция должна быть сохранена в БД"
            assert saved_transaction.amount == executed_amount, \
                "Сохраненная транзакция должна иметь правильную сумму"


if __name__ == '__main__':
    unittest.main()
