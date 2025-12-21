# Design Document

## Overview

Исправление критических проблем с календарной легендой: завышенные оценки ширины индикаторов (текущие 60-85px против реальных 30-50px) и неработающая кнопка "Подробнее" из-за проблем с доступом к page объекту. Решение обеспечит корректное отображение полной легенды при достаточной ширине календаря и стабильную работу модального окна.

## Architecture

### Current Problems Analysis

**Проблема 1: Завышенные оценки ширины**
- Текущие оценки: 60-85px на индикатор
- Реальные размеры: ~30-50px на индикатор
- Результат: требуется 670px вместо реальных ~350-400px
- Следствие: полная легенда не показывается даже при широких календарях

**Проблема 2: Неработающая кнопка "Подробнее"**
- Проблема с получением page объекта из события
- Метод `_safe_get_page()` не всегда находит page
- Модальное окно не открывается при клике

**Проблема 3: Неточное определение ширины календаря**
- Вычисления основаны на теоретических размерах страницы
- Не учитывают реальные размеры календарного виджета
- Могут быть неточности в расчёте layout

### Solution Architecture

**Компонентная архитектура (обновлённая):**
```
CalendarLegend (исправленный)
├── WidthCalculator - точные вычисления ширины индикаторов
├── PageAccessManager - надёжный доступ к page объекту
├── ModalManager - стабильное управление модальным окном
└── DebugLogger - отладочное логирование для диагностики
```

**Ключевые изменения:**
1. **Пересчёт оценок ширины** - реалистичные значения 30-55px
2. **Улучшенный доступ к page** - множественные стратегии получения page объекта
3. **Отладочное логирование** - для диагностики проблем в продакшене

## Components and Interfaces

### WidthCalculator

```python
class WidthCalculator:
    """Точные вычисления ширины индикаторов."""
    
    @staticmethod
    def calculate_indicator_width(indicator: LegendIndicator) -> int:
        """
        Вычисляет реальную ширину индикатора.
        
        Учитывает:
        - Ширину визуального элемента (10-16px)
        - Длину текстовой метки (6-8px на символ)
        - Отступ между элементом и текстом (5px)
        
        Returns:
            Реалистичная ширина в пикселях (30-55px)
        """
        
    @staticmethod
    def calculate_total_width(indicators: List[LegendIndicator]) -> int:
        """
        Вычисляет общую требуемую ширину для всех индикаторов.
        
        Returns:
            Общая ширина с учётом отступов между элементами
        """
```

### PageAccessManager

```python
class PageAccessManager:
    """Надёжный доступ к page объекту."""
    
    def __init__(self, legend_component):
        self.legend = legend_component
        self.cached_page = None
        
    def get_page(self, event_or_control=None) -> Optional[ft.Page]:
        """
        Получает page объект используя множественные стратегии.
        
        Стратегии:
        1. Из события (event.control.page)
        2. Из кэша компонента (self.cached_page)
        3. Из родительского контрола (self.legend.page)
        4. Из глобального контекста (если доступен)
        
        Returns:
            Page объект или None
        """
        
    def cache_page(self, page: ft.Page):
        """Кэширует page объект для последующего использования."""
        
    def is_page_available(self) -> bool:
        """Проверяет доступность page объекта."""
```

### Updated INDICATOR_CONFIGS

```python
# Обновлённая конфигурация с реалистичными оценками ширины
UPDATED_INDICATOR_CONFIGS = {
    IndicatorType.INCOME_DOT: LegendIndicator(
        type=IndicatorType.INCOME_DOT,
        visual_element=ft.Container(width=10, height=10, border_radius=5, bgcolor=ft.Colors.GREEN),
        label="Доход",
        description="Зелёная точка обозначает дни с доходными транзакциями",
        priority=1,
        estimated_width=45  # Было: 60px, стало: 45px
    ),
    IndicatorType.EXPENSE_DOT: LegendIndicator(
        type=IndicatorType.EXPENSE_DOT,
        visual_element=ft.Container(width=10, height=10, border_radius=5, bgcolor=ft.Colors.RED),
        label="Расход",
        description="Красная точка обозначает дни с расходными транзакциями",
        priority=2,
        estimated_width=50  # Было: 65px, стало: 50px
    ),
    IndicatorType.PLANNED_SYMBOL: LegendIndicator(
        type=IndicatorType.PLANNED_SYMBOL,
        visual_element=ft.Text("◆", size=12, color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD),
        label="Плановая",
        description="Символ ◆ обозначает дни с плановыми транзакциями",
        priority=3,
        estimated_width=55  # Было: 75px, стало: 55px
    ),
    IndicatorType.PENDING_SYMBOL: LegendIndicator(
        type=IndicatorType.PENDING_SYMBOL,
        visual_element=ft.Text("📋", size=12),
        label="Отложенный",
        description="Символ 📋 обозначает дни с отложенными платежами",
        priority=4,
        estimated_width=60  # Было: 85px, стало: 60px
    ),
    IndicatorType.LOAN_SYMBOL: LegendIndicator(
        type=IndicatorType.LOAN_SYMBOL,
        visual_element=ft.Text("💳", size=12),
        label="Кредит",
        description="Символ 💳 обозначает дни с платежами по кредитам",
        priority=5,
        estimated_width=50  # Было: 70px, стало: 50px
    ),
    IndicatorType.CASH_GAP_BG: LegendIndicator(
        type=IndicatorType.CASH_GAP_BG,
        visual_element=ft.Container(width=16, height=12, bgcolor=ft.Colors.AMBER_100, border_radius=2),
        label="Разрыв",
        description="Жёлтый фон дня обозначает кассовый разрыв (отрицательный прогноз)",
        priority=6,
        estimated_width=50  # Было: 70px, стало: 50px
    ),
    IndicatorType.OVERDUE_BG: LegendIndicator(
        type=IndicatorType.OVERDUE_BG,
        visual_element=ft.Container(width=16, height=12, bgcolor=ft.Colors.RED_100, border_radius=2, border=ft.border.all(1, ft.Colors.RED_700)),
        label="Просрочка",
        description="Красный фон дня обозначает просроченные платежи по кредитам",
        priority=7,
        estimated_width=55  # Было: 85px, стало: 55px
    )
}

# Новая общая требуемая ширина: 45+50+55+60+50+50+55 + (6*20) отступы + 40 padding = 365 + 120 + 40 = 525px
# Было: 670px, стало: 525px - экономия 145px!
```

## Data Models

### DebugInfo

```python
@dataclass
class DebugInfo:
    """Отладочная информация для диагностики проблем."""
    
    calendar_width: Optional[int]
    required_width: int
    should_show_full: bool
    indicators_count: int
    page_available: bool
    modal_created: bool
    timestamp: str
```

### WidthCalculationResult

```python
@dataclass
class WidthCalculationResult:
    """Результат вычисления ширины."""
    
    total_width: int
    individual_widths: Dict[IndicatorType, int]
    spacing_width: int
    padding_width: int
    is_accurate: bool  # True если вычисления точные, False если fallback
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

После анализа всех требований выявлены следующие группы свойств:

**Группа 1: Оценки ширины (1.2, 1.3, 1.5, 3.1-3.5)** - можно объединить в свойства о точности и реалистичности оценок ширины.

**Группа 2: Логика отображения (1.1, 1.4, 4.3)** - можно объединить в свойства о корректном выборе режима отображения.

**Группа 3: Работа с page объектом (2.2, 2.5, 5.2)** - можно объединить в свойства о надёжном доступе к page.

**Группа 4: Модальное окно (2.1, 2.3, 2.4, 5.1, 5.3, 5.4)** - можно разделить на свойства и примеры.

### Correctness Properties

Property 1: Realistic width estimation
*For any* indicator in the legend, its estimated width should be between 30px and 60px, reflecting realistic text and visual element sizes
**Validates: Requirements 1.2, 3.1, 3.2, 3.3**

Property 2: Accurate total width calculation
*For any* set of indicators, the calculated total width should equal the sum of individual widths plus spacing (20px between elements) plus padding (40px)
**Validates: Requirements 1.5, 3.4**

Property 3: Width-based display mode selection
*For any* calendar width of 500px or greater, the legend should display all indicators in full mode without the "Details" button
**Validates: Requirements 1.1, 1.4**

Property 4: Text length consideration in width estimation
*For any* indicator with a longer text label, its estimated width should be proportionally larger than indicators with shorter labels
**Validates: Requirements 1.3, 3.5**

Property 5: Responsive display mode updates
*For any* change in calendar width that crosses the threshold (500px), the legend should update its display mode accordingly
**Validates: Requirements 4.3**

Property 6: Page object access reliability
*For any* attempt to access the page object, the system should try multiple strategies and handle failures gracefully without throwing exceptions
**Validates: Requirements 2.2, 2.5**

Property 7: Modal dialog stability
*For any* modal dialog operation (open/close), the system should complete successfully or fail gracefully without crashing the application
**Validates: Requirements 5.1, 5.5**

Property 8: Fallback behavior consistency
*For any* error in width calculation or page access, the system should use consistent fallback values and continue operating
**Validates: Requirements 4.2, 4.5**

Property 9: Error handling robustness
*For any* error condition (missing page, calculation failure, modal issues), the system should log the error and continue functioning
**Validates: Requirements 2.5, 5.5**

## Error Handling

### Enhanced Page Access Strategy

```python
def get_page_with_multiple_strategies(self, event_or_control=None) -> Optional[ft.Page]:
    """
    Множественные стратегии получения page объекта.
    """
    strategies = [
        lambda: self._get_page_from_event(event_or_control),
        lambda: self._get_page_from_cache(),
        lambda: self._get_page_from_component(),
        lambda: self._get_page_from_parent(),
    ]
    
    for i, strategy in enumerate(strategies):
        try:
            page = strategy()
            if page:
                logger.debug(f"Page объект получен через стратегию {i+1}")
                self._cache_page(page)  # Кэшируем для будущего использования
                return page
        except Exception as e:
            logger.debug(f"Стратегия {i+1} не сработала: {e}")
            continue
    
    logger.warning("Не удалось получить page объект ни одной из стратегий")
    return None
```

### Width Calculation Error Handling

```python
def calculate_width_with_fallback(self) -> WidthCalculationResult:
    """
    Вычисление ширины с обработкой ошибок и fallback.
    """
    try:
        # Попытка точного вычисления
        individual_widths = {}
        for indicator in self.all_indicators:
            individual_widths[indicator.type] = self._calculate_precise_width(indicator)
        
        total = sum(individual_widths.values())
        spacing = (len(self.all_indicators) - 1) * 20
        padding = 40
        
        return WidthCalculationResult(
            total_width=total + spacing + padding,
            individual_widths=individual_widths,
            spacing_width=spacing,
            padding_width=padding,
            is_accurate=True
        )
        
    except Exception as e:
        logger.error(f"Ошибка при точном вычислении ширины: {e}")
        
        # Fallback к безопасным значениям
        fallback_width = len(self.all_indicators) * 45 + (len(self.all_indicators) - 1) * 20 + 40
        
        return WidthCalculationResult(
            total_width=fallback_width,
            individual_widths={},
            spacing_width=(len(self.all_indicators) - 1) * 20,
            padding_width=40,
            is_accurate=False
        )
```

### Modal Dialog Error Recovery

```python
def open_modal_with_recovery(self, event) -> bool:
    """
    Открытие модального окна с восстановлением после ошибок.
    """
    try:
        page = self.page_manager.get_page(event)
        if not page:
            # Попытка альтернативного способа получения page
            page = self._try_alternative_page_access()
        
        if not page:
            logger.warning("Модальное окно не может быть открыто: page недоступен")
            self._show_fallback_notification()
            return False
        
        # Проверяем, что модальное окно создано
        if not self.modal_manager.dialog:
            self.modal_manager.create_modal(self.all_indicators)
        
        return self.modal_manager.open_modal(page)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при открытии модального окна: {e}")
        self._show_error_notification()
        return False
```

## Testing Strategy

### Dual Testing Approach

**Unit Tests:**
- Тестирование новых вычислений ширины
- Проверка стратегий доступа к page объекту
- Тестирование fallback поведения
- Проверка обработки ошибок

**Property-Based Tests:**
- Тестирование реалистичности оценок ширины с различными индикаторами
- Проверка корректности логики отображения с различными ширинами календаря
- Тестирование стабильности модального окна с различными условиями
- Проверка надёжности доступа к page объекту

### Property Test Configuration

**Минимум 100 итераций** для каждого property теста с использованием библиотеки Hypothesis.

**Теги для property тестов:**
- **Feature: calendar-legend-width-fix, Property 1**: Realistic width estimation
- **Feature: calendar-legend-width-fix, Property 2**: Accurate total width calculation
- **Feature: calendar-legend-width-fix, Property 3**: Width-based display mode selection
- И так далее для всех 9 свойств

### Test Data Generators

```python
from hypothesis import strategies as st

# Генераторы для тестирования исправлений
calendar_widths = st.integers(min_value=300, max_value=1200)
indicator_labels = st.text(min_size=3, max_size=12, alphabet=st.characters(whitelist_categories=['L']))
realistic_widths = st.integers(min_value=30, max_value=60)

# Генератор для page объектов (mock)
page_availability = st.booleans()
page_access_scenarios = st.sampled_from([
    'event_has_page',
    'event_control_has_page', 
    'component_has_page',
    'no_page_available'
])
```

### Integration Testing

**Сценарии интеграционного тестирования:**
1. **Полный цикл с исправленными ширинами** - создание легенды, проверка режима отображения
2. **Работа кнопки "Подробнее"** - клик, открытие модального окна, закрытие
3. **Адаптивное поведение** - изменение ширины календаря, обновление режима
4. **Обработка ошибок** - симуляция различных ошибочных условий

### Performance Testing

**Проверка производительности исправлений:**
- Время вычисления ширины не должно превышать 1ms
- Открытие модального окна не должно превышать 100ms
- Обновление режима отображения не должно превышать 50ms

## Implementation Plan

### Phase 1: Width Calculation Fixes
1. Обновить INDICATOR_CONFIGS с реалистичными оценками ширины
2. Добавить WidthCalculator для точных вычислений
3. Обновить логику _calculate_required_width()

### Phase 2: Page Access Improvements  
1. Создать PageAccessManager с множественными стратегиями
2. Обновить _safe_get_page() для использования новых стратегий
3. Добавить кэширование page объекта

### Phase 3: Modal Dialog Stability
1. Улучшить обработку ошибок в ModalManager
2. Добавить fallback уведомления при недоступности модального окна
3. Улучшить логирование для отладки

### Phase 4: Testing and Validation
1. Создать comprehensive test suite
2. Провести интеграционное тестирование
3. Валидировать исправления в реальном приложении

### Expected Results

**После исправлений:**
- Требуемая ширина: ~525px (было 670px)
- Полная легенда при ширине календаря ≥ 500px
- Работающая кнопка "Подробнее" в 95%+ случаев
- Стабильная работа модального окна
- Подробное логирование для диагностики проблем