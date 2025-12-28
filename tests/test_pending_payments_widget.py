"""
Unit тесты для PendingPaymentsWidget.

Тестирует:
- Инициализацию кнопки добавления отложенного платежа
- Взаимодействие с кнопкой
- Обработку callback функций
- Состояние UI компонентов
"""
import unittest
from unittest.mock import Mock, MagicMock
from datetime import date
from decimal import Decimal
import flet as ft

from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.models.models import PendingPaymentDB
from finance_tracker.models.enums import PendingPaymentPriority


class TestPendingPaymentsWidget(unittest.TestCase):
    """Unit тесты для PendingPaymentsWidget."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_cancel = Mock()
        self.mock_on_delete = Mock()
        self.mock_on_show_all = Mock()
        self.mock_on_add_payment = Mock()

    def tearDown(self):
        """Очистка после каждого теста."""
        pass

    def test_add_payment_button_exists(self):
        """
        Тест наличия кнопки добавления платежа в виджете.
        
        **Property 1: Кнопка добавления существует и имеет правильные атрибуты**
        **Validates: Requirements 1.1, 4.2, 4.3, 4.4**
        
        Проверяет:
        - Создание кнопки при инициализации виджета
        - Наличие кнопки в структуре заголовка
        
        Requirements: 1.1, 4.1
        """
        # Arrange & Act - создаем виджет с callback для добавления
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
        )

        # Assert - проверяем наличие кнопки
        self.assertIsNotNone(widget.add_payment_button, "Кнопка добавления должна быть создана")
        self.assertIsInstance(widget.add_payment_button, ft.IconButton, "Кнопка должна быть IconButton")

    def test_add_payment_button_attributes(self):
        """
        Тест атрибутов кнопки добавления платежа.
        
        **Property 1: Кнопка добавления существует и имеет правильные атрибуты**
        **Validates: Requirements 1.1, 4.2, 4.3, 4.4**
        
        Проверяет:
        - Иконку кнопки (ft.Icons.ADD)
        - Tooltip кнопки
        - Цвет кнопки (PRIMARY)
        
        Requirements: 4.2, 4.3, 4.4
        """
        # Arrange & Act - создаем виджет
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
        )

        # Assert - проверяем атрибуты кнопки
        add_button = widget.add_payment_button
        
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Кнопка должна иметь иконку ADD")
        self.assertEqual(add_button.tooltip, "Добавить отложенный платёж", "Кнопка должна иметь правильный tooltip")
        self.assertEqual(add_button.icon_color, ft.Colors.PRIMARY, "Кнопка должна иметь PRIMARY цвет")

    def test_add_payment_button_callback_invocation(self):
        """
        Тест вызова callback при нажатии кнопки добавления.
        
        **Property 1: Кнопка добавления существует и имеет правильные атрибуты**
        **Validates: Requirements 1.1, 4.2, 4.3, 4.4**
        
        Проверяет:
        - Вызов callback функции при нажатии кнопки
        - Корректную установку обработчика события
        
        Requirements: 1.1, 1.2
        """
        # Arrange - создаем виджет с mock callback
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
        )

        # Act - симулируем нажатие кнопки
        add_button = widget.add_payment_button
        self.assertIsNotNone(add_button.on_click, "on_click должен быть установлен")
        
        # Нажимаем кнопку (Flet передает event, но мы его не используем)
        add_button.on_click(None)

        # Assert - проверяем вызов callback
        self.mock_on_add_payment.assert_called_once()

    def test_add_payment_button_in_header_layout(self):
        """
        Тест расположения кнопки добавления в заголовке виджета.
        
        Проверяет:
        - Наличие кнопки в структуре заголовка
        - Правильное расположение кнопки (рядом с кнопкой "Показать все")
        - Структуру заголовка (Row с правильными элементами)
        
        Requirements: 4.1
        """
        # Arrange & Act - создаем виджет
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
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
        self.assertEqual(len(buttons_row.controls), 2, "Должно быть 2 кнопки: добавить и показать все")
        
        # Первая кнопка - добавить платёж
        add_button = buttons_row.controls[0]
        self.assertIsInstance(add_button, ft.IconButton, "Первая кнопка должна быть IconButton")
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Первая кнопка должна быть кнопкой добавления")
        
        # Вторая кнопка - показать все
        show_all_button = buttons_row.controls[1]
        self.assertIsInstance(show_all_button, ft.IconButton, "Вторая кнопка должна быть IconButton")

    def test_add_payment_button_with_none_callback(self):
        """
        Тест инициализации кнопки добавления с None callback.
        
        Проверяет:
        - Создание кнопки с корректными атрибутами даже без callback
        - Безопасную обработку None callback
        
        Requirements: 1.1, 4.2, 4.3, 4.4
        """
        # Arrange & Act - создаем виджет без callback для добавления
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=None
        )

        # Assert - проверяем, что кнопка все равно создана
        self.assertIsNotNone(widget.add_payment_button, "Кнопка должна быть создана даже без callback")
        
        # Проверяем атрибуты кнопки (должны быть такими же)
        add_button = widget.add_payment_button
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Иконка должна быть ADD даже без callback")
        self.assertEqual(add_button.tooltip, "Добавить отложенный платёж", "Tooltip должен быть установлен")
        self.assertEqual(add_button.icon_color, ft.Colors.PRIMARY, "Цвет должен быть PRIMARY")
        
        # Проверяем, что on_click установлен для безопасности
        self.assertIsNotNone(add_button.on_click, "on_click должен быть установлен даже без callback")

    def test_add_payment_button_click_with_none_callback(self):
        """
        Тест нажатия на кнопку добавления без callback.
        
        Проверяет:
        - Безопасную обработку нажатия без callback
        - Отсутствие исключений при нажатии
        
        Requirements: 1.1
        """
        # Arrange - создаем виджет без callback
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=None
        )

        # Act & Assert - нажатие не должно вызывать исключений
        add_button = widget.add_payment_button
        
        try:
            add_button.on_click(None)
            # Если дошли сюда, значит исключений не было
        except Exception as e:
            self.fail(f"Нажатие кнопки без callback не должно вызывать исключения: {e}")

    def test_callback_storage_in_widget(self):
        """
        Тест сохранения callback в виджете.
        
        Проверяет:
        - Сохранение callback функции в атрибуте виджета
        - Доступность callback для использования
        
        Requirements: 1.1, 1.2
        """
        # Arrange & Act - создаем виджет с callback
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
        )

        # Assert - проверяем сохранение callback
        self.assertEqual(widget.on_add_payment, self.mock_on_add_payment, "Callback должен быть сохранен в виджете")

    def test_button_attributes_consistency(self):
        """
        Тест консистентности атрибутов кнопки при разных условиях.

        Проверяет:
        - Одинаковые атрибуты кнопки независимо от callback

        Requirements: 4.2, 4.3, 4.4
        """
        # Arrange - создаем два виджета: с callback и без
        widget_with_callback = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment
        )

        widget_without_callback = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=None
        )

        # Act - получаем кнопки из обоих виджетов
        button_with_callback = widget_with_callback.add_payment_button
        button_without_callback = widget_without_callback.add_payment_button

        # Assert - проверяем, что атрибуты одинаковые
        self.assertEqual(button_with_callback.icon, button_without_callback.icon)
        self.assertEqual(button_with_callback.tooltip, button_without_callback.tooltip)
        self.assertEqual(button_with_callback.icon_color, button_without_callback.icon_color)


class TestPendingPaymentsWidgetEditButton(unittest.TestCase):
    """Unit тесты для кнопки редактирования в PendingPaymentsWidget."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_cancel = Mock()
        self.mock_on_delete = Mock()
        self.mock_on_show_all = Mock()
        self.mock_on_add_payment = Mock()
        self.mock_on_edit = Mock()

    def test_on_edit_callback_storage(self):
        """
        Тест сохранения callback для редактирования в виджете.

        Проверяет:
        - Сохранение on_edit callback в атрибуте виджета.
        """
        # Arrange & Act
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_add_payment=self.mock_on_add_payment,
            on_edit=self.mock_on_edit
        )

        # Assert
        self.assertEqual(widget.on_edit, self.mock_on_edit, "on_edit callback должен быть сохранён")

    def test_on_edit_callback_none_by_default(self):
        """
        Тест значения по умолчанию для on_edit callback.

        Проверяет:
        - on_edit равен None если не передан.
        """
        # Arrange & Act
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all
        )

        # Assert
        self.assertIsNone(widget.on_edit, "on_edit должен быть None по умолчанию")

    def test_edit_button_in_payment_card(self):
        """
        Тест наличия кнопки редактирования в карточке платежа.

        Проверяет:
        - Кнопка редактирования присутствует в карточке платежа.
        - Кнопка имеет правильную иконку и tooltip.
        """
        # Arrange
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_edit=self.mock_on_edit
        )

        # Создаём mock платежа
        mock_payment = Mock(spec=PendingPaymentDB)
        mock_payment.id = 1
        mock_payment.amount = Decimal("100.00")
        mock_payment.description = "Тестовый платёж"
        mock_payment.priority = PendingPaymentPriority.MEDIUM
        mock_payment.planned_date = None

        # Act
        card = widget._build_payment_card(mock_payment)

        # Assert - ищем кнопку редактирования в структуре карточки
        # Карточка содержит Column -> последний элемент Row с кнопками
        card_column = card.content
        buttons_row = card_column.controls[-1]  # Последний элемент - Row с кнопками

        # Проверяем, что есть 4 кнопки (execute, edit, cancel, delete)
        self.assertEqual(len(buttons_row.controls), 4, "Должно быть 4 кнопки действий")

        # Вторая кнопка должна быть кнопкой редактирования
        edit_button = buttons_row.controls[1]
        self.assertIsInstance(edit_button, ft.IconButton, "Вторая кнопка должна быть IconButton")
        self.assertEqual(edit_button.icon, ft.Icons.EDIT_OUTLINED, "Кнопка должна иметь иконку EDIT_OUTLINED")
        self.assertEqual(edit_button.tooltip, "Редактировать", "Кнопка должна иметь tooltip 'Редактировать'")

    def test_edit_button_callback_invocation(self):
        """
        Тест вызова callback при нажатии кнопки редактирования.

        Проверяет:
        - Вызов on_edit callback с правильным платежом.
        """
        # Arrange
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_edit=self.mock_on_edit
        )

        mock_payment = Mock(spec=PendingPaymentDB)
        mock_payment.id = 1
        mock_payment.amount = Decimal("100.00")
        mock_payment.description = "Тестовый платёж"
        mock_payment.priority = PendingPaymentPriority.MEDIUM
        mock_payment.planned_date = None

        card = widget._build_payment_card(mock_payment)
        card_column = card.content
        buttons_row = card_column.controls[-1]
        edit_button = buttons_row.controls[1]

        # Act - симулируем нажатие кнопки
        edit_button.on_click(None)

        # Assert
        self.mock_on_edit.assert_called_once_with(mock_payment)

    def test_safe_edit_payment_with_none_callback(self):
        """
        Тест безопасного вызова _safe_edit_payment без callback.

        Проверяет:
        - Отсутствие исключений при вызове без callback.
        """
        # Arrange
        widget = PendingPaymentsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_cancel=self.mock_on_cancel,
            on_delete=self.mock_on_delete,
            on_show_all=self.mock_on_show_all,
            on_edit=None  # Без callback
        )

        mock_payment = Mock(spec=PendingPaymentDB)
        mock_payment.id = 1

        # Act & Assert - не должно быть исключений
        try:
            widget._safe_edit_payment(mock_payment)
        except Exception as e:
            self.fail(f"_safe_edit_payment не должен вызывать исключения без callback: {e}")


if __name__ == '__main__':
    unittest.main()
