"""
UI тесты для CalendarLegend компонента.

Проверяет пользовательский интерфейс календарной легенды:
- Атрибуты кнопки "Подробнее"
- Открытие модального окна при клике
- Видимость кнопки в зависимости от ширины
- Содержимое модального окна
- Кнопка закрытия модального окна
- Property 12: Event handling robustness
"""
import unittest
from unittest.mock import Mock, MagicMock, patch

import flet as ft
from hypothesis import given, strategies as st

from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    INDICATOR_CONFIGS
)


def create_mock_page():
    """Создает полностью настроенный mock объект для Flet Page."""
    mock_page = MagicMock()
    
    # Настройка основных методов
    mock_page.open = Mock()
    mock_page.close = Mock()
    mock_page.update = Mock()
    mock_page.add = Mock()
    mock_page.remove = Mock()
    
    # Настройка свойств
    mock_page.width = 1200
    mock_page.height = 800
    mock_page.theme_mode = "light"
    
    # Настройка диалогов
    mock_page.dialog = None
    mock_page.snack_bar = None
    
    return mock_page


class TestCalendarLegendUI(unittest.TestCase):
    """UI тесты для CalendarLegend компонента."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаём mock для логгера, чтобы избежать ошибок логирования в тестах
        self.logger_patcher = patch('finance_tracker.components.calendar_legend.logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.mock_page = create_mock_page()

    def tearDown(self):
        """Очистка после каждого теста."""
        self.logger_patcher.stop()

    def test_details_button_attributes(self):
        """Тест атрибутов кнопки 'Подробнее'."""
        # Создаём легенду с узкой шириной, чтобы появилась кнопка "Подробнее"
        legend = CalendarLegend(calendar_width=400)
        
        # Получаем кнопку из компактной легенды
        compact_legend = legend._build_compact_legend()
        details_button = compact_legend.controls[-1]  # Последний элемент
        
        # Проверяем атрибуты кнопки
        self.assertIsInstance(details_button, ft.TextButton)
        self.assertEqual(details_button.text, "Подробнее...")
        self.assertIsNotNone(details_button.on_click)
        self.assertEqual(details_button.height, 30)

    def test_details_button_click_opens_modal(self):
        """Тест открытия модального окна при клике на 'Подробнее'."""
        legend = CalendarLegend(calendar_width=400)
        
        # Симулируем клик на кнопку "Подробнее"
        mock_event = Mock()
        mock_event.control.page = self.mock_page
        
        # Мокируем метод open_modal ModalManager'а для проверки вызова
        with patch.object(legend.modal_manager, 'open_modal', return_value=True) as mock_open:
            legend._open_modal_safe(mock_event)
            
            # Проверяем вызов открытия модального окна с event_or_control
            mock_open.assert_called_once_with(event_or_control=mock_event)

    def test_details_button_visibility_based_on_width(self):
        """Тест видимости кнопки в зависимости от ширины."""
        # Широкая ширина - кнопка не должна показываться
        wide_legend = CalendarLegend(calendar_width=1000)
        self.assertTrue(wide_legend._should_show_full_legend())
        
        # Узкая ширина - кнопка должна показываться
        narrow_legend = CalendarLegend(calendar_width=300)
        self.assertFalse(narrow_legend._should_show_full_legend())
        
        # Проверяем наличие кнопки в компактной легенде
        compact_legend = narrow_legend._build_compact_legend()
        last_control = compact_legend.controls[-1]
        self.assertIsInstance(last_control, ft.TextButton)
        self.assertEqual(last_control.text, "Подробнее...")
        
        # Проверяем отсутствие кнопки в полной легенде
        full_legend = wide_legend._build_full_legend()
        button_texts = [
            control.text for control in full_legend.controls 
            if hasattr(control, 'text') and control.text
        ]
        self.assertNotIn("Подробнее...", button_texts)

    def test_modal_dialog_content(self):
        """Тест содержимого модального окна."""
        legend = CalendarLegend()
        modal = legend.modal_manager.create_modal(legend.all_indicators)
        
        # Проверяем заголовок
        self.assertEqual(modal.title.value, "Легенда календаря")
        
        # Проверяем наличие всех индикаторов в содержимом
        content = modal.content
        self.assertIsInstance(content, ft.Column)
        
        # Проверяем, что модальное окно содержит группы индикаторов
        controls = content.controls
        self.assertGreater(len(controls), 0)
        
        # Проверяем наличие кнопки закрытия
        self.assertEqual(len(modal.actions), 1)
        close_button = modal.actions[0]
        self.assertEqual(close_button.text, "Закрыть")

    def test_modal_close_button_functionality(self):
        """Тест функциональности кнопки закрытия модального окна."""
        legend = CalendarLegend()
        modal = legend.modal_manager.create_modal(legend.all_indicators)
        
        # Открываем модальное окно
        self.mock_page.dialog = modal
        modal.open = True
        
        # Симулируем клик на кнопку "Закрыть"
        close_button = modal.actions[0]  # Первая кнопка - "Закрыть"
        mock_event = Mock()
        mock_event.control.page = self.mock_page
        
        # Мокируем метод close_modal для проверки вызова
        with patch.object(legend.modal_manager, 'close_modal', return_value=True) as mock_close:
            close_button.on_click(mock_event)
            
            # Проверяем вызов закрытия модального окна с дополнительным параметром
            mock_close.assert_called_once_with(self.mock_page, mock_event)

    def test_modal_error_handling_without_page(self):
        """Тест обработки ошибок при отсутствии page объекта."""
        legend = CalendarLegend()
        
        # Симулируем событие без page объекта
        mock_event = Mock()
        mock_event.control = None
        mock_event.page = None
        
        # Попытка открытия не должна вызывать исключений
        try:
            result = legend._open_modal_safe(mock_event)
            # Операция должна завершиться без ошибок, но неуспешно
            # (результат не проверяем, так как метод может не возвращать значение)
        except Exception as e:
            self.fail(f"_open_modal_safe raised an exception with no page: {e}")

    def test_safe_get_page_robustness(self):
        """Тест устойчивости метода _safe_get_page к различным входным данным."""
        legend = CalendarLegend()
        
        # Тест с None
        result = legend._safe_get_page(None)
        self.assertIsNone(result)
        
        # Тест с объектом без атрибутов
        empty_obj = object()
        result = legend._safe_get_page(empty_obj)
        self.assertIsNone(result)
        
        # Тест с корректным событием
        mock_event = Mock()
        mock_page = Mock()
        mock_event.control.page = mock_page
        
        result = legend._safe_get_page(mock_event)
        self.assertEqual(result, mock_page)

    def test_legend_item_creation_robustness(self):
        """Тест устойчивости создания элементов легенды к некорректным данным."""
        legend = CalendarLegend()
        
        # Тест с None значениями
        item = legend._build_legend_item(None, None)
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)
        
        # Тест с пустой строкой
        item = legend._build_legend_item(ft.Colors.GREEN, "")
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)
        
        # Тест с очень длинной строкой
        long_text = "A" * 1000
        item = legend._build_legend_item(ft.Colors.RED, long_text)
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)

    def test_ui_initialization_stability(self):
        """Тест стабильности инициализации UI при различных условиях."""
        # Тест с различными ширинами
        widths = [None, 100, 300, 500, 800, 1200, 2000]
        
        for width in widths:
            try:
                legend = CalendarLegend(calendar_width=width)
                self.assertIsNotNone(legend.content)
                self.assertIsInstance(legend.content, ft.Row)
            except Exception as e:
                self.fail(f"CalendarLegend initialization failed with width {width}: {e}")

    def test_backward_compatibility_methods(self):
        """Тест методов обратной совместимости."""
        legend = CalendarLegend()
        
        # Тест _open_dlg (должен перенаправлять на _open_modal_safe)
        mock_event = Mock()
        mock_event.control = None
        
        with patch.object(legend, '_open_modal_safe') as mock_open_modal:
            legend._open_dlg(mock_event)
            mock_open_modal.assert_called_once_with(mock_event)
        
        # Тест _close_dlg
        mock_event = Mock()
        mock_event.control.page = self.mock_page
        
        with patch.object(legend.modal_manager, 'close_modal', return_value=True) as mock_close:
            legend._close_dlg(mock_event)
            mock_close.assert_called_once_with(self.mock_page)

    @given(st.integers(min_value=200, max_value=1500))
    def test_adaptive_button_display_property(self, calendar_width):
        """
        **Feature: calendar-legend-improvement, Property 12: Event handling robustness**
        **Validates: Requirements 3.1, 3.4, 5.2, 5.3**
        
        Property: Кнопка 'Подробнее' должна отображаться только при недостаточной ширине.
        """
        legend = CalendarLegend(calendar_width=calendar_width)
        
        required_width = legend._calculate_required_width()
        should_show_full = calendar_width >= required_width
        
        if should_show_full:
            # При достаточной ширине кнопка не должна показываться
            full_legend = legend._build_full_legend()
            button_texts = [
                control.text for control in full_legend.controls 
                if hasattr(control, 'text') and control.text
            ]
            assert "Подробнее..." not in button_texts
        else:
            # При недостаточной ширине кнопка должна показываться
            compact_legend = legend._build_compact_legend()
            button_texts = [
                control.text for control in compact_legend.controls 
                if hasattr(control, 'text') and control.text
            ]
            assert "Подробнее..." in button_texts

    @given(st.one_of(st.none(), st.text(), st.integers()))
    def test_event_handling_robustness_property(self, invalid_event_data):
        """
        **Feature: calendar-legend-improvement, Property 12: Event handling robustness**
        **Validates: Requirements 5.3**
        
        Property: Любые события должны обрабатываться без исключений.
        """
        legend = CalendarLegend()
        
        # Тестируем обработку некорректных событий
        try:
            legend._safe_get_page(invalid_event_data)
            # Метод должен вернуть None или корректное значение, но не упасть
        except Exception as e:
            # Если возникло исключение, это нарушение свойства
            assert False, f"Event handling failed with data {invalid_event_data}: {e}"

    @given(st.booleans())
    def test_modal_operations_robustness_property(self, has_page):
        """
        **Feature: calendar-legend-improvement, Property 12: Event handling robustness**
        **Validates: Requirements 3.1, 5.2**
        
        Property: Операции с модальным окном должны быть устойчивы к отсутствию page.
        """
        legend = CalendarLegend()
        
        # Создаём событие с page или без него
        mock_event = Mock()
        if has_page:
            mock_event.control.page = create_mock_page()
        else:
            mock_event.control = None
            mock_event.page = None
        
        # Операции не должны вызывать исключений
        try:
            legend._open_modal_safe(mock_event)
            legend._close_dlg(mock_event)
        except Exception as e:
            assert False, f"Modal operations failed with has_page={has_page}: {e}"

    def test_ui_component_structure(self):
        """Тест структуры UI компонентов."""
        # Тест полной легенды
        legend = CalendarLegend(calendar_width=1200)
        full_legend = legend._build_full_legend()
        
        self.assertIsInstance(full_legend, ft.Row)
        self.assertEqual(full_legend.alignment, ft.MainAxisAlignment.CENTER)
        self.assertEqual(full_legend.spacing, 20)
        self.assertEqual(full_legend.vertical_alignment, ft.CrossAxisAlignment.CENTER)
        
        # Тест компактной легенды
        compact_legend = legend._build_compact_legend()
        
        self.assertIsInstance(compact_legend, ft.Row)
        self.assertEqual(compact_legend.alignment, ft.MainAxisAlignment.CENTER)
        self.assertEqual(compact_legend.spacing, 20)
        self.assertEqual(compact_legend.vertical_alignment, ft.CrossAxisAlignment.CENTER)

    def test_legend_content_consistency(self):
        """Тест консистентности содержимого легенды."""
        legend = CalendarLegend()
        
        # Проверяем, что все индикаторы из конфигурации присутствуют
        self.assertEqual(len(legend.all_indicators), len(INDICATOR_CONFIGS))
        
        # Проверяем сортировку по приоритету
        priorities = [indicator.priority for indicator in legend.all_indicators]
        self.assertEqual(priorities, sorted(priorities))
        
        # Проверяем, что все типы индикаторов представлены
        indicator_types = {indicator.type for indicator in legend.all_indicators}
        expected_types = set(IndicatorType)
        self.assertEqual(indicator_types, expected_types)


if __name__ == '__main__':
    unittest.main()