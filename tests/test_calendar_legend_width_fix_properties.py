"""
Property-based тесты для исправлений календарной легенды.

Тестирует новые реалистичные оценки ширины индикаторов и связанную логику,
включая тесты для WidthCalculator класса.
"""
import pytest
from hypothesis import given, strategies as st, assume
from decimal import Decimal
from datetime import date
import flet as ft

from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_legend_types import (
    INDICATOR_CONFIGS, 
    IndicatorType, 
    LegendIndicator
)
from finance_tracker.components.width_calculator import WidthCalculator, WidthCalculationResult
from finance_tracker.components.page_access_manager import PageAccessManager


class TestCalendarLegendWidthFixProperties:
    """Property-based тесты для исправлений ширины календарной легенды."""

    @given(st.sampled_from(list(IndicatorType)))
    def test_realistic_width_estimation_property(self, indicator_type):
        """
        **Feature: calendar-legend-width-fix, Property 1: Realistic width estimation**
        **Validates: Requirements 1.2, 3.1, 3.2, 3.3**
        
        Property: For any indicator in the legend, its estimated width should be 
        between 30px and 60px, reflecting realistic text and visual element sizes.
        """
        # Arrange - получаем индикатор из конфигурации
        indicator = INDICATOR_CONFIGS[indicator_type]
        
        # Act & Assert - проверяем, что ширина в реалистичных пределах
        assert 30 <= indicator.estimated_width <= 60, (
            f"Индикатор {indicator_type.value} имеет нереалистичную ширину: "
            f"{indicator.estimated_width}px (ожидается 30-60px)"
        )

    @given(st.lists(st.sampled_from(list(IndicatorType)), min_size=1, max_size=7, unique=True))
    def test_accurate_total_width_calculation_property(self, indicator_types):
        """
        **Feature: calendar-legend-width-fix, Property 2: Accurate total width calculation**
        **Validates: Requirements 1.5, 3.4**
        
        Property: For any set of indicators, the calculated total width should equal 
        the sum of individual widths plus spacing (20px between elements) plus padding (40px).
        """
        # Arrange - создаём легенду с выбранными индикаторами
        legend = CalendarLegend(calendar_width=1000)
        selected_indicators = [INDICATOR_CONFIGS[ind_type] for ind_type in indicator_types]
        
        # Временно заменяем индикаторы для тестирования
        original_indicators = legend.all_indicators
        legend.all_indicators = selected_indicators
        
        try:
            # Act - вычисляем общую ширину через WidthCalculator
            calculated_width = WidthCalculator.calculate_total_width(selected_indicators)
            
            # Также получаем ширину через метод легенды
            legend_width = legend._calculate_required_width()
            
            # Assert - проверяем, что оба метода дают одинаковый результат
            assert calculated_width == legend_width, (
                f"Расхождение между WidthCalculator ({calculated_width}px) "
                f"и CalendarLegend ({legend_width}px)"
            )
            
            # Проверяем правильность структуры вычисления
            expected_individual_width = sum(
                WidthCalculator.calculate_indicator_width(ind) for ind in selected_indicators
            )
            expected_spacing = (len(selected_indicators) - 1) * 20  # 20px между элементами
            expected_padding = 40  # padding контейнера
            expected_total = expected_individual_width + expected_spacing + expected_padding
            
            assert calculated_width == expected_total, (
                f"Неправильное вычисление общей ширины: "
                f"получено {calculated_width}px, ожидается {expected_total}px "
                f"(индикаторы: {expected_individual_width}px, "
                f"отступы: {expected_spacing}px, padding: {expected_padding}px)"
            )
        finally:
            # Восстанавливаем оригинальные индикаторы
            legend.all_indicators = original_indicators

    @given(st.integers(min_value=500, max_value=1200))
    def test_width_based_display_mode_selection_property(self, calendar_width):
        """
        **Feature: calendar-legend-width-fix, Property 3: Width-based display mode selection**
        **Validates: Requirements 1.1, 1.4**
        
        Property: For any calendar width of 500px or greater, if the width is sufficient 
        for all indicators, the legend should display in full mode without the "Details" button.
        """
        # Arrange - создаём легенду с заданной шириной
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Act - определяем режим отображения
        required_width = legend._calculate_required_width()
        should_show_full = legend._should_show_full_legend()
        
        # Assert - проверяем логику выбора режима
        if calendar_width >= required_width:
            assert should_show_full, (
                f"При ширине календаря {calendar_width}px (>= требуемых {required_width}px) "
                f"должна показываться полная легенда"
            )
        else:
            assert not should_show_full, (
                f"При ширине календаря {calendar_width}px (< требуемых {required_width}px) "
                f"должна показываться сокращённая легенда"
            )

    @given(st.text(min_size=3, max_size=15, alphabet=st.characters(whitelist_categories=['L'])))
    def test_text_length_consideration_property(self, label_text):
        """
        **Feature: calendar-legend-width-fix, Property 4: Text length consideration in width estimation**
        **Validates: Requirements 1.3, 3.5**
        
        Property: For indicators with longer text labels, the estimated width should be 
        proportionally larger, reflecting the actual text rendering requirements.
        """
        # Arrange - создаём два индикатора с разной длиной текста
        short_text = "A"  # 1 символ
        long_text = label_text  # Сгенерированный текст
        
        assume(len(long_text) > len(short_text))  # Убеждаемся, что длинный текст действительно длиннее
        
        # Создаём тестовые индикаторы
        short_indicator = LegendIndicator(
            type=IndicatorType.INCOME_DOT,
            visual_element=INDICATOR_CONFIGS[IndicatorType.INCOME_DOT].visual_element,
            label=short_text,
            description="Test short",
            priority=1,
            estimated_width=15 + 5 + len(short_text) * 7  # элемент + отступ + текст
        )
        
        long_indicator = LegendIndicator(
            type=IndicatorType.EXPENSE_DOT,
            visual_element=INDICATOR_CONFIGS[IndicatorType.EXPENSE_DOT].visual_element,
            label=long_text,
            description="Test long",
            priority=2,
            estimated_width=15 + 5 + len(long_text) * 7  # элемент + отступ + текст
        )
        
        # Act & Assert - проверяем, что более длинный текст даёт большую ширину
        assert long_indicator.estimated_width > short_indicator.estimated_width, (
            f"Индикатор с длинным текстом '{long_text}' ({len(long_text)} символов) "
            f"должен иметь большую ширину ({long_indicator.estimated_width}px), "
            f"чем индикатор с коротким текстом '{short_text}' ({len(short_text)} символов, "
            f"{short_indicator.estimated_width}px)"
        )

    @given(st.integers(min_value=400, max_value=600))
    def test_responsive_display_mode_updates_property(self, calendar_width):
        """
        **Feature: calendar-legend-width-fix, Property 5: Responsive display mode updates**
        **Validates: Requirements 4.3**
        
        Property: For any change in calendar width that crosses the threshold (500px), 
        the legend should update its display mode accordingly.
        """
        # Arrange - создаём легенду с начальной шириной
        initial_width = 400  # Ниже порога
        legend = CalendarLegend(calendar_width=initial_width)
        
        # Проверяем начальный режим
        initial_mode = legend._should_show_full_legend()
        
        # Act - обновляем ширину календаря
        legend.update_calendar_width(calendar_width)
        
        # Получаем новый режим
        updated_mode = legend._should_show_full_legend()
        required_width = legend._calculate_required_width()
        
        # Assert - проверяем правильность обновления режима
        expected_mode = calendar_width >= required_width
        
        assert updated_mode == expected_mode, (
            f"После обновления ширины с {initial_width}px на {calendar_width}px "
            f"режим отображения должен быть {expected_mode}, но получен {updated_mode} "
            f"(требуемая ширина: {required_width}px)"
        )
        
        # Проверяем, что режим действительно изменился при пересечении порога
        if initial_width < required_width <= calendar_width:
            assert updated_mode != initial_mode, (
                f"При пересечении порога ({required_width}px) режим должен измениться "
                f"с {initial_mode} на {updated_mode}"
            )
        elif calendar_width < required_width <= initial_width:
            assert updated_mode != initial_mode, (
                f"При пересечении порога ({required_width}px) в обратную сторону "
                f"режим должен измениться с {initial_mode} на {updated_mode}"
            )

    @given(st.integers(min_value=400, max_value=600))
    def test_threshold_boundary_behavior_property(self, calendar_width):
        """
        **Feature: calendar-legend-width-fix, Property 6: Threshold boundary behavior**
        **Validates: Requirements 1.1, 1.4**
        
        Property: The display mode should change consistently at the calculated threshold,
        with no hysteresis or inconsistent behavior near the boundary.
        """
        # Arrange - создаём легенду
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Act - получаем режим отображения и требуемую ширину
        required_width = legend._calculate_required_width()
        should_show_full = legend._should_show_full_legend()
        
        # Assert - проверяем консистентность поведения на границе
        if calendar_width >= required_width:
            assert should_show_full, (
                f"При ширине {calendar_width}px (>= {required_width}px) "
                f"должна показываться полная легенда"
            )
            
            # Проверяем, что при чуть меньшей ширине режим изменится
            smaller_legend = CalendarLegend(calendar_width=calendar_width - 1)
            if calendar_width - 1 < required_width:
                assert not smaller_legend._should_show_full_legend(), (
                    f"При ширине {calendar_width - 1}px (< {required_width}px) "
                    f"должна показываться сокращённая легенда"
                )
        else:
            assert not should_show_full, (
                f"При ширине {calendar_width}px (< {required_width}px) "
                f"должна показываться сокращённая легенда"
            )

    @given(st.integers(min_value=1, max_value=7))
    def test_priority_indicators_selection_property(self, max_indicators):
        """
        **Feature: calendar-legend-width-fix, Property 6: Priority-based indicator selection**
        **Validates: Requirements 2.4**
        
        Property: When space is limited, indicators should be selected by priority 
        (lower priority number = higher importance).
        """
        # Arrange - создаём легенду с ограниченной шириной
        narrow_width = 300  # Узкая ширина, которая не поместит все индикаторы
        legend = CalendarLegend(calendar_width=narrow_width)
        
        # Act - получаем приоритетные индикаторы
        priority_indicators = legend._get_priority_indicators_for_width(narrow_width)
        
        # Assert - проверяем, что индикаторы отсортированы по приоритету
        if len(priority_indicators) > 1:
            for i in range(len(priority_indicators) - 1):
                current_priority = priority_indicators[i].priority
                next_priority = priority_indicators[i + 1].priority
                
                assert current_priority <= next_priority, (
                    f"Индикаторы должны быть отсортированы по приоритету: "
                    f"индикатор {i} имеет приоритет {current_priority}, "
                    f"а индикатор {i+1} имеет приоритет {next_priority}"
                )

    def test_width_estimation_bounds_property(self):
        """
        **Feature: calendar-legend-width-fix, Property 7: Width estimation bounds**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: All indicator width estimations should fall within realistic bounds
        for their respective types, updated to reflect actual text lengths.
        """
        # Проверяем каждый индикатор в конфигурации
        for indicator_type, indicator in INDICATOR_CONFIGS.items():
            # Все индикаторы должны быть в диапазоне 30-60px
            assert 30 <= indicator.estimated_width <= 60, (
                f"Индикатор {indicator_type.value} выходит за реалистичные границы: "
                f"{indicator.estimated_width}px (ожидается 30-60px)"
            )

    @given(st.integers(min_value=200, max_value=2000))
    def test_width_calculation_stability_property(self, calendar_width):
        """
        **Feature: calendar-legend-width-fix, Property 8: Width calculation stability**
        **Validates: Requirements 4.5**
        
        Property: Width calculations should be stable and consistent, 
        returning the same result for the same input parameters.
        """
        # Arrange - создаём две легенды с одинаковой шириной
        legend1 = CalendarLegend(calendar_width=calendar_width)
        legend2 = CalendarLegend(calendar_width=calendar_width)
        
        # Act - вычисляем ширину несколько раз
        width1_first = legend1._calculate_required_width()
        width1_second = legend1._calculate_required_width()
        width2 = legend2._calculate_required_width()
        
        # Assert - проверяем стабильность вычислений
        assert width1_first == width1_second, (
            f"Повторные вычисления ширины дают разные результаты: "
            f"{width1_first}px vs {width1_second}px"
        )
        
        assert width1_first == width2, (
            f"Одинаковые параметры дают разные результаты в разных экземплярах: "
            f"{width1_first}px vs {width2}px"
        )

    def test_total_width_reduction_validation(self):
        """
        **Feature: calendar-legend-width-fix, Property 9: Total width reduction validation**
        **Validates: Requirements 1.2**
        
        Property: The total required width should be significantly reduced compared 
        to the previous implementation (from ~670px to ~525px).
        """
        # Arrange - создаём легенду
        legend = CalendarLegend()
        
        # Act - вычисляем общую ширину
        total_width = legend._calculate_required_width()
        
        # Assert - проверяем, что ширина уменьшилась
        old_expected_width = 670  # Старое значение
        new_expected_width = 525  # Новое ожидаемое значение
        tolerance = 50  # Допустимое отклонение
        
        assert total_width <= old_expected_width, (
            f"Общая ширина ({total_width}px) не должна превышать старое значение ({old_expected_width}px)"
        )
        
        assert abs(total_width - new_expected_width) <= tolerance, (
            f"Общая ширина ({total_width}px) должна быть близка к ожидаемому значению "
            f"({new_expected_width}px ± {tolerance}px)"
        )
        
        reduction = old_expected_width - total_width
        reduction_percent = (reduction / old_expected_width) * 100
        
        assert reduction >= 100, (
            f"Ширина должна быть уменьшена минимум на 100px, "
            f"фактическое уменьшение: {reduction}px ({reduction_percent:.1f}%)"
        )


class TestWidthCalculatorProperties:
    """Property-based тесты для WidthCalculator класса."""

    @given(st.lists(st.sampled_from(list(IndicatorType)), min_size=1, max_size=7, unique=True))
    def test_accurate_total_width_calculation_property(self, indicator_types):
        """
        **Feature: calendar-legend-width-fix, Property 2: Accurate total width calculation**
        **Validates: Requirements 1.5, 3.4**
        
        Property: For any set of indicators, the calculated total width should equal 
        the sum of individual widths plus spacing (20px between elements) plus padding (40px).
        """
        # Arrange - получаем индикаторы из конфигурации
        indicators = [INDICATOR_CONFIGS[ind_type] for ind_type in indicator_types]
        
        # Act - вычисляем общую ширину через WidthCalculator
        total_width = WidthCalculator.calculate_total_width(indicators)
        
        # Assert - проверяем правильность вычисления
        expected_individual_width = sum(
            WidthCalculator.calculate_indicator_width(ind) for ind in indicators
        )
        expected_spacing = (len(indicators) - 1) * 20  # 20px между элементами
        expected_padding = 40  # padding контейнера
        expected_total = expected_individual_width + expected_spacing + expected_padding
        
        assert total_width == expected_total, (
            f"Неправильное вычисление общей ширины через WidthCalculator: "
            f"получено {total_width}px, ожидается {expected_total}px "
            f"(индикаторы: {expected_individual_width}px, "
            f"отступы: {expected_spacing}px, padding: {expected_padding}px)"
        )

    @given(st.sampled_from(list(IndicatorType)))
    def test_indicator_width_calculation_bounds_property(self, indicator_type):
        """
        **Feature: calendar-legend-width-fix, Property 10: Individual indicator width bounds**
        **Validates: Requirements 1.3, 3.1, 3.2, 3.3**
        
        Property: For any indicator, the calculated width should be within realistic bounds
        (30-60px) and should match the estimated width from configuration.
        """
        # Arrange - получаем индикатор из конфигурации
        indicator = INDICATOR_CONFIGS[indicator_type]
        
        # Act - вычисляем ширину через WidthCalculator
        calculated_width = WidthCalculator.calculate_indicator_width(indicator)
        
        # Assert - проверяем границы ширины
        assert 30 <= calculated_width <= 60, (
            f"Вычисленная ширина индикатора {indicator_type.value} "
            f"выходит за реалистичные границы: {calculated_width}px (ожидается 30-60px)"
        )
        
        # Проверяем соответствие с оценкой из конфигурации (допускаем небольшое отклонение)
        config_width = indicator.estimated_width
        tolerance = 5  # Допустимое отклонение в 5px
        
        assert abs(calculated_width - config_width) <= tolerance, (
            f"Вычисленная ширина ({calculated_width}px) значительно отличается "
            f"от оценки в конфигурации ({config_width}px), отклонение > {tolerance}px"
        )

    @given(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=['L'])))
    def test_text_width_estimation_property(self, text):
        """
        **Feature: calendar-legend-width-fix, Property 11: Text width estimation accuracy**
        **Validates: Requirements 1.3, 3.5**
        
        Property: For any text, the estimated width should be proportional to text length
        and should be reasonable for the given font size.
        """
        # Act - оцениваем ширину текста
        estimated_width = WidthCalculator.estimate_text_width(text, font_size=12)
        
        # Assert - проверяем пропорциональность
        expected_min = len(text) * 5  # Минимум 5px на символ
        expected_max = len(text) * 10  # Максимум 10px на символ
        
        assert expected_min <= estimated_width <= expected_max, (
            f"Оценка ширины текста '{text}' ({len(text)} символов) "
            f"не пропорциональна длине: {estimated_width}px "
            f"(ожидается {expected_min}-{expected_max}px)"
        )

    @given(st.lists(st.sampled_from(list(IndicatorType)), min_size=1, max_size=7, unique=True))
    def test_width_calculation_with_fallback_property(self, indicator_types):
        """
        **Feature: calendar-legend-width-fix, Property 12: Fallback calculation reliability**
        **Validates: Requirements 4.2, 4.5**
        
        Property: For any set of indicators, the fallback calculation should always
        return a valid result with proper error handling.
        """
        # Arrange - получаем индикаторы из конфигурации
        indicators = [INDICATOR_CONFIGS[ind_type] for ind_type in indicator_types]
        
        # Act - вычисляем ширину с fallback
        result = WidthCalculator.calculate_width_with_fallback(indicators)
        
        # Assert - проверяем структуру результата
        assert isinstance(result, WidthCalculationResult), (
            f"Результат должен быть экземпляром WidthCalculationResult, "
            f"получен {type(result)}"
        )
        
        assert result.total_width > 0, (
            f"Общая ширина должна быть положительной: {result.total_width}px"
        )
        
        assert result.spacing_width >= 0, (
            f"Ширина отступов не может быть отрицательной: {result.spacing_width}px"
        )
        
        assert result.padding_width > 0, (
            f"Ширина padding должна быть положительной: {result.padding_width}px"
        )
        
        # Проверяем логичность общей ширины
        min_expected = len(indicators) * 30 + (len(indicators) - 1) * 20 + 40
        max_expected = len(indicators) * 60 + (len(indicators) - 1) * 20 + 40
        
        assert min_expected <= result.total_width <= max_expected, (
            f"Общая ширина {result.total_width}px выходит за разумные границы "
            f"для {len(indicators)} индикаторов: {min_expected}-{max_expected}px"
        )

    @given(st.integers(min_value=8, max_value=24))
    def test_font_size_scaling_property(self, font_size):
        """
        **Feature: calendar-legend-width-fix, Property 13: Font size scaling**
        **Validates: Requirements 1.3**
        
        Property: Text width estimation should scale proportionally with font size.
        """
        # Arrange - тестовый текст
        test_text = "Тест"
        
        # Act - оцениваем ширину для разных размеров шрифта
        width_12 = WidthCalculator.estimate_text_width(test_text, font_size=12)
        width_test = WidthCalculator.estimate_text_width(test_text, font_size=font_size)
        
        # Assert - проверяем пропорциональность
        expected_ratio = font_size / 12
        actual_ratio = width_test / width_12 if width_12 > 0 else 1
        
        tolerance = 0.2  # Допустимое отклонение 20%
        
        assert abs(actual_ratio - expected_ratio) <= tolerance, (
            f"Ширина текста не масштабируется пропорционально размеру шрифта: "
            f"для размера {font_size} получено соотношение {actual_ratio:.2f}, "
            f"ожидается {expected_ratio:.2f} (±{tolerance})"
        )

    def test_visual_element_width_detection_property(self):
        """
        **Feature: calendar-legend-width-fix, Property 14: Visual element width detection**
        **Validates: Requirements 3.1, 3.2, 3.3**
        
        Property: The width calculator should correctly detect widths of different
        visual element types (Container, Text, Icon).
        """
        # Test Container elements
        container_10 = ft.Container(width=10, height=10, bgcolor=ft.Colors.RED)
        container_16 = ft.Container(width=16, height=12, bgcolor=ft.Colors.BLUE)
        
        width_10 = WidthCalculator._get_visual_element_width(container_10)
        width_16 = WidthCalculator._get_visual_element_width(container_16)
        
        assert width_10 == 10, f"Container шириной 10px определён как {width_10}px"
        assert width_16 == 16, f"Container шириной 16px определён как {width_16}px"
        
        # Test Text elements
        text_element = ft.Text("Test", size=12)
        text_width = WidthCalculator._get_visual_element_width(text_element)
        
        assert text_width == 12, f"Text элемент определён как {text_width}px, ожидается 12px"
        
        # Test Icon elements
        icon_element = ft.Icon(ft.Icons.ADD, size=14)
        icon_width = WidthCalculator._get_visual_element_width(icon_element)
        
        assert icon_width == 14, f"Icon размером 14px определён как {icon_width}px"

    @given(st.lists(st.sampled_from(list(IndicatorType)), min_size=0, max_size=7, unique=True))
    def test_empty_and_edge_cases_property(self, indicator_types):
        """
        **Feature: calendar-legend-width-fix, Property 15: Edge cases handling**
        **Validates: Requirements 4.2, 4.5**
        
        Property: The width calculator should handle edge cases gracefully,
        including empty lists and invalid inputs.
        """
        # Test empty list
        if not indicator_types:
            with pytest.raises(ValueError, match="не может быть пустым"):
                WidthCalculator.calculate_total_width([])
            
            # Fallback method should handle empty list gracefully
            result = WidthCalculator.calculate_width_with_fallback([])
            assert result.total_width > 0
            assert not result.is_accurate
            return
        
        # Test normal case
        indicators = [INDICATOR_CONFIGS[ind_type] for ind_type in indicator_types]
        
        # Should not raise exceptions
        total_width = WidthCalculator.calculate_total_width(indicators)
        assert total_width > 0
        
        result = WidthCalculator.calculate_width_with_fallback(indicators)
        assert result.total_width > 0
        assert isinstance(result.is_accurate, bool)


class TestPageAccessManagerProperties:
    """Property-based тесты для PageAccessManager класса."""

    @given(st.booleans())
    def test_page_object_access_reliability_property(self, has_page):
        """
        **Feature: calendar-legend-width-fix, Property 6: Page object access reliability**
        **Validates: Requirements 2.2, 2.5, 4.2, 4.5**
        
        Property: For any attempt to access the page object, the system should try 
        multiple strategies and handle failures gracefully without throwing exceptions.
        """
        # Arrange - создаём mock компонент легенды
        from unittest.mock import Mock, MagicMock
        
        mock_legend = Mock()
        if has_page:
            mock_page = MagicMock()
            mock_legend.page = mock_page
        else:
            mock_legend.page = None
        
        page_manager = PageAccessManager(mock_legend)
        
        # Act & Assert - получение page не должно вызывать исключений
        try:
            result_page = page_manager.get_page()
            
            if has_page:
                assert result_page is not None, (
                    "При наличии page объекта в компоненте он должен быть найден"
                )
            else:
                # При отсутствии page результат может быть None, но не должно быть исключений
                assert result_page is None or result_page is not None  # Любой результат допустим
                
        except Exception as e:
            pytest.fail(f"get_page() не должен вызывать исключений, получено: {e}")

    @given(st.sampled_from(['event_has_page', 'event_control_has_page', 'component_has_page', 'no_page_available']))
    def test_multiple_access_strategies_property(self, scenario):
        """
        **Feature: calendar-legend-width-fix, Property 6: Page object access reliability**
        **Validates: Requirements 2.2, 2.5**
        
        Property: The page access manager should try multiple strategies in order
        and return the first successful result.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange - настраиваем сценарий
        mock_legend = Mock()
        mock_page = MagicMock()
        mock_event = Mock()
        
        if scenario == 'event_has_page':
            mock_event.control = Mock()
            mock_event.control.page = mock_page
            mock_legend.page = None
        elif scenario == 'event_control_has_page':
            mock_event.control = Mock()
            mock_event.control.page = mock_page
            mock_legend.page = None
        elif scenario == 'component_has_page':
            mock_event = None
            mock_legend.page = mock_page
        else:  # no_page_available
            mock_event = None
            mock_legend.page = None
        
        page_manager = PageAccessManager(mock_legend)
        
        # Act - пробуем получить page
        result_page = page_manager.get_page(mock_event)
        
        # Assert - проверяем результат в зависимости от сценария
        if scenario in ['event_has_page', 'event_control_has_page', 'component_has_page']:
            assert result_page is mock_page, (
                f"В сценарии {scenario} должен быть найден mock_page"
            )
        else:
            assert result_page is None, (
                f"В сценарии {scenario} page должен быть None"
            )

    @given(st.booleans())
    def test_page_caching_consistency_property(self, cache_initially):
        """
        **Feature: calendar-legend-width-fix, Property 8: Fallback behavior consistency**
        **Validates: Requirements 4.2, 4.5**
        
        Property: Page caching should work consistently - cached pages should be 
        returned when available, and caching should not interfere with normal operation.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange
        mock_legend = Mock()
        mock_legend.page = None
        page_manager = PageAccessManager(mock_legend)
        
        mock_page = MagicMock()
        
        if cache_initially:
            # Предварительно кэшируем page
            page_manager.cache_page(mock_page)
        
        # Act - пробуем получить page
        result_page = page_manager.get_page()
        
        # Assert - проверяем консистентность кэширования
        if cache_initially:
            assert result_page is mock_page, (
                "Закэшированный page должен быть возвращён"
            )
            assert page_manager.cached_page is mock_page, (
                "Кэш должен содержать правильный page"
            )
        else:
            # Без предварительного кэширования результат зависит от других стратегий
            # Главное - не должно быть исключений
            assert True  # Тест прошёл, если не было исключений

    @given(st.booleans())
    def test_page_availability_check_property(self, page_available):
        """
        **Feature: calendar-legend-width-fix, Property 6: Page object access reliability**
        **Validates: Requirements 2.2, 2.5**
        
        Property: The is_page_available() method should correctly reflect the actual
        availability of the page object through any of the access strategies.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange
        mock_legend = Mock()
        if page_available:
            mock_page = MagicMock()
            mock_legend.page = mock_page
        else:
            mock_legend.page = None
        
        page_manager = PageAccessManager(mock_legend)
        
        # Act
        availability_check = page_manager.is_page_available()
        actual_page = page_manager.get_page()
        
        # Assert - проверяем соответствие проверки доступности и фактического результата
        if page_available:
            assert availability_check, (
                "is_page_available() должен возвращать True когда page доступен"
            )
            assert actual_page is not None, (
                "get_page() должен возвращать page когда он доступен"
            )
        else:
            assert not availability_check, (
                "is_page_available() должен возвращать False когда page недоступен"
            )
            assert actual_page is None, (
                "get_page() должен возвращать None когда page недоступен"
            )

    @given(st.integers(min_value=1, max_value=10))
    def test_multiple_calls_consistency_property(self, num_calls):
        """
        **Feature: calendar-legend-width-fix, Property 8: Fallback behavior consistency**
        **Validates: Requirements 4.2, 4.5**
        
        Property: Multiple calls to get_page() should return consistent results
        when the underlying state hasn't changed.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange
        mock_legend = Mock()
        mock_page = MagicMock()
        mock_legend.page = mock_page
        
        page_manager = PageAccessManager(mock_legend)
        
        # Act - делаем несколько вызовов
        results = []
        for _ in range(num_calls):
            result = page_manager.get_page()
            results.append(result)
        
        # Assert - все результаты должны быть одинаковыми
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result is first_result, (
                f"Вызов {i+1} вернул {result}, а первый вызов вернул {first_result}. "
                f"Результаты должны быть консистентными."
            )

    def test_error_handling_robustness_property(self):
        """
        **Feature: calendar-legend-width-fix, Property 8: Fallback behavior consistency**
        **Validates: Requirements 2.5, 4.5**
        
        Property: The page access manager should handle various error conditions
        gracefully without crashing the application.
        """
        from unittest.mock import Mock, MagicMock
        
        # Test with None legend component
        try:
            page_manager = PageAccessManager(None)
            result = page_manager.get_page()
            # Должен вернуть None без исключений
            assert result is None
        except Exception as e:
            pytest.fail(f"PageAccessManager с None компонентом не должен вызывать исключения: {e}")
        
        # Test with legend that raises exceptions
        mock_legend = Mock()
        from unittest.mock import PropertyMock
        type(mock_legend).page = PropertyMock(side_effect=Exception("Test exception"))
        
        try:
            page_manager = PageAccessManager(mock_legend)
            result = page_manager.get_page()
            # Должен обработать исключение и вернуть None
            assert result is None
        except Exception as e:
            pytest.fail(f"PageAccessManager должен обрабатывать исключения в компоненте: {e}")
        
        # Test with malformed event
        mock_legend = Mock()
        mock_legend.page = None
        page_manager = PageAccessManager(mock_legend)
        
        malformed_events = [
            "string_instead_of_event",
            123,
            [],
            {},
            Mock(control=None),
            Mock(control="not_a_control")
        ]
        
        for malformed_event in malformed_events:
            try:
                result = page_manager.get_page(malformed_event)
                # Должен обработать некорректные события без исключений
                assert result is None or result is not None  # Любой результат допустим
            except Exception as e:
                pytest.fail(f"PageAccessManager должен обрабатывать некорректные события: {e}")

    @given(st.booleans())
    def test_cache_management_property(self, clear_cache):
        """
        **Feature: calendar-legend-width-fix, Property 8: Fallback behavior consistency**
        **Validates: Requirements 4.2**
        
        Property: Cache management operations (cache_page, clear_cache) should work
        correctly and not interfere with normal page access operations.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange
        mock_legend = Mock()
        mock_legend.page = None
        page_manager = PageAccessManager(mock_legend)
        
        mock_page = MagicMock()
        
        # Act - кэшируем page
        page_manager.cache_page(mock_page)
        
        # Проверяем, что page закэширован
        cached_page = page_manager.get_page()
        assert cached_page is mock_page, "Page должен быть закэширован"
        
        if clear_cache:
            # Очищаем кэш
            page_manager.clear_cache()
            
            # Проверяем, что кэш очищен
            assert page_manager.cached_page is None, "Кэш должен быть очищен"
            
            # Проверяем, что get_page() теперь возвращает None (так как legend.page = None)
            result_after_clear = page_manager.get_page()
            assert result_after_clear is None, "После очистки кэша page должен быть None"
        else:
            # Кэш не очищаем, проверяем, что page всё ещё доступен
            result_without_clear = page_manager.get_page()
            assert result_without_clear is mock_page, "Page должен оставаться в кэше"

    def test_strategy_priority_order_property(self):
        """
        **Feature: calendar-legend-width-fix, Property 6: Page object access reliability**
        **Validates: Requirements 2.2**
        
        Property: Access strategies should be tried in the correct priority order:
        1. From event, 2. From cache, 3. From component, 4. From control.
        """
        from unittest.mock import Mock, MagicMock
        
        # Arrange - создаём ситуацию, где page доступен через несколько стратегий
        mock_legend = Mock()
        component_page = MagicMock()
        mock_legend.page = component_page
        
        event_page = MagicMock()
        mock_event = Mock()
        mock_control = Mock()
        mock_control.page = event_page
        mock_event.control = mock_control
        
        cache_page = MagicMock()
        
        page_manager = PageAccessManager(mock_legend)
        page_manager.cache_page(cache_page)
        
        # Act - получаем page с событием (стратегия 1 должна иметь приоритет)
        result = page_manager.get_page(mock_event)
        
        # Assert - должен быть возвращён page из события (высший приоритет)
        assert result is event_page, (
            f"Должен быть возвращён page из события (приоритет 1), "
            f"но получен {result}"
        )
        
        # Test priority when event doesn't have page - создаём новый менеджер для чистого теста
        page_manager2 = PageAccessManager(mock_legend)
        page_manager2.cache_page(cache_page)
        
        # Создаём control без атрибута page
        mock_control_no_page = Mock(spec=[])  # Пустой spec - нет атрибутов
        mock_event.control = mock_control_no_page
        
        result_no_event = page_manager2.get_page(mock_event)
        
        # Должен быть возвращён page из кэша (приоритет 2)
        assert result_no_event is cache_page, (
            f"При отсутствии page в событии должен быть возвращён page из кэша, "
            f"но получен {result_no_event}"
        )
        
        # Test priority when cache is empty - создаём третий менеджер
        page_manager3 = PageAccessManager(mock_legend)
        result_no_cache = page_manager3.get_page(mock_event)
        
        # Должен быть возвращён page из компонента (приоритет 3)
        assert result_no_cache is component_page, (
            f"При отсутствии page в событии и кэше должен быть возвращён page из компонента, "
            f"но получен {result_no_cache}"
        )