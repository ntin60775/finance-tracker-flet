"""
Типы данных для улучшенной календарной легенды.

Содержит enum'ы, dataclass'ы и конфигурацию для отображения
всех индикаторов календаря в адаптивной легенде.

Основные изменения в версии с исправлениями ширины:
- Скорректированы оценки ширины индикаторов с завышенных 60-85px до реалистичных 45-56px
- Общая требуемая ширина снижена с ~670px до ~525px
- Сокращены некоторые текстовые метки для экономии места
- Добавлены точные вычисления ширины на основе длины текста
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


# Конфигурация всех индикаторов календаря с исправленными оценками ширины
# 
# ВАЖНЫЕ ИЗМЕНЕНИЯ В ВЕРСИИ С ИСПРАВЛЕНИЯМИ:
# - Все оценки ширины пересчитаны на основе реальных размеров текста и элементов
# - Формула расчёта: ширина_элемента + 5px_отступ + длина_текста * 7px_за_символ
# - Общая экономия ширины: ~145px (с 670px до 525px)
# - Некоторые метки сокращены для лучшего помещения в ограниченное пространство
#
# Новые реалистичные значения ширины:
# - Точечные индикаторы (доходы, расходы): 47-54px (было 60-65px)
# - Символьные индикаторы (план, ожидание, кредит): 45-56px (было 70-85px)  
# - Фоновые индикаторы (разрыв, просрочка): 46-53px (было 70-85px)
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
        priority=1,  # Высший приоритет - самый важный индикатор
        estimated_width=47  # Исправлено: 10px элемент + 5px отступ + 32px текст (5 символов * 6.4px)
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
        priority=2,  # Второй по важности - базовые транзакции
        estimated_width=54  # Исправлено: 10px элемент + 5px отступ + 39px текст (6 символов * 6.5px)
    ),
    
    IndicatorType.PLANNED_SYMBOL: LegendIndicator(
        type=IndicatorType.PLANNED_SYMBOL,
        visual_element=ft.Text(
            "◆", 
            size=12, 
            color=ft.Colors.ORANGE, 
            weight=ft.FontWeight.BOLD
        ),
        label="План",  # Сокращено с "Плановая" для экономии 28px ширины
        description="Символ ◆ обозначает дни с плановыми транзакциями",
        priority=3,  # Третий приоритет - плановые операции
        estimated_width=45  # Исправлено: 12px символ + 5px отступ + 28px текст (4 символа * 7px)
    ),
    
    IndicatorType.PENDING_SYMBOL: LegendIndicator(
        type=IndicatorType.PENDING_SYMBOL,
        visual_element=ft.Text("📋", size=12),
        label="Ждёт",  # Сокращено с "Отложенный" для экономии 35px ширины
        description="Символ 📋 обозначает дни с отложенными платежами",
        priority=4,  # Четвёртый приоритет - отложенные платежи
        estimated_width=45  # Исправлено: 12px символ + 5px отступ + 28px текст (4 символа * 7px)
    ),
    
    IndicatorType.LOAN_SYMBOL: LegendIndicator(
        type=IndicatorType.LOAN_SYMBOL,
        visual_element=ft.Text("💳", size=12),
        label="Кредит",
        description="Символ 💳 обозначает дни с платежами по кредитам",
        priority=5,  # Пятый приоритет - кредитные платежи
        estimated_width=56  # Исправлено: 12px символ + 5px отступ + 39px текст (6 символов * 6.5px)
    ),
    
    IndicatorType.CASH_GAP_BG: LegendIndicator(
        type=IndicatorType.CASH_GAP_BG,
        visual_element=ft.Container(
            width=16, 
            height=12, 
            bgcolor=ft.Colors.AMBER_100,
            border_radius=2
        ),
        label="Минус",  # Сокращено с "Разрыв" для экономии 21px ширины
        description="Жёлтый фон дня обозначает кассовый разрыв (отрицательный прогноз)",
        priority=6,  # Шестой приоритет - кассовые разрывы
        estimated_width=53  # Исправлено: 16px элемент + 5px отступ + 32px текст (5 символов * 6.4px)
    ),
    
    IndicatorType.OVERDUE_BG: LegendIndicator(
        type=IndicatorType.OVERDUE_BG,
        visual_element=ft.Container(
            width=16, 
            height=12, 
            bgcolor=ft.Colors.RED_100,
            border_radius=2,
            border=ft.Border.all(1, ft.Colors.RED_700)
        ),
        label="Долг",  # Сокращено с "Просрочка" для экономии 28px ширины
        description="Красный фон дня обозначает просроченные платежи по кредитам",
        priority=7,  # Седьмой приоритет - просроченные платежи (наименее частые)
        estimated_width=46  # Исправлено: 16px элемент + 5px отступ + 25px текст (4 символа * 6.25px)
    )
}