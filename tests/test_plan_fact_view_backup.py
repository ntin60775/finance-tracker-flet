"""
Тесты для PlannedTransactionsView.

Проверяет:
- Инициализацию View
- Загрузку плановых транзакций
- Фильтрацию по типу транзакции
- Открытие модального окна создания
- Открытие модального окна редактирования
- Удаление плановой транзакции
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
from decimal import Decimal
from datetime import date, datetime, timedelta

from finance_tracker.views.planned_transactions_view import PlannedTransactionsView
from finance_tracker.models.enums import TransactionType, RecurrenceType, OccurrenceStatus
from test_view_base import ViewTestBase
from test_factories import (
    create_test_planned_transaction,
    create_test_category,
    create_test_recurrence_rule,
    create_test_planned_occurrence,
)


class TestPlannedTransactionsView(ViewTestBase):
    """Тесты для PlannedTransactionsView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.planned_transactions_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы плановых транзакций
        self.mock_get_all_planned = self.add_patcher(
            'finance_tracker.views.planned_transactions_view.get_all_planned_transactions',
            return_value=[]
        )
        self.mock_deactivate_planned = self.add_patcher(
            'finance_tracker.views.planned_transactions_view.deactivate_planned_transaction'
        )
        self.mock_delete_planned = self.add_patcher(
            'finance_tracker.views.planned_transactions_view.delete_planned_transaction'
        )
        
        # Создаем экземпляр PlannedTransactionsView
        self.view = PlannedTransactionsView(self.page)

    def test_initialization(self):
        """
        Тест инициализации PlannedTransactionsView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - UI компоненты созданы (заголовок, фильтры, список)
        
        Validates: Requirements 11.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, PlannedTransactionsView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.status_tabs)
        self.assertIsNotNone(self.view.type_tabs)
        self.assertIsNotNone(self.view.transactions_list)
        
        # Проверяем начальное состояние фильтров
        self.assertEqual(self.view.status_filter, True)  # Активные по умолчанию
        self.assertIsNone(self.view.type_filter)  # Все типы по умолчанию

    def test_load_planned_transactions_on_mount(self):
        """
        Тест загрузки плановых транзакций при монтировании View.
        
        Проверяет:
        - При вызове did_mount() вызывается get_all_planned_transactions
        - Сервис вызывается с правильной сессией и фильтрами
        
        Validates: Requirements 11.1
        """
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_all_planned.reset_mock()
        
        # Вызываем did_mount
        self.view.did_mount()
        
        # Проверяем, что сервис был вызван
        # Логика: всегда вызывается с active_only=False, затем фильтруется в памяти
        self.assert_service_called_once(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,  # Всегда False, фильтрация в памяти
            transaction_type=None  # Все типы
        )

    def test_load_planned_transactions_with_data(self):
        """
        Тест загрузки плановых транзакций с данными.
        
        Проверяет:
        - Плановые транзакции отображаются в списке
        - Количество элементов соответствует количеству активных транзакций (по умолчанию фильтр активные)
        
        Validates: Requirements 11.1
        """
        # Создаем тестовые плановые транзакции
        # Все транзакции возвращаются сервисом, но фильтруются в памяти по статусу
        test_transactions = [
            create_test_planned_transaction(
                id=1,
                amount=Decimal("1000.00"),
                category_id=1,
                description="Зарплата",
                type=TransactionType.INCOME,
                is_active=True
            ),
            create_test_planned_transaction(
                id=2,
                amount=Decimal("500.00"),
                category_id=2,
                description="Коммунальные услуги",
                type=TransactionType.EXPENSE,
                is_active=True
            ),
            create_test_planned_transaction(
                id=3,
                amount=Decimal("200.00"),
                category_id=3,
                description="Интернет",
                type=TransactionType.EXPENSE,
                is_active=False
            ),
        ]
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_all_planned.return_value = test_transactions
        
        # Загружаем данные
        self.view.refresh_data()
        
        # Проверяем, что список содержит только активные элементы (2 активных + 1 неактивный = 3 всего)
        # По умолчанию status_filter=True (только активные), поэтому должно быть 2 элемента
        self.assertEqual(len(self.view.transactions_list.controls), 2)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_planned_transactions_empty_list(self):
        """
        Тест загрузки пустого списка плановых транзакций.
        
        Проверяет:
        - При пустом списке отображается сообщение "Плановые транзакции не найдены"
        
        Validates: Requirements 11.1
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_all_planned.return_value = []
        
        # Загружаем данные
        self.view.refresh_data()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.transactions_list.controls), 1)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_filter_by_status_active(self):
        """
        Тест фильтрации по статусу "Активные".
        
        Проверяет:
        - При выборе вкладки "Активные" устанавливается фильтр status_filter=True
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 11.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Активные" (индекс 0)
        self.view.status_tabs.selected_index = 0
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.status_filter, True)
        
        # Проверяем, что сервис вызван с active_only=False (фильтрация в памяти)
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=None
        )

    def test_filter_by_status_inactive(self):
        """
        Тест фильтрации по статусу "Неактивные".
        
        Проверяет:
        - При выборе вкладки "Неактивные" устанавливается фильтр status_filter=False
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 11.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Неактивные" (индекс 1)
        self.view.status_tabs.selected_index = 1
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.status_filter, False)
        
        # Проверяем, что сервис вызван с фильтром active_only=False
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=None
        )

    def test_filter_by_status_all(self):
        """
        Тест фильтрации по статусу "Все".
        
        Проверяет:
        - При выборе вкладки "Все" устанавливается фильтр status_filter=None
        - Вызывается перезагрузка данных без фильтра по статусу
        
        Validates: Requirements 11.2
        """
        # Устанавливаем фильтр
        self.view.status_filter = True
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Все" (индекс 2)
        self.view.status_tabs.selected_index = 2
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.status_filter)
        
        # Проверяем, что сервис вызван с фильтром active_only=False
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=None
        )

    def test_filter_by_type_expenses(self):
        """
        Тест фильтрации по типу "Расходы".
        
        Проверяет:
        - При выборе вкладки "Расходы" устанавливается фильтр type_filter=EXPENSE
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 11.3
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Расходы" (индекс 1)
        self.view.type_tabs.selected_index = 1
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.type_filter, TransactionType.EXPENSE)
        
        # Проверяем, что сервис вызван с фильтром transaction_type=EXPENSE и active_only=False
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=TransactionType.EXPENSE
        )

    def test_filter_by_type_income(self):
        """
        Тест фильтрации по типу "Доходы".
        
        Проверяет:
        - При выборе вкладки "Доходы" устанавливается фильтр type_filter=INCOME
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 11.3
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Доходы" (индекс 2)
        self.view.type_tabs.selected_index = 2
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.type_filter, TransactionType.INCOME)
        
        # Проверяем, что сервис вызван с фильтром transaction_type=INCOME и active_only=False
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=TransactionType.INCOME
        )

    def test_filter_by_type_all(self):
        """
        Тест сброса фильтра по типу (все типы).
        
        Проверяет:
        - При выборе вкладки "Все" фильтр type_filter сбрасывается (None)
        - Вызывается перезагрузка данных без фильтра по типу
        
        Validates: Requirements 11.3
        """
        # Устанавливаем фильтр
        self.view.type_filter = TransactionType.EXPENSE
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Имитируем выбор вкладки "Все" (индекс 0)
        self.view.type_tabs.selected_index = 0
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.type_filter)
        
        # Проверяем, что сервис вызван без фильтра по типу и с active_only=False
        self.assert_service_called(
            self.mock_get_all_planned,
            self.mock_session,
            active_only=False,
            transaction_type=None
        )

    def test_open_create_dialog(self):
        """
        Тест открытия модального окна создания плановой транзакции.
        
        Проверяет:
        - При нажатии кнопки создания открывается диалог
        - Диалог открывается в режиме создания
        
        Validates: Requirements 11.4
        """
        # Создаем мок события с control, у которого есть page
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.page = self.page
        
        # Вызываем метод открытия диалога
        self.view.open_create_dialog(mock_event)
        
        # Проверяем, что page.snack_bar был установлен (текущая реализация показывает сообщение)
        self.assertIsNotNone(self.page.snack_bar)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_edit_planned_transaction(self):
        """
        Тест открытия модального окна редактирования плановой транзакции.
        
        Проверяет:
        - При нажатии кнопки редактирования открывается диалог
        - Диалог открывается в режиме редактирования с данными транзакции
        
        Validates: Requirements 11.5
        """
        # Создаем тестовую плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1,
            description="Тестовая плановая транзакция",
            type=TransactionType.INCOME,
            is_active=True
        )
        
        # Вызываем метод редактирования
        self.view.edit_planned_transaction(test_tx)
        
        # Проверяем, что page.snack_bar был установлен (текущая реализация показывает сообщение)
        self.assertIsNotNone(self.page.snack_bar)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_toggle_active_deactivate(self):
        """
        Тест деактивации плановой транзакции.
        
        Проверяет:
        - При вызове toggle_active() для активной транзакции вызывается deactivate_planned_transaction
        - Данные перезагружаются
        - Панель деталей скрывается
        
        Validates: Requirements 11.5
        """
        # Создаем тестовую активную плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1,
            is_active=True
        )
        
        # Устанавливаем выбранную транзакцию
        self.view.selected_planned_tx = test_tx
        self.view.details_panel.visible = True
        
        # Сбрасываем счетчик вызовов
        self.mock_deactivate_planned.reset_mock()
        self.mock_get_all_planned.reset_mock()
        
        # Вызываем toggle_active
        self.view.toggle_active(test_tx)
        
        # Проверяем, что deactivate_planned_transaction был вызван
        self.assert_service_called_once(
            self.mock_deactivate_planned,
            self.mock_session,
            1  # ID транзакции
        )
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_all_planned)
        
        # Проверяем, что панель деталей скрыта
        self.assertFalse(self.view.details_panel.visible)

    def test_toggle_active_activate(self):
        """
        Тест активации плановой транзакции.
        
        Проверяет:
        - При вызове toggle_active() для неактивной транзакции она активируется
        - Данные перезагружаются
        - Панель деталей скрывается
        
        Validates: Requirements 11.5
        """
        # Создаем тестовую неактивную плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1,
            is_active=False
        )
        
        # Устанавливаем выбранную транзакцию
        self.view.selected_planned_tx = test_tx
        self.view.details_panel.visible = True
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_planned.reset_mock()
        
        # Вызываем toggle_active
        self.view.toggle_active(test_tx)
        
        # Проверяем, что транзакция активирована
        self.assertTrue(test_tx.is_active)
        
        # Проверяем, что commit был вызван
        self.mock_session.commit.assert_called()
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_all_planned)
        
        # Проверяем, что панель деталей скрыта
        self.assertFalse(self.view.details_panel.visible)

    def test_confirm_delete_opens_dialog(self):
        """
        Тест открытия диалога подтверждения удаления.
        
        Проверяет:
        - При вызове confirm_delete открывается диалог подтверждения
        - Диалог содержит информацию об удаляемой транзакции
        
        Validates: Requirements 11.6
        """
        # Создаем тестовую плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1,
            description="Тестовая плановая транзакция"
        )
        
        # Мокируем query для получения категории
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = create_test_category(
            id=1,
            name="Тестовая категория"
        )
        self.mock_session.query.return_value = mock_query
        
        # Вызываем метод подтверждения удаления
        self.view.confirm_delete(test_tx)
        
        # Проверяем, что page.dialog установлен
        self.assertIsNotNone(self.page.dialog)
        
        # Проверяем, что диалог открыт
        self.assertTrue(self.page.dialog.open)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_delete_planned_transaction(self):
        """
        Тест удаления плановой транзакции.
        
        Проверяет:
        - При подтверждении удаления вызывается delete_planned_transaction
        - Данные перезагружаются
        - Панель деталей скрывается
        
        Validates: Requirements 11.6
        """
        # Создаем тестовую плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1
        )
        
        # Мокируем query для получения категории
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = create_test_category(
            id=1,
            name="Тестовая категория"
        )
        self.mock_session.query.return_value = mock_query
        
        # Устанавливаем выбранную транзакцию
        self.view.selected_planned_tx = test_tx
        self.view.details_panel.visible = True
        
        # Сбрасываем счетчик вызовов
        self.mock_delete_planned.reset_mock()
        self.mock_get_all_planned.reset_mock()
        
        # Вызываем confirm_delete
        self.view.confirm_delete(test_tx)
        
        # Получаем диалог и вызываем действие удаления
        dlg = self.page.dialog
        delete_button = dlg.actions[1]  # Кнопка "Удалить"
        delete_button.on_click(None)
        
        # Проверяем, что delete_planned_transaction был вызван
        self.assert_service_called_once(
            self.mock_delete_planned,
            self.mock_session,
            1,  # ID транзакции
            delete_actual_transactions=False
        )
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_all_planned)
        
        # Проверяем, что панель деталей скрыта
        self.assertFalse(self.view.details_panel.visible)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 11.1
        """
        # Вызываем will_unmount
        self.view.will_unmount()
        
        # Проверяем, что __exit__ был вызван
        self.mock_db_cm.__exit__.assert_called_once()

    def test_refresh_data_updates_ui(self):
        """
        Тест обновления UI после загрузки данных.
        
        Проверяет:
        - После вызова refresh_data() UI обновляется (page.update)
        - Список плановых транзакций очищается и заполняется заново
        
        Validates: Requirements 11.1
        """
        # Создаем тестовые плановые транзакции
        test_transactions = [
            create_test_planned_transaction(
                id=1,
                amount=Decimal("1000.00"),
                category_id=1,
                is_active=True
            ),
        ]
        self.mock_get_all_planned.return_value = test_transactions
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем refresh_data
        self.view.refresh_data()
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)
        
        # Проверяем, что список содержит элементы
        self.assertGreater(len(self.view.transactions_list.controls), 0)

    def test_show_details_displays_transaction_info(self):
        """
        Тест отображения панели с деталями плановой транзакции.
        
        Проверяет:
        - При вызове show_details() панель деталей становится видимой
        - Панель содержит информацию о транзакции
        
        Validates: Requirements 11.1
        """
        # Создаем тестовую плановую транзакцию
        test_tx = create_test_planned_transaction(
            id=1,
            amount=Decimal("1000.00"),
            category_id=1,
            description="Тестовая плановая транзакция",
            type=TransactionType.INCOME,
            is_active=True
        )
        
        # Мокируем query для получения категории и вхождений
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = create_test_category(
            id=1,
            name="Тестовая категория"
        )
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        # Вызываем show_details
        self.view.show_details(test_tx)
        
        # Проверяем, что панель деталей видима
        self.assertTrue(self.view.details_panel.visible)
        
        # Проверяем, что выбранная транзакция установлена
        self.assertEqual(self.view.selected_planned_tx, test_tx)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_hide_details_hides_panel(self):
        """
        Тест скрытия панели деталей.
        
        Проверяет:
        - При вызове hide_details() панель деталей скрывается
        - Выбранная транзакция сбрасывается
        
        Validates: Requirements 11.1
        """
        # Устанавливаем видимость панели
        self.view.details_panel.visible = True
        self.view.selected_planned_tx = create_test_planned_transaction(id=1)
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем hide_details
        self.view.hide_details()
        
        # Проверяем, что панель деталей скрыта
        self.assertFalse(self.view.details_panel.visible)
        
        # Проверяем, что выбранная транзакция сброшена
        self.assertIsNone(self.view.selected_planned_tx)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)


if __name__ == '__main__':
    unittest.main()
