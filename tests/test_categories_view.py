"""
Тесты для CategoriesView.

Проверяет:
- Инициализацию View
- Загрузку категорий
- Фильтрацию по типу транзакции
- Открытие модального окна создания
- Открытие модального окна редактирования
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
from decimal import Decimal

from finance_tracker.views.categories_view import CategoriesView, CategoryDialog
from finance_tracker.models.enums import TransactionType
from test_view_base import ViewTestBase
from test_factories import create_test_category


class TestCategoriesView(ViewTestBase):
    """Тесты для CategoriesView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.categories_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы категорий
        self.mock_get_all_categories = self.add_patcher(
            'finance_tracker.views.categories_view.get_all_categories',
            return_value=[]
        )
        self.mock_create_category = self.add_patcher(
            'finance_tracker.views.categories_view.create_category'
        )
        self.mock_update_category = self.add_patcher(
            'finance_tracker.views.categories_view.update_category'
        )
        self.mock_delete_category = self.add_patcher(
            'finance_tracker.views.categories_view.delete_category'
        )
        
        # Создаем экземпляр CategoriesView
        self.view = CategoriesView(self.page)

    def test_initialization(self):
        """
        Тест инициализации CategoriesView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - UI компоненты созданы (заголовок, фильтры, список)
        
        Validates: Requirements 6.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, CategoriesView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.filter_tabs)
        self.assertIsNotNone(self.view.categories_list)
        
        # Проверяем начальное состояние фильтра
        self.assertIsNone(self.view.current_filter)
        self.assertEqual(self.view.filter_tabs.selected_index, 0)

    def test_load_categories_on_mount(self):
        """
        Тест загрузки категорий при монтировании View.
        
        Проверяет:
        - При вызове did_mount() вызывается get_all_categories
        - Сервис вызывается с правильной сессией и фильтром
        
        Validates: Requirements 6.1
        """
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_all_categories.reset_mock()
        
        # Вызываем did_mount
        self.view.did_mount()
        
        # Проверяем, что сервис был вызван
        self.assert_service_called_once(
            self.mock_get_all_categories,
            self.mock_session,
            None  # Фильтр по умолчанию - None (все категории)
        )

    def test_load_categories_with_data(self):
        """
        Тест загрузки категорий с данными.
        
        Проверяет:
        - Категории отображаются в списке
        - Количество элементов соответствует количеству категорий
        
        Validates: Requirements 6.1
        """
        # Создаем тестовые категории
        test_categories = [
            create_test_category(id=1, name="Продукты", type=TransactionType.EXPENSE),
            create_test_category(id=2, name="Зарплата", type=TransactionType.INCOME),
            create_test_category(id=3, name="Транспорт", type=TransactionType.EXPENSE),
        ]
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_all_categories.return_value = test_categories
        
        # Загружаем данные
        self.view.refresh_data()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.categories_list.controls), 3)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_categories_empty_list(self):
        """
        Тест загрузки пустого списка категорий.
        
        Проверяет:
        - При пустом списке отображается сообщение "Категории не найдены"
        
        Validates: Requirements 6.1
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_all_categories.return_value = []
        
        # Загружаем данные
        self.view.refresh_data()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.categories_list.controls), 1)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_filter_change_to_expenses(self):
        """
        Тест фильтрации по расходам.
        
        Проверяет:
        - При выборе вкладки "Расходы" устанавливается фильтр EXPENSE
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 6.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_categories.reset_mock()
        
        # Имитируем выбор вкладки "Расходы" (индекс 1)
        self.view.filter_tabs.selected_index = 1
        self.view.on_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.current_filter, TransactionType.EXPENSE)
        
        # Проверяем, что сервис вызван с фильтром EXPENSE
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            TransactionType.EXPENSE
        )

    def test_filter_change_to_income(self):
        """
        Тест фильтрации по доходам.
        
        Проверяет:
        - При выборе вкладки "Доходы" устанавливается фильтр INCOME
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 6.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_categories.reset_mock()
        
        # Имитируем выбор вкладки "Доходы" (индекс 2)
        self.view.filter_tabs.selected_index = 2
        self.view.on_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.current_filter, TransactionType.INCOME)
        
        # Проверяем, что сервис вызван с фильтром INCOME
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            TransactionType.INCOME
        )

    def test_filter_change_to_all(self):
        """
        Тест сброса фильтра (все категории).
        
        Проверяет:
        - При выборе вкладки "Все" фильтр сбрасывается (None)
        - Вызывается перезагрузка данных без фильтра
        
        Validates: Requirements 6.2
        """
        # Устанавливаем фильтр
        self.view.current_filter = TransactionType.EXPENSE
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_categories.reset_mock()
        
        # Имитируем выбор вкладки "Все" (индекс 0)
        self.view.filter_tabs.selected_index = 0
        self.view.on_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.current_filter)
        
        # Проверяем, что сервис вызван без фильтра
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            None
        )

    def test_open_create_dialog(self):
        """
        Тест открытия модального окна создания категории.
        
        Проверяет:
        - При нажатии кнопки создания открывается CategoryDialog
        - Диалог открывается в режиме создания (без категории)
        
        Validates: Requirements 6.3
        """
        # Создаем мок события с control, у которого есть page
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.page = self.page
        
        # Вызываем метод открытия диалога
        self.view.open_create_dialog(mock_event)
        
        # Проверяем, что page.open был вызван
        self.assert_modal_opened(self.page)
        
        # Проверяем, что открыт CategoryDialog
        call_args = self.page.open.call_args
        opened_dialog = call_args[0][0]
        self.assertIsInstance(opened_dialog, CategoryDialog)
        
        # Проверяем, что диалог в режиме создания (category=None)
        self.assertIsNone(opened_dialog.category)

    def test_open_edit_dialog(self):
        """
        Тест открытия модального окна редактирования категории.
        
        Проверяет:
        - При нажатии кнопки редактирования открывается CategoryDialog
        - Диалог открывается в режиме редактирования (с категорией)
        - Переданная категория соответствует выбранной
        
        Validates: Requirements 6.4
        """
        # Создаем тестовую категорию
        test_category = create_test_category(
            id=1,
            name="Тестовая категория",
            type=TransactionType.EXPENSE
        )
        
        # Вызываем метод открытия диалога редактирования
        self.view.open_edit_dialog(test_category)
        
        # Проверяем, что page.open был вызван
        self.assert_modal_opened(self.page)
        
        # Проверяем, что открыт CategoryDialog
        call_args = self.page.open.call_args
        opened_dialog = call_args[0][0]
        self.assertIsInstance(opened_dialog, CategoryDialog)
        
        # Проверяем, что диалог в режиме редактирования (category передана)
        self.assertIsNotNone(opened_dialog.category)
        self.assertEqual(opened_dialog.category.id, test_category.id)
        self.assertEqual(opened_dialog.category.name, test_category.name)

    def test_confirm_delete_opens_dialog(self):
        """
        Тест открытия диалога подтверждения удаления.
        
        Проверяет:
        - При вызове confirm_delete открывается диалог подтверждения
        - Диалог содержит информацию об удаляемой категории
        
        Validates: Requirements 6.5
        """
        # Вызываем метод подтверждения удаления
        self.view.confirm_delete(category_id=1, name="Тестовая категория")
        
        # Проверяем, что page.dialog установлен
        self.assertIsNotNone(self.page.dialog)
        
        # Проверяем, что диалог открыт
        self.assertTrue(self.page.dialog.open)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 1.2
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
        - Список категорий очищается и заполняется заново
        
        Validates: Requirements 6.1
        """
        # Создаем тестовые категории
        test_categories = [
            create_test_category(id=1, name="Категория 1", type=TransactionType.EXPENSE),
        ]
        self.mock_get_all_categories.return_value = test_categories
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем refresh_data
        self.view.refresh_data()
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)
        
        # Проверяем, что список содержит элементы
        self.assertGreater(len(self.view.categories_list.controls), 0)


if __name__ == '__main__':
    unittest.main()
