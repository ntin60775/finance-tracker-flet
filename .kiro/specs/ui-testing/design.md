# Дизайн-документ: UI-тестирование Finance Tracker

## Overview

Система UI-тестирования для Finance Tracker Flet предназначена для автоматической проверки корректности работы пользовательского интерфейса. Основная цель - предотвратить регрессии при изменениях кода путем автоматизации базовых пользовательских сценариев.

Текущая архитектура приложения построена на Flet framework с паттерном View-Service-Repository. Каждый View (экран) является самостоятельным компонентом, который:
- Управляет своей сессией БД через context manager
- Взаимодействует с сервисами для получения/изменения данных
- Содержит модальные окна для создания/редактирования сущностей
- Обрабатывает пользовательские действия через callback-функции

## Architecture

### Архитектура тестирования

Тестовая архитектура следует трехуровневой модели:

1. **Unit-тесты View** - изолированное тестирование отдельных View с моками сервисов
2. **Integration-тесты** - тестирование взаимодействия View с реальными сервисами и БД
3. **Smoke-тесты** - быстрые проверки базовой работоспособности всех компонентов

### Стратегия мокирования

Для изоляции тестов используется многоуровневое мокирование:

**Уровень 1: Мокирование Flet Page**
- `page` объект мокируется через `unittest.mock.MagicMock`
- Позволяет проверять вызовы `page.open()`, `page.update()`, `page.dialog`

**Уровень 2: Мокирование сервисов**
- Все функции сервисов мокируются через `patch()`
- Возвращают предсказуемые тестовые данные
- Позволяют проверить, что View вызывает правильные сервисы с правильными параметрами

**Уровень 3: Мокирование БД (для integration-тестов)**
- Используется in-memory SQLite через фикстуру `db_session`
- Реальная схема БД, но изолированные данные
- Автоматическая очистка после каждого теста

### Паттерн тестирования View

Каждый View тестируется по единому паттерну:

```python
class TestXxxView(unittest.TestCase):
    def setUp(self):
        # 1. Создание моков для всех зависимостей
        # 2. Настройка возвращаемых значений
        # 3. Создание экземпляра View
        
    def tearDown(self):
        # Очистка моков
        
    def test_initialization(self):
        # Проверка корректной инициализации
        
    def test_load_data(self):
        # Проверка загрузки данных
        
    def test_filter_change(self):
        # Проверка фильтрации (если есть)
        
    def test_modal_open(self):
        # Проверка открытия модальных окон
```

## Components and Interfaces

### Тестируемые View компоненты

**HomeView**
- Календарь с транзакциями
- Панель транзакций выбранного дня
- Виджет плановых транзакций
- Виджет отложенных платежей
- Модальные окна: TransactionModal, ExecuteOccurrenceModal, ExecutePendingPaymentModal

**CategoriesView**
- Список категорий с фильтрацией по типу
- Модальное окно CategoryDialog (создание/редактирование)
- Подтверждение удаления

**LendersView**
- Список займодателей с фильтрацией
- Модальное окно LenderModal
- Проверка удаления с активными кредитами

**LoansView**
- Список кредитов с фильтрацией по статусу
- Статистика по кредитам
- Модальное окно LoanModal
- Навигация к LoanDetailsView

**LoanDetailsView**
- Детали кредита
- График платежей
- Модальное окно досрочного погашения
- Кнопка "Назад"

**PendingPaymentsView**
- Список отложенных платежей
- Статистика
- Действия: выполнить, отменить, удалить

**PlannedTransactionsView**
- Список плановых транзакций с фильтрацией
- Модальное окно PlannedTransactionModal
- CRUD операции

**PlanFactView**
- План-факт анализ
- Фильтры: период, категория
- Расчет отклонений

**SettingsView**
- Управление настройками
- Изменение темы
- Изменение размеров окна
- Сброс настроек

**MainWindow**
- Навигационное меню
- Переключение между View

### Интерфейсы тестирования

**Базовый интерфейс теста View:**
```python
class ViewTestBase:
    """Базовый класс для тестов View."""
    
    def create_mock_page(self) -> MagicMock:
        """Создание мока page."""
        
    def create_mock_session(self) -> Mock:
        """Создание мока сессии БД."""
        
    def assert_service_called(self, mock_service, *args):
        """Проверка вызова сервиса."""
        
    def assert_modal_opened(self, page_mock, modal_type):
        """Проверка открытия модального окна."""
```

## Data Models

### Тестовые данные

Для тестов используются фабрики тестовых данных:

**CategoryFactory**
```python
def create_test_category(
    id: int = 1,
    name: str = "Тестовая категория",
    type: TransactionType = TransactionType.EXPENSE,
    is_system: bool = False
) -> CategoryDB
```

**TransactionFactory**
```python
def create_test_transaction(
    id: int = 1,
    date: datetime.date = None,
    amount: Decimal = Decimal("100.00"),
    category_id: int = 1,
    description: str = "Тест"
) -> TransactionDB
```

**LoanFactory**
```python
def create_test_loan(
    id: int = 1,
    name: str = "Тестовый кредит",
    principal: Decimal = Decimal("100000"),
    interest_rate: Decimal = Decimal("10.5"),
    status: LoanStatus = LoanStatus.ACTIVE
) -> LoanDB
```

### Структура тестовых данных

Тестовые данные организованы по принципу:
- **Минимальные валидные данные** - для smoke-тестов
- **Граничные значения** - для проверки edge cases
- **Невалидные данные** - для проверки обработки ошибок

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptance Criteria Testing Prework

1.1 WHEN каждый View создается THEN он SHALL инициализироваться без исключений
Thoughts: Это базовая проверка, что View может быть создан. Мы можем создать каждый View с моками и проверить, что не возникло исключений.
Testable: yes - example

1.2 WHEN каждый View создается THEN все обязательные атрибуты (page, session) SHALL быть установлены
Thoughts: Это проверка инвариантов после создания. Для любого View после создания должны быть установлены page и session.
Testable: yes - property

1.3 WHEN каждый View создается THEN основные UI компоненты (заголовок, контейнеры) SHALL быть созданы
Thoughts: Это проверка структуры UI. Для любого View должны существовать основные компоненты.
Testable: yes - property

1.4 WHEN тест запускается THEN он SHALL выполняться быстро (менее 1 секунды на View)
Thoughts: Это проверка производительности, не функциональное требование.
Testable: no

2.1 WHEN View инициализируется THEN соответствующие сервисы загрузки данных SHALL быть вызваны
Thoughts: Для любого View при инициализации должны вызываться определенные сервисы. Это можно проверить через моки.
Testable: yes - property

2.2 WHEN View получает данные THEN UI компоненты SHALL быть обновлены
Thoughts: Это проверка, что после загрузки данных UI отражает эти данные. Можно проверить через моки.
Testable: yes - property

2.3 WHEN View получает пустой список данных THEN SHALL отображаться сообщение о пустом состоянии
Thoughts: Это edge case - проверка поведения при пустых данных.
Testable: edge-case

2.4 WHEN сервис возвращает ошибку THEN View SHALL обработать её корректно
Thoughts: Это edge case - проверка обработки ошибок.
Testable: edge-case

3.1 WHEN пользователь меняет фильтр THEN данные SHALL быть перезагружены с новым фильтром
Thoughts: Для любого View с фильтрами, изменение фильтра должно вызывать перезагрузку. Можно проверить через моки.
Testable: yes - property

3.2 WHEN фильтр установлен на "Все" THEN данные SHALL загружаться без фильтрации
Thoughts: Это конкретный пример поведения фильтра.
Testable: yes - example

3.3 WHEN фильтр меняется THEN UI SHALL обновиться с новыми данными
Thoughts: Это следствие 3.1, проверяет что UI отражает новые данные.
Testable: yes - property

3.4 WHEN фильтр применяется к пустому списку THEN SHALL отображаться сообщение о пустом состоянии
Thoughts: Edge case - фильтрация пустых данных.
Testable: edge-case

4.1 WHEN пользователь нажимает кнопку создания THEN модальное окно SHALL открыться в режиме создания
Thoughts: Для любого View с модальными окнами, нажатие кнопки создания должно открывать модалку. Можно проверить через моки page.open().
Testable: yes - property

4.2 WHEN пользователь нажимает кнопку редактирования THEN модальное окно SHALL открыться в режиме редактирования с данными объекта
Thoughts: Для любого View с редактированием, должна открываться модалка с данными. Можно проверить через моки.
Testable: yes - property

4.3 WHEN модальное окно открывается THEN все поля SHALL быть инициализированы корректно
Thoughts: Это проверка инвариантов модального окна. Для любой модалки поля должны быть инициализированы.
Testable: yes - property

4.4 WHEN модальное окно закрывается THEN View SHALL обновить данные
Thoughts: После закрытия модалки View должен перезагрузить данные. Можно проверить через моки.
Testable: yes - property

5.1 WHEN пользователь кликает на пункт меню THEN соответствующий View SHALL открыться
Thoughts: Для любого пункта меню должен открываться соответствующий View. Это можно проверить через навигацию.
Testable: yes - property

5.2 WHEN View открывается через меню THEN он SHALL инициализироваться корректно
Thoughts: Это следствие 1.1 и 1.2 - View должен корректно инициализироваться.
Testable: yes - property

5.3 WHEN происходит переход между View THEN предыдущий View SHALL корректно закрыться
Thoughts: При навигации должна вызываться will_unmount и закрываться сессия.
Testable: yes - property

5.4 WHEN открывается каждый пункт меню THEN приложение SHALL работать без ошибок
Thoughts: Это smoke test - проверка, что все пункты меню работают.
Testable: yes - example

6.1-6.5, 7.1-7.5, 8.1-8.5, 9.1-9.5, 10.1-10.5, 11.1-11.5, 12.1-12.5, 13.1-13.5, 14.1-14.5
Thoughts: Эти критерии специфичны для конкретных View. Они являются примерами применения общих свойств (загрузка данных, фильтрация, модальные окна) к конкретным экранам.
Testable: yes - example (для каждого View)

### Property Reflection

Анализируя выявленные свойства, можно выделить следующие группы:

**Группа 1: Инициализация View**
- Property 1.2 (атрибуты установлены) и Property 1.3 (компоненты созданы) можно объединить в одно свойство "View корректно инициализирован"

**Группа 2: Загрузка данных**
- Property 2.1 (сервисы вызваны) и Property 2.2 (UI обновлен) - это последовательные шаги одного процесса, но проверяют разные аспекты

**Группа 3: Фильтрация**
- Property 3.1 (перезагрузка с фильтром) и Property 3.3 (UI обновлен) - Property 3.3 является следствием 3.1, можно объединить

**Группа 4: Модальные окна**
- Property 4.1 (открытие создания) и Property 4.2 (открытие редактирования) - разные режимы, нужны оба
- Property 4.3 (поля инициализированы) - часть проверки 4.1 и 4.2
- Property 4.4 (обновление после закрытия) - отдельный аспект

**Группа 5: Навигация**
- Property 5.1 (открытие View) и Property 5.2 (корректная инициализация) - Property 5.2 дублирует Property 1.2/1.3

После рефлексии оставляем следующие уникальные свойства:

### Correctness Properties

**Property 1: View инициализация**
*For any* View, при создании с валидными page и session, View должен инициализироваться без исключений и иметь установленные атрибуты page, session и основные UI компоненты.
**Validates: Requirements 1.1, 1.2, 1.3**

**Property 2: Загрузка данных при инициализации**
*For any* View с загрузкой данных, при инициализации должны быть вызваны соответствующие сервисы загрузки данных.
**Validates: Requirements 2.1**

**Property 3: Обновление UI после загрузки данных**
*For any* View, после успешной загрузки данных UI компоненты должны отражать загруженные данные.
**Validates: Requirements 2.2**

**Property 4: Фильтрация данных**
*For any* View с фильтрами, изменение фильтра должно вызывать перезагрузку данных с новым фильтром и обновление UI.
**Validates: Requirements 3.1, 3.3**

**Property 5: Открытие модального окна создания**
*For any* View с функцией создания, нажатие кнопки создания должно открывать модальное окно в режиме создания с корректно инициализированными полями.
**Validates: Requirements 4.1, 4.3**

**Property 6: Открытие модального окна редактирования**
*For any* View с функцией редактирования, нажатие кнопки редактирования должно открывать модальное окно в режиме редактирования с данными выбранного объекта.
**Validates: Requirements 4.2, 4.3**

**Property 7: Обновление данных после закрытия модального окна**
*For any* View с модальными окнами, после закрытия модального окна View должен перезагрузить данные.
**Validates: Requirements 4.4**

**Property 8: Навигация между View**
*For any* пункта меню, клик на пункт меню должен открывать соответствующий View с корректной инициализацией.
**Validates: Requirements 5.1, 5.2**

**Property 9: Закрытие View при навигации**
*For any* View, при переходе к другому View должен вызываться will_unmount и корректно закрываться сессия БД.
**Validates: Requirements 5.3**

## Error Handling

### Стратегия обработки ошибок в тестах

**Ожидаемые ошибки:**
- Ошибки валидации данных (пустые поля, некорректные форматы)
- Ошибки БД (нарушение constraints, отсутствие записей)
- Ошибки бизнес-логики (удаление займодателя с активными кредитами)

**Обработка в тестах:**
```python
def test_error_handling(self):
    # Настраиваем мок для возврата ошибки
    self.mock_service.side_effect = ValueError("Test error")
    
    # Вызываем метод
    self.view.load_data()
    
    # Пр��веряем, что ошибка обработана
    self.page.open.assert_called()  # SnackBar с ошибкой
    # Проверяем логирование
    self.mock_logger.error.assert_called()
```

**Edge cases:**
- Пустые списки данных
- Отсутствие обязательных связей (категория удалена, но есть транзакции)
- Некорректные даты (будущие даты для транзакций)
- Граничные значения (очень большие суммы, отрицательные значения)

## Testing Strategy

### Dual Testing Approach

Используется комбинированный подход:

**Unit-тесты:**
- Изолированное тестирование каждого View
- Мокирование всех зависимостей (сервисы, БД, page)
- Быстрое выполнение (< 1 сек на тест)
- Фокус на логике View (вызовы сервисов, обработка событий)

**Property-based тесты:**
- Проверка универсальных свойств на множестве входных данных
- Использование библиотеки Hypothesis для Python
- Генерация случайных, но валидных тестовых данных
- Минимум 100 итераций на каждое свойство

### Property-Based Testing Configuration

**Библиотека:** Hypothesis (https://hypothesis.readthedocs.io/)

**Конфигурация:**
```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(
    view_name=st.sampled_from(['HomeView', 'CategoriesView', 'LoansView']),
    page=st.builds(create_mock_page),
    session=st.builds(create_mock_session)
)
def test_view_initialization_property(view_name, page, session):
    """
    Feature: ui-testing, Property 1: View инициализация
    Validates: Requirements 1.1, 1.2, 1.3
    """
    view_class = get_view_class(view_name)
    view = view_class(page)
    
    assert view.page is page
    assert view.session is not None
    assert len(view.controls) > 0
```

**Стратегии генерации данных:**
```python
# Генерация категорий
categories_strategy = st.builds(
    CategoryDB,
    id=st.integers(min_value=1),
    name=st.text(min_size=1, max_size=50),
    type=st.sampled_from([TransactionType.EXPENSE, TransactionType.INCOME]),
    is_system=st.booleans()
)

# Генерация транзакций
transactions_strategy = st.builds(
    TransactionDB,
    id=st.integers(min_value=1),
    date=st.dates(min_value=datetime.date(2020, 1, 1)),
    amount=st.decimals(min_value=0.01, max_value=1000000, places=2),
    category_id=st.integers(min_value=1),
    description=st.text(max_size=200)
)
```

### Test Organization

**Структура тестов:**
```
tests/
├── conftest.py                          # Общие фикстуры
├── test_factories.py                    # Фабрики тестовых данных
├── test_view_base.py                    # Базовый класс для тестов View
├── test_home_view.py                    # Unit-тесты HomeView
├── test_categories_view.py              # Unit-тесты CategoriesView
├── test_lenders_view.py                 # Unit-тесты LendersView
├── test_loans_view.py                   # Unit-тесты LoansView
├── test_loan_details_view.py            # Unit-тесты LoanDetailsView
├── test_pending_payments_view.py        # Unit-тесты PendingPaymentsView
├── test_planned_transactions_view.py    # Unit-тесты PlannedTransactionsView
├── test_plan_fact_view.py               # Unit-тесты PlanFactView
├── test_settings_view.py                # Unit-тесты SettingsView
├── test_main_window.py                  # Unit-тесты MainWindow
└── test_view_properties.py              # Property-based тесты для всех View
```

### Test Execution

**Запуск всех тестов:**
```bash
pytest tests/
```

**Запуск только unit-тестов:**
```bash
pytest tests/ -k "not property"
```

**Запуск только property-based тестов:**
```bash
pytest tests/test_view_properties.py
```

**Запуск с покрытием:**
```bash
pytest tests/ --cov=src/finance_tracker/views --cov-report=html
```

### Success Criteria

**Минимальные требования:**
- Все smoke-тесты проходят (инициализация View без ошибок)
- Покрытие кода View >= 80%
- Все property-based тесты проходят 100 итераций без ошибок
- Время выполнения всех тестов < 30 секунд

**Желаемые требования:**
- Покрытие кода View >= 90%
- Все edge cases покрыты тестами
- Integration-тесты для критических сценариев (создание транзакции, исполнение кредитного платежа)

## Implementation Notes

### Особенности тестирования Flet

**Проблема:** Flet использует асинхронную модель обновления UI, что усложняет тестирование.

**Решение:** 
- Мокирование `page.update()` и проверка его вызовов
- Синхронное тестирование логики View без реального рендеринга
- Фокус на проверке вызовов методов, а не визуального состояния

**Проблема:** Некоторые View создают persistent сессии БД через context manager.

**Решение:**
- Мокирование `get_db_session()` для возврата мок-сессии
- Проверка вызова `__enter__` и `__exit__` для контроля жизненного цикла сессии
- В integration-тестах использование реальной in-memory БД

**Проблема:** Модальные окна открываются через `page.open(dialog)`.

**Решение:**
- Проверка вызова `page.open()` с правильным типом диалога
- Мокирование диалогов для изоляции тестов View
- Отдельные тесты для самих модальных окон

### Рекомендации по написанию тестов

1. **Изолируйте тесты:** Каждый тест должен быть независимым и не влиять на другие
2. **Используйте фабрики:** Создавайте тестовые данные через фабрики для консистентности
3. **Проверяйте поведение, а не реализацию:** Тестируйте что делает View, а не как
4. **Тестируйте edge cases:** Пустые списки, ошибки сервисов, некорректные данные
5. **Документируйте тесты:** Каждый тест должен иметь docstring с описанием проверяемого сценария
6. **Используйте осмысленные имена:** `test_categories_view_loads_data_on_init` лучше чем `test_1`

### Интеграция с CI/CD

Тесты должны запускаться автоматически при:
- Каждом push в репозиторий
- Создании pull request
- Перед релизом

Конфигурация для GitHub Actions:
```yaml
name: UI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov hypothesis
      - name: Run tests
        run: pytest tests/ --cov=src/finance_tracker/views --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```
