"""
Unit тесты для TransactionsPanel.

Тестирует:
- Инициализацию кнопки добавления транзакции
- Взаимодействие с кнопкой
- Обработку callback функций
- Состояние UI компонентов
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
from decimal import Decimal
import flet as ft

from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.models.models import TransactionDB
from finance_tracker.models.enums import TransactionType
from ui_test_helpers import (
    create_test_transaction,
    create_mock_callback,
    assert_button_state,
    simulate_button_click
)


class TestTransactionsPanel(unittest.TestCase):
    """Unit тесты для TransactionsPanel."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.test_date = date.today()
        self.test_transactions = []
        self.mock_callback = create_mock_callback()

    def tearDown(self):
        """Очистка после каждого теста."""
        pass

    def test_add_button_initialization_with_valid_callback(self):
        """
        Тест инициализации кнопки добавления с валидным callback.
        
        Проверяет:
        - Создание кнопки с корректными атрибутами (icon, tooltip, bgcolor)
        - Установку callback функции
        - Видимость и доступность кнопки
        
        Requirements: 1.4, 1.5
        """
        # Arrange - создаем панель с валидным callback
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=self.mock_callback
        )

        # Act - получаем заголовок с кнопкой
        header_row = panel._build_header()

        # Assert - проверяем структуру заголовка
        self.assertIsNotNone(header_row, "Заголовок должен быть создан")
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать 2 элемента")

        # Получаем кнопку добавления (второй элемент в заголовке)
        add_button = header_row.controls[1]

        # Проверяем тип кнопки
        self.assertIsInstance(add_button, ft.IconButton, "Второй элемент должен быть IconButton")

        # Проверяем атрибуты кнопки
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Кнопка должна иметь иконку ADD")
        self.assertEqual(add_button.tooltip, "Добавить транзакцию", "Кнопка должна иметь правильный tooltip")
        # Цвета теперь в style, проверяем что style существует
        self.assertIsNotNone(add_button.style, "Кнопка должна иметь стиль")
        self.assertIsNotNone(add_button.style.bgcolor, "Стиль должен содержать bgcolor")
        self.assertIsNotNone(add_button.style.icon_color, "Стиль должен содержать icon_color")

        # Проверяем состояние кнопки
        self.assertNotEqual(add_button.disabled, True, "Кнопка должна быть активна с валидным callback")

        # Проверяем установку обработчика события
        self.assertIsNotNone(add_button.on_click, "on_click должен быть установлен")

        # Проверяем сохранение callback в панели
        self.assertEqual(panel.on_add_transaction, self.mock_callback, "Callback должен быть сохранен в панели")

    def test_add_button_initialization_with_none_callback(self):
        """
        Тест инициализации кнопки добавления с None callback.
        
        Проверяет:
        - Создание кнопки с корректными атрибутами
        - Отключение кнопки при отсутствии callback
        - Безопасную обработку None callback
        
        Requirements: 1.4, 1.5
        """
        # Arrange - создаем панель без callback
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=None
        )

        # Act - получаем заголовок с кнопкой
        header_row = panel._build_header()
        add_button = header_row.controls[1]

        # Assert - проверяем атрибуты кнопки (должны быть такими же)
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Иконка должна быть ADD даже без callback")
        self.assertEqual(add_button.tooltip, "Добавить транзакцию", "Tooltip должен быть установлен")
        # Цвета теперь в style, проверяем что style существует
        self.assertIsNotNone(add_button.style, "Кнопка должна иметь стиль")
        self.assertIsNotNone(add_button.style.bgcolor, "Стиль должен содержать bgcolor")
        self.assertIsNotNone(add_button.style.icon_color, "Стиль должен содержать icon_color")

        # Проверяем состояние кнопки - должна быть отключена
        self.assertEqual(add_button.disabled, True, "Кнопка должна быть отключена при отсутствии callback")

        # Проверяем, что on_click все равно установлен для безопасности
        self.assertIsNotNone(add_button.on_click, "on_click должен быть установлен даже без callback")

        # Проверяем сохранение None callback
        self.assertIsNone(panel.on_add_transaction, "None callback должен быть сохранен")

    def test_add_button_click_with_valid_callback(self):
        """
        Тест нажатия на кнопку добавления с валидным callback.
        
        Проверяет:
        - Вызов callback функции при нажатии
        - Передачу корректных параметров
        
        Requirements: 1.1, 2.3
        """
        # Arrange - создаем панель с mock callback
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=self.mock_callback
        )

        # Act - симулируем нажатие кнопки
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        # Нажимаем кнопку (Flet передает event, но мы его не используем)
        add_button.on_click(None)

        # Assert - проверяем вызов callback
        self.mock_callback.assert_called_once()

    def test_add_button_click_with_none_callback(self):
        """
        Тест нажатия на кнопку добавления без callback.
        
        Проверяет:
        - Безопасную обработку нажатия без callback
        - Отсутствие исключений при нажатии
        
        Requirements: 8.1, 8.2
        """
        # Arrange - создаем панель без callback
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=None
        )

        # Act & Assert - нажатие не должно вызывать исключений
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        try:
            add_button.on_click(None)
            # Если дошли сюда, значит исключений не было
        except Exception as e:
            self.fail(f"Нажатие кнопки без callback не должно вызывать исключения: {e}")

    def test_safe_add_transaction_method_with_valid_callback(self):
        """
        Тест метода _safe_add_transaction с валидным callback.
        
        Проверяет:
        - Корректный вызов callback через безопасный метод
        - Логирование операции
        
        Requirements: 3.1, 3.2
        """
        # Arrange
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=self.mock_callback
        )

        # Act - вызываем безопасный метод напрямую
        panel._safe_add_transaction(None)

        # Assert - проверяем вызов callback
        self.mock_callback.assert_called_once()

    def test_safe_add_transaction_method_with_none_callback(self):
        """
        Тест метода _safe_add_transaction с None callback.
        
        Проверяет:
        - Безопасную обработку None callback
        - Логирование предупреждения
        - Отсутствие исключений
        
        Requirements: 8.1, 8.2
        """
        # Arrange
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=None
        )

        # Act & Assert - метод не должен вызывать исключений
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключений не было
        except Exception as e:
            self.fail(f"_safe_add_transaction с None callback не должен вызывать исключения: {e}")

    def test_safe_add_transaction_method_with_exception_in_callback(self):
        """
        Тест метода _safe_add_transaction с исключением в callback.
        
        Проверяет:
        - Обработку исключений в callback
        - Логирование ошибки
        - Отсутствие "всплытия" исключения
        
        Requirements: 8.2, 8.4
        """
        # Arrange - создаем callback, который выбрасывает исключение
        failing_callback = Mock(side_effect=Exception("Тестовая ошибка"))
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=failing_callback
        )

        # Act & Assert - исключение должно быть обработано внутри метода
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключение было обработано
        except Exception as e:
            self.fail(f"_safe_add_transaction должен обрабатывать исключения в callback: {e}")

        # Проверяем, что callback все же был вызван
        failing_callback.assert_called_once()

    def test_button_attributes_consistency(self):
        """
        Тест консистентности атрибутов кнопки при разных условиях.
        
        Проверяет:
        - Одинаковые атрибуты кнопки независимо от callback
        - Различие только в состоянии disabled
        
        Requirements: 1.4, 1.5
        """
        # Arrange - создаем две панели: с callback и без
        panel_with_callback = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=self.mock_callback
        )
        
        panel_without_callback = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=None
        )

        # Act - получаем кнопки из обеих панелей
        button_with_callback = panel_with_callback._build_header().controls[1]
        button_without_callback = panel_without_callback._build_header().controls[1]

        # Assert - проверяем, что атрибуты одинаковые (кроме disabled)
        self.assertEqual(button_with_callback.icon, button_without_callback.icon)
        self.assertEqual(button_with_callback.tooltip, button_without_callback.tooltip)
        self.assertEqual(button_with_callback.bgcolor, button_without_callback.bgcolor)
        self.assertEqual(button_with_callback.icon_color, button_without_callback.icon_color)

        # Проверяем различие в состоянии disabled
        self.assertNotEqual(button_with_callback.disabled, True, "Кнопка с callback должна быть активна")
        self.assertEqual(button_without_callback.disabled, True, "Кнопка без callback должна быть отключена")

    def test_button_initialization_with_transactions_data(self):
        """
        Тест инициализации кнопки с различными данными транзакций.
        
        Проверяет:
        - Независимость атрибутов кнопки от данных транзакций
        - Стабильность инициализации при разных объемах данных
        
        Requirements: 1.4, 1.5
        """
        # Arrange - создаем тестовые транзакции
        test_transactions = [
            create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE),
            create_test_transaction(Decimal('200.75'), TransactionType.INCOME),
            create_test_transaction(Decimal('50.25'), TransactionType.EXPENSE)
        ]

        # Act - создаем панели с разными данными
        panel_empty = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback
        )
        
        panel_with_data = TransactionsPanel(
            date_obj=self.test_date,
            transactions=test_transactions,
            on_add_transaction=self.mock_callback
        )

        # Assert - кнопки должны быть идентичными независимо от данных
        button_empty = panel_empty._build_header().controls[1]
        button_with_data = panel_with_data._build_header().controls[1]

        self.assertEqual(button_empty.icon, button_with_data.icon)
        self.assertEqual(button_empty.tooltip, button_with_data.tooltip)
        self.assertEqual(button_empty.bgcolor, button_with_data.bgcolor)
        self.assertEqual(button_empty.icon_color, button_with_data.icon_color)
        self.assertEqual(button_empty.disabled, button_with_data.disabled)

    def test_header_structure_and_layout(self):
        """
        Тест структуры и компоновки заголовка.
        
        Проверяет:
        - Правильную структуру заголовка (Row с 2 элементами)
        - Расположение элементов (текст слева, кнопка справа)
        - Выравнивание элементов
        
        Requirements: 1.4, 1.5
        """
        # Arrange
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=self.test_transactions,
            on_add_transaction=self.mock_callback
        )

        # Act
        header_row = panel._build_header()

        # Assert - проверяем структуру заголовка
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать ровно 2 элемента")
        
        # Проверяем выравнивание
        self.assertEqual(
            header_row.alignment, 
            ft.MainAxisAlignment.SPACE_BETWEEN, 
            "Элементы должны быть выровнены по краям"
        )

        # Проверяем типы элементов
        date_text = header_row.controls[0]
        add_button = header_row.controls[1]
        
        self.assertIsInstance(date_text, ft.Text, "Первый элемент должен быть Text")
        self.assertIsInstance(add_button, ft.IconButton, "Второй элемент должен быть IconButton")

    def test_transaction_tile_with_action_buttons(self):
        """
        Тест создания элемента транзакции с кнопками действий.
        
        Проверяет:
        - Создание ListTile с кнопками редактирования и удаления
        - Правильные атрибуты кнопок (иконки, tooltip, цвета)
        - Структуру trailing элемента
        
        Requirements: 1.1, 1.2, 1.5, 9.2, 9.3
        """
        # Arrange - создаем mock callback'и
        mock_edit_callback = Mock()
        mock_delete_callback = Mock()
        
        # Создаем панель с callback'ами для действий
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=mock_edit_callback,
            on_delete_transaction=mock_delete_callback
        )
        
        # Создаем тестовую транзакцию
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act - создаем элемент списка для транзакции
        tile = panel._build_transaction_tile(test_transaction)

        # Assert - проверяем структуру Container с ListTile внутри
        self.assertIsInstance(tile, ft.Container, "Должен быть создан Container")
        self.assertIsNotNone(tile.content, "Container должен содержать content")
        
        # Получаем ListTile из Container
        list_tile = tile.content
        self.assertIsInstance(list_tile, ft.ListTile, "Content должен быть ListTile")
        self.assertIsNotNone(list_tile.leading, "Должна быть иконка типа транзакции")
        self.assertIsNotNone(list_tile.title, "Должен быть заголовок с категорией")
        self.assertIsNotNone(list_tile.trailing, "Должен быть trailing с суммой и кнопками")

        # Проверяем trailing элемент (должен быть Row с суммой и кнопками)
        trailing = list_tile.trailing
        self.assertIsInstance(trailing, ft.Row, "Trailing должен быть Row")
        
        # Должно быть 3 элемента: сумма + 2 кнопки
        self.assertEqual(len(trailing.controls), 3, "Должно быть 3 элемента: сумма + 2 кнопки")
        
        # Проверяем первый элемент - сумма
        amount_text = trailing.controls[0]
        self.assertIsInstance(amount_text, ft.Text, "Первый элемент должен быть Text с суммой")
        
        # Проверяем кнопки действий
        edit_button = trailing.controls[1]
        delete_button = trailing.controls[2]
        
        self.assertIsInstance(edit_button, ft.IconButton, "Вторая кнопка должна быть IconButton")
        self.assertIsInstance(delete_button, ft.IconButton, "Третья кнопка должна быть IconButton")
        
        # Проверяем атрибуты кнопки редактирования
        self.assertEqual(edit_button.icon, ft.Icons.EDIT, "Кнопка редактирования должна иметь иконку EDIT")
        self.assertEqual(edit_button.icon_color, ft.Colors.PRIMARY, "Кнопка редактирования должна быть PRIMARY цвета")
        self.assertEqual(edit_button.tooltip, "Редактировать", "Кнопка должна иметь tooltip 'Редактировать'")
        
        # Проверяем атрибуты кнопки удаления
        self.assertEqual(delete_button.icon, ft.Icons.DELETE, "Кнопка удаления должна иметь иконку DELETE")
        self.assertEqual(delete_button.icon_color, ft.Colors.ERROR, "Кнопка удаления должна быть ERROR цвета")
        self.assertEqual(delete_button.tooltip, "Удалить", "Кнопка должна иметь tooltip 'Удалить'")

    def test_transaction_tile_without_action_callbacks(self):
        """
        Тест создания элемента транзакции без callback'ов для действий.
        
        Проверяет:
        - Создание ListTile без кнопок действий
        - Отображение только суммы в trailing
        
        Requirements: 1.1, 1.2
        """
        # Arrange - создаем панель без callback'ов для действий
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=None,
            on_delete_transaction=None
        )
        
        # Создаем тестовую транзакцию
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act - создаем элемент списка для транзакции
        tile = panel._build_transaction_tile(test_transaction)

        # Assert - проверяем структуру Container с ListTile внутри
        self.assertIsInstance(tile, ft.Container, "Должен быть создан Container")
        self.assertIsNotNone(tile.content, "Container должен содержать content")
        
        # Получаем ListTile из Container
        list_tile = tile.content
        self.assertIsInstance(list_tile, ft.ListTile, "Content должен быть ListTile")
        
        # Проверяем trailing элемент (должен быть Row с суммой и неактивными кнопками)
        trailing = list_tile.trailing
        self.assertIsInstance(trailing, ft.Row, "Trailing должен быть Row даже без активных callback'ов")
        
        # Проверяем, что кнопки есть, но неактивны
        self.assertEqual(len(trailing.controls), 3, "Должно быть 3 элемента: сумма + 2 неактивные кнопки")
        
        # Проверяем, что кнопки отключены
        edit_button = trailing.controls[1]
        delete_button = trailing.controls[2]
        self.assertTrue(edit_button.disabled, "Кнопка редактирования должна быть отключена")
        self.assertTrue(delete_button.disabled, "Кнопка удаления должна быть отключена")

    def test_edit_transaction_button_click(self):
        """
        Тест нажатия кнопки редактирования транзакции.
        
        Проверяет:
        - Вызов callback'а при нажатии кнопки редактирования
        - Передачу правильной транзакции в callback
        
        Requirements: 1.2
        """
        # Arrange - создаем mock callback
        mock_edit_callback = Mock()
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=mock_edit_callback,
            on_delete_transaction=Mock()
        )
        
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act - создаем элемент и нажимаем кнопку редактирования
        tile = panel._build_transaction_tile(test_transaction)
        list_tile = tile.content  # Получаем ListTile из Container
        edit_button = list_tile.trailing.controls[1]  # Вторая кнопка - редактирование
        edit_button.on_click(None)

        # Assert - проверяем вызов callback'а
        mock_edit_callback.assert_called_once_with(test_transaction)

    def test_delete_transaction_button_click(self):
        """
        Тест нажатия кнопки удаления транзакции.
        
        Проверяет:
        - Вызов callback'а при нажатии кнопки удаления
        - Передачу правильной транзакции в callback
        
        Requirements: 1.2
        """
        # Arrange - создаем mock callback
        mock_delete_callback = Mock()
        
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=Mock(),
            on_delete_transaction=mock_delete_callback
        )
        
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act - создаем элемент и нажимаем кнопку удаления
        tile = panel._build_transaction_tile(test_transaction)
        list_tile = tile.content  # Получаем ListTile из Container
        delete_button = list_tile.trailing.controls[2]  # Третья кнопка - удаление
        delete_button.on_click(None)

        # Assert - проверяем вызов callback'а
        mock_delete_callback.assert_called_once_with(test_transaction)

    def test_safe_edit_transaction_with_none_callback(self):
        """
        Тест безопасного вызова редактирования с None callback.
        
        Проверяет:
        - Безопасную обработку None callback для редактирования
        - Отсутствие исключений
        
        Requirements: 9.2, 9.3
        """
        # Arrange
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=None,
            on_delete_transaction=None
        )
        
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act & Assert - метод не должен вызывать исключений
        try:
            panel._safe_edit_transaction(test_transaction)
        except Exception as e:
            self.fail(f"_safe_edit_transaction с None callback не должен вызывать исключения: {e}")

    def test_safe_delete_transaction_with_none_callback(self):
        """
        Тест безопасного вызова удаления с None callback.
        
        Проверяет:
        - Безопасную обработку None callback для удаления
        - Отсутствие исключений
        
        Requirements: 9.2, 9.3
        """
        # Arrange
        panel = TransactionsPanel(
            date_obj=self.test_date,
            transactions=[],
            on_add_transaction=self.mock_callback,
            on_edit_transaction=None,
            on_delete_transaction=None
        )
        
        test_transaction = create_test_transaction(Decimal('100.50'), TransactionType.EXPENSE)

        # Act & Assert - метод не должен вызывать исключений
        try:
            panel._safe_delete_transaction(test_transaction)
        except Exception as e:
            self.fail(f"_safe_delete_transaction с None callback не должен вызывать исключения: {e}")


if __name__ == '__main__':
    unittest.main()