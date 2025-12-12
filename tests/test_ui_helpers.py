"""
Тесты для вспомогательных функций UI тестирования.

Проверяет корректность работы:
- Assertion helpers
- Генераторов тестовых данных
- Утилит для работы с UI компонентами
"""
import unittest
from unittest.mock import Mock, MagicMock
from datetime import date, datetime
from decimal import Decimal
import uuid
import flet as ft

from ui_test_helpers import (
    assert_modal_opened, assert_modal_not_opened, assert_modal_closed,
    assert_modal_state, assert_form_field_value, assert_button_state,
    create_test_category, create_test_transaction, create_test_transaction_create_data,
    create_test_categories_list, create_test_transactions_list,
    simulate_button_click, simulate_text_input, simulate_dropdown_selection,
    create_mock_callback, create_mock_db_context_manager
)
from property_generators import (
    valid_amounts, invalid_amounts, transaction_dates, transaction_descriptions,
    category_names, uuid_strings, transaction_create_data
)
from finance_tracker.models.enums import TransactionType


class TestUIHelpers(unittest.TestCase):
    """Тесты для вспомогательных функций UI тестирования."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock(spec=ft.Page)
        self.mock_page.overlay = []
        self.mock_page.dialog = None
        self.mock_page.open = MagicMock()
        self.mock_page.close = MagicMock()
    
    def test_assert_modal_opened_success(self):
        """Тест успешной проверки открытия модального окна."""
        # Arrange
        mock_dialog = MagicMock(spec=ft.AlertDialog)
        # Симулируем вызов page.open с диалогом
        self.mock_page.open(mock_dialog)
        
        # Act & Assert - не должно вызывать исключение
        assert_modal_opened(self.mock_page, ft.AlertDialog)
    
    def test_assert_modal_not_opened_success(self):
        """Тест успешной проверки, что модальное окно не открывалось."""
        # Arrange - page.open не вызывался
        self.mock_page.open.assert_not_called = MagicMock()
        
        # Act & Assert - не должно вызывать исключение
        assert_modal_not_opened(self.mock_page)
    
    def test_assert_form_field_value_success(self):
        """Тест проверки значения поля формы."""
        # Arrange
        mock_field = MagicMock()
        mock_field.value = "test_value"
        
        # Act & Assert - не должно вызывать исключение
        assert_form_field_value(mock_field, "test_value", "test_field")
    
    def test_assert_button_state_enabled(self):
        """Тест проверки состояния активной кнопки."""
        # Arrange
        mock_button = MagicMock()
        mock_button.disabled = False
        
        # Act & Assert - не должно вызывать исключение
        assert_button_state(mock_button, is_enabled=True, button_name="test_button")
    
    def test_assert_button_state_disabled(self):
        """Тест проверки состояния неактивной кнопки."""
        # Arrange
        mock_button = MagicMock()
        mock_button.disabled = True
        
        # Act & Assert - не должно вызывать исключение
        assert_button_state(mock_button, is_enabled=False, button_name="test_button")


class TestDataGenerators(unittest.TestCase):
    """Тесты для генераторов тестовых данных."""
    
    def test_create_test_category_default(self):
        """Тест создания тестовой категории с параметрами по умолчанию."""
        # Act
        category = create_test_category()
        
        # Assert
        self.assertIsNotNone(category.id)
        self.assertIsNotNone(category.name)
        self.assertEqual(category.type, TransactionType.EXPENSE)
        self.assertFalse(category.is_system)
        self.assertIsInstance(category.created_at, datetime)
    
    def test_create_test_category_custom(self):
        """Тест создания тестовой категории с кастомными параметрами."""
        # Arrange
        custom_name = "Кастомная категория"
        
        # Act
        category = create_test_category(
            category_type=TransactionType.INCOME,
            name=custom_name,
            is_system=True
        )
        
        # Assert
        self.assertEqual(category.name, custom_name)
        self.assertEqual(category.type, TransactionType.INCOME)
        self.assertTrue(category.is_system)
    
    def test_create_test_transaction_default(self):
        """Тест создания тестовой транзакции с параметрами по умолчанию."""
        # Act
        transaction = create_test_transaction()
        
        # Assert
        self.assertIsNotNone(transaction.id)
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.type, TransactionType.EXPENSE)
        self.assertIsNotNone(transaction.category_id)
        self.assertIsNotNone(transaction.description)
        self.assertEqual(transaction.transaction_date, date.today())
        self.assertIsInstance(transaction.created_at, datetime)
    
    def test_create_test_transaction_custom(self):
        """Тест создания тестовой транзакции с кастомными параметрами."""
        # Arrange
        custom_amount = Decimal('250.75')
        custom_category_id = str(uuid.uuid4())
        custom_description = "Кастомная транзакция"
        custom_date = date(2024, 12, 1)
        
        # Act
        transaction = create_test_transaction(
            amount=custom_amount,
            transaction_type=TransactionType.INCOME,
            category_id=custom_category_id,
            description=custom_description,
            transaction_date=custom_date
        )
        
        # Assert
        self.assertEqual(transaction.amount, custom_amount)
        self.assertEqual(transaction.type, TransactionType.INCOME)
        self.assertEqual(transaction.category_id, custom_category_id)
        self.assertEqual(transaction.description, custom_description)
        self.assertEqual(transaction.transaction_date, custom_date)
    
    def test_create_test_transaction_create_data(self):
        """Тест создания данных для TransactionCreate."""
        # Act
        data = create_test_transaction_create_data()
        
        # Assert
        self.assertIsInstance(data.amount, Decimal)
        self.assertGreater(data.amount, Decimal('0'))
        self.assertIn(data.type, [TransactionType.INCOME, TransactionType.EXPENSE])
        self.assertIsNotNone(data.category_id)
        # Проверяем, что это валидный UUID
        uuid.UUID(data.category_id)  # Должно не вызывать исключение
        self.assertEqual(data.transaction_date, date.today())
    
    def test_create_test_categories_list(self):
        """Тест создания списка тестовых категорий."""
        # Act
        categories = create_test_categories_list(expense_count=3, income_count=2)
        
        # Assert
        self.assertEqual(len(categories['expense']), 3)
        self.assertEqual(len(categories['income']), 2)
        self.assertEqual(len(categories['all']), 5)
        
        # Проверяем типы категорий
        for category in categories['expense']:
            self.assertEqual(category.type, TransactionType.EXPENSE)
        
        for category in categories['income']:
            self.assertEqual(category.type, TransactionType.INCOME)
        
        # Проверяем, что первые категории системные
        self.assertTrue(categories['expense'][0].is_system)
        self.assertTrue(categories['income'][0].is_system)
    
    def test_create_test_transactions_list(self):
        """Тест создания списка тестовых транзакций."""
        # Arrange
        category_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Act
        transactions = create_test_transactions_list(
            count=5,
            category_ids=category_ids,
            date_range_days=7
        )
        
        # Assert
        self.assertEqual(len(transactions), 5)
        
        # Проверяем, что все транзакции имеют валидные данные
        for i, transaction in enumerate(transactions):
            self.assertIsNotNone(transaction.id)
            self.assertGreater(transaction.amount, Decimal('0'))
            self.assertIn(transaction.category_id, category_ids)
            self.assertIsNotNone(transaction.description)
            self.assertLessEqual(transaction.transaction_date, date.today())


class TestUIUtilities(unittest.TestCase):
    """Тесты для утилит работы с UI компонентами."""
    
    def test_simulate_button_click(self):
        """Тест симуляции нажатия кнопки."""
        # Arrange
        mock_callback = Mock()
        mock_button = MagicMock()
        mock_button.on_click = mock_callback
        
        # Act
        simulate_button_click(mock_button)
        
        # Assert
        mock_callback.assert_called_once_with(None)
    
    def test_simulate_text_input(self):
        """Тест симуляции ввода текста."""
        # Arrange
        mock_field = MagicMock()
        mock_field.on_change = Mock()
        test_value = "test input"
        
        # Act
        simulate_text_input(mock_field, test_value)
        
        # Assert
        self.assertEqual(mock_field.value, test_value)
        mock_field.on_change.assert_called_once_with(None)
    
    def test_simulate_dropdown_selection(self):
        """Тест симуляции выбора в выпадающем списке."""
        # Arrange
        mock_dropdown = MagicMock()
        mock_dropdown.on_change = Mock()
        test_value = "selected_option"
        
        # Act
        simulate_dropdown_selection(mock_dropdown, test_value)
        
        # Assert
        self.assertEqual(mock_dropdown.value, test_value)
        mock_dropdown.on_change.assert_called_once_with(None)
    
    def test_create_mock_callback(self):
        """Тест создания мок callback функции."""
        # Act
        callback = create_mock_callback()
        
        # Assert
        self.assertIsInstance(callback, Mock)
    
    def test_create_mock_db_context_manager(self):
        """Тест создания мок context manager для БД."""
        # Act
        mock_cm = create_mock_db_context_manager()
        
        # Assert
        self.assertIsInstance(mock_cm, Mock)
        self.assertIsNotNone(mock_cm.__enter__)
        self.assertIsNotNone(mock_cm.__exit__)
        
        # Проверяем работу context manager
        with mock_cm as session:
            self.assertIsNotNone(session)
            self.assertTrue(hasattr(session, 'commit'))
            self.assertTrue(hasattr(session, 'rollback'))


if __name__ == '__main__':
    unittest.main()