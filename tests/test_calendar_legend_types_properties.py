"""
Property-based тесты для типов данных календарной легенды.

Проверяет корректность моделей данных, enum'ов и конфигурации
индикаторов календарной легенды.
"""
import pytest
from hypothesis import given, strategies as st

import flet as ft

from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    LegendIndicator,
    INDICATOR_CONFIGS
)


class TestCalendarLegendTypesProperties:
    """Property-based тесты для типов данных календарной легенды."""

    @given(st.sampled_from(list(IndicatorType)))
    def test_complete_indicator_display_property(self, indicator_type):
        """
        **Feature: calendar-legend-improvement, Property 1: Complete indicator display**
        **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**
        
        Property: Для любого типа индикатора должна существовать полная конфигурация
        с визуальным элементом, меткой, описанием, приоритетом и шириной.
        """
        # Проверяем, что для каждого типа индикатора есть конфигурация
        assert indicator_type in INDICATOR_CONFIGS, f"Отсутствует конфигурация для {indicator_type}"
        
        config = INDICATOR_CONFIGS[indicator_type]
        
        # Проверяем, что конфигурация содержит все необходимые поля
        assert config.type == indicator_type
        assert config.visual_element is not None
        assert isinstance(config.label, str) and len(config.label) > 0
        assert isinstance(config.description, str) and len(config.description) > 0
        assert isinstance(config.priority, int) and config.priority > 0
        assert isinstance(config.estimated_width, int) and config.estimated_width > 0
        
        # Проверяем, что визуальный элемент является корректным Flet контролом
        assert isinstance(config.visual_element, (ft.Container, ft.Text, ft.Icon))

    def test_all_indicator_types_configured(self):
        """
        Тест: Все типы индикаторов должны быть сконфигурированы.
        
        Проверяет, что INDICATOR_CONFIGS содержит конфигурацию для всех 7 типов
        индикаторов согласно требованиям 1.2-1.8.
        """
        # Проверяем, что все enum значения присутствуют в конфигурации
        all_indicator_types = set(IndicatorType)
        configured_types = set(INDICATOR_CONFIGS.keys())
        
        assert all_indicator_types == configured_types, (
            f"Не все типы индикаторов сконфигурированы. "
            f"Отсутствуют: {all_indicator_types - configured_types}, "
            f"Лишние: {configured_types - all_indicator_types}"
        )
        
        # Проверяем, что у нас ровно 7 индикаторов согласно требованиям
        assert len(INDICATOR_CONFIGS) == 7, (
            f"Ожидается 7 индикаторов, получено {len(INDICATOR_CONFIGS)}"
        )

    @given(st.sampled_from(list(DisplayMode)))
    def test_display_mode_enum_completeness(self, display_mode):
        """
        Property: Все режимы отображения должны быть корректными enum значениями.
        """
        # Проверяем, что все режимы отображения имеют строковые значения
        assert isinstance(display_mode.value, str)
        assert len(display_mode.value) > 0
        
        # Проверяем, что режим является одним из ожидаемых
        expected_modes = {"auto", "full", "compact", "modal"}
        assert display_mode.value in expected_modes

    def test_indicator_priority_uniqueness(self):
        """
        Тест: Приоритеты индикаторов должны быть уникальными.
        
        Проверяет, что каждый индикатор имеет уникальный приоритет
        для корректной сортировки при ограниченном пространстве.
        """
        priorities = [config.priority for config in INDICATOR_CONFIGS.values()]
        
        # Проверяем уникальность приоритетов
        assert len(priorities) == len(set(priorities)), (
            f"Приоритеты должны быть уникальными. Найдены дубликаты: {priorities}"
        )
        
        # Проверяем, что приоритеты начинаются с 1 и идут подряд
        sorted_priorities = sorted(priorities)
        expected_priorities = list(range(1, len(priorities) + 1))
        assert sorted_priorities == expected_priorities, (
            f"Приоритеты должны быть последовательными начиная с 1. "
            f"Ожидается: {expected_priorities}, получено: {sorted_priorities}"
        )

    @given(st.sampled_from(list(IndicatorType)))
    def test_visual_element_consistency_property(self, indicator_type):
        """
        Property: Визуальные элементы должны соответствовать типу индикатора.
        
        Проверяет, что точки используют Container, символы используют Text,
        а фоновые индикаторы используют Container с соответствующими цветами.
        """
        config = INDICATOR_CONFIGS[indicator_type]
        visual_element = config.visual_element
        
        if indicator_type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT]:
            # Точки должны быть Container'ами с круглой формой
            assert isinstance(visual_element, ft.Container)
            assert visual_element.width == visual_element.height  # Квадратная форма
            assert visual_element.border_radius == visual_element.width // 2  # Круглая форма
            assert visual_element.bgcolor is not None
            
        elif indicator_type in [IndicatorType.PLANNED_SYMBOL, IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]:
            # Символы должны быть Text элементами
            assert isinstance(visual_element, ft.Text)
            assert visual_element.value is not None and len(visual_element.value) > 0
            
        elif indicator_type in [IndicatorType.CASH_GAP_BG, IndicatorType.OVERDUE_BG]:
            # Фоновые индикаторы должны быть Container'ами с фоном
            assert isinstance(visual_element, ft.Container)
            assert visual_element.bgcolor is not None
            assert visual_element.width > 0 and visual_element.height > 0

    def test_color_consistency_with_calendar(self):
        """
        Тест: Цвета индикаторов должны соответствовать цветам в календаре.
        
        Проверяет, что цвета в конфигурации легенды совпадают с цветами,
        используемыми в календарном виджете.
        """
        # Проверяем цвета точек
        income_config = INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]
        expense_config = INDICATOR_CONFIGS[IndicatorType.EXPENSE_DOT]
        
        assert income_config.visual_element.bgcolor == ft.Colors.GREEN
        assert expense_config.visual_element.bgcolor == ft.Colors.RED
        
        # Проверяем цвет символа плановой транзакции
        planned_config = INDICATOR_CONFIGS[IndicatorType.PLANNED_SYMBOL]
        assert planned_config.visual_element.color == ft.Colors.ORANGE
        
        # Проверяем цвета фоновых индикаторов
        cash_gap_config = INDICATOR_CONFIGS[IndicatorType.CASH_GAP_BG]
        overdue_config = INDICATOR_CONFIGS[IndicatorType.OVERDUE_BG]
        
        assert cash_gap_config.visual_element.bgcolor == ft.Colors.AMBER_100
        assert overdue_config.visual_element.bgcolor == ft.Colors.RED_100

    @given(st.sampled_from(list(IndicatorType)))
    def test_estimated_width_reasonableness_property(self, indicator_type):
        """
        Property: Оценочная ширина индикаторов должна быть разумной.
        
        Проверяет, что ширина находится в разумных пределах для UI элементов.
        """
        config = INDICATOR_CONFIGS[indicator_type]
        
        # Ширина должна быть в разумных пределах (от 30 до 150 пикселей)
        assert 30 <= config.estimated_width <= 150, (
            f"Ширина {config.estimated_width}px для {indicator_type} "
            f"выходит за разумные пределы (30-150px)"
        )

    def test_label_and_description_quality(self):
        """
        Тест: Метки и описания должны быть информативными.
        
        Проверяет качество текстовых описаний индикаторов.
        """
        for indicator_type, config in INDICATOR_CONFIGS.items():
            # Метка должна быть короткой и информативной
            assert 3 <= len(config.label) <= 15, (
                f"Метка '{config.label}' для {indicator_type} должна быть 3-15 символов"
            )
            
            # Описание должно быть подробным
            assert 20 <= len(config.description) <= 200, (
                f"Описание для {indicator_type} должно быть 20-200 символов"
            )
            
            # Описание должно содержать название индикатора
            label_lower = config.label.lower()
            description_lower = config.description.lower()
            
            # Проверяем, что описание связано с меткой или типом индикатора
            type_keywords = {
                IndicatorType.INCOME_DOT: ["доход", "зелён"],
                IndicatorType.EXPENSE_DOT: ["расход", "красн"],
                IndicatorType.PLANNED_SYMBOL: ["план", "◆"],
                IndicatorType.PENDING_SYMBOL: ["отложен", "📋"],
                IndicatorType.LOAN_SYMBOL: ["кредит", "💳"],
                IndicatorType.CASH_GAP_BG: ["разрыв", "жёлт"],
                IndicatorType.OVERDUE_BG: ["просроч", "красн"]
            }
            
            keywords = type_keywords.get(indicator_type, [])
            assert any(keyword in description_lower for keyword in keywords), (
                f"Описание '{config.description}' для {indicator_type} "
                f"должно содержать один из ключевых слов: {keywords}"
            )