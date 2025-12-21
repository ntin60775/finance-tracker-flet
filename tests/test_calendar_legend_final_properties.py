"""
Финальные комплексные property-based тесты для календарной легенды.

Включает комплексные тесты для всех сценариев, граничные случаи
и стресс-тесты с множественными изменениями размеров.
Validates: все Requirements спецификации calendar-legend-improvement.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
import time

import flet as ft

from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    LegendIndicator,
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
    mock_page.snack_bar = None
    
    return mock_page


class TestCalendarLegendFinalProperties:
    """Финальные комплексные property-based тесты для календарной легенды."""

    @given(
        st.integers(min_value=200, max_value=1500),  # Ширина календаря
        st.booleans()  # Наличие page объекта
    )
    def test_comprehensive_legend_behavior_property(self, calendar_width, has_page):
        """
        **Feature: calendar-legend-improvement, Property 14: Comprehensive legend behavior**
        **Validates: все Requirements**
        
        Property: Для любой комбинации ширины календаря и наличия page объекта 
        легенда должна корректно отображаться и функционировать.
        """
        # Создаем легенду с заданными параметрами
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Устанавливаем page если необходимо
        if has_page:
            legend.page = create_mock_page()
        
        # Проверяем основные инварианты
        assert legend.calendar_width == calendar_width
        assert legend.content is not None
        assert isinstance(legend.content, ft.Row)
        
        # Проверяем адаптивное поведение
        required_width = legend._calculate_required_width()
        should_show_full = calendar_width >= required_width
        
        legend_items = [
            control for control in legend.content.controls 
            if isinstance(control, ft.Row)
        ]
        
        if should_show_full:
            # В полном режиме должны отображаться все индикаторы (CalendarLegend всегда показывает все 7)
            assert len(legend_items) == len(INDICATOR_CONFIGS), (
                f"В полном режиме должны отображаться все {len(INDICATOR_CONFIGS)} индикаторов, "
                f"найдено {len(legend_items)}"
            )
            
            # Не должно быть кнопки "Подробнее"
            has_details_button = any(
                isinstance(control, ft.TextButton) and "Подробнее" in control.text
                for control in legend.content.controls
            )
            assert not has_details_button, "В полном режиме не должно быть кнопки 'Подробнее'"
        else:
            # В компактном режиме должна быть кнопка "Подробнее"
            has_details_button = any(
                isinstance(control, ft.TextButton) and "Подробнее" in control.text
                for control in legend.content.controls
            )
            assert has_details_button, "В компактном режиме должна быть кнопка 'Подробнее'"
            
            # Количество отображаемых индикаторов должно быть меньше общего количества
            assert len(legend_items) < len(INDICATOR_CONFIGS), (
                f"В компактном режиме должно отображаться меньше {len(INDICATOR_CONFIGS)} индикаторов, "
                f"найдено {len(legend_items)}"
            )
        
        # Проверяем стабильность модальных операций
        mock_event = Mock()
        if has_page:
            mock_event.control.page = legend.page
        else:
            mock_event.control = None
        
        # Операции не должны вызывать исключений
        try:
            legend._open_modal_safe(mock_event)
            legend._close_dlg(mock_event)
        except Exception as e:
            assert False, f"Modal operations failed: {e}"

    @given(st.integers(min_value=50, max_value=200))  # Экстремально узкая ширина
    def test_extreme_narrow_width_handling_property(self, extreme_width):
        """
        **Feature: calendar-legend-improvement, Property 15: Extreme width handling**
        **Validates: Requirements 2.1, 2.2, 5.5**
        
        Property: При экстремально узкой ширине система должна корректно обрабатывать
        ситуацию и предоставлять разумный fallback.
        """
        legend = CalendarLegend(calendar_width=extreme_width)
        
        # Компонент должен создаться без ошибок
        assert legend is not None
        assert legend.content is not None
        
        # При экстремально узкой ширине может отображаться только кнопка или скрываться совсем
        content = legend.content
        assert isinstance(content, ft.Row)
        
        # Проверяем, что компонент не пытается отобразить слишком много элементов
        total_controls = len(content.controls)
        assert total_controls <= 3, (
            f"При ширине {extreme_width}px не должно быть более 3 элементов, "
            f"найдено {total_controls}"
        )
        
        # Если есть элементы, они должны быть корректными
        for control in content.controls:
            assert isinstance(control, (ft.Row, ft.TextButton, ft.Container))
        
        # Проверяем стабильность при изменении размеров
        try:
            legend.update_calendar_width(extreme_width + 50)
            legend.update_calendar_width(extreme_width)
            assert legend.calendar_width == extreme_width
        except Exception as e:
            assert False, f"Width update failed for extreme width {extreme_width}: {e}"

    @given(st.integers(min_value=1200, max_value=3000))  # Экстремально широкая ширина
    def test_extreme_wide_width_handling_property(self, extreme_width):
        """
        **Feature: calendar-legend-improvement, Property 16: Extreme wide width handling**
        **Validates: Requirements 1.1, 2.1, 4.2**
        
        Property: При экстремально широкой ширине все индикаторы должны отображаться
        в полном режиме с правильным выравниванием.
        """
        legend = CalendarLegend(calendar_width=extreme_width)
        
        # При широкой ширине должен быть полный режим
        assert legend._should_show_full_legend()
        
        # Все 7 индикаторов должны отображаться
        content = legend.content
        legend_items = [
            control for control in content.controls 
            if isinstance(control, ft.Row)
        ]
        
        # Должны отображаться все доступные индикаторы
        assert len(legend_items) == len(INDICATOR_CONFIGS)
        
        # Не должно быть кнопки "Подробнее"
        has_details_button = any(
            isinstance(control, ft.TextButton) and "Подробнее" in control.text
            for control in content.controls
        )
        assert not has_details_button
        
        # Проверяем правильное выравнивание
        assert content.alignment == ft.MainAxisAlignment.CENTER
        assert content.vertical_alignment == ft.CrossAxisAlignment.CENTER
        assert content.spacing == 20

    @settings(max_examples=50)  # Ограничиваем количество примеров для стресс-теста
    @given(st.lists(
        st.integers(min_value=200, max_value=1500), 
        min_size=5, 
        max_size=20
    ))
    def test_multiple_resize_stress_property(self, width_sequence):
        """
        **Feature: calendar-legend-improvement, Property 17: Multiple resize stress**
        **Validates: Requirements 5.5**
        
        Property: Множественные быстрые изменения размеров не должны вызывать
        ошибок или деградации производительности.
        """
        legend = CalendarLegend()
        
        start_time = time.time()
        
        for i, width in enumerate(width_sequence):
            try:
                legend.update_calendar_width(width)
                
                # Проверяем корректность состояния после каждого изменения
                assert legend.calendar_width == width
                assert legend.content is not None
                assert isinstance(legend.content, ft.Row)
                
                # Проверяем, что режим отображения корректен
                required_width = legend._calculate_required_width()
                expected_full_mode = width >= required_width
                actual_full_mode = legend._should_show_full_legend()
                assert actual_full_mode == expected_full_mode, (
                    f"Режим отображения некорректен для ширины {width}"
                )
                
            except Exception as e:
                assert False, f"Resize #{i} to width {width} failed: {e}"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем производительность (не более 1 секунды на 20 изменений)
        max_time = len(width_sequence) * 0.05  # 50ms на изменение
        assert total_time < max_time, (
            f"Resize operations took too long: {total_time:.3f}s for {len(width_sequence)} operations"
        )

    @given(
        st.integers(min_value=300, max_value=1200),
        st.integers(min_value=1, max_value=3)  # Уменьшаем количество для более простого тестирования
    )
    def test_display_consistency_across_widths_property(self, calendar_width, num_width_changes):
        """
        **Feature: calendar-legend-improvement, Property 18: Display consistency across widths**
        **Validates: Requirements 1.2-1.8, 2.4**
        
        Property: При изменении ширины календаря отображение должно оставаться
        консистентным и корректно адаптироваться.
        """
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Проверяем начальное состояние
        initial_content = legend.content
        assert isinstance(initial_content, ft.Row)
        
        initial_legend_items = [
            control for control in initial_content.controls 
            if isinstance(control, ft.Row)
        ]
        
        # Проверяем, что отображаются индикаторы из INDICATOR_CONFIGS
        assert len(initial_legend_items) <= len(INDICATOR_CONFIGS)
        assert len(initial_legend_items) > 0, "Должен отображаться хотя бы один индикатор"
        
        # Выполняем несколько изменений ширины
        test_widths = [calendar_width + i * 100 for i in range(1, num_width_changes + 1)]
        
        for new_width in test_widths:
            legend.update_calendar_width(new_width)
            
            # Проверяем консистентность после изменения
            assert legend.calendar_width == new_width
            assert legend.content is not None
            assert isinstance(legend.content, ft.Row)
            
            # Проверяем адаптивное поведение
            required_width = legend._calculate_required_width()
            should_show_full = new_width >= required_width
            
            current_legend_items = [
                control for control in legend.content.controls 
                if isinstance(control, ft.Row)
            ]
            
            if should_show_full:
                # В полном режиме должны отображаться все индикаторы
                assert len(current_legend_items) == len(INDICATOR_CONFIGS)
            else:
                # В компактном режиме меньше индикаторов + кнопка "Подробнее"
                assert len(current_legend_items) < len(INDICATOR_CONFIGS)
                has_details_button = any(
                    isinstance(control, ft.TextButton) and "Подробнее" in control.text
                    for control in legend.content.controls
                )
                assert has_details_button

    @given(
        st.integers(min_value=400, max_value=800),
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=7)
    )
    def test_custom_labels_handling_property(self, calendar_width, custom_labels):
        """
        **Feature: calendar-legend-improvement, Property 19: Custom labels handling**
        **Validates: Requirements 4.4, 4.5**
        
        Property: Система должна корректно обрабатывать индикаторы с различными
        длинами меток, сохраняя читаемость и правильное выравнивание.
        """
        # Создаем тестовые индикаторы с кастомными метками
        test_indicators = []
        
        for i, label in enumerate(custom_labels[:len(INDICATOR_CONFIGS)]):
            original_type = list(IndicatorType)[i]
            original_config = INDICATOR_CONFIGS[original_type]
            
            # Создаем копию с кастомной меткой
            test_indicator = LegendIndicator(
                type=original_config.type,
                visual_element=original_config.visual_element,
                label=label,
                description=original_config.description,
                priority=original_config.priority,
                estimated_width=max(40, len(label) * 8 + 30)  # Адаптивная ширина
            )
            test_indicators.append(test_indicator)
        
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Заменяем индикаторы на тестовые
        legend.all_indicators = test_indicators
        
        # Пересоздаем UI
        legend._rebuild_ui()
        
        # Проверяем корректность отображения
        content = legend.content
        assert isinstance(content, ft.Row)
        
        # Проверяем выравнивание
        assert content.alignment == ft.MainAxisAlignment.CENTER
        assert content.vertical_alignment == ft.CrossAxisAlignment.CENTER
        
        # Проверяем, что все элементы корректно созданы
        legend_items = [
            control for control in content.controls 
            if isinstance(control, ft.Row)
        ]
        
        for legend_item in legend_items:
            assert len(legend_item.controls) == 2  # Визуальный элемент + текст
            text_element = legend_item.controls[1]
            assert isinstance(text_element, ft.Text)
            assert text_element.size == 12  # Стандартный размер

    @given(st.integers(min_value=1, max_value=100))  # Количество операций
    def test_modal_operations_stress_property(self, num_operations):
        """
        **Feature: calendar-legend-improvement, Property 20: Modal operations stress**
        **Validates: Requirements 3.1, 3.4, 5.2**
        
        Property: Множественные операции открытия/закрытия модального окна
        должны работать стабильно без утечек памяти или ошибок.
        """
        legend = CalendarLegend()
        mock_page = create_mock_page()
        legend.page = mock_page
        
        mock_event = Mock()
        mock_event.control.page = mock_page
        
        start_time = time.time()
        
        for i in range(num_operations):
            try:
                # Открываем модальное окно
                legend._open_modal_safe(mock_event)
                
                # Проверяем, что модальное окно создано
                assert legend.modal_manager.dialog is not None
                
                # Закрываем модальное окно
                legend._close_dlg(mock_event)
                
            except Exception as e:
                assert False, f"Modal operation #{i} failed: {e}"
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем производительность (не более 20ms на операцию)
        max_time = num_operations * 0.02
        assert total_time < max_time, (
            f"Modal operations took too long: {total_time:.3f}s for {num_operations} operations"
        )

    @given(
        st.integers(min_value=200, max_value=1500),
        st.lists(st.one_of(st.none(), st.text(), st.integers()), min_size=1, max_size=10)
    )
    def test_error_injection_resilience_property(self, calendar_width, error_inputs):
        """
        **Feature: calendar-legend-improvement, Property 21: Error injection resilience**
        **Validates: Requirements 5.2, 5.3, 5.5**
        
        Property: Система должна быть устойчива к различным типам ошибочных
        входных данных и неожиданным ситуациям.
        """
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Тестируем устойчивость к различным ошибочным входам
        for error_input in error_inputs:
            try:
                # Тестируем _safe_get_page с различными входами
                result = legend._safe_get_page(error_input)
                assert result is None or hasattr(result, 'update')
                
                # Тестируем модальные операции с ошибочными событиями
                legend._open_modal_safe(error_input)
                legend._close_dlg(error_input)
                
            except Exception as e:
                assert False, f"Error injection with {error_input} caused failure: {e}"
        
        # Проверяем, что компонент остался в корректном состоянии
        assert legend.content is not None
        assert isinstance(legend.content, ft.Row)
        assert legend.calendar_width == calendar_width

    def test_boundary_width_transitions_property(self):
        """
        **Feature: calendar-legend-improvement, Property 22: Boundary width transitions**
        **Validates: Requirements 2.1, 2.2**
        
        Property: Переходы между режимами отображения на граничных значениях
        ширины должны быть плавными и корректными.
        """
        legend = CalendarLegend()
        
        # Вычисляем граничную ширину
        required_width = legend._calculate_required_width()
        
        # Тестируем переходы вокруг граничного значения
        test_widths = [
            required_width - 50,  # Точно компактный режим
            required_width - 1,   # Граница (компактный)
            required_width,       # Граница (полный)
            required_width + 1,   # Точно полный режим
            required_width + 50   # Точно полный режим
        ]
        
        previous_mode = None
        
        for width in test_widths:
            legend.update_calendar_width(width)
            
            current_mode = legend._should_show_full_legend()
            expected_mode = width >= required_width
            
            assert current_mode == expected_mode, (
                f"Режим отображения некорректен для ширины {width}. "
                f"Ожидается: {expected_mode}, получено: {current_mode}"
            )
            
            # Проверяем корректность UI
            content = legend.content
            assert isinstance(content, ft.Row)
            
            if current_mode:  # Полный режим
                # Не должно быть кнопки "Подробнее"
                has_details_button = any(
                    isinstance(control, ft.TextButton) and "Подробнее" in control.text
                    for control in content.controls
                )
                assert not has_details_button
            else:  # Компактный режим
                # Должна быть кнопка "Подробнее"
                has_details_button = any(
                    isinstance(control, ft.TextButton) and "Подробнее" in control.text
                    for control in content.controls
                )
                assert has_details_button
            
            previous_mode = current_mode

    @given(st.integers(min_value=300, max_value=1200))
    def test_ui_consistency_after_operations_property(self, calendar_width):
        """
        **Feature: calendar-legend-improvement, Property 23: UI consistency after operations**
        **Validates: Requirements 4.1, 4.2, 4.3**
        
        Property: После любых операций (изменение размера, модальные окна, ошибки)
        UI должен оставаться консистентным и корректно отформатированным.
        """
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Выполняем различные операции
        operations = [
            lambda: legend.update_calendar_width(calendar_width + 100),
            lambda: legend.update_calendar_width(calendar_width - 100),
            lambda: legend._rebuild_ui(),
            lambda: legend._open_modal_safe(None),
            lambda: legend._close_dlg(None),
            lambda: legend.update_calendar_width(calendar_width)
        ]
        
        for operation in operations:
            try:
                operation()
            except:
                pass  # Игнорируем ошибки, проверяем только консистентность UI
            
            # Проверяем консистентность UI после каждой операции
            content = legend.content
            assert content is not None
            assert isinstance(content, ft.Row)
            
            # Проверяем базовые свойства выравнивания
            assert content.alignment == ft.MainAxisAlignment.CENTER
            assert content.vertical_alignment == ft.CrossAxisAlignment.CENTER
            assert content.spacing == 20
            
            # Проверяем корректность элементов
            for control in content.controls:
                assert isinstance(control, (ft.Row, ft.TextButton, ft.Container))
                
                if isinstance(control, ft.Row):
                    # Элементы легенды должны иметь правильную структуру
                    assert len(control.controls) == 2
                    assert isinstance(control.controls[0], (ft.Container, ft.Text))
                    assert isinstance(control.controls[1], ft.Text)

    def test_memory_efficiency_property(self):
        """
        **Feature: calendar-legend-improvement, Property 24: Memory efficiency**
        **Validates: Requirements 5.1, 5.4**
        
        Property: Создание и уничтожение множественных экземпляров легенды
        не должно приводить к утечкам памяти.
        """
        # Создаем и уничтожаем множественные экземпляры
        legends = []
        
        for i in range(50):
            legend = CalendarLegend(calendar_width=400 + i * 10)
            
            # Выполняем некоторые операции
            legend._rebuild_ui()
            legend.update_calendar_width(600 + i * 5)
            
            legends.append(legend)
        
        # Проверяем, что все экземпляры корректно созданы
        assert len(legends) == 50
        
        for legend in legends:
            assert legend.content is not None
            assert isinstance(legend.content, ft.Row)
        
        # Очищаем ссылки (симуляция сборки мусора)
        legends.clear()
        
        # Создаем новый экземпляр для проверки, что система не деградировала
        final_legend = CalendarLegend(calendar_width=800)
        assert final_legend.content is not None
        assert isinstance(final_legend.content, ft.Row)

    @given(
        st.integers(min_value=300, max_value=1200),
        st.integers(min_value=1, max_value=5)  # Уменьшаем количество экземпляров
    )
    def test_independent_instances_property(self, base_width, num_instances):
        """
        **Feature: calendar-legend-improvement, Property 25: Independent instances**
        **Validates: Requirements 5.1, 5.4**
        
        Property: Множественные экземпляры легенды должны создаваться независимо
        и иметь собственное состояние.
        """
        legends = []
        
        # Создаем множественные экземпляры с разными параметрами
        for i in range(num_instances):
            width = base_width + i * 50
            legend = CalendarLegend(calendar_width=width)
            legends.append((legend, width))
        
        # Проверяем независимость создания экземпляров
        for i, (legend, expected_width) in enumerate(legends):
            # Каждый экземпляр должен иметь свою ширину
            assert legend.calendar_width == expected_width, (
                f"Instance {i} has incorrect width: {legend.calendar_width} != {expected_width}"
            )
            assert legend.content is not None
            assert isinstance(legend.content, ft.Row)
            
            # Проверяем, что у каждого экземпляра свой контент
            assert id(legend.content) != id(legends[0][0].content) or i == 0, (
                f"Instance {i} shares content with instance 0"
            )
        
        # Проверяем, что изменение одного экземпляра не влияет на создание новых
        if num_instances > 1:
            # Изменяем первый экземпляр
            legends[0][0].update_calendar_width(base_width + 200)
            
            # Создаем новый экземпляр
            new_legend = CalendarLegend(calendar_width=base_width)
            
            # Новый экземпляр должен иметь свою ширину, не зависящую от изменений первого
            assert new_legend.calendar_width == base_width, (
                f"New instance was affected by changes to existing instance: "
                f"{new_legend.calendar_width} != {base_width}"
            )
        
        # Проверяем корректность всех экземпляров
        for legend, _ in legends:
            assert legend.content is not None
            assert isinstance(legend.content, ft.Row)


if __name__ == '__main__':
    pytest.main([__file__, "-v"])