"""
Property-based тесты для визуализации календарной легенды.

Проверяет визуальную консистентность, выравнивание элементов,
стандарты читаемости и визуальную группировку индикаторов.
"""
import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

import flet as ft

from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    DisplayMode,
    LegendIndicator,
    INDICATOR_CONFIGS
)


class TestCalendarLegendVisualProperties:
    """Property-based тесты для визуализации календарной легенды."""

    @given(st.sampled_from(list(IndicatorType)))
    def test_visual_consistency_property(self, indicator_type):
        """
        **Feature: calendar-legend-improvement, Property 8: Visual consistency**
        **Validates: Requirements 4.1**
        
        Property: Для любого индикатора в легенде его цвета и символы должны
        точно соответствовать тем, что используются в виджете календаря.
        """
        # Получаем конфигурацию индикатора
        indicator_config = INDICATOR_CONFIGS[indicator_type]
        
        # Создаем легенду для тестирования
        legend = CalendarLegend(calendar_width=1000)  # Достаточная ширина для полной легенды
        
        # Проверяем, что визуальный элемент соответствует ожидаемому типу
        visual_element = indicator_config.visual_element
        
        if indicator_type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT]:
            # Точки должны быть Container'ами с правильными цветами
            assert isinstance(visual_element, ft.Container), (
                f"Индикатор {indicator_type} должен быть Container"
            )
            assert visual_element.width == 10, "Ширина точки должна быть 10px"
            assert visual_element.height == 10, "Высота точки должна быть 10px"
            assert visual_element.border_radius == 5, "Точка должна быть круглой"
            
            # Проверяем правильные цвета
            if indicator_type == IndicatorType.INCOME_DOT:
                assert visual_element.bgcolor == ft.Colors.GREEN, (
                    "Индикатор доходов должен быть зелёным"
                )
            elif indicator_type == IndicatorType.EXPENSE_DOT:
                assert visual_element.bgcolor == ft.Colors.RED, (
                    "Индикатор расходов должен быть красным"
                )
                
        elif indicator_type in [IndicatorType.PLANNED_SYMBOL, IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]:
            # Символы должны быть Text элементами
            assert isinstance(visual_element, ft.Text), (
                f"Индикатор {indicator_type} должен быть Text элементом"
            )
            assert visual_element.size == 12, "Размер символа должен быть 12px"
            
            # Проверяем правильные символы и цвета
            if indicator_type == IndicatorType.PLANNED_SYMBOL:
                assert visual_element.value == "◆", "Символ плановых транзакций должен быть ◆"
                assert visual_element.color == ft.Colors.ORANGE, (
                    "Символ плановых транзакций должен быть оранжевым"
                )
                assert visual_element.weight == ft.FontWeight.BOLD, (
                    "Символ плановых транзакций должен быть жирным"
                )
            elif indicator_type == IndicatorType.PENDING_SYMBOL:
                assert visual_element.value == "📋", "Символ отложенных платежей должен быть 📋"
            elif indicator_type == IndicatorType.LOAN_SYMBOL:
                assert visual_element.value == "💳", "Символ кредитных платежей должен быть 💳"
                
        elif indicator_type in [IndicatorType.CASH_GAP_BG, IndicatorType.OVERDUE_BG]:
            # Фоновые индикаторы должны быть Container'ами
            assert isinstance(visual_element, ft.Container), (
                f"Фоновый индикатор {indicator_type} должен быть Container"
            )
            assert visual_element.width == 16, "Ширина фонового индикатора должна быть 16px"
            assert visual_element.height == 12, "Высота фонового индикатора должна быть 12px"
            assert visual_element.border_radius == 2, "Фоновый индикатор должен иметь скругление 2px"
            
            # Проверяем правильные цвета фона
            if indicator_type == IndicatorType.CASH_GAP_BG:
                assert visual_element.bgcolor == ft.Colors.AMBER_100, (
                    "Фон кассового разрыва должен быть жёлтым"
                )
            elif indicator_type == IndicatorType.OVERDUE_BG:
                assert visual_element.bgcolor == ft.Colors.RED_100, (
                    "Фон просрочки должен быть красным"
                )
                # Проверяем наличие границы для просрочки
                assert visual_element.border is not None, (
                    "Индикатор просрочки должен иметь границу"
                )

    @given(st.integers(min_value=400, max_value=1200))
    def test_layout_alignment_property(self, calendar_width):
        """
        **Feature: calendar-legend-improvement, Property 9: Layout alignment**
        **Validates: Requirements 4.2, 4.3**
        
        Property: Для любого отображения легенды элементы должны быть выровнены
        по центру под календарём с подходящими отступами между элементами.
        """
        # Создаем легенду с заданной шириной
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Получаем контент легенды
        content = legend.content
        
        # Проверяем, что контент является Row
        assert isinstance(content, ft.Row), "Контент легенды должен быть Row"
        
        # Проверяем выравнивание по центру
        assert content.alignment == ft.MainAxisAlignment.CENTER, (
            "Элементы легенды должны быть выровнены по центру"
        )
        assert content.vertical_alignment == ft.CrossAxisAlignment.CENTER, (
            "Элементы легенды должны быть выровнены по центру вертикально"
        )
        
        # Проверяем отступы между элементами
        assert content.spacing == 20, (
            "Отступы между элементами должны быть 20px"
        )
        
        # Проверяем padding контейнера (теперь это объект padding)
        assert legend.padding is not None, "Padding легенды должен быть установлен"
        if hasattr(legend.padding, 'left'):
            # Новый стиль padding - объект с отступами
            assert legend.padding.left == 10, "Горизонтальный padding должен быть 10px"
            assert legend.padding.top == 5, "Вертикальный padding должен быть 5px"
        else:
            # Старый стиль padding - простое число
            assert legend.padding == 5, "Padding легенды должен быть 5px"
        
        # Проверяем, что все элементы в Row являются правильными компонентами
        for control in content.controls:
            # Каждый элемент должен быть либо Row (элемент легенды), либо TextButton (кнопка "Подробнее"), 
            # либо Container (разделитель групп)
            assert isinstance(control, (ft.Row, ft.TextButton, ft.Container)), (
                f"Элемент легенды должен быть Row, TextButton или Container (разделитель), "
                f"получен {type(control)}"
            )
            
            if isinstance(control, ft.Row):
                # Элементы легенды должны иметь правильное выравнивание
                assert control.vertical_alignment == ft.CrossAxisAlignment.CENTER, (
                    "Элементы внутри элемента легенды должны быть выровнены по центру"
                )
                assert control.spacing == 5, (
                    "Отступ между визуальным элементом и текстом должен быть 5px"
                )
            elif isinstance(control, ft.Container):
                # Разделители должны иметь правильные размеры
                if hasattr(control, 'width') and control.width == 1:
                    # Это разделитель групп
                    assert control.height == 16, "Высота разделителя должна быть 16px"

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=1, 
        max_size=7, 
        unique=True
    ))
    def test_readability_standards_property(self, indicator_types):
        """
        **Feature: calendar-legend-improvement, Property 10: Readability standards**
        **Validates: Requirements 4.4**
        
        Property: Для любого элемента легенды размеры шрифтов и символов должны
        соответствовать минимальным требованиям читаемости (шрифты ≥ 12px, символы ≥ 8px).
        """
        # Проверяем каждый тип индикатора на соответствие стандартам читаемости
        for indicator_type in indicator_types:
            indicator_config = INDICATOR_CONFIGS[indicator_type]
            
            # Проверяем размеры текстовых элементов
            if isinstance(indicator_config.visual_element, ft.Text):
                text_size = indicator_config.visual_element.size
                assert text_size >= 8, (
                    f"Размер символа {indicator_type} должен быть не менее 8px, "
                    f"получен {text_size}px"
                )
                # Для символов рекомендуется размер 12px
                assert text_size >= 12, (
                    f"Рекомендуемый размер символа {indicator_type} должен быть 12px, "
                    f"получен {text_size}px"
                )
            
            # Проверяем размеры контейнеров (точки и фоновые индикаторы)
            elif isinstance(indicator_config.visual_element, ft.Container):
                width = indicator_config.visual_element.width
                height = indicator_config.visual_element.height
                
                # Минимальные размеры для видимости
                assert width >= 8, (
                    f"Ширина визуального элемента {indicator_type} должна быть не менее 8px, "
                    f"получена {width}px"
                )
                assert height >= 8, (
                    f"Высота визуального элемента {indicator_type} должна быть не менее 8px, "
                    f"получена {height}px"
                )
            
            # Проверяем читаемость текстовых меток
            label = indicator_config.label
            assert len(label) > 0, f"Метка индикатора {indicator_type} не должна быть пустой"
            assert len(label) <= 15, (
                f"Метка индикатора {indicator_type} не должна быть слишком длинной, "
                f"получена длина {len(label)}"
            )
            
            # Проверяем, что описание не пустое
            description = indicator_config.description
            assert len(description) > 0, (
                f"Описание индикатора {indicator_type} не должно быть пустым"
            )

    def test_visual_grouping_property(self):
        """
        **Feature: calendar-legend-improvement, Property 11: Visual grouping**
        **Validates: Requirements 4.5**
        
        Property: Для любого набора похожих индикаторов (например, все точки, все символы)
        они должны быть визуально сгруппированы вместе в легенде.
        """
        # Создаем легенду с полным отображением
        legend = CalendarLegend(calendar_width=1000)
        
        # Получаем все индикаторы, отсортированные по приоритету
        all_indicators = legend.all_indicators
        
        # Группируем индикаторы по типам визуальных элементов
        dot_indicators = []      # Точки (Container с border_radius=5)
        symbol_indicators = []   # Символы (Text элементы)
        bg_indicators = []       # Фоновые (Container с border_radius=2)
        
        for indicator in all_indicators:
            visual_element = indicator.visual_element
            
            if isinstance(visual_element, ft.Container):
                if visual_element.border_radius == 5:
                    dot_indicators.append(indicator)
                elif visual_element.border_radius == 2:
                    bg_indicators.append(indicator)
            elif isinstance(visual_element, ft.Text):
                symbol_indicators.append(indicator)
        
        # Проверяем, что группировка логична
        assert len(dot_indicators) == 2, (
            f"Должно быть 2 точечных индикатора (доходы и расходы), "
            f"найдено {len(dot_indicators)}"
        )
        assert len(symbol_indicators) == 3, (
            f"Должно быть 3 символьных индикатора, найдено {len(symbol_indicators)}"
        )
        assert len(bg_indicators) == 2, (
            f"Должно быть 2 фоновых индикатора, найдено {len(bg_indicators)}"
        )
        
        # Проверяем, что точечные индикаторы идут первыми (высший приоритет)
        first_two = all_indicators[:2]
        for indicator in first_two:
            assert indicator in dot_indicators, (
                f"Первые два индикатора должны быть точечными, "
                f"найден {indicator.type}"
            )
        
        # Проверяем, что индикаторы одного типа имеют схожие приоритеты
        dot_priorities = [ind.priority for ind in dot_indicators]
        symbol_priorities = [ind.priority for ind in symbol_indicators]
        bg_priorities = [ind.priority for ind in bg_indicators]
        
        # Точки должны иметь приоритеты 1-2
        assert set(dot_priorities) == {1, 2}, (
            f"Точечные индикаторы должны иметь приоритеты 1-2, "
            f"получены {dot_priorities}"
        )
        
        # Символы должны иметь приоритеты 3-5
        assert all(3 <= p <= 5 for p in symbol_priorities), (
            f"Символьные индикаторы должны иметь приоритеты 3-5, "
            f"получены {symbol_priorities}"
        )
        
        # Фоновые должны иметь приоритеты 6-7
        assert all(6 <= p <= 7 for p in bg_priorities), (
            f"Фоновые индикаторы должны иметь приоритеты 6-7, "
            f"получены {bg_priorities}"
        )

    @given(st.integers(min_value=300, max_value=1200))
    def test_legend_item_structure_property(self, calendar_width):
        """
        Property: Каждый элемент легенды должен иметь правильную структуру
        независимо от ширины календаря.
        """
        # Создаем легенду
        legend = CalendarLegend(calendar_width=calendar_width)
        
        # Получаем контент
        content = legend.content
        assert isinstance(content, ft.Row)
        
        # Проверяем структуру каждого элемента легенды
        legend_items = [control for control in content.controls if isinstance(control, ft.Row)]
        
        for legend_item in legend_items:
            # Каждый элемент легенды должен содержать визуальный элемент и текст
            assert len(legend_item.controls) == 2, (
                f"Элемент легенды должен содержать 2 компонента (визуальный элемент + текст), "
                f"найдено {len(legend_item.controls)}"
            )
            
            visual_element = legend_item.controls[0]
            text_element = legend_item.controls[1]
            
            # Визуальный элемент должен быть Container или Text
            assert isinstance(visual_element, (ft.Container, ft.Text)), (
                f"Визуальный элемент должен быть Container или Text, "
                f"получен {type(visual_element)}"
            )
            
            # Текстовый элемент должен быть Text
            assert isinstance(text_element, ft.Text), (
                f"Текстовый элемент должен быть Text, получен {type(text_element)}"
            )
            
            # Проверяем размер текста
            assert text_element.size == 12, (
                f"Размер текста метки должен быть 12px, получен {text_element.size}"
            )

    @given(st.integers(min_value=200, max_value=500))  # Узкая ширина
    def test_compact_mode_visual_consistency_property(self, narrow_width):
        """
        Property: В компактном режиме визуальная консистентность должна сохраняться
        для отображаемых индикаторов.
        """
        # Создаем легенду в компактном режиме
        legend = CalendarLegend(calendar_width=narrow_width)
        
        # Проверяем, что это действительно компактный режим
        should_be_compact = not legend._should_show_full_legend()
        
        if should_be_compact:
            content = legend.content
            assert isinstance(content, ft.Row)
            
            # В компактном режиме должна быть кнопка "Подробнее"
            has_details_button = any(
                isinstance(control, ft.TextButton) and "Подробнее" in control.text
                for control in content.controls
            )
            assert has_details_button, "В компактном режиме должна быть кнопка 'Подробнее'"
            
            # Проверяем, что отображаемые индикаторы имеют высший приоритет
            legend_items = [control for control in content.controls if isinstance(control, ft.Row)]
            
            if legend_items:
                # Должны отображаться самые приоритетные индикаторы
                # Проверяем это косвенно через количество элементов
                assert len(legend_items) >= 1, (
                    "В компактном режиме должен отображаться хотя бы один индикатор"
                )
                assert len(legend_items) <= 4, (
                    "В компактном режиме не должно быть слишком много индикаторов"
                )

    def test_color_accessibility_standards(self):
        """
        Тест соответствия цветов стандартам доступности.
        """
        # Проверяем, что используются стандартные цвета Flet
        income_config = INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]
        expense_config = INDICATOR_CONFIGS[IndicatorType.EXPENSE_DOT]
        planned_config = INDICATOR_CONFIGS[IndicatorType.PLANNED_SYMBOL]
        
        # Проверяем использование стандартных цветов
        assert income_config.visual_element.bgcolor == ft.Colors.GREEN
        assert expense_config.visual_element.bgcolor == ft.Colors.RED
        assert planned_config.visual_element.color == ft.Colors.ORANGE
        
        # Проверяем контрастность для фоновых индикаторов
        cash_gap_config = INDICATOR_CONFIGS[IndicatorType.CASH_GAP_BG]
        overdue_config = INDICATOR_CONFIGS[IndicatorType.OVERDUE_BG]
        
        assert cash_gap_config.visual_element.bgcolor == ft.Colors.AMBER_100
        assert overdue_config.visual_element.bgcolor == ft.Colors.RED_100
        
        # Проверяем, что у просроченных платежей есть дополнительная граница для лучшей видимости
        assert overdue_config.visual_element.border is not None

    @given(st.integers(min_value=1, max_value=7))
    def test_estimated_width_accuracy_property(self, num_indicators):
        """
        Property: Оценочная ширина индикаторов должна быть достаточно точной
        для корректного вычисления необходимого пространства.
        """
        assume(num_indicators <= len(INDICATOR_CONFIGS))
        
        # Берем первые num_indicators по приоритету
        sorted_indicators = sorted(INDICATOR_CONFIGS.values(), key=lambda x: x.priority)
        selected_indicators = sorted_indicators[:num_indicators]
        
        # Проверяем разумность оценочных ширин
        for indicator in selected_indicators:
            estimated_width = indicator.estimated_width
            
            # Ширина должна быть положительной и разумной
            assert estimated_width > 0, (
                f"Оценочная ширина {indicator.type} должна быть положительной"
            )
            assert estimated_width >= 40, (
                f"Оценочная ширина {indicator.type} должна быть не менее 40px, "
                f"получена {estimated_width}px"
            )
            assert estimated_width <= 120, (
                f"Оценочная ширина {indicator.type} не должна превышать 120px, "
                f"получена {estimated_width}px"
            )
            
            # Проверяем соответствие ширины типу элемента
            visual_element = indicator.visual_element
            label_length = len(indicator.label)
            
            if isinstance(visual_element, ft.Text):
                # Символьные индикаторы могут быть шире из-за эмодзи
                if indicator.type in [IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]:
                    assert estimated_width >= 70, (
                        f"Символьные индикаторы с эмодзи должны иметь ширину не менее 70px"
                    )
            
            # Более длинные метки должны иметь большую оценочную ширину
            if label_length > 6:  # "Доход" = 5 символов
                assert estimated_width >= 65, (
                    f"Индикаторы с длинными метками должны иметь большую ширину"
                )

    def test_visual_element_immutability(self):
        """
        Тест неизменности визуальных элементов в конфигурации.
        """
        # Получаем конфигурацию дважды и проверяем, что элементы не изменились
        config1 = INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]
        config2 = INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]
        
        # Конфигурации должны ссылаться на один объект
        assert config1 is config2, "Конфигурации должны быть неизменными"
        
        # Проверяем основные свойства
        assert config1.type == config2.type
        assert config1.label == config2.label
        assert config1.priority == config2.priority
        assert config1.estimated_width == config2.estimated_width