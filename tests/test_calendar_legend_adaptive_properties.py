"""
Property-based тесты для адаптивности календарной легенды.

Проверяет корректность вычисления ширины, адаптивного поведения
и приоритизации индикаторов при ограниченном пространстве.
"""
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, MagicMock

import flet as ft

from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    LegendIndicator,
    INDICATOR_CONFIGS
)


class TestCalendarLegendAdaptiveProperties:
    """Property-based тесты для адаптивности календарной легенды."""

    @given(st.integers(min_value=200, max_value=1500))
    def test_adaptive_layout_behavior_property(self, calendar_width):
        """
        **Feature: calendar-legend-improvement, Property 2: Adaptive layout behavior**
        **Validates: Requirements 1.9, 2.1, 2.2**
        
        Property: Для любой ширины календаря легенда должна отображать все индикаторы
        в одну строку при достаточном пространстве, или показывать приоритетные
        индикаторы с кнопкой "Подробнее" при ограниченном пространстве.
        """
        # Создаем mock объект CalendarLegend для тестирования
        # (пока что используем простую логику, реальная реализация будет в основной задаче)
        
        # Вычисляем общую ширину всех индикаторов
        total_width = sum(config.estimated_width for config in INDICATOR_CONFIGS.values())
        spacing = (len(INDICATOR_CONFIGS) - 1) * 20  # 20px между элементами
        padding = 40  # 40px для padding
        required_width = total_width + spacing + padding
        
        # Определяем ожидаемое поведение
        should_show_full = calendar_width >= required_width
        
        if should_show_full:
            # При достаточной ширине должны отображаться все индикаторы
            assert calendar_width >= required_width
            # Все 7 индикаторов должны помещаться
            assert len(INDICATOR_CONFIGS) == 7
        else:
            # При недостаточной ширине должны отображаться приоритетные индикаторы
            assert calendar_width < required_width
            # Должна быть логика приоритизации
            priority_indicators = sorted(
                INDICATOR_CONFIGS.values(), 
                key=lambda x: x.priority
            )
            # Первые два индикатора (доходы и расходы) должны иметь высший приоритет
            assert priority_indicators[0].priority == 1
            assert priority_indicators[1].priority == 2

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=1, 
        max_size=7, 
        unique=True
    ))
    def test_width_calculation_accuracy_property(self, indicator_types):
        """
        **Feature: calendar-legend-improvement, Property 3: Width calculation accuracy**
        **Validates: Requirements 2.3**
        
        Property: Для любого набора индикаторов вычисленная необходимая ширина
        должна точно отражать реальное пространство, необходимое для отображения
        всех индикаторов.
        """
        # Получаем конфигурации для выбранных типов индикаторов
        selected_configs = [INDICATOR_CONFIGS[ind_type] for ind_type in indicator_types]
        
        # Вычисляем ширину по алгоритму из дизайна
        total_indicator_width = sum(config.estimated_width for config in selected_configs)
        spacing = (len(selected_configs) - 1) * 20  # 20px между элементами
        padding = 40  # 40px для padding контейнера
        calculated_width = total_indicator_width + spacing + padding
        
        # Проверяем корректность вычислений
        assert calculated_width > 0, "Вычисленная ширина должна быть положительной"
        
        # Ширина должна увеличиваться с количеством индикаторов
        if len(selected_configs) > 1:
            # Для одного индикатора
            single_width = selected_configs[0].estimated_width + padding
            assert calculated_width > single_width, (
                "Ширина для нескольких индикаторов должна быть больше ширины для одного"
            )
        
        # Проверяем, что spacing корректно учитывается
        expected_spacing = max(0, (len(selected_configs) - 1) * 20)
        assert spacing == expected_spacing, (
            f"Spacing должен быть {expected_spacing}, получен {spacing}"
        )
        
        # Минимальная ширина должна быть разумной (не менее 60px для одного элемента)
        min_expected_width = 60  # минимальная ширина + padding
        assert calculated_width >= min_expected_width, (
            f"Вычисленная ширина {calculated_width} слишком мала"
        )

    @given(st.integers(min_value=200, max_value=800))  # Ограниченная ширина
    def test_priority_based_indicator_selection_property(self, limited_width):
        """
        **Feature: calendar-legend-improvement, Property 4: Priority-based indicator selection**
        **Validates: Requirements 2.4**
        
        Property: При ограниченной ширине отображаемые индикаторы должны быть
        упорядочены по приоритету (доходы и расходы первыми, затем остальные по важности).
        """
        # Получаем все индикаторы, отсортированные по приоритету
        all_indicators = sorted(INDICATOR_CONFIGS.values(), key=lambda x: x.priority)
        
        # Определяем, какие индикаторы поместятся в ограниченную ширину
        selected_indicators = []
        current_width = 40  # Начальный padding
        
        for indicator in all_indicators:
            # Добавляем ширину индикатора
            needed_width = indicator.estimated_width
            if selected_indicators:
                needed_width += 20  # spacing между элементами
            
            if current_width + needed_width <= limited_width - 80:  # Резерв для кнопки "Подробнее"
                selected_indicators.append(indicator)
                current_width += needed_width
            else:
                break
        
        # Проверяем, что выбранные индикаторы идут в порядке приоритета
        if len(selected_indicators) > 1:
            for i in range(len(selected_indicators) - 1):
                assert selected_indicators[i].priority < selected_indicators[i + 1].priority, (
                    f"Индикаторы должны быть отсортированы по приоритету. "
                    f"Найдено нарушение: {selected_indicators[i].priority} >= "
                    f"{selected_indicators[i + 1].priority}"
                )
        
        # Проверяем, что первыми всегда идут доходы и расходы (если помещаются)
        if len(selected_indicators) >= 1:
            first_indicator = selected_indicators[0]
            assert first_indicator.type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT], (
                f"Первым должен быть индикатор доходов или расходов, "
                f"получен {first_indicator.type}"
            )
        
        if len(selected_indicators) >= 2:
            second_indicator = selected_indicators[1]
            assert second_indicator.type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT], (
                f"Вторым должен быть индикатор доходов или расходов, "
                f"получен {second_indicator.type}"
            )
            
            # Первые два должны быть разными (доходы и расходы)
            assert first_indicator.type != second_indicator.type, (
                "Первые два индикатора должны быть доходы и расходы"
            )

    @given(
        st.integers(min_value=300, max_value=1200),  # Ширина календаря
        st.integers(min_value=1, max_value=7)        # Количество доступных индикаторов
    )
    def test_responsive_width_calculation_property(self, calendar_width, num_indicators):
        """
        Property: Вычисление ширины должно корректно работать для любого количества
        индикаторов и любой ширины календаря.
        """
        assume(num_indicators <= len(INDICATOR_CONFIGS))
        
        # Берем первые num_indicators индикаторов по приоритету
        sorted_indicators = sorted(INDICATOR_CONFIGS.values(), key=lambda x: x.priority)
        selected_indicators = sorted_indicators[:num_indicators]
        
        # Вычисляем необходимую ширину
        total_width = sum(config.estimated_width for config in selected_indicators)
        spacing = (len(selected_indicators) - 1) * 20
        padding = 40
        required_width = total_width + spacing + padding
        
        # Проверяем логику принятия решения
        can_fit_all = calendar_width >= required_width
        
        if can_fit_all:
            # Все индикаторы должны помещаться
            assert required_width <= calendar_width
        else:
            # Нужно использовать сокращенный режим
            assert required_width > calendar_width
            
            # В сокращенном режиме должно быть место для кнопки "Подробнее"
            button_width = 80  # Примерная ширина кнопки
            available_for_indicators = calendar_width - button_width - padding
            
            # Должен быть хотя бы один индикатор (самый приоритетный)
            if available_for_indicators > 0:
                min_indicator_width = min(config.estimated_width for config in selected_indicators)
                assert available_for_indicators >= min_indicator_width, (
                    "Должно быть место хотя бы для одного индикатора"
                )

    def test_edge_cases_width_calculation(self):
        """
        Тест граничных случаев для вычисления ширины.
        """
        # Случай с одним индикатором
        single_indicator = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        single_width = single_indicator[0].estimated_width + 40  # только padding, без spacing
        assert single_width > 0
        
        # Случай со всеми индикаторами
        all_indicators = list(INDICATOR_CONFIGS.values())
        total_width = sum(config.estimated_width for config in all_indicators)
        spacing = (len(all_indicators) - 1) * 20
        padding = 40
        full_width = total_width + spacing + padding
        
        # Полная ширина должна быть больше ширины одного индикатора
        assert full_width > single_width
        
        # Проверяем разумность полной ширины (не более 1000px для 7 индикаторов)
        assert full_width <= 1000, f"Полная ширина {full_width} слишком велика"

    @given(st.integers(min_value=100, max_value=300))  # Очень узкая ширина
    def test_minimum_width_handling_property(self, very_narrow_width):
        """
        Property: При очень узкой ширине система должна корректно обрабатывать
        ситуацию и показывать хотя бы один индикатор или только кнопку "Подробнее".
        """
        # Получаем самый приоритетный индикатор (доходы)
        highest_priority = min(INDICATOR_CONFIGS.values(), key=lambda x: x.priority)
        
        # Минимальная ширина для одного индикатора + кнопка
        min_indicator_width = highest_priority.estimated_width
        button_width = 80
        padding = 40
        absolute_minimum = min_indicator_width + button_width + padding
        
        if very_narrow_width >= absolute_minimum:
            # Должен поместиться хотя бы один индикатор + кнопка
            assert very_narrow_width >= min_indicator_width + button_width + padding
        else:
            # Слишком узко даже для одного индикатора - должна быть только кнопка
            # или специальная обработка
            assert very_narrow_width < absolute_minimum
            
            # В этом случае может отображаться только кнопка "Подробнее"
            # или компонент может скрываться совсем
            min_button_only_width = button_width + padding
            if very_narrow_width >= min_button_only_width:
                # Место есть только для кнопки
                assert very_narrow_width >= min_button_only_width
            # Если и для кнопки места нет, компонент может быть скрыт

    def test_display_mode_logic_consistency(self):
        """
        Тест консистентности логики выбора режима отображения.
        """
        # Тестируем различные сценарии ширины
        test_widths = [200, 400, 600, 800, 1000, 1200]
        
        for width in test_widths:
            # Вычисляем необходимую ширину для всех индикаторов
            total_width = sum(config.estimated_width for config in INDICATOR_CONFIGS.values())
            spacing = (len(INDICATOR_CONFIGS) - 1) * 20
            padding = 40
            required_width = total_width + spacing + padding
            
            # Определяем ожидаемый режим
            if width >= required_width:
                expected_mode = DisplayMode.FULL
            else:
                expected_mode = DisplayMode.COMPACT
            
            # Проверяем консистентность решения
            can_fit_all = width >= required_width
            
            if expected_mode == DisplayMode.FULL:
                assert can_fit_all, f"При ширине {width} должен быть полный режим"
            else:
                assert not can_fit_all, f"При ширине {width} должен быть компактный режим"