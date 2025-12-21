"""
Unit тесты для адаптивной функциональности CalendarLegend.

Проверяет корректность работы методов вычисления ширины,
определения режима отображения и построения UI.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch

import flet as ft

from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    INDICATOR_CONFIGS
)


class TestCalendarLegendAdaptiveUnit(unittest.TestCase):
    """Unit тесты для адаптивной функциональности CalendarLegend."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаём mock для логгера, чтобы избежать ошибок логирования в тестах
        self.logger_patcher = patch('finance_tracker.components.calendar_legend.logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        """Очистка после каждого теста."""
        self.logger_patcher.stop()

    def test_initialization_without_width(self):
        """Тест инициализации без указания ширины календаря."""
        legend = CalendarLegend()
        
        # Проверяем базовые свойства
        self.assertIsNone(legend.calendar_width)
        self.assertEqual(legend.display_mode, DisplayMode.AUTO)
        self.assertIsNotNone(legend.all_indicators)
        self.assertIsNotNone(legend.modal_manager)
        
        # Проверяем, что загружены все индикаторы
        self.assertEqual(len(legend.all_indicators), 7)
        
        # Проверяем сортировку по приоритету
        priorities = [indicator.priority for indicator in legend.all_indicators]
        self.assertEqual(priorities, sorted(priorities))

    def test_initialization_with_width(self):
        """Тест инициализации с указанием ширины календаря."""
        test_width = 800
        legend = CalendarLegend(calendar_width=test_width)
        
        self.assertEqual(legend.calendar_width, test_width)
        self.assertIsNotNone(legend.content)

    def test_calculate_required_width(self):
        """Тест вычисления необходимой ширины."""
        legend = CalendarLegend()
        
        required_width = legend._calculate_required_width()
        
        # Проверяем, что ширина положительная
        self.assertGreater(required_width, 0)
        
        # Проверяем, что ширина разумная (не слишком большая и не слишком маленькая)
        self.assertGreater(required_width, 200)  # Минимум для 7 индикаторов
        self.assertLess(required_width, 1000)    # Максимум разумный

    def test_calculate_required_width_formula(self):
        """Тест корректности формулы вычисления ширины."""
        legend = CalendarLegend()
        
        # Получаем фактическую ширину от WidthCalculator
        actual_width = legend._calculate_required_width()
        
        # Проверяем, что ширина находится в разумных пределах (обновленные значения)
        # Ожидаем около 521px (новое значение от WidthCalculator)
        self.assertGreaterEqual(actual_width, 500)
        self.assertLessEqual(actual_width, 550)
        
        # Проверяем, что это именно значение от WidthCalculator
        self.assertEqual(actual_width, 521)

    def test_should_show_full_legend_no_width(self):
        """Тест определения режима отображения без указания ширины."""
        legend = CalendarLegend()
        
        # Без указания ширины должна показываться полная легенда
        self.assertTrue(legend._should_show_full_legend())

    def test_should_show_full_legend_wide_width(self):
        """Тест определения режима отображения при широкой ширине."""
        wide_width = 1200  # Заведомо достаточная ширина
        legend = CalendarLegend(calendar_width=wide_width)
        
        self.assertTrue(legend._should_show_full_legend())

    def test_should_show_full_legend_narrow_width(self):
        """Тест определения режима отображения при узкой ширине."""
        narrow_width = 300  # Заведомо недостаточная ширина
        legend = CalendarLegend(calendar_width=narrow_width)
        
        self.assertFalse(legend._should_show_full_legend())

    def test_get_priority_indicators_for_width(self):
        """Тест получения приоритетных индикаторов для заданной ширины."""
        legend = CalendarLegend()
        
        # Тестируем с узкой шириной
        narrow_width = 400
        priority_indicators = legend._get_priority_indicators_for_width(narrow_width)
        
        # Должны получить хотя бы первые два индикатора (доходы и расходы)
        self.assertGreaterEqual(len(priority_indicators), 1)
        self.assertLessEqual(len(priority_indicators), len(legend.all_indicators))
        
        # Проверяем, что индикаторы идут по приоритету
        if len(priority_indicators) > 1:
            for i in range(len(priority_indicators) - 1):
                self.assertLess(
                    priority_indicators[i].priority,
                    priority_indicators[i + 1].priority
                )

    def test_get_priority_indicators_first_two_are_income_expense(self):
        """Тест, что первые два индикатора - доходы и расходы."""
        legend = CalendarLegend()
        
        # Берём достаточную ширину для первых двух индикаторов
        width_for_two = 300
        priority_indicators = legend._get_priority_indicators_for_width(width_for_two)
        
        if len(priority_indicators) >= 2:
            types = {indicator.type for indicator in priority_indicators[:2]}
            expected_types = {IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT}
            self.assertEqual(types, expected_types)

    def test_build_legend_item_with_color(self):
        """Тест создания элемента легенды с цветом (обратная совместимость)."""
        legend = CalendarLegend()
        
        item = legend._build_legend_item(ft.Colors.GREEN, "Тест")
        
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)
        self.assertIsInstance(item.controls[0], ft.Container)
        self.assertIsInstance(item.controls[1], ft.Text)
        self.assertEqual(item.controls[1].value, "Тест")

    def test_build_legend_item_with_visual_element(self):
        """Тест создания элемента легенды с визуальным элементом."""
        legend = CalendarLegend()
        
        visual_element = ft.Text("◆", size=12, color=ft.Colors.ORANGE)
        item = legend._build_legend_item(visual_element, "Плановая")
        
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)
        self.assertEqual(item.controls[0], visual_element)
        self.assertEqual(item.controls[1].value, "Плановая")

    def test_build_full_legend(self):
        """Тест построения полной легенды с визуальной группировкой."""
        legend = CalendarLegend()
        
        full_legend = legend._build_full_legend()
        
        self.assertIsInstance(full_legend, ft.Row)
        # Теперь должно быть 7 индикаторов + 2 разделителя между группами = 9 элементов
        # (dots: 2 индикатора | symbols: 3 индикатора | backgrounds: 2 индикатора)
        self.assertEqual(len(full_legend.controls), 9)
        self.assertEqual(full_legend.alignment, ft.MainAxisAlignment.CENTER)
        
        # Проверяем, что есть разделители между группами
        separators = [c for c in full_legend.controls if isinstance(c, ft.Container) and hasattr(c, 'width') and c.width == 1]
        self.assertEqual(len(separators), 2, "Должно быть 2 разделителя между 3 группами")

    def test_build_compact_legend(self):
        """Тест построения сокращённой легенды."""
        legend = CalendarLegend(calendar_width=400)  # Узкая ширина
        
        compact_legend = legend._build_compact_legend()
        
        self.assertIsInstance(compact_legend, ft.Row)
        # Должно быть больше 1 элемента (индикаторы + кнопка)
        self.assertGreater(len(compact_legend.controls), 1)
        
        # Последний элемент должен быть кнопкой "Подробнее"
        last_control = compact_legend.controls[-1]
        self.assertIsInstance(last_control, ft.TextButton)
        self.assertEqual(last_control.text, "Подробнее...")

    def test_update_calendar_width_no_mode_change(self):
        """Тест обновления ширины без изменения режима отображения."""
        legend = CalendarLegend(calendar_width=1000)  # Широкая ширина
        
        # Обновляем на другую широкую ширину
        legend.update_calendar_width(1200)
        
        self.assertEqual(legend.calendar_width, 1200)

    def test_update_calendar_width_with_mode_change(self):
        """Тест обновления ширины с изменением режима отображения."""
        legend = CalendarLegend(calendar_width=1000)  # Широкая ширина (полный режим)
        
        # Обновляем на узкую ширину (должен переключиться в компактный режим)
        legend.update_calendar_width(300)
        
        self.assertEqual(legend.calendar_width, 300)
        self.assertFalse(legend._should_show_full_legend())

    def test_safe_get_page_from_event_control(self):
        """Тест безопасного получения page из события с control."""
        legend = CalendarLegend()
        
        # Создаём mock события с control.page
        mock_event = Mock()
        mock_page = Mock()
        mock_event.control.page = mock_page
        
        result = legend._safe_get_page(mock_event)
        
        self.assertEqual(result, mock_page)

    def test_safe_get_page_from_event_page(self):
        """Тест безопасного получения page из события с page."""
        legend = CalendarLegend()
        
        # Создаём mock события с прямым page
        mock_event = Mock()
        mock_page = Mock()
        mock_event.page = mock_page
        mock_event.control = None
        
        result = legend._safe_get_page(mock_event)
        
        self.assertEqual(result, mock_page)

    def test_safe_get_page_none(self):
        """Тест безопасного получения page при отсутствии page."""
        legend = CalendarLegend()
        
        # Создаём mock события без page
        mock_event = Mock()
        mock_event.control = None
        mock_event.page = None
        
        result = legend._safe_get_page(mock_event)
        
        self.assertIsNone(result)

    def test_open_modal_safe_success(self):
        """Тест успешного открытия модального окна."""
        legend = CalendarLegend()
        
        # Создаём mock события и page
        mock_event = Mock()
        mock_page = Mock()
        mock_event.control.page = mock_page
        
        # Мокируем метод open_modal ModalManager'а
        with patch.object(legend.modal_manager, 'open_modal', return_value=True) as mock_open:
            legend._open_modal_safe(mock_event)
            
            # Проверяем, что метод был вызван с event_or_control параметром
            mock_open.assert_called_once_with(event_or_control=mock_event)

    def test_open_modal_safe_no_page(self):
        """Тест открытия модального окна без page."""
        legend = CalendarLegend()
        
        # Создаём mock события без page
        mock_event = Mock()
        mock_event.control = None
        mock_event.page = None
        
        # Мокируем метод open_modal ModalManager'а
        with patch.object(legend.modal_manager, 'open_modal', return_value=False) as mock_open:
            # Мокируем _safe_get_page чтобы он возвращал None
            with patch.object(legend, '_safe_get_page', return_value=None):
                legend._open_modal_safe(mock_event)
                
                # Проверяем, что метод был вызван с event_or_control
                mock_open.assert_called_once_with(event_or_control=mock_event)

    def test_backward_compatibility_methods(self):
        """Тест методов обратной совместимости."""
        legend = CalendarLegend()
        
        # Проверяем, что методы существуют и не вызывают ошибок
        content = legend._build_full_legend_content()
        self.assertIsNotNone(content)
        
        # Тестируем _open_dlg (должен перенаправлять на _open_modal_safe)
        mock_event = Mock()
        mock_event.control = None
        
        with patch.object(legend, '_open_modal_safe') as mock_open_modal:
            legend._open_dlg(mock_event)
            mock_open_modal.assert_called_once_with(mock_event)

    def test_error_handling_in_calculate_width(self):
        """Тест обработки ошибок при вычислении ширины."""
        legend = CalendarLegend()
        
        # Мокируем ошибку при итерации по all_indicators
        # Создаём объект, который вызывает ошибку при итерации
        class ErrorIterator:
            def __iter__(self):
                raise Exception("Test error")
        
        legend.all_indicators = ErrorIterator()
        width = legend._calculate_required_width()
        
        # Должен вернуть fallback значение (обновленное значение)
        self.assertEqual(width, 525)

    def test_error_handling_in_build_legend_item(self):
        """Тест обработки ошибок при создании элемента легенды."""
        legend = CalendarLegend()
        
        # Тестируем с некорректными данными
        item = legend._build_legend_item(None, None)
        
        # Должен создать fallback элемент
        self.assertIsInstance(item, ft.Row)
        self.assertEqual(len(item.controls), 2)


if __name__ == '__main__':
    unittest.main()