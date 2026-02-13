"""
Тесты для CategoriesView.

Проверяет:
- Инициализацию View
- Загрузку категорий
- Открытие модального окна создания
- Открытие модального окна редактирования
"""

import unittest
from unittest.mock import Mock

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
            "finance_tracker.views.categories_view.get_db_session", return_value=self.mock_db_cm
        )

        # Патчим сервисы категорий
        self.mock_get_all_categories = self.add_patcher(
            "finance_tracker.views.categories_view.get_all_categories", return_value=[]
        )
        self.mock_get_expense_tree = self.add_patcher(
            "finance_tracker.views.categories_view.get_expense_tree", return_value=[]
        )
        self.mock_create_category = self.add_patcher(
            "finance_tracker.views.categories_view.create_category"
        )
        self.mock_update_category = self.add_patcher(
            "finance_tracker.views.categories_view.update_category"
        )
        self.mock_delete_category = self.add_patcher(
            "finance_tracker.views.categories_view.delete_category"
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
        - UI компоненты созданы (заголовок, split layout)

        Validates: Requirements 6.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, CategoriesView)

        # Проверяем атрибуты
        self.assertEqual(self.view._page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)

        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.income_list)
        self.assertIsNotNone(self.view.expense_list)
        self.assertIsNotNone(self.view.split_layout)

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
        self.mock_get_expense_tree.reset_mock()

        # Вызываем did_mount
        self.view.did_mount()

        self.assert_service_called_once(
            self.mock_get_all_categories,
            self.mock_session,
            TransactionType.INCOME,
        )
        self.assert_service_called_once(self.mock_get_expense_tree, self.mock_session)

    def test_load_categories_with_data(self):
        """
        Тест загрузки категорий с данными.

        Проверяет:
        - Категории отображаются в списке
        - Количество элементов соответствует количеству категорий

        Validates: Requirements 6.1
        """
        income_categories = [
            create_test_category(id="inc-1", name="Зарплата", type=TransactionType.INCOME),
        ]
        expense_root = create_test_category(
            id="exp-root", name="Продукты", type=TransactionType.EXPENSE
        )
        expense_child = create_test_category(
            id="exp-child",
            name="Кофе",
            type=TransactionType.EXPENSE,
            parent_id="exp-root",
        )
        expense_tree = [{"category": expense_root, "children": [expense_child]}]

        self.mock_get_all_categories.return_value = income_categories
        self.mock_get_expense_tree.return_value = expense_tree

        # Загружаем данные
        self.view.refresh_data()

        self.assertEqual(len(self.view.income_list.controls), 1)
        self.assertEqual(len(self.view.expense_list.controls), 2)

        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_categories_empty_list(self):
        """
        Тест загрузки пустого списка категорий.

        Проверяет:
        - При пустом списке отображается сообщение "Категории не найдены"

        Validates: Requirements 6.1
        """
        self.mock_get_all_categories.return_value = []
        self.mock_get_expense_tree.return_value = []

        # Загружаем данные
        self.view.refresh_data()

        self.assertEqual(len(self.view.income_list.controls), 1)
        self.assertEqual(len(self.view.expense_list.controls), 1)

        self.assert_page_updated(self.page)

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
            id="exp-1", name="Тестовая категория", type=TransactionType.EXPENSE
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
        self.view.confirm_delete(category_id="cat-1", name="Тестовая категория")

        # Проверяем, что page.open был вызван (современный API)
        self.assert_modal_opened(self.page)

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
        income_categories = [
            create_test_category(id="inc-1", name="Категория 1", type=TransactionType.INCOME),
        ]
        expense_root = create_test_category(
            id="exp-1", name="Расход 1", type=TransactionType.EXPENSE
        )

        self.mock_get_all_categories.return_value = income_categories
        self.mock_get_expense_tree.return_value = [{"category": expense_root, "children": []}]

        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()

        # Вызываем refresh_data
        self.view.refresh_data()

        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

        self.assertEqual(len(self.view.income_list.controls), 1)
        self.assertEqual(len(self.view.expense_list.controls), 1)

    def test_category_dialog_prevents_second_level_nesting(self):
        expense_root = create_test_category(
            id="exp-root", name="Продукты", type=TransactionType.EXPENSE
        )
        expense_child = create_test_category(
            id="exp-child",
            name="Кофе",
            type=TransactionType.EXPENSE,
            parent_id="exp-root",
        )
        self.mock_get_expense_tree.return_value = [
            {"category": expense_root, "children": [expense_child]}
        ]

        on_success = Mock()
        dialog = CategoryDialog(session=self.mock_session, on_success=on_success, category=None)
        dialog.name_field.value = "Новая категория"
        dialog.parent_dropdown.value = "exp-child"

        dialog.save_category(None)

        self.mock_create_category.assert_not_called()
        self.assertTrue(dialog.error_text.visible)
        self.assertIn("второго уровня", dialog.error_text.value)


if __name__ == "__main__":
    unittest.main()
