"""
Тесты обработки ошибок для CalendarLegend компонента.

Проверяет устойчивость компонента к различным ошибочным ситуациям:
- Обработка ошибок при отсутствии page объекта
- Fallback значения при ошибках вычисления ширины
- Стабильность при изменении размеров окна
- Property 7: Page object handling
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


class TestCalendarLegendErrorHandling(unittest.TestCase):
    """Тесты обработки ошибок для CalendarLegend компонента."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        # Создаём mock для логгера, чтобы избежать ошибок логирования в тестах
        self.logger_patcher = patch('finance_tracker.components.calendar_legend.logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.mock_page = create_mock_page()

    def tearDown(self):
        """Очистка после каждого теста."""
        self.logger_patcher.stop()

    def test_page_object_missing_in_modal_operations(self):
        """Тест обработки ошибок при отсутствии page объекта в модальных операциях."""
        legend = CalendarLegend()
        
        # Тест открытия модального окна без page
        mock_event_no_page = Mock()
        mock_event_no_page.control = None
        mock_event_no_page.page = None
        
        # Операция не должна вызывать исключений
        try:
            legend._open_modal_safe(mock_event_no_page)
            # Проверяем, что логгер был вызван с предупреждением
            self.mock_logger.warning.assert_called()
        except Exception as e:
            self.fail(f"_open_modal_safe raised exception with no page: {e}")
        
        # Тест закрытия модального окна без page
        try:
            legend._close_dlg(mock_event_no_page)
            # Операция должна завершиться без ошибок
        except Exception as e:
            self.fail(f"_close_dlg raised exception with no page: {e}")

    def test_page_object_with_invalid_attributes(self):
        """Тест обработки page объектов с некорректными атрибутами."""
        legend = CalendarLegend()
        
        # Тест с None - это нормальная ситуация, не требующая логирования
        result = legend._safe_get_page(None)
        self.assertIsNone(result)
        
        # Тест с числом - hasattr вернёт False, но не вызовет исключение
        result = legend._safe_get_page(12345)
        self.assertIsNone(result)
        
        # Тест с объектом без нужных атрибутов - тоже нормальная ситуация
        empty_obj = object()
        result = legend._safe_get_page(empty_obj)
        self.assertIsNone(result)
        
        # Все эти случаи должны обрабатываться без исключений
        # и возвращать None, что является корректным поведением

    def test_width_calculation_fallback_on_error(self):
        """Тест fallback значений при ошибках вычисления ширины."""
        legend = CalendarLegend()
        
        # Мокируем ошибку при доступе к estimated_width
        class ErrorIndicator:
            @property
            def estimated_width(self):
                raise Exception("Test error in width calculation")
        
        # Заменяем индикаторы на проблемные
        legend.all_indicators = [ErrorIndicator(), ErrorIndicator()]
        
        # Метод должен вернуть fallback значение
        width = legend._calculate_required_width()
        self.assertEqual(width, 800)  # Fallback значение
        
        # Проверяем, что ошибка была залогирована
        self.mock_logger.error.assert_called()

    def test_width_calculation_with_empty_indicators(self):
        """Тест вычисления ширины с пустым списком индикаторов."""
        legend = CalendarLegend()
        
        # Устанавливаем пустой список индикаторов
        legend.all_indicators = []
        
        # Метод должен вернуть минимальную ширину
        width = legend._calculate_required_width()
        self.assertEqual(width, 100)  # Минимальная ширина для пустого списка

    def test_priority_indicators_fallback_on_error(self):
        """Тест fallback при ошибке в получении приоритетных индикаторов."""
        legend = CalendarLegend()
        
        # Мокируем ошибку при итерации по индикаторам
        class ErrorIndicator:
            def __init__(self, priority):
                self.priority = priority
                
            @property
            def estimated_width(self):
                raise Exception("Test error")
        
        legend.all_indicators = [ErrorIndicator(1), ErrorIndicator(2)]
        
        # Метод должен вернуть fallback (первые два индикатора)
        result = legend._get_priority_indicators_for_width(400)
        self.assertEqual(len(result), 2)
        
        # Проверяем, что ошибка была залогирована
        self.mock_logger.error.assert_called()

    def test_ui_initialization_fallback_on_error(self):
        """Тест fallback UI при ошибке инициализации."""
        # Мокируем ошибку в методе _should_show_full_legend
        with patch.object(CalendarLegend, '_should_show_full_legend', side_effect=Exception("Test error")):
            legend = CalendarLegend()
            
            # Компонент должен создаться с fallback UI
            self.assertIsNotNone(legend.content)
            
            # Проверяем, что ошибка была залогирована
            self.mock_logger.error.assert_called()

    def test_legend_item_creation_with_invalid_visual_element(self):
        """Тест создания элемента легенды с некорректным визуальным элементом."""
        legend = CalendarLegend()
        
        # Тест с объектом, который вызывает ошибку при создании Row
        # Мокируем ошибку в ft.Row только для первого вызова
        original_row = ft.Row
        call_count = 0
        
        def mock_row_with_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Первый вызов - ошибка
                raise Exception("Test error in Row creation")
            else:  # Последующие вызовы - нормальная работа
                return original_row(*args, **kwargs)
        
        with patch('flet.Row', side_effect=mock_row_with_error):
            # Метод должен создать fallback элемент
            item = legend._build_legend_item(ft.Colors.GREEN, "Test")
            # Должен получиться какой-то объект (не None)
            self.assertIsNotNone(item)
            # Проверяем, что это объект с атрибутами Flet компонента
            self.assertTrue(hasattr(item, 'controls') or hasattr(item, 'value'))
            
            # Проверяем, что ошибка была залогирована
            self.mock_logger.error.assert_called()

    def test_modal_manager_error_handling(self):
        """Тест обработки ошибок в ModalManager."""
        legend = CalendarLegend()
        
        # Мокируем ошибку в modal_manager.open_modal
        with patch.object(legend.modal_manager, 'open_modal', side_effect=Exception("Modal error")):
            mock_event = Mock()
            mock_event.control.page = self.mock_page
            
            # Операция не должна вызывать исключений
            try:
                legend._open_modal_safe(mock_event)
                # Проверяем, что ошибка была залогирована
                self.mock_logger.error.assert_called()
            except Exception as e:
                self.fail(f"_open_modal_safe raised exception on modal manager error: {e}")

    def test_window_resize_stability(self):
        """Тест стабильности при изменении размеров окна."""
        legend = CalendarLegend(calendar_width=800)
        
        # Симулируем множественные изменения размеров
        widths = [300, 600, 1200, 400, 800, 1000, 500]
        
        for width in widths:
            try:
                legend.update_calendar_width(width)
                self.assertEqual(legend.calendar_width, width)
                self.assertIsNotNone(legend.content)
            except Exception as e:
                self.fail(f"Window resize to {width} caused error: {e}")

    def test_rebuild_ui_error_handling(self):
        """Тест обработки ошибок при перестройке UI."""
        legend = CalendarLegend()
        
        # Мокируем ошибку в _build_full_legend
        with patch.object(legend, '_build_full_legend', side_effect=Exception("UI build error")):
            # Операция не должна вызывать исключений
            try:
                legend._rebuild_ui()
                # Проверяем, что ошибка была залогирована
                self.mock_logger.error.assert_called()
            except Exception as e:
                self.fail(f"_rebuild_ui raised exception: {e}")

    def test_fallback_legend_creation(self):
        """Тест создания fallback легенды при критических ошибках."""
        legend = CalendarLegend()
        
        # Тестируем _build_fallback_legend
        fallback_legend = legend._build_fallback_legend()
        
        self.assertIsInstance(fallback_legend, ft.Row)
        self.assertGreater(len(fallback_legend.controls), 0)
        self.assertEqual(fallback_legend.alignment, ft.MainAxisAlignment.CENTER)

    def test_critical_fallback_ui(self):
        """Тест критического fallback UI при множественных ошибках."""
        legend = CalendarLegend()
        
        # Мокируем ошибку даже в _build_fallback_legend
        with patch.object(legend, '_create_details_button', side_effect=Exception("Critical error")):
            # Вызываем _build_fallback_ui напрямую
            legend._build_fallback_ui()
            
            # Компонент должен иметь минимальный контент
            self.assertIsNotNone(legend.content)

    @given(st.one_of(st.none(), st.text(), st.integers(), st.booleans()))
    def test_safe_get_page_robustness_property(self, invalid_input):
        """
        **Feature: calendar-legend-improvement, Property 7: Page object handling**
        **Validates: Requirements 5.2, 5.3**
        
        Property: _safe_get_page должен обрабатывать любые входные данные без исключений.
        """
        legend = CalendarLegend()
        
        try:
            result = legend._safe_get_page(invalid_input)
            # Результат должен быть None или валидным page объектом
            assert result is None or hasattr(result, 'update')
        except Exception as e:
            assert False, f"_safe_get_page failed with input {invalid_input}: {e}"

    @given(st.lists(st.integers(min_value=100, max_value=2000), min_size=1, max_size=10))
    def test_multiple_width_changes_stability_property(self, width_sequence):
        """
        **Feature: calendar-legend-improvement, Property 7: Page object handling**
        **Validates: Requirements 5.5**
        
        Property: Множественные изменения ширины не должны вызывать ошибок.
        """
        legend = CalendarLegend()
        
        for width in width_sequence:
            try:
                legend.update_calendar_width(width)
                assert legend.calendar_width == width
                assert legend.content is not None
            except Exception as e:
                assert False, f"Width change to {width} failed: {e}"

    @given(st.one_of(st.none(), st.text(), st.integers()))
    def test_modal_operations_error_resilience_property(self, invalid_event):
        """
        **Feature: calendar-legend-improvement, Property 7: Page object handling**
        **Validates: Requirements 5.2, 5.3**
        
        Property: Модальные операции должны быть устойчивы к некорректным событиям.
        """
        legend = CalendarLegend()
        
        try:
            legend._open_modal_safe(invalid_event)
            legend._close_dlg(invalid_event)
            # Операции не должны вызывать исключений
        except Exception as e:
            assert False, f"Modal operations failed with event {invalid_event}: {e}"

    def test_indicator_loading_error_recovery(self):
        """Тест восстановления при ошибке загрузки индикаторов."""
        # Мокируем ошибку в _get_all_indicators
        with patch.object(CalendarLegend, '_get_all_indicators', side_effect=Exception("Indicator loading error")):
            # Создание компонента не должно падать
            try:
                legend = CalendarLegend()
                # Компонент должен создаться с пустым списком индикаторов
                self.assertIsNotNone(legend)
            except Exception as e:
                self.fail(f"CalendarLegend creation failed on indicator loading error: {e}")

    def test_visual_grouping_error_handling(self):
        """Тест обработки ошибок при визуальной группировке индикаторов."""
        legend = CalendarLegend()
        
        # Создаём индикатор с проблемным visual_element
        class ErrorIndicator:
            def __init__(self):
                self.priority = 1
                self.type = IndicatorType.INCOME_DOT
                
            @property
            def visual_element(self):
                raise Exception("Visual element error")
        
        error_indicators = [ErrorIndicator()]
        
        # Метод должен вернуть fallback группировку
        result = legend._group_indicators_visually(error_indicators)
        
        # Должен вернуть словарь с группой "all"
        self.assertIsInstance(result, dict)
        self.assertIn("all", result)
        
        # Проверяем, что ошибка была залогирована
        self.mock_logger.error.assert_called()

    def test_separator_creation_stability(self):
        """Тест стабильности создания разделителей между группами."""
        legend = CalendarLegend()
        
        # Тестируем создание разделителя
        separator = legend._create_group_separator()
        
        self.assertIsInstance(separator, ft.Container)
        self.assertEqual(separator.width, 1)
        self.assertEqual(separator.height, 16)

    def test_details_button_creation_stability(self):
        """Тест стабильности создания кнопки 'Подробнее'."""
        legend = CalendarLegend()
        
        # Тестируем создание кнопки
        button = legend._create_details_button()
        
        self.assertIsInstance(button, ft.TextButton)
        self.assertEqual(button.text, "Подробнее...")
        self.assertEqual(button.height, 30)
        self.assertIsNotNone(button.on_click)

    def test_backward_compatibility_error_handling(self):
        """Тест обработки ошибок в методах обратной совместимости."""
        legend = CalendarLegend()
        
        # Тест _open_dlg с некорректным событием
        try:
            legend._open_dlg(None)
            # Не должно вызывать исключений
        except Exception as e:
            self.fail(f"_open_dlg failed with None event: {e}")
        
        # Тест _close_dlg с некорректным событием
        try:
            legend._close_dlg(None)
            # Не должно вызывать исключений
        except Exception as e:
            self.fail(f"_close_dlg failed with None event: {e}")


if __name__ == '__main__':
    unittest.main()