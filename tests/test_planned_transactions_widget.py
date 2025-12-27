"""
Unit тесты для PlannedTransactionsWidget.

Тестирует:
- Инициализацию кнопки добавления плановой транзакции
- Взаимодействие с кнопкой
- Обработку callback функций
- Состояние UI компонентов

Requirements: 2.1, 2.2, 2.3, 2.4
"""
import unittest
from unittest.mock import Mock
import flet as ft

from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget


class TestPlannedTransactionsWidgetAddButton(unittest.TestCase):
    """Unit тесты для кнопки добавления в PlannedTransactionsWidget."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_skip = Mock()
        self.mock_on_show_all = Mock()
        self.mock_on_add_planned_transaction = Mock()

    def tearDown(self):
        """Очистка после каждого теста."""
        pass

    def test_add_button_exists_when_callback_provided(self):
        """
        Тест наличия кнопки добавления при заданном callback.
        
        Проверяет:
        - Создание кнопки при инициализации виджета с callback
        - Наличие кнопки в атрибуте add_button
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет с callback для добавления
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем наличие кнопки
        self.assertIsNotNone(
            widget.add_button, 
            "Кнопка добавления должна быть создана при заданном callback"
        )
        self.assertIsInstance(
            widget.add_button, 
            ft.IconButton, 
            "Кнопка должна быть IconButton"
        )

    def test_add_button_not_exists_when_callback_none(self):
        """
        Тест отсутствия кнопки добавления при callback=None.
        
        Проверяет:
        - Отсутствие кнопки при инициализации виджета без callback
        - add_button должен быть None
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback для добавления
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем отсутствие кнопки
        self.assertIsNone(
            widget.add_button, 
            "Кнопка добавления не должна создаваться при callback=None"
        )

    def test_add_button_icon_attribute(self):
        """
        Тест атрибута icon кнопки добавления.
        
        Проверяет:
        - Иконку кнопки (ft.Icons.ADD)
        
        Requirements: 2.2
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем иконку кнопки
        self.assertEqual(
            widget.add_button.icon, 
            ft.Icons.ADD, 
            "Кнопка должна иметь иконку ADD"
        )

    def test_add_button_tooltip_attribute(self):
        """
        Тест атрибута tooltip кнопки добавления.
        
        Проверяет:
        - Tooltip кнопки ("Добавить плановую транзакцию")
        
        Requirements: 2.3
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем tooltip кнопки
        self.assertEqual(
            widget.add_button.tooltip, 
            "Добавить плановую транзакцию", 
            "Кнопка должна иметь правильный tooltip"
        )

    def test_add_button_color_attribute(self):
        """
        Тест атрибута цвета кнопки добавления.
        
        Проверяет:
        - Цвет иконки кнопки (ft.Colors.PRIMARY)
        
        Requirements: 2.4
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем цвет кнопки
        self.assertEqual(
            widget.add_button.icon_color, 
            ft.Colors.PRIMARY, 
            "Кнопка должна иметь PRIMARY цвет"
        )

    def test_add_button_callback_invocation(self):
        """
        Тест вызова callback при нажатии кнопки добавления.
        
        Проверяет:
        - Вызов callback функции при нажатии кнопки
        - Корректную установку обработчика события
        
        Requirements: 2.1
        """
        # Arrange - создаем виджет с mock callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Act - симулируем нажатие кнопки
        add_button = widget.add_button
        self.assertIsNotNone(
            add_button.on_click, 
            "on_click должен быть установлен"
        )
        
        # Нажимаем кнопку (Flet передает event, но мы его не используем)
        add_button.on_click(None)

        # Assert - проверяем вызов callback
        self.mock_on_add_planned_transaction.assert_called_once()

    def test_add_button_in_header_layout_when_callback_provided(self):
        """
        Тест расположения кнопки добавления в заголовке виджета.
        
        Проверяет:
        - Наличие кнопки в структуре заголовка
        - Правильное расположение кнопки (рядом с кнопкой "Показать все")
        - Структуру заголовка (Row с правильными элементами)
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем структуру заголовка
        # Заголовок - это первый элемент в content.controls
        header_row = widget.content.controls[0]
        
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать 2 элемента")
        
        # Второй элемент заголовка должен быть Row с кнопками
        buttons_row = header_row.controls[1]
        self.assertIsInstance(buttons_row, ft.Row, "Второй элемент должен быть Row с кнопками")
        
        # В Row с кнопками должно быть 2 кнопки: добавить и показать все
        self.assertEqual(
            len(buttons_row.controls), 
            2, 
            "Должно быть 2 кнопки: добавить и показать все"
        )
        
        # Первая кнопка - добавить плановую транзакцию
        add_button = buttons_row.controls[0]
        self.assertIsInstance(add_button, ft.IconButton, "Первая кнопка должна быть IconButton")
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Первая кнопка должна быть кнопкой добавления")
        
        # Вторая кнопка - показать все
        show_all_button = buttons_row.controls[1]
        self.assertIsInstance(show_all_button, ft.TextButton, "Вторая кнопка должна быть TextButton")

    def test_header_layout_without_add_button_when_callback_none(self):
        """
        Тест структуры заголовка без кнопки добавления.
        
        Проверяет:
        - Отсутствие кнопки добавления в заголовке при callback=None
        - Наличие только кнопки "Показать все"
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем структуру заголовка
        header_row = widget.content.controls[0]
        
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать 2 элемента")
        
        # Второй элемент заголовка должен быть Row с кнопками
        buttons_row = header_row.controls[1]
        self.assertIsInstance(buttons_row, ft.Row, "Второй элемент должен быть Row с кнопками")
        
        # В Row с кнопками должна быть только 1 кнопка: показать все
        self.assertEqual(
            len(buttons_row.controls), 
            1, 
            "Должна быть только 1 кнопка: показать все"
        )
        
        # Единственная кнопка - показать все
        show_all_button = buttons_row.controls[0]
        self.assertIsInstance(show_all_button, ft.TextButton, "Кнопка должна быть TextButton")

    def test_callback_storage_in_widget(self):
        """
        Тест сохранения callback в виджете.
        
        Проверяет:
        - Сохранение callback функции в атрибуте виджета
        - Доступность callback для использования
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет с callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем сохранение callback
        self.assertEqual(
            widget.on_add_planned_transaction, 
            self.mock_on_add_planned_transaction, 
            "Callback должен быть сохранен в виджете"
        )

    def test_callback_storage_none_in_widget(self):
        """
        Тест сохранения None callback в виджете.
        
        Проверяет:
        - Сохранение None в атрибуте виджета при отсутствии callback
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем сохранение None
        self.assertIsNone(
            widget.on_add_planned_transaction, 
            "Callback должен быть None в виджете"
        )


if __name__ == '__main__':
    unittest.main()
