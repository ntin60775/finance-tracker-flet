# Finance Tracker

Finance Tracker - это десктопное приложение для управления личными финансами, построенное на Flet framework.

## Возможности

- Учет доходов и расходов
- Управление категориями транзакций
- Управление кредитами и займами
- Плановые транзакции с повторениями
- Отложенные платежи
- План-факт анализ
- Прогноз баланса
- Календарь транзакций

## Установка

### Требования

- Python >= 3.9

### Установка зависимостей

```bash
pip install -e .
```

### Установка зависимостей для разработки

```bash
pip install -e ".[dev]"
```

## Запуск приложения

```bash
python main.py
```

Или через установленную команду:

```bash
finance-tracker
```

## Запуск тестов

Проект использует pytest для тестирования и включает как unit-тесты, так и property-based тесты (с использованием Hypothesis).

### Запуск всех тестов

Для запуска всех тестов (unit-тесты + property-based тесты):

```bash
pytest tests/
```

### Запуск только UI-тестов

Для запуска только тестов пользовательского интерфейса (View компонентов):

```bash
pytest tests/test_*_view.py
```

Или для запуска тестов конкретного View:

```bash
pytest tests/test_home_view.py
pytest tests/test_categories_view.py
pytest tests/test_loans_view.py
```

### Запуск property-based тестов

Для запуска только property-based тестов (тесты с суффиксом `_properties`):

```bash
pytest tests/test_*_properties.py
```

Или для запуска конкретной группы property-тестов:

```bash
pytest tests/test_transaction_properties.py
pytest tests/test_loan_properties.py
pytest tests/test_category_properties.py
```

### Проверка покрытия кода

Для запуска тестов с проверкой покрытия кода:

```bash
pytest tests/ --cov=src/finance_tracker --cov-report=html
```

После выполнения команды отчет о покрытии будет доступен в директории `htmlcov/index.html`.

Для вывода покрытия в терминал:

```bash
pytest tests/ --cov=src/finance_tracker --cov-report=term
```

Для проверки покрытия только View компонентов:

```bash
pytest tests/test_*_view.py --cov=src/finance_tracker/views --cov-report=html
```

### Дополнительные опции pytest

Запуск тестов с подробным выводом:

```bash
pytest tests/ -v
```

Запуск тестов с остановкой на первой ошибке:

```bash
pytest tests/ -x
```

Запуск конкретного теста:

```bash
pytest tests/test_home_view.py::TestHomeView::test_initialization
```

Запуск тестов с фильтром по имени:

```bash
pytest tests/ -k "test_load_data"
```

## Структура проекта

```
finance_tracker/
├── src/
│   └── finance_tracker/
│       ├── models/          # Модели данных (SQLAlchemy)
│       ├── services/        # Бизнес-логика
│       ├── views/           # UI компоненты (Flet Views)
│       ├── widgets/         # Переиспользуемые UI компоненты
│       ├── utils/           # Утилиты (логирование, обработка ошибок)
│       ├── database.py      # Настройка БД
│       ├── config.py        # Конфигурация приложения
│       └── app.py           # Главное приложение
├── tests/                   # Тесты
├── main.py                  # Точка входа
└── pyproject.toml          # Конфигурация проекта
```

## Лицензия

AGPL-3.0
