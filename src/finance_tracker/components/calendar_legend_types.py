"""
Типы данных для улучшенной календарной легенды.

Содержит enum'ы, dataclass'ы и конфигурацию для отображения
всех индикаторов календаря в адаптивной легенде.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Union, Dict

import flet as ft


class IndicatorType(Enum):
    """Типы индикаторов календаря."""
    
    INCOME_DOT = "income_dot"           # Зелёная точка - доходы
    EXPENSE_DOT = "expense_dot"         # Красная точка - расходы
    PLANNED_SYMBOL = "planned_symbol"   # ◆ символ - плановые транзакции
    PENDING_SYMBOL = "pending_symbol"   # 📋 символ - отложенные платежи
    LOAN_SYMBOL = "loan_symbol"         # 💳 символ - платежи по кредитам
    CASH_GAP_BG = "cash_gap_bg"         # Жёлтый фон - кассовые разрывы
    OVERDUE_BG = "overdue_bg"           # Красный фон - просроченные платежи


class DisplayMode(Enum):
    """Режимы отображения легенды."""
    
    AUTO = "auto"           # Автоматический выбор режима
    FULL = "full"           # Полная легенда в одну строку
    COMPACT = "compact"     # Сокращённая легенда с кнопкой "Подробнее"
    MODAL_ONLY = "modal"    # Только модальное окно


@dataclass
class LegendIndicator:
    """Модель индикатора легенды."""
    
    type: IndicatorType
    visual_element: Union[ft.Container, ft.Text, ft.Icon]
    label: str
    description: str
    priority: int  # Для сортировки при ограниченном пространстве (1 = высший приоритет)
    estimated_width: int  # Примерная ширина в пикселях


# Конфигурация всех индикаторов календаря
INDICATOR_CONFIGS: Dict[IndicatorType, LegendIndicator] = {
    IndicatorType.INCOME_DOT: LegendIndicator(
        type=IndicatorType.INCOME_DOT,
        visual_element=ft.Container(
            width=10, 
            height=10, 
            border_radius=5, 
            bgcolor=ft.Colors.GREEN
        ),
        label="Доход",
        description="Зелёная точка обозначает дни с доходными транзакциями",
        priority=1,  # Высший приоритет
        estimated_width=60
    ),
    
    IndicatorType.EXPENSE_DOT: LegendIndicator(
        type=IndicatorType.EXPENSE_DOT,
        visual_element=ft.Container(
            width=10, 
            height=10, 
            border_radius=5, 
            bgcolor=ft.Colors.RED
        ),
        label="Расход",
        description="Красная точка обозначает дни с расходными транзакциями",
        priority=2,  # Высший приоритет
        estimated_width=65
    ),
    
    IndicatorType.PLANNED_SYMBOL: LegendIndicator(
        type=IndicatorType.PLANNED_SYMBOL,
        visual_element=ft.Text(
            "◆", 
            size=12, 
            color=ft.Colors.ORANGE, 
            weight=ft.FontWeight.BOLD
        ),
        label="Плановая",
        description="Символ ◆ обозначает дни с плановыми транзакциями",
        priority=3,
        estimated_width=75
    ),
    
    IndicatorType.PENDING_SYMBOL: LegendIndicator(
        type=IndicatorType.PENDING_SYMBOL,
        visual_element=ft.Text("📋", size=12),
        label="Отложенный",
        description="Символ 📋 обозначает дни с отложенными платежами",
        priority=4,
        estimated_width=85
    ),
    
    IndicatorType.LOAN_SYMBOL: LegendIndicator(
        type=IndicatorType.LOAN_SYMBOL,
        visual_element=ft.Text("💳", size=12),
        label="Кредит",
        description="Символ 💳 обозначает дни с платежами по кредитам",
        priority=5,
        estimated_width=70
    ),
    
    IndicatorType.CASH_GAP_BG: LegendIndicator(
        type=IndicatorType.CASH_GAP_BG,
        visual_element=ft.Container(
            width=16, 
            height=12, 
            bgcolor=ft.Colors.AMBER_100,
            border_radius=2
        ),
        label="Разрыв",
        description="Жёлтый фон дня обозначает кассовый разрыв (отрицательный прогноз)",
        priority=6,
        estimated_width=70
    ),
    
    IndicatorType.OVERDUE_BG: LegendIndicator(
        type=IndicatorType.OVERDUE_BG,
        visual_element=ft.Container(
            width=16, 
            height=12, 
            bgcolor=ft.Colors.RED_100,
            border_radius=2,
            border=ft.border.all(1, ft.Colors.RED_700)
        ),
        label="Просрочка",
        description="Красный фон дня обозначает просроченные платежи по кредитам",
        priority=7,
        estimated_width=85
    )
}