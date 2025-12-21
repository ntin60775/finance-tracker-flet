# Design Document: Миграция на современный Flet Dialog API

## Overview

Данный документ описывает дизайн системы автоматической миграции кодовой базы Finance Tracker с устаревшего Flet Dialog API на современный подход через `page.open()` и `page.close()`.

Система включает:
- Статический анализ кода для обнаружения паттернов использования диалогов
- Автоматическую миграцию простых случаев
- Валидацию корректности миграции через запуск тестов
- Обновление steering правил для предотвращения регрессии

## Architecture

### Компоненты системы

```
migration_system/
├── analyzer/              # Статический анализ кода
│   ├── pattern_detector.py    # Обнаружение паттернов API
│   ├── mock_validator.py      # Проверка mock объектов
│   └── complexity_estimator.py # Оценка сложности миграции
├── migrator/              # Автоматическая миграция
│   ├── code_transformer.py    # AST трансформации
│   ├── backup_manager.py      # Управление резервными копиями
│   └── rollback_handler.py    # Откат изменений
├── validator/             # Валидация миграции
│   ├── test_runner.py         # Запуск тестов
│   └── result_analyzer.py     # Анализ результатов
└── reporter/              # Отчётность
    ├── report_generator.py    # Генерация отчётов
    └── ci_integrator.py       # Интеграция с CI/CD
```

### Архитектурные решения

**1. AST-based трансформация вместо regex**
- **Решение:** Использовать Python AST (Abstract Syntax Tree) для анализа и модификации кода
- **Обоснование:** 
  - Regex не может корректно обрабатывать сложные случаи (вложенные вызовы, многострочные выражения)
  - AST гарантирует синтаксическую корректность после трансформации
  - Позволяет точно определить контекст использования API
- **Альтернатива:** Regex замены - отклонена из-за хрупкости и ограниченности

**2. Backup-first подход**
- **Решение:** Создавать резервные копии перед любой модификацией
- **Обоснование:**
  - Безопасность - всегда можно откатить изменения
  - Возможность сравнения до/после миграции
  - Защита от потери данных при ошибках
- **Реализация:** `.backup/` директория с timestamp в именах файлов

**3. Test-driven validation**
- **Решение:** Валидация через запуск полного набора тестов после миграции
- **Обоснование:**
  - Тесты - единственный надёжный способ проверить корректность поведения
  - Автоматическое обнаружение регрессий
  - Объективная метрика успешности миграции
- **Критерий успеха:** Все тесты, проходившие до миграции, должны проходить после


## Components and Interfaces

### 1. Pattern Detector

**Назначение:** Обнаружение паттернов использования Dialog API в коде

**Интерфейс:**
```python
class PatternDetector:
    def analyze_file(self, file_path: str) -> FileAnalysisResult:
        """
        Анализирует файл на наличие паттернов Dialog API.
        
        Args:
            file_path: Путь к анализируемому файлу
            
        Returns:
            FileAnalysisResult с найденными паттернами
        """
        
    def find_legacy_patterns(self, ast_tree: ast.Module) -> List[LegacyPattern]:
        """Находит устаревшие паттерны использования API."""
        
    def find_modern_patterns(self, ast_tree: ast.Module) -> List[ModernPattern]:
        """Находит современные паттерны использования API."""
```

**Обнаруживаемые паттерны:**

*Устаревший API:*
- `page.dialog = dialog_instance`
- `dialog.open = True`
- `dialog.open = False`
- `page.update()` после установки диалога

*Современный API:*
- `page.open(dialog_instance)`
- `page.close(dialog_instance)`

**Структура результата:**
```python
@dataclass
class LegacyPattern:
    pattern_type: str  # "dialog_assignment", "open_assignment", "close_assignment"
    line_number: int
    column: int
    code_snippet: str
    context: str  # Окружающий код для понимания контекста
    
@dataclass
class FileAnalysisResult:
    file_path: str
    file_type: str  # "test" или "production"
    legacy_patterns: List[LegacyPattern]
    modern_patterns: List[ModernPattern]
    complexity: str  # "simple", "medium", "complex"
    requires_migration: bool
```

### 2. Mock Validator

**Назначение:** Проверка mock объектов Page на наличие методов open() и close()

**Интерфейс:**
```python
class MockValidator:
    def validate_page_mocks(self, file_path: str) -> MockValidationResult:
        """
        Проверяет mock объекты Page в тестовом файле.
        
        Args:
            file_path: Путь к тестовому файлу
            
        Returns:
            MockValidationResult с результатами проверки
        """
        
    def find_mock_definitions(self, ast_tree: ast.Module) -> List[MockDefinition]:
        """Находит определения mock объектов для Page."""
        
    def check_mock_methods(self, mock_def: MockDefinition) -> List[str]:
        """Проверяет наличие необходимых методов в mock объекте."""
```

**Проверяемые паттерны:**
- `MagicMock()` без настройки методов
- `Mock()` без настройки методов
- `create_mock_page()` helper функции
- Явная настройка `mock_page.open = Mock()`

**Структура результата:**
```python
@dataclass
class MockDefinition:
    variable_name: str
    line_number: int
    has_open_method: bool
    has_close_method: bool
    mock_type: str  # "MagicMock", "Mock", "custom"
    
@dataclass
class MockValidationResult:
    file_path: str
    mock_definitions: List[MockDefinition]
    invalid_mocks: List[MockDefinition]
    requires_update: bool
```

### 3. Code Transformer

**Назначение:** AST-based трансформация кода для миграции на новый API

**Интерфейс:**
```python
class CodeTransformer(ast.NodeTransformer):
    def transform_file(self, file_path: str) -> TransformationResult:
        """
        Трансформирует файл, заменяя устаревший API на современный.
        
        Args:
            file_path: Путь к файлу для трансформации
            
        Returns:
            TransformationResult с результатами трансформации
        """
        
    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Обрабатывает присваивания (page.dialog = ...)."""
        
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        """Обрабатывает доступ к атрибутам (dialog.open = ...)."""
        
    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        """Обрабатывает вызовы page.update()."""
```

**Трансформации:**

*Трансформация 1: Dialog assignment*
```python
# До
page.dialog = my_dialog
my_dialog.open = True
page.update()

# После
page.open(my_dialog)
```

*Трансформация 2: Dialog closing*
```python
# До
my_dialog.open = False
page.update()

# После
page.close(my_dialog)
```

*Трансформация 3: Mock объекты*
```python
# До
mock_page = MagicMock()

# После
mock_page = MagicMock()
mock_page.open = Mock()
mock_page.close = Mock()
```

**Структура результата:**
```python
@dataclass
class Transformation:
    transformation_type: str
    line_number: int
    original_code: str
    transformed_code: str
    
@dataclass
class TransformationResult:
    file_path: str
    transformations: List[Transformation]
    success: bool
    error_message: Optional[str]
```


### 4. Backup Manager

**Назначение:** Управление резервными копиями файлов перед миграцией

**Интерфейс:**
```python
class BackupManager:
    def create_backup(self, file_path: str) -> str:
        """
        Создаёт резервную копию файла.
        
        Args:
            file_path: Путь к файлу для резервного копирования
            
        Returns:
            Путь к созданной резервной копии
        """
        
    def restore_backup(self, backup_path: str) -> bool:
        """Восстанавливает файл из резервной копии."""
        
    def cleanup_backups(self, max_age_days: int = 7) -> int:
        """Удаляет старые резервные копии."""
```

**Структура резервных копий:**
```
.backup/
├── 2024-12-21_15-30-45/
│   ├── tests/
│   │   ├── test_home_view.py.bak
│   │   └── test_transaction_modal.py.bak
│   └── src/
│       └── finance_tracker/
│           └── views/
│               └── home_view.py.bak
└── manifest.json  # Метаданные о резервных копиях
```

**Manifest структура:**
```python
@dataclass
class BackupManifest:
    timestamp: str
    files: List[BackupFileInfo]
    migration_status: str  # "in_progress", "completed", "rolled_back"
    
@dataclass
class BackupFileInfo:
    original_path: str
    backup_path: str
    file_hash: str  # SHA256 для проверки целостности
    file_size: int
```

### 5. Test Runner

**Назначение:** Запуск тестов для валидации миграции

**Интерфейс:**
```python
class TestRunner:
    def run_tests(self, test_filter: Optional[str] = None) -> TestResult:
        """
        Запускает тесты через pytest.
        
        Args:
            test_filter: Фильтр для запуска конкретных тестов (например, "test_*_view.py")
            
        Returns:
            TestResult с результатами выполнения
        """
        
    def run_specific_tests(self, file_paths: List[str]) -> TestResult:
        """Запускает тесты только для указанных файлов."""
        
    def compare_results(self, before: TestResult, after: TestResult) -> TestComparison:
        """Сравнивает результаты тестов до и после миграции."""
```

**Структура результата:**
```python
@dataclass
class TestResult:
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    failed_tests: List[FailedTest]
    
@dataclass
class FailedTest:
    test_name: str
    test_file: str
    error_message: str
    traceback: str
    
@dataclass
class TestComparison:
    new_failures: List[FailedTest]
    fixed_tests: List[str]
    regression_detected: bool
```

### 6. Report Generator

**Назначение:** Генерация отчётов о миграции

**Интерфейс:**
```python
class ReportGenerator:
    def generate_analysis_report(self, analysis_results: List[FileAnalysisResult]) -> str:
        """Генерирует отчёт об анализе кодовой базы."""
        
    def generate_migration_report(self, migration_results: List[TransformationResult]) -> str:
        """Генерирует отчёт о выполненной миграции."""
        
    def generate_validation_report(self, test_comparison: TestComparison) -> str:
        """Генерирует отчёт о валидации миграции."""
```

**Формат отчёта:**
```markdown
# Отчёт о миграции на современный Flet Dialog API

## Сводка
- Проанализировано файлов: 45
- Требуют миграции: 23
- Успешно мигрировано: 20
- Требуют ручной миграции: 3

## Детали по файлам

### tests/test_home_view.py
- **Статус:** ✅ Успешно мигрировано
- **Найдено паттернов:** 5
- **Выполнено трансформаций:** 5
- **Тесты:** Все проходят

### src/finance_tracker/views/home_view.py
- **Статус:** ⚠️ Требует ручной миграции
- **Причина:** Сложная логика с условными диалогами
- **Рекомендация:** Проверить строки 145-167

## Результаты тестирования
- До миграции: 175 passed
- После миграции: 175 passed
- Регрессий: 0
```

## Data Models

### Enums

```python
class PatternType(str, Enum):
    """Типы паттернов использования Dialog API."""
    DIALOG_ASSIGNMENT = "dialog_assignment"  # page.dialog = dialog
    OPEN_ASSIGNMENT = "open_assignment"      # dialog.open = True
    CLOSE_ASSIGNMENT = "close_assignment"    # dialog.open = False
    PAGE_OPEN_CALL = "page_open_call"        # page.open(dialog)
    PAGE_CLOSE_CALL = "page_close_call"      # page.close(dialog)
    PAGE_UPDATE_CALL = "page_update_call"    # page.update()

class FileType(str, Enum):
    """Типы файлов для анализа."""
    TEST = "test"
    PRODUCTION = "production"
    UNKNOWN = "unknown"

class MigrationComplexity(str, Enum):
    """Сложность миграции файла."""
    SIMPLE = "simple"      # Прямая замена паттернов
    MEDIUM = "medium"      # Требует анализа контекста
    COMPLEX = "complex"    # Требует ручной миграции

class MigrationStatus(str, Enum):
    """Статус миграции."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
```

### Core Models

```python
@dataclass
class MigrationConfig:
    """Конфигурация процесса миграции."""
    project_root: str
    test_directories: List[str]
    production_directories: List[str]
    exclude_patterns: List[str]
    backup_directory: str
    dry_run: bool
    auto_rollback_on_test_failure: bool
    
@dataclass
class MigrationPlan:
    """План миграции для всего проекта."""
    total_files: int
    files_to_migrate: List[str]
    files_by_complexity: Dict[MigrationComplexity, List[str]]
    estimated_duration: float
    recommended_order: List[str]
```


## Correctness Properties

*Свойство (property) - это характеристика или поведение, которое должно выполняться для всех валидных выполнений системы. Свойства служат мостом между человеко-читаемыми спецификациями и машинно-проверяемыми гарантиями корректности.*


### Property 1: Полнота обнаружения паттернов

*For any* Python файл, содержащий работу с Flet диалогами, система должна обнаружить все паттерны использования Dialog API (как устаревшие, так и современные).

**Validates: Requirements 1.1, 2.1, 3.1, 9.1**

**Формализация:**
```python
def property_pattern_detection_completeness(file_content: str) -> bool:
    """
    Свойство: Все паттерны Dialog API должны быть обнаружены.
    """
    actual_patterns = pattern_detector.analyze_file(file_content)
    expected_patterns = manually_count_patterns(file_content)
    
    return len(actual_patterns) == len(expected_patterns)
```

**Тестирование:**
- Генерировать случайные Python файлы с различными паттернами
- Проверять, что количество обнаруженных паттернов совпадает с ожидаемым
- Тестировать edge cases: вложенные вызовы, многострочные выражения, комментарии

### Property 2: Корректная классификация устаревшего API

*For any* обнаруженный паттерн `page.dialog =`, `dialog.open = True`, или `dialog.open = False`, система должна классифицировать его как устаревший API.

**Validates: Requirements 1.2, 1.3, 2.2, 2.3**

**Формализация:**
```python
def property_legacy_api_classification(pattern: DetectedPattern) -> bool:
    """
    Свойство: Устаревшие паттерны должны быть классифицированы как legacy.
    """
    legacy_patterns = ["page.dialog =", "dialog.open = True", "dialog.open = False"]
    
    if any(legacy in pattern.code for legacy in legacy_patterns):
        return pattern.classification == "legacy"
    return True
```

### Property 3: Корректная классификация современного API

*For any* обнаруженный паттерн `page.open(...)` или `page.close(...)`, система должна классифицировать его как современный API.

**Validates: Requirements 1.4, 1.5**

**Формализация:**
```python
def property_modern_api_classification(pattern: DetectedPattern) -> bool:
    """
    Свойство: Современные паттерны должны быть классифицированы как modern.
    """
    modern_patterns = ["page.open(", "page.close("]
    
    if any(modern in pattern.code for modern in modern_patterns):
        return pattern.classification == "modern"
    return True
```

### Property 4: Валидация mock объектов

*For any* mock объект Page, найденный в тестовом файле, система должна проверить наличие методов `open` и `close`, и пометить как требующий обновления, если хотя бы один метод отсутствует.

**Validates: Requirements 3.2, 3.3, 3.4**

**Формализация:**
```python
def property_mock_validation(mock_definition: MockDefinition) -> bool:
    """
    Свойство: Mock объекты без open/close должны быть помечены как невалидные.
    """
    has_both_methods = mock_definition.has_open_method and mock_definition.has_close_method
    
    if not has_both_methods:
        return mock_definition in validation_result.invalid_mocks
    else:
        return mock_definition not in validation_result.invalid_mocks
```

### Property 5: Корректность трансформации кода (Round-trip)

*For any* файл с устаревшим Dialog API, после трансформации и обратной трансформации (если бы она существовала), семантика кода должна сохраниться. Практически это проверяется через прохождение тестов.

**Validates: Requirements 4.1, 4.2, 4.3, 5.1, 5.2, 5.3**

**Формализация:**
```python
def property_transformation_correctness(original_file: str) -> bool:
    """
    Свойство: Трансформация должна сохранять семантику кода.
    """
    # Запускаем тесты до трансформации
    tests_before = test_runner.run_tests()
    
    # Выполняем трансформацию
    transformed_file = code_transformer.transform_file(original_file)
    
    # Запускаем тесты после трансформации
    tests_after = test_runner.run_tests()
    
    # Семантика сохранена, если тесты проходят так же
    return tests_before.passed == tests_after.passed
```

### Property 6: Создание резервных копий

*For any* файл, подвергающийся миграции, система должна создать резервную копию перед началом трансформации.

**Validates: Requirements 4.4, 5.4**

**Формализация:**
```python
def property_backup_creation(file_path: str) -> bool:
    """
    Свойство: Резервная копия должна быть создана до миграции.
    """
    backup_manager.create_backup(file_path)
    code_transformer.transform_file(file_path)
    
    # Проверяем существование backup файла
    backup_exists = backup_manager.backup_exists(file_path)
    
    # Проверяем идентичность содержимого
    backup_content = backup_manager.read_backup(file_path)
    original_content = read_file_before_transformation(file_path)
    
    return backup_exists and (backup_content == original_content)
```

### Property 7: Полнота отчётов

*For any* результат анализа или миграции, сгенерированный отчёт должен содержать информацию обо всех обработанных файлах, включая номера строк, фрагменты кода и статус миграции.

**Validates: Requirements 1.6, 2.5, 2.6, 3.5, 9.5, 9.6**

**Формализация:**
```python
def property_report_completeness(analysis_results: List[FileAnalysisResult]) -> bool:
    """
    Свойство: Отчёт должен содержать информацию обо всех файлах.
    """
    report = report_generator.generate_analysis_report(analysis_results)
    
    # Проверяем, что все файлы упомянуты в отчёте
    for result in analysis_results:
        if result.requires_migration:
            assert result.file_path in report
            assert str(result.legacy_patterns[0].line_number) in report
            assert result.legacy_patterns[0].code_snippet in report
    
    return True
```

### Property 8: Корректная классификация файлов

*For any* файл, найденный при поиске паттернов, система должна корректно определить его тип (test/production), используемый API (legacy/modern), и сложность миграции (simple/medium/complex).

**Validates: Requirements 9.2, 9.3, 9.4**

**Формализация:**
```python
def property_file_classification(file_path: str) -> bool:
    """
    Свойство: Файлы должны быть корректно классифицированы.
    """
    result = pattern_detector.analyze_file(file_path)
    
    # Проверка типа файла
    if "test" in file_path or file_path.startswith("tests/"):
        assert result.file_type == FileType.TEST
    else:
        assert result.file_type == FileType.PRODUCTION
    
    # Проверка используемого API
    if result.legacy_patterns and not result.modern_patterns:
        assert result.api_type == "legacy"
    elif result.modern_patterns and not result.legacy_patterns:
        assert result.api_type == "modern"
    else:
        assert result.api_type == "mixed"
    
    # Проверка сложности
    if len(result.legacy_patterns) <= 3 and result.context_complexity == "simple":
        assert result.complexity == MigrationComplexity.SIMPLE
    
    return True
```

### Property 9: Идемпотентность миграции

*For any* файл, уже использующий современный API, повторная миграция не должна изменять код.

**Validates: Requirements 4.1, 4.2, 5.1, 5.2**

**Формализация:**
```python
def property_migration_idempotence(file_path: str) -> bool:
    """
    Свойство: Миграция современного кода не должна его изменять.
    """
    # Первая миграция
    first_result = code_transformer.transform_file(file_path)
    first_content = read_file(file_path)
    
    # Вторая миграция
    second_result = code_transformer.transform_file(file_path)
    second_content = read_file(file_path)
    
    # Если файл уже использует современный API, он не должен измениться
    if not first_result.transformations:
        return first_content == second_content
    
    # Если была миграция, повторная не должна ничего менять
    return second_content == first_content and not second_result.transformations
```

### Property 10: Откат при падении тестов

*For any* миграция, приводящая к падению тестов, система должна автоматически восстановить оригинальные файлы из резервных копий.

**Validates: Requirements 4.6, 5.6, 7.6**

**Формализация:**
```python
def property_rollback_on_test_failure(file_path: str) -> bool:
    """
    Свойство: При падении тестов должен происходить откат.
    """
    original_content = read_file(file_path)
    
    # Создаём backup
    backup_path = backup_manager.create_backup(file_path)
    
    # Выполняем миграцию
    code_transformer.transform_file(file_path)
    
    # Симулируем падение тестов
    test_result = TestResult(passed=0, failed=10, total_tests=10)
    
    # Система должна откатить изменения
    if test_result.failed > 0:
        backup_manager.restore_backup(backup_path)
    
    restored_content = read_file(file_path)
    
    return restored_content == original_content
```


## Error Handling

### Категории ошибок

**1. Ошибки анализа кода**
- **SyntaxError при парсинге:** Файл содержит синтаксические ошибки Python
- **Обработка:** Пропустить файл, добавить в отчёт как "требует ручной проверки"
- **Логирование:** ERROR уровень с путём к файлу и описанием ошибки

**2. Ошибки трансформации**
- **Невозможность определить контекст:** Сложная логика, требующая ручной миграции
- **Обработка:** Пометить файл как "complex", не выполнять автоматическую трансформацию
- **Логирование:** WARNING уровень с описанием проблемного участка кода

**3. Ошибки файловой системы**
- **Отсутствие прав на запись:** Невозможно создать backup или записать трансформированный файл
- **Обработка:** Прервать миграцию, сообщить пользователю
- **Логирование:** ERROR уровень с путём к файлу

**4. Ошибки тестирования**
- **Падение тестов после миграции:** Трансформация изменила семантику кода
- **Обработка:** Автоматический откат из backup, добавить файл в список "требует ручной миграции"
- **Логирование:** ERROR уровень с именами упавших тестов и traceback

**5. Ошибки резервного копирования**
- **Невозможность создать backup:** Недостаточно места на диске или проблемы с правами
- **Обработка:** Прервать миграцию до начала трансформации
- **Логирование:** ERROR уровень, критическая ошибка

### Стратегии обработки

**Fail-fast для критических ошибок:**
- Отсутствие прав на запись
- Невозможность создать backup
- Критические ошибки парсинга AST

**Graceful degradation для некритических:**
- Синтаксические ошибки в отдельных файлах - пропустить файл
- Сложная логика - пометить для ручной миграции
- Падение отдельных тестов - откатить конкретный файл

**Автоматический откат:**
- При падении тестов после миграции
- При обнаружении изменения семантики кода
- По явному запросу пользователя

### Логирование ошибок

**Формат лога:**
```python
logger.error(
    "Ошибка при миграции файла",
    extra={
        "file_path": file_path,
        "error_type": "transformation_error",
        "error_message": str(e),
        "traceback": traceback.format_exc(),
        "patterns_found": len(patterns),
        "transformations_attempted": len(transformations)
    }
)
```

**Уровни логирования:**
- **ERROR:** Критические ошибки, требующие внимания
- **WARNING:** Потенциальные проблемы, система продолжает работу
- **INFO:** Важные события (начало/конец миграции, создание backup)
- **DEBUG:** Детальная информация для отладки

## Testing Strategy

### Dual Testing Approach

Система миграции требует комплексного тестирования, включающего как unit тесты для отдельных компонентов, так и property-based тесты для проверки универсальных свойств.

### Unit Tests

**Тестирование Pattern Detector:**
```python
def test_detect_legacy_dialog_assignment():
    """Тест обнаружения устаревшего паттерна page.dialog ="""
    code = """
    def open_modal(page, dialog):
        page.dialog = dialog
        dialog.open = True
        page.update()
    """
    
    result = pattern_detector.analyze_file(code)
    
    assert len(result.legacy_patterns) == 3
    assert result.legacy_patterns[0].pattern_type == PatternType.DIALOG_ASSIGNMENT
    assert result.requires_migration == True

def test_detect_modern_page_open():
    """Тест обнаружения современного паттерна page.open()"""
    code = """
    def open_modal(page, dialog):
        page.open(dialog)
    """
    
    result = pattern_detector.analyze_file(code)
    
    assert len(result.modern_patterns) == 1
    assert result.modern_patterns[0].pattern_type == PatternType.PAGE_OPEN_CALL
    assert result.requires_migration == False
```

**Тестирование Code Transformer:**
```python
def test_transform_dialog_assignment():
    """Тест трансформации page.dialog = в page.open()"""
    original = """
    page.dialog = my_dialog
    my_dialog.open = True
    page.update()
    """
    
    expected = """
    page.open(my_dialog)
    """
    
    result = code_transformer.transform_file(original)
    
    assert result.success == True
    assert len(result.transformations) == 1
    assert normalize_whitespace(result.transformed_code) == normalize_whitespace(expected)

def test_transform_preserves_other_code():
    """Тест сохранения остального кода при трансформации"""
    original = """
    def some_function():
        x = 10
        page.dialog = my_dialog
        my_dialog.open = True
        page.update()
        return x * 2
    """
    
    result = code_transformer.transform_file(original)
    
    assert "def some_function():" in result.transformed_code
    assert "x = 10" in result.transformed_code
    assert "return x * 2" in result.transformed_code
    assert "page.open(my_dialog)" in result.transformed_code
```

**Тестирование Backup Manager:**
```python
def test_create_backup():
    """Тест создания резервной копии"""
    test_file = "test_file.py"
    original_content = "print('original')"
    write_file(test_file, original_content)
    
    backup_path = backup_manager.create_backup(test_file)
    
    assert os.path.exists(backup_path)
    assert read_file(backup_path) == original_content

def test_restore_backup():
    """Тест восстановления из резервной копии"""
    test_file = "test_file.py"
    original_content = "print('original')"
    write_file(test_file, original_content)
    
    backup_path = backup_manager.create_backup(test_file)
    
    # Изменяем файл
    write_file(test_file, "print('modified')")
    
    # Восстанавливаем
    backup_manager.restore_backup(backup_path)
    
    assert read_file(test_file) == original_content
```

### Property-Based Tests

**Конфигурация Hypothesis:**
- Минимум 100 итераций для каждого property теста
- Генераторы для создания случайных Python файлов с различными паттернами
- Стратегии для генерации валидного Python кода

**Property Test 1: Полнота обнаружения**
```python
@given(st.text(min_size=10, max_size=1000))
def test_pattern_detection_completeness_property(code_snippet):
    """
    **Feature: flet-dialog-api-migration, Property 1: Полнота обнаружения паттернов**
    **Validates: Requirements 1.1, 2.1, 3.1, 9.1**
    
    Property: Все паттерны Dialog API должны быть обнаружены.
    """
    # Генерируем валидный Python код с паттернами
    assume(is_valid_python(code_snippet))
    
    result = pattern_detector.analyze_file(code_snippet)
    manual_count = count_patterns_manually(code_snippet)
    
    assert len(result.legacy_patterns) + len(result.modern_patterns) == manual_count
```

**Property Test 2: Идемпотентность миграции**
```python
@given(st.text(min_size=10, max_size=1000))
def test_migration_idempotence_property(code_snippet):
    """
    **Feature: flet-dialog-api-migration, Property 9: Идемпотентность миграции**
    **Validates: Requirements 4.1, 4.2, 5.1, 5.2**
    
    Property: Повторная миграция не должна изменять уже мигрированный код.
    """
    assume(is_valid_python(code_snippet))
    
    # Первая миграция
    first_result = code_transformer.transform_file(code_snippet)
    
    # Вторая миграция
    second_result = code_transformer.transform_file(first_result.transformed_code)
    
    # Код не должен измениться
    assert first_result.transformed_code == second_result.transformed_code
    assert len(second_result.transformations) == 0
```

**Property Test 3: Сохранение семантики**
```python
@given(st.text(min_size=10, max_size=1000))
def test_transformation_preserves_semantics_property(code_snippet):
    """
    **Feature: flet-dialog-api-migration, Property 5: Корректность трансформации**
    **Validates: Requirements 4.1, 4.2, 4.3, 5.1, 5.2, 5.3**
    
    Property: Трансформация должна сохранять семантику кода.
    """
    assume(is_valid_python(code_snippet))
    assume(has_dialog_patterns(code_snippet))
    
    # Создаём тестовый файл
    test_file = create_temp_file(code_snippet)
    
    # Запускаем тесты до миграции
    tests_before = run_tests_for_file(test_file)
    
    # Выполняем миграцию
    code_transformer.transform_file(test_file)
    
    # Запускаем тесты после миграции
    tests_after = run_tests_for_file(test_file)
    
    # Семантика сохранена, если тесты проходят так же
    assert tests_before.passed == tests_after.passed
```

### Integration Tests

**Полный цикл миграции:**
```python
def test_complete_migration_workflow():
    """Интеграционный тест: полный цикл миграции проекта"""
    # Подготовка тестового проекта
    test_project = create_test_project_with_legacy_api()
    
    # Анализ
    analysis_results = analyzer.analyze_project(test_project)
    assert len(analysis_results.files_to_migrate) > 0
    
    # Миграция
    migration_results = migrator.migrate_project(test_project)
    assert migration_results.success == True
    
    # Валидация
    test_results = validator.validate_migration(test_project)
    assert test_results.all_tests_passed == True
    
    # Проверка отчёта
    report = reporter.generate_report(migration_results)
    assert "Успешно мигрировано" in report
```

### Test Data Generators

**Генератор Python кода с Dialog паттернами:**
```python
def generate_code_with_dialog_patterns():
    """Генерирует валидный Python код с различными паттернами Dialog API"""
    patterns = [
        "page.dialog = dialog\ndialog.open = True\npage.update()",
        "page.open(dialog)",
        "dialog.open = False\npage.update()",
        "page.close(dialog)"
    ]
    
    return random.choice(patterns)
```


## Implementation Details

### AST Transformation Strategy

**Использование Python AST модуля:**

Python предоставляет встроенный модуль `ast` для работы с абстрактным синтаксическим деревом. Мы используем `ast.NodeTransformer` для модификации кода.

**Пример трансформации:**

```python
import ast
import astor  # Для преобразования AST обратно в код

class DialogAPITransformer(ast.NodeTransformer):
    def __init__(self):
        self.dialog_variable = None
        self.transformations = []
    
    def visit_Assign(self, node):
        """Обрабатывает присваивания page.dialog = dialog"""
        # Проверяем, является ли это присваиванием page.dialog
        if (isinstance(node.targets[0], ast.Attribute) and
            isinstance(node.targets[0].value, ast.Name) and
            node.targets[0].value.id == 'page' and
            node.targets[0].attr == 'dialog'):
            
            # Сохраняем имя переменной диалога
            if isinstance(node.value, ast.Name):
                self.dialog_variable = node.value.id
            
            # Удаляем это присваивание (вернём None)
            self.transformations.append({
                'type': 'dialog_assignment_removed',
                'line': node.lineno
            })
            return None
        
        return self.generic_visit(node)
    
    def visit_Expr(self, node):
        """Обрабатывает выражения, включая dialog.open = True"""
        # Проверяем, является ли это присваиванием dialog.open
        if (isinstance(node.value, ast.Assign) and
            isinstance(node.value.targets[0], ast.Attribute) and
            node.value.targets[0].attr == 'open'):
            
            dialog_name = node.value.targets[0].value.id
            open_value = node.value.value
            
            # Если dialog.open = True, заменяем на page.open(dialog)
            if isinstance(open_value, ast.Constant) and open_value.value == True:
                new_call = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='page', ctx=ast.Load()),
                            attr='open',
                            ctx=ast.Load()
                        ),
                        args=[ast.Name(id=dialog_name, ctx=ast.Load())],
                        keywords=[]
                    )
                )
                self.transformations.append({
                    'type': 'open_assignment_to_page_open',
                    'line': node.lineno
                })
                return new_call
            
            # Если dialog.open = False, заменяем на page.close(dialog)
            elif isinstance(open_value, ast.Constant) and open_value.value == False:
                new_call = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='page', ctx=ast.Load()),
                            attr='close',
                            ctx=ast.Load()
                        ),
                        args=[ast.Name(id=dialog_name, ctx=ast.Load())],
                        keywords=[]
                    )
                )
                self.transformations.append({
                    'type': 'close_assignment_to_page_close',
                    'line': node.lineno
                })
                return new_call
        
        return self.generic_visit(node)
```

### Pattern Detection Algorithm

**Алгоритм обнаружения паттернов:**

1. **Парсинг файла в AST:**
   ```python
   with open(file_path, 'r', encoding='utf-8') as f:
       source_code = f.read()
   tree = ast.parse(source_code)
   ```

2. **Обход AST дерева:**
   ```python
   class PatternVisitor(ast.NodeVisitor):
       def __init__(self):
           self.patterns = []
       
       def visit_Assign(self, node):
           # Проверка на page.dialog = ...
           if self._is_dialog_assignment(node):
               self.patterns.append(LegacyPattern(
                   pattern_type="dialog_assignment",
                   line_number=node.lineno,
                   code_snippet=ast.unparse(node)
               ))
           self.generic_visit(node)
   ```

3. **Классификация паттернов:**
   - Legacy: `page.dialog =`, `dialog.open = True/False`
   - Modern: `page.open(...)`, `page.close(...)`

4. **Оценка сложности:**
   - Simple: Прямые присваивания без условий
   - Medium: Присваивания внутри условных блоков
   - Complex: Динамическое определение диалога, множественные условия

### Backup Strategy

**Структура backup директории:**

```
.backup/
├── 2024-12-21_15-30-45/          # Timestamp миграции
│   ├── manifest.json              # Метаданные
│   ├── tests/
│   │   └── test_home_view.py.bak
│   └── src/
│       └── finance_tracker/
│           └── views/
│               └── home_view.py.bak
└── 2024-12-20_10-15-30/          # Предыдущая миграция
    └── ...
```

**Manifest.json структура:**

```json
{
  "timestamp": "2024-12-21T15:30:45",
  "migration_status": "completed",
  "files": [
    {
      "original_path": "tests/test_home_view.py",
      "backup_path": ".backup/2024-12-21_15-30-45/tests/test_home_view.py.bak",
      "file_hash": "sha256:abc123...",
      "file_size": 15234,
      "transformations_count": 5
    }
  ],
  "test_results": {
    "before": {"passed": 175, "failed": 0},
    "after": {"passed": 175, "failed": 0}
  }
}
```

### CI/CD Integration

**GitHub Actions workflow пример:**

```yaml
name: Flet Dialog API Check

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  check-dialog-api:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install -e ".[dev]"
    
    - name: Run Dialog API checker
      run: |
        python -m migration_system.ci_checker \
          --files-changed ${{ github.event.pull_request.changed_files }}
    
    - name: Comment on PR
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: '⚠️ Обнаружено использование устаревшего Flet Dialog API. Пожалуйста, используйте `page.open()` и `page.close()`.'
          })
```

### Steering Rules Update

**Обновление .kiro/steering/ui-testing.md:**

После успешной миграции система автоматически обновит steering правила, добавив раздел:

```markdown
### Dialog Management Standard (ОБЯЗАТЕЛЬНО)

**КРИТИЧЕСКИ ВАЖНО:** В проекте используется ТОЛЬКО современный способ работы с диалогами через `page.open()` и `page.close()`.

**✅ ПРАВИЛЬНО (используй ТОЛЬКО этот способ):**
```python
def open_dialog(e):
    page.open(dialog)  # Открываем диалог

def close_dialog(e):
    page.close(dialog)  # Закрываем диалог
```

**❌ НЕПРАВИЛЬНО (НЕ используй устаревший способ):**
```python
# ЗАПРЕЩЕНО в этом проекте!
def open_dialog(e):
    page.dialog = dialog
    dialog.open = True
    page.update()
```

**Применяется к:**
- `ft.AlertDialog`
- `ft.BottomSheet`
- `ft.SnackBar`
- Любые другие overlay компоненты

**В тестах:**
- Mock объекты ДОЛЖНЫ иметь методы `page.open()` и `page.close()`
- Проверки ДОЛЖНЫ использовать `page.open.assert_called()` и `page.close.assert_called()`
- НЕ проверять `page.dialog` или `dialog.open` атрибуты
```

## Migration Workflow

### Пошаговый процесс миграции

**Фаза 1: Анализ (Requirements 1, 2, 3, 9)**

1. Сканирование проекта для поиска всех Python файлов
2. Классификация файлов (test/production)
3. Обнаружение паттернов Dialog API
4. Валидация mock объектов в тестах
5. Оценка сложности миграции
6. Генерация отчёта об анализе

**Фаза 2: Планирование**

1. Определение порядка миграции файлов:
   - Сначала тесты (для обеспечения валидации)
   - Затем production код
   - Простые файлы перед сложными
2. Создание плана миграции с оценкой времени
3. Получение подтверждения пользователя

**Фаза 3: Миграция (Requirements 4, 5)**

Для каждого файла:
1. Создание резервной копии
2. Выполнение AST трансформации
3. Запись трансформированного кода
4. Запуск тестов для валидации
5. При падении тестов - откат из backup
6. Обновление статуса миграции

**Фаза 4: Валидация (Requirement 7)**

1. Запуск полного набора тестов
2. Сравнение результатов до/после миграции
3. Анализ регрессий
4. Генерация отчёта о валидации

**Фаза 5: Финализация (Requirement 8)**

1. Обновление steering правил
2. Создание commit с изменениями
3. Генерация финального отчёта
4. Очистка старых backup файлов

### Команды CLI

**Анализ проекта:**
```bash
python -m migration_system analyze --project-root . --output report.md
```

**Миграция с dry-run:**
```bash
python -m migration_system migrate --project-root . --dry-run
```

**Полная миграция:**
```bash
python -m migration_system migrate --project-root . --auto-rollback
```

**Откат миграции:**
```bash
python -m migration_system rollback --backup-timestamp 2024-12-21_15-30-45
```

**Проверка для CI:**
```bash
python -m migration_system ci-check --files-changed file1.py file2.py
```

## Performance Considerations

### Оптимизация производительности

**1. Параллельная обработка файлов:**
- Использование `multiprocessing` для анализа множества файлов
- Каждый файл обрабатывается в отдельном процессе
- Ограничение количества параллельных процессов (CPU count)

**2. Кэширование результатов анализа:**
- Хэширование содержимого файлов (SHA256)
- Пропуск повторного анализа неизменённых файлов
- Хранение кэша в `.migration_cache/`

**3. Инкрементальная миграция:**
- Возможность мигрировать только изменённые файлы
- Отслеживание статуса миграции каждого файла
- Продолжение с места остановки при прерывании

**4. Оптимизация тестирования:**
- Запуск только тестов, связанных с мигрированными файлами
- Использование pytest-xdist для параллельного запуска тестов
- Кэширование результатов тестов

### Ожидаемая производительность

- **Анализ:** ~100 файлов/секунду
- **Трансформация:** ~50 файлов/секунду
- **Тестирование:** зависит от количества и сложности тестов
- **Полная миграция проекта (45 файлов):** ~2-5 минут

## Security Considerations

### Безопасность миграции

**1. Валидация входных данных:**
- Проверка, что файлы находятся внутри project root
- Защита от path traversal атак
- Валидация Python синтаксиса перед трансформацией

**2. Целостность резервных копий:**
- SHA256 хэширование backup файлов
- Проверка целостности при восстановлении
- Защита backup директории от случайного удаления

**3. Безопасное выполнение кода:**
- Использование AST вместо eval/exec
- Изоляция тестового окружения
- Ограничение прав доступа к файлам

**4. Логирование безопасности:**
- Запись всех операций с файлами
- Аудит трансформаций
- Отслеживание попыток несанкционированного доступа

## Future Enhancements

### Возможные улучшения

**1. Поддержка других Flet компонентов:**
- Миграция BottomSheet API
- Миграция SnackBar API
- Универсальный фреймворк для миграции любых API
