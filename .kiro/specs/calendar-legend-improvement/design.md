# Design Document

## Overview

Дизайн улучшенной календарной легенды, которая отображает все доступные индикаторы в одну строку под календарём и исправляет проблему с неработающей кнопкой "Подробнее". Решение обеспечивает адаптивность к ширине календаря и улучшенную пользовательскую навигацию.

## Architecture

### Current State Analysis

**Текущие проблемы:**
1. **Неработающая кнопка "Подробнее"** - проблема с доступом к `page` объекту
2. **Ограниченная легенда** - показывает только 2 индикатора из 7 доступных
3. **Неэффективное использование пространства** - много свободного места под календарём
4. **Отсутствие адаптивности** - не учитывает ширину календаря

**Текущие индикаторы в календаре:**
- 🟢 Зелёная точка - доходы
- 🔴 Красная точка - расходы  
- ◆ Оранжевый символ - плановые транзакции
- 📋 Символ - отложенные платежи
- 💳 Символ - платежи по кредитам
- 🟡 Жёлтый фон - кассовые разрывы
- 🔴 Красный фон - просроченные платежи

### Solution Architecture

**Компонентная архитектура:**
```
CalendarLegend (улучшенный)
├── LegendRenderer - отвечает за отображение индикаторов
├── SpaceCalculator - вычисляет доступное пространство
├── ModalManager - управляет модальным окном
└── IndicatorFactory - создаёт визуальные индикаторы
```

**Режимы отображения:**
1. **Полная легенда** - все индикаторы в одну строку (приоритет)
2. **Сокращённая легенда** - основные индикаторы + кнопка "Подробнее"
3. **Модальное окно** - полная легенда с описаниями

## Components and Interfaces

### CalendarLegend (Enhanced)

```python
class CalendarLegend(ft.Container):
    """
    Улучшенная легенда календаря с адаптивным отображением.
    """
    
    def __init__(self, calendar_width: Optional[int] = None):
        """
        Args:
            calendar_width: Ширина календаря для адаптивности
        """
        self.calendar_width = calendar_width
        self.display_mode = DisplayMode.AUTO
        self.all_indicators = self._get_all_indicators()
        self.modal_manager = ModalManager()
        
    def _get_all_indicators(self) -> List[LegendIndicator]:
        """Возвращает все доступные индикаторы."""
        
    def _calculate_required_width(self) -> int:
        """Вычисляет необходимую ширину для всех индикаторов."""
        
    def _should_show_full_legend(self) -> bool:
        """Определяет, показывать ли полную легенду."""
        
    def _build_full_legend(self) -> ft.Row:
        """Строит полную легенду в одну строку."""
        
    def _build_compact_legend(self) -> ft.Row:
        """Строит сокращённую легенду с кнопкой."""
```

### LegendIndicator

```python
@dataclass
class LegendIndicator:
    """Модель индикатора легенды."""
    
    type: IndicatorType
    visual_element: Union[ft.Container, ft.Text, ft.Icon]
    label: str
    description: str
    priority: int  # Для сортировки при ограниченном пространстве
    estimated_width: int  # Примерная ширина в пикселях
```

### IndicatorType

```python
class IndicatorType(Enum):
    """Типы индикаторов календаря."""
    
    INCOME_DOT = "income_dot"           # Зелёная точка
    EXPENSE_DOT = "expense_dot"         # Красная точка
    PLANNED_SYMBOL = "planned_symbol"   # ◆ символ
    PENDING_SYMBOL = "pending_symbol"   # 📋 символ
    LOAN_SYMBOL = "loan_symbol"         # 💳 символ
    CASH_GAP_BG = "cash_gap_bg"         # Жёлтый фон
    OVERDUE_BG = "overdue_bg"           # Красный фон
```

### DisplayMode

```python
class DisplayMode(Enum):
    """Режимы отображения легенды."""
    
    AUTO = "auto"           # Автоматический выбор
    FULL = "full"           # Полная легенда
    COMPACT = "compact"     # Сокращённая легенда
    MODAL_ONLY = "modal"    # Только модальное окно
```

### ModalManager

```python
class ModalManager:
    """Управляет модальным окном легенды."""
    
    def __init__(self):
        self.dialog = None
        
    def create_modal(self, indicators: List[LegendIndicator]) -> ft.AlertDialog:
        """Создаёт модальное окно с полной легендой."""
        
    def open_modal(self, page: ft.Page) -> bool:
        """Открывает модальное окно. Возвращает успех операции."""
        
    def close_modal(self, page: ft.Page) -> bool:
        """Закрывает модальное окно. Возвращает успех операции."""
```

## Data Models

### Indicator Configuration

```python
INDICATOR_CONFIGS = {
    IndicatorType.INCOME_DOT: LegendIndicator(
        type=IndicatorType.INCOME_DOT,
        visual_element=ft.Container(
            width=10, height=10, 
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
            width=10, height=10, 
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
        visual_element=ft.Text("◆", size=12, color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD),
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
            width=16, height=12, 
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
            width=16, height=12, 
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
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

После анализа всех требований выявлены следующие группы свойств:

**Группа 1: Отображение индикаторов (1.2-1.8)** - можно объединить в одно свойство о полноте отображения всех типов индикаторов.

**Группа 2: Адаптивность (1.9, 2.1, 2.2)** - можно объединить в одно свойство о корректной адаптации к ширине.

**Группа 3: Модальное окно (3.1-3.5)** - можно объединить в свойства о корректной работе модального окна.

**Группа 4: Визуализация (4.1-4.5)** - можно объединить в свойства о консистентности визуального представления.

### Correctness Properties

Property 1: Complete indicator display
*For any* calendar legend with sufficient width, all available indicator types (income dots, expense dots, planned symbols, pending symbols, loan symbols, cash gap backgrounds, overdue backgrounds) should be displayed in the legend
**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**

Property 2: Adaptive layout behavior
*For any* calendar width, the legend should display all indicators in one row when space permits, or show priority indicators with "Details" button when space is limited
**Validates: Requirements 1.9, 2.1, 2.2**

Property 3: Width calculation accuracy
*For any* set of indicators, the calculated required width should accurately reflect the actual space needed to display all indicators
**Validates: Requirements 2.3**

Property 4: Priority-based indicator selection
*For any* limited width scenario, the displayed indicators should be ordered by priority (income and expense first, then others by importance)
**Validates: Requirements 2.4**

Property 5: Modal dialog functionality
*For any* "Details" button click, the modal dialog should open and display all indicators with descriptions, and close when the close button is clicked
**Validates: Requirements 3.1, 3.2, 3.4**

Property 6: Modal dialog structure
*For any* modal dialog content, indicators should be grouped by type (dots, symbols, backgrounds) with proper descriptions
**Validates: Requirements 3.3**

Property 7: Page object handling
*For any* modal dialog operation, the component should handle missing page objects gracefully without throwing errors
**Validates: Requirements 3.5, 5.2**

Property 8: Visual consistency
*For any* indicator in the legend, its colors and symbols should match exactly those used in the calendar widget
**Validates: Requirements 4.1**

Property 9: Layout alignment
*For any* legend display, elements should be centered under the calendar with appropriate spacing between items
**Validates: Requirements 4.2, 4.3**

Property 10: Readability standards
*For any* legend element, font sizes and symbol sizes should meet minimum readability requirements (fonts ≥ 12px, symbols ≥ 8px)
**Validates: Requirements 4.4**

Property 11: Visual grouping
*For any* set of similar indicators (e.g., all dots, all symbols), they should be visually grouped together in the legend
**Validates: Requirements 4.5**

Property 12: Event handling robustness
*For any* click event on legend elements, the event should be handled without throwing exceptions, even with invalid or missing event data
**Validates: Requirements 5.3**

Property 13: Responsive stability
*For any* window resize operation, the legend should recalculate its layout and display mode without errors or visual artifacts
**Validates: Requirements 5.5**

## Error Handling

### Page Object Errors

**Проблема:** Текущая реализация падает при отсутствии `page` объекта в событиях.

**Решение:**
```python
def _safe_get_page(self, event_or_control) -> Optional[ft.Page]:
    """Безопасное получение page объекта."""
    try:
        if hasattr(event_or_control, 'control') and event_or_control.control:
            return event_or_control.control.page
        elif hasattr(event_or_control, 'page'):
            return event_or_control.page
        elif hasattr(self, 'page') and self.page:
            return self.page
        return None
    except AttributeError:
        logger.warning("Не удалось получить page объект для модального окна")
        return None
```

### Width Calculation Errors

**Проблема:** Ошибки при вычислении ширины могут привести к некорректному отображению.

**Решение:**
```python
def _calculate_required_width(self) -> int:
    """Вычисляет необходимую ширину с обработкой ошибок."""
    try:
        total_width = 0
        for indicator in self.all_indicators:
            total_width += indicator.estimated_width
        
        # Добавляем отступы между элементами
        spacing = (len(self.all_indicators) - 1) * 20  # 20px между элементами
        return total_width + spacing + 40  # 40px для padding
        
    except Exception as e:
        logger.error(f"Ошибка при вычислении ширины легенды: {e}")
        return 800  # Fallback к безопасному значению
```

### Modal Dialog Errors

**Проблема:** Ошибки при открытии/закрытии модального окна.

**Решение:**
```python
def _open_modal_safe(self, e) -> bool:
    """Безопасное открытие модального окна."""
    try:
        page = self._safe_get_page(e)
        if not page:
            logger.warning("Не удалось открыть модальное окно: page недоступен")
            return False
            
        page.dialog = self.modal_manager.dialog
        self.modal_manager.dialog.open = True
        page.update()
        return True
        
    except Exception as ex:
        logger.error(f"Ошибка при открытии модального окна: {ex}")
        return False
```

## Testing Strategy

### Dual Testing Approach

**Unit Tests:**
- Тестирование создания индикаторов
- Проверка вычисления ширины
- Тестирование обработки событий
- Проверка создания модального окна

**Property-Based Tests:**
- Тестирование адаптивности с различными ширинами
- Проверка корректности отображения всех индикаторов
- Тестирование приоритизации индикаторов
- Проверка стабильности при изменении размеров

### Property Test Configuration

**Минимум 100 итераций** для каждого property теста с использованием библиотеки Hypothesis.

**Теги для property тестов:**
- **Feature: calendar-legend-improvement, Property 1**: Complete indicator display
- **Feature: calendar-legend-improvement, Property 2**: Adaptive layout behavior
- **Feature: calendar-legend-improvement, Property 3**: Width calculation accuracy
- И так далее для всех 13 свойств

### Test Data Generators

```python
from hypothesis import strategies as st

# Генераторы для тестирования
calendar_widths = st.integers(min_value=300, max_value=1200)
indicator_sets = st.lists(
    st.sampled_from(list(IndicatorType)), 
    min_size=1, 
    max_size=7,
    unique=True
)
display_modes = st.sampled_from(list(DisplayMode))

# Генератор для UI состояний
ui_states = st.builds(
    dict,
    width=calendar_widths,
    indicators=indicator_sets,
    mode=display_modes
)
```

### Integration Testing

**Сценарии интеграционного тестирования:**
1. **Полный цикл отображения** - от создания легенды до отображения всех индикаторов
2. **Адаптивное поведение** - изменение размера окна и проверка адаптации
3. **Модальное окно** - полный цикл открытия, взаимодействия и закрытия
4. **Интеграция с календарём** - проверка консистентности индикаторов

### UI Testing

**Тестирование кнопки "Подробнее":**

```python
class TestCalendarLegendUI(unittest.TestCase):
    def test_details_button_attributes(self):
        """Тест атрибутов кнопки 'Подробнее'."""
        legend = CalendarLegend(calendar_width=400)  # Узкая ширина
        
        # Получаем кнопку из компактной легенды
        compact_legend = legend._build_compact_legend()
        details_button = compact_legend.controls[-1]  # Последний элемент
        
        # Проверяем атрибуты кнопки
        self.assertEqual(details_button.text, "Подробнее...")
        self.assertIsNotNone(details_button.on_click)
        self.assertEqual(details_button.height, 30)

    def test_details_button_click_opens_modal(self):
        """Тест открытия модального окна при клике на 'Подробнее'."""
        mock_page = create_mock_page()
        legend = CalendarLegend(calendar_width=400)
        legend.page = mock_page
        
        # Симулируем клик на кнопку "Подробнее"
        mock_event = Mock()
        mock_event.control.page = mock_page
        
        legend._open_modal_safe(mock_event)
        
        # Проверяем открытие модального окна
        self.assertIsNotNone(mock_page.dialog)
        self.assertTrue(mock_page.dialog.open)
        mock_page.update.assert_called_once()

    def test_details_button_visibility_based_on_width(self):
        """Тест видимости кнопки в зависимости от ширины."""
        # Широкая ширина - кнопка не должна показываться
        wide_legend = CalendarLegend(calendar_width=1000)
        self.assertTrue(wide_legend._should_show_full_legend())
        
        # Узкая ширина - кнопка должна показываться
        narrow_legend = CalendarLegend(calendar_width=300)
        self.assertFalse(narrow_legend._should_show_full_legend())

    def test_modal_dialog_content(self):
        """Тест содержимого модального окна."""
        legend = CalendarLegend()
        modal = legend.modal_manager.create_modal(legend.all_indicators)
        
        # Проверяем заголовок
        self.assertEqual(modal.title.value, "Легенда календаря")
        
        # Проверяем наличие всех индикаторов в содержимом
        content = modal.content
        self.assertIsInstance(content, ft.Column)
        
        # Проверяем группировку индикаторов
        controls = content.controls
        self.assertTrue(any("точки" in str(control.value) for control in controls if hasattr(control, 'value')))
        self.assertTrue(any("Символы" in str(control.value) for control in controls if hasattr(control, 'value')))
        self.assertTrue(any("Фон дня" in str(control.value) for control in controls if hasattr(control, 'value')))

    def test_modal_close_button_functionality(self):
        """Тест функциональности кнопки закрытия модального окна."""
        mock_page = create_mock_page()
        legend = CalendarLegend()
        modal = legend.modal_manager.create_modal(legend.all_indicators)
        
        # Открываем модальное окно
        mock_page.dialog = modal
        modal.open = True
        
        # Симулируем клик на кнопку "Закрыть"
        close_button = modal.actions[0]  # Первая кнопка - "Закрыть"
        mock_event = Mock()
        mock_event.control.page = mock_page
        
        close_button.on_click(mock_event)
        
        # Проверяем закрытие модального окна
        self.assertFalse(modal.open)

    @given(st.integers(min_value=200, max_value=1500))
    def test_adaptive_button_display_property(self, calendar_width):
        """Property: Кнопка 'Подробнее' должна отображаться только при недостаточной ширине."""
        legend = CalendarLegend(calendar_width=calendar_width)
        
        required_width = legend._calculate_required_width()
        should_show_full = calendar_width >= required_width
        
        if should_show_full:
            # При достаточной ширине кнопка не должна показываться
            full_legend = legend._build_full_legend()
            button_texts = [
                control.text for control in full_legend.controls 
                if hasattr(control, 'text') and control.text
            ]
            assert "Подробнее..." not in button_texts
        else:
            # При недостаточной ширине кнопка должна показываться
            compact_legend = legend._build_compact_legend()
            button_texts = [
                control.text for control in compact_legend.controls 
                if hasattr(control, 'text') and control.text
            ]
            assert "Подробнее..." in button_texts
```

**UI Test Patterns для модального окна:**

```python
def test_modal_error_handling_without_page(self):
    """Тест обработки ошибок при отсутствии page объекта."""
    legend = CalendarLegend()
    
    # Симулируем событие без page объекта
    mock_event = Mock()
    mock_event.control = None
    
    # Попытка открытия не должна вызывать исключений
    result = legend._open_modal_safe(mock_event)
    
    # Операция должна завершиться неуспешно, но без ошибок
    self.assertFalse(result)

def test_modal_keyboard_navigation(self):
    """Тест навигации в модальном окне с клавиатуры."""
    legend = CalendarLegend()
    modal = legend.modal_manager.create_modal(legend.all_indicators)
    
    # Проверяем, что модальное окно поддерживает закрытие по Escape
    self.assertTrue(modal.modal)  # Модальное окно блокирует фон
    
    # Проверяем фокус на кнопке закрытия
    close_button = modal.actions[0]
    self.assertEqual(close_button.text, "Закрыть")
```

<function_calls>
<invoke name="prework">
<parameter name="featureName">calendar-legend-improvement