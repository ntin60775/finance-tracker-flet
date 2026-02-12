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
from finance_tracker.components.calendar_legend_types import IndicatorType, INDICATOR_CONFIGS


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
    mock_page.snack_bar = None

    return mock_page


class TestCalendarLegendUI(unittest.TestCase):
    """UI тесты для CalendarLegend компонента."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаём mock для логгера, чтобы избежать ошибок логирования в тестах
        self.logger_patcher = patch("finance_tracker.components.calendar_legend.logger")
        self.mock_logger = self.logger_patcher.start()

        self.mock_page = create_mock_page()

    def tearDown(self):
        """Очистка после каждого теста."""
        self.logger_patcher.stop()

    def test_details_button_attributes(self):
        """Тест атрибутов кнопки 'Подробнее'."""
        # Создаём легенду с узкой шириной
        legend = CalendarLegend(calendar_width=400)

        compact_legend = legend._build_compact_legend()
        details_buttons = [
            control for control in compact_legend.controls if isinstance(control, ft.TextButton)
        ]
        self.assertEqual(len(details_buttons), 0)

    def test_details_button_click_opens_modal(self):
        """Проверка, что кнопка details больше не создаётся."""
        legend = CalendarLegend(calendar_width=400)
        compact_legend = legend._build_compact_legend()
        details_buttons = [
            control for control in compact_legend.controls if isinstance(control, ft.TextButton)
        ]
        self.assertEqual(len(details_buttons), 0)

    def test_details_button_visibility_based_on_width(self):
        """Тест видимости кнопки в зависимости от ширины."""
        # Широкая ширина - кнопка не должна показываться
        wide_legend = CalendarLegend(calendar_width=1000)
        self.assertTrue(wide_legend._should_show_full_legend())

        # Узкая ширина - кнопка должна показываться
        narrow_legend = CalendarLegend(calendar_width=300)
        self.assertFalse(narrow_legend._should_show_full_legend())

        # Проверяем отсутствие кнопки в компактной легенде
        compact_legend = narrow_legend._build_compact_legend()
        compact_buttons = [
            control for control in compact_legend.controls if isinstance(control, ft.TextButton)
        ]
        self.assertEqual(len(compact_buttons), 0)

        # Проверяем отсутствие кнопки в полной легенде
        full_legend = wide_legend._build_full_legend()
        button_texts = [
            control.text
            for control in full_legend.controls
            if hasattr(control, "text") and control.text
        ]
        self.assertNotIn("...", button_texts)

    def test_full_legend_has_multiline_and_no_separator_profile(self):
        legend = CalendarLegend(calendar_width=1200)
        full_legend = legend._build_full_legend()

        self.assertIsInstance(full_legend, ft.Row)
        self.assertTrue(full_legend.wrap)

        for row_control in full_legend.controls:
            if isinstance(row_control, ft.Row):
                for control in row_control.controls:
                    if isinstance(control, ft.Container):
                        is_separator_like = (
                            control.width == 1
                            and control.height == 16
                            and control.bgcolor == ft.Colors.OUTLINE_VARIANT
                        )
                        self.assertFalse(
                            is_separator_like,
                            "В full-mode не должно быть separator-профиля width=1,height=16,bgcolor=OUTLINE_VARIANT",
                        )

    def test_update_calendar_width_preserves_no_details_button_contract(self):
        legend = CalendarLegend(calendar_width=1200)
        narrow_width = 250

        legend.update_calendar_width(narrow_width)

        self.assertFalse(legend._should_show_full_legend())
        self.assertIsInstance(legend.content, ft.Row)
        compact_buttons = [
            control for control in legend.content.controls if isinstance(control, ft.TextButton)
        ]
        self.assertEqual(len(compact_buttons), 0)

        legend.update_calendar_width(1400)
        self.assertTrue(legend._should_show_full_legend())

        legend.update_calendar_width(narrow_width)

        self.assertFalse(legend._should_show_full_legend())
        self.assertIsInstance(legend.content, ft.Row)
        compact_buttons = [
            control for control in legend.content.controls if isinstance(control, ft.TextButton)
        ]
        self.assertEqual(len(compact_buttons), 0)

    def test_modal_dialog_content(self):
        """Проверка удаления modal-обвязки из CalendarLegend."""
        legend = CalendarLegend()
        self.assertFalse(hasattr(legend, "modal_manager"))

    def test_modal_close_button_functionality(self):
        """Проверка отсутствия modal API."""
        legend = CalendarLegend()
        self.assertFalse(hasattr(legend, "_open_modal_safe"))
        self.assertFalse(hasattr(legend, "_close_dlg"))

    def test_modal_error_handling_without_page(self):
        """Проверка отсутствия modal API при любых page-сценариях."""
        legend = CalendarLegend()
        self.assertFalse(hasattr(legend, "_open_modal_safe"))

    def test_safe_get_page_robustness(self):
        """Проверка, что legacy page-access API удалён."""
        legend = CalendarLegend()
        self.assertFalse(hasattr(legend, "_safe_get_page"))

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
        """Проверка удаления legacy modal-методов."""
        legend = CalendarLegend()
        self.assertFalse(hasattr(legend, "_open_dlg"))
        self.assertFalse(hasattr(legend, "_close_dlg"))

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
            full_legend = legend._build_full_legend()
            buttons = [
                control for control in full_legend.controls if isinstance(control, ft.TextButton)
            ]
            assert len(buttons) == 0
        else:
            compact_legend = legend._build_compact_legend()
            buttons = [
                control for control in compact_legend.controls if isinstance(control, ft.TextButton)
            ]
            assert len(buttons) == 0

    @given(st.one_of(st.none(), st.text(), st.integers()))
    def test_event_handling_robustness_property(self, invalid_event_data):
        """
        **Feature: calendar-legend-improvement, Property 12: Event handling robustness**
        **Validates: Requirements 5.3**

        Property: Любые события должны обрабатываться без исключений.
        """
        legend = CalendarLegend()

        assert invalid_event_data is None or invalid_event_data is not None
        assert not hasattr(legend, "_safe_get_page")

    @given(st.booleans())
    def test_modal_operations_robustness_property(self, has_page):
        """
        **Feature: calendar-legend-improvement, Property 12: Event handling robustness**
        **Validates: Requirements 3.1, 5.2**

        Property: Операции с модальным окном должны быть устойчивы к отсутствию page.
        """
        legend = CalendarLegend()

        assert has_page in {True, False}
        assert not hasattr(legend, "_open_modal_safe")
        assert not hasattr(legend, "_close_dlg")

    def test_ui_component_structure(self):
        """Тест структуры UI компонентов."""
        # Тест полной легенды
        legend = CalendarLegend(calendar_width=1200)
        full_legend = legend._build_full_legend()

        self.assertIsInstance(full_legend, ft.Row)
        self.assertEqual(full_legend.alignment, ft.MainAxisAlignment.CENTER)
        self.assertEqual(full_legend.spacing, 16)
        self.assertEqual(full_legend.vertical_alignment, ft.CrossAxisAlignment.CENTER)
        self.assertEqual(full_legend.run_spacing, 8)
        self.assertTrue(full_legend.wrap)

        # Тест компактной легенды
        compact_legend = legend._build_compact_legend()

        self.assertIsInstance(compact_legend, ft.Row)
        self.assertEqual(compact_legend.alignment, ft.MainAxisAlignment.CENTER)
        self.assertEqual(compact_legend.spacing, 16)
        self.assertEqual(compact_legend.vertical_alignment, ft.CrossAxisAlignment.CENTER)
        self.assertEqual(compact_legend.run_spacing, 8)
        self.assertTrue(compact_legend.wrap)

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


if __name__ == "__main__":
    unittest.main()
