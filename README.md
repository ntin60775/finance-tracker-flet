# Finance Tracker Flet

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
- Экспорт и импорт данных (публичный функционал)
- Облачная синхронизация (расширенный функционал через Git submodule)

## Установка

### Требования

- Python >= 3.9

### Клонирование проекта

**Базовая версия (без расширенного функционала синхронизации):**

```bash
git clone https://github.com/BarykinME/finance-tracker-flet.git
cd finance-tracker-flet
```

**Полная версия (с расширенным функционалом синхронизации):**

```bash
git clone --recurse-submodules https://github.com/BarykinME/finance-tracker-flet.git
cd finance-tracker-flet
```

Если вы уже клонировали проект без submodules, можете добавить их позже:

```bash
git submodule init
git submodule update
```

### Установка зависимостей

```bash
pip install -e .
```

### Установка зависимостей для разработки

```bash
pip install -e ".[dev]"
```

## Запуск приложения

Приложение можно запустить несколькими способами:

### Способ 1: Через модуль Python (рекомендуется)

```bash
python -m finance_tracker
```

### Способ 2: Через launcher в корне проекта

```bash
python main.py
```

### Способ 3: Через установленную команду

После установки пакета доступна команда:

```bash
finance-tracker
```

## Пользовательские данные

Все пользовательские данные (база данных, логи, настройки, экспорты) хранятся в отдельной директории:

```
.finance_tracker_data/
├── finance.db           # База данных SQLite
├── config.json          # Настройки пользователя
├── logs/                # Логи приложения
│   └── finance_tracker.log
└── exports/             # Экспортированные файлы
    └── backup_*.json
```

Это позволяет:
- Легко найти и удалить пользовательские данные
- Не замусоривать корень проекта
- Сохранять данные при обновлении приложения
- Работать одинаково в режиме разработки и .exe

### Миграция на UUID (декабрь 2024)

**Важно:** Начиная с версии декабря 2024, приложение использует UUID вместо Integer ID для всех записей в базе данных.

**Что это означает:**
- Все идентификаторы (ID) теперь имеют формат UUID (например, `550e8400-e29b-41d4-a716-446655440000`)
- Обеспечена глобальная уникальность идентификаторов для будущей синхронизации между устройствами
- Все таблицы теперь имеют колонку `updated_at` для отслеживания изменений

**Автоматическая миграция:**
- При первом запуске новой версии приложение автоматически обнаружит старую схему БД (Integer ID)
- Старая база данных будет удалена, и создана новая с UUID схемой
- **Рекомендация:** Сделайте экспорт данных перед обновлением, если хотите сохранить историю

**Для разработчиков:**
- Все сервисы теперь принимают `str` (UUID) вместо `int` для параметров ID
- Pydantic модели автоматически валидируют формат UUID
- Утилита `validate_uuid_format()` доступна в `utils/validation.py`
- Подробная документация миграции: `.kiro/specs/uuid-migration/`

## Запуск тестов

Проект использует комплексную стратегию тестирования с pytest, включающую unit-тесты, property-based тесты (Hypothesis), UI-тесты и интеграционные тесты.

### Типы тестов

**Unit тесты** - изолированное тестирование отдельных компонентов:
- Сервисы (`test_*_service.py`)
- UI компоненты (`test_*_view.py`, `test_*_modal.py`)
- Утилиты и вспомогательные функции

**Property-based тесты** - проверка универсальных свойств на случайных данных:
- Инварианты бизнес-логики (`test_*_properties.py`)
- Корректность алгоритмов
- Обработка граничных случаев

**UI тесты** - тестирование пользовательского интерфейса:
- Инициализация View компонентов
- Взаимодействие с кнопками и формами
- Открытие модальных окон
- Валидация пользовательского ввода

**Интеграционные тесты** - проверка взаимодействия компонентов:
- Полные пользовательские сценарии
- Взаимодействие View ↔ Service ↔ Database
- End-to-end тестирование функций

### Быстрый старт

Запуск всех тестов:
```bash
pytest tests/
```

Запуск с покрытием кода:
```bash
pytest tests/ --cov=src/finance_tracker --cov-report=html
```

Просмотр отчета о покрытии:
```bash
# Откройте htmlcov/index.html в браузере
```

### Запуск по категориям тестов

#### Unit тесты

Все unit тесты:
```bash
pytest tests/test_*_service.py tests/test_*_view.py tests/test_*_modal.py
```

Тесты сервисов (бизнес-логика):
```bash
pytest tests/test_*_service.py
```

Тесты UI компонентов:
```bash
pytest tests/test_*_view.py tests/test_*_modal.py
```

Конкретный компонент:
```bash
pytest tests/test_home_view.py
pytest tests/test_transaction_modal.py
pytest tests/test_transaction_service.py
```

#### Property-based тесты

Все property-based тесты:
```bash
pytest tests/test_*_properties.py
```

По доменам:
```bash
pytest tests/test_transaction_properties.py    # Транзакции
pytest tests/test_loan_properties.py           # Кредиты
pytest tests/test_category_properties.py       # Категории
pytest tests/test_balance_forecast_properties.py # Прогноз баланса
```

#### UI тесты

Все UI тесты (View + Modal):
```bash
pytest tests/test_*_view.py tests/test_*_modal.py
```

Тесты View компонентов:
```bash
pytest tests/test_*_view.py
```

Тесты модальных окон:
```bash
pytest tests/test_*_modal.py
```

Тесты конкретного UI компонента:
```bash
pytest tests/test_home_view.py              # Главный экран
pytest tests/test_categories_view.py        # Управление категориями
pytest tests/test_loans_view.py             # Список кредитов
pytest tests/test_transaction_modal.py      # Модальное окно транзакции
```

#### Интеграционные тесты

Все интеграционные тесты:
```bash
pytest tests/test_integration*.py
```

Конкретные интеграции:
```bash
pytest tests/test_integration.py                    # Основные интеграции
pytest tests/test_loan_payment_integration.py       # Интеграция платежей по кредитам
pytest tests/test_integration_regression.py         # Регрессионные тесты
```

### Проверка покрытия кода

Полное покрытие:
```bash
pytest tests/ --cov=src/finance_tracker --cov-report=html --cov-report=term
```

Покрытие по компонентам:
```bash
# Только View компоненты
pytest tests/test_*_view.py --cov=src/finance_tracker/views --cov-report=html

# Только сервисы
pytest tests/test_*_service.py --cov=src/finance_tracker/services --cov-report=html

# Только модальные окна
pytest tests/test_*_modal.py --cov=src/finance_tracker/components --cov-report=html
```

Минимальный порог покрытия:
```bash
pytest tests/ --cov=src/finance_tracker --cov-fail-under=80
```

### Специальные тесты

#### Тесты кнопки добавления транзакции

Полный набор тестов для кнопки добавления транзакции:
```bash
pytest tests/ -k "add_transaction_button or transaction_modal"
```

Unit тесты кнопки:
```bash
pytest tests/test_home_view.py -k "add_transaction"
pytest tests/test_transactions_panel.py -k "add_button"
```

Property-based тесты кнопки:
```bash
pytest tests/test_*_properties.py -k "button or modal"
```

#### Тесты обработки ошибок

Тесты устойчивости к ошибкам:
```bash
pytest tests/ -k "error or exception or robustness"
```

#### Performance тесты

Тесты производительности:
```bash
pytest tests/test_performance_properties.py
```

### Дополнительные опции pytest

Подробный вывод:
```bash
pytest tests/ -v
```

Остановка на первой ошибке:
```bash
pytest tests/ -x
```

Запуск конкретного теста:
```bash
pytest tests/test_home_view.py::TestHomeView::test_initialization
```

Фильтрация по имени теста:
```bash
pytest tests/ -k "test_load_data"
pytest tests/ -k "property and transaction"
pytest tests/ -k "not slow"  # Исключить медленные тесты
```

Параллельный запуск (требует pytest-xdist):
```bash
pytest tests/ -n auto  # Автоматическое определение количества процессов
pytest tests/ -n 4     # 4 параллельных процесса
```

Повторный запуск упавших тестов:
```bash
pytest tests/ --lf      # Только последние упавшие тесты
pytest tests/ --ff      # Сначала упавшие, потом остальные
```

### Отладка тестов

Запуск с отладчиком:
```bash
pytest tests/test_home_view.py --pdb
```

Вывод print statements:
```bash
pytest tests/ -s
```

Подробная информация о фикстурах:
```bash
pytest tests/ --fixtures
```

### CI/CD команды

Команды для непрерывной интеграции:

Быстрая проверка (smoke tests):
```bash
pytest tests/test_*_view.py -x --tb=short
```

Полная проверка с покрытием:
```bash
pytest tests/ --cov=src/finance_tracker --cov-report=xml --cov-fail-under=80 --tb=short
```

Только критические тесты:
```bash
pytest tests/ -m "not slow" --tb=short
```

### Создание новых тестов

Для добавления новых тестов в проект следуйте этим шагам:

1. **Определите тип теста:**
   - `test_*_service.py` - для тестирования бизнес-логики
   - `test_*_view.py` - для тестирования UI компонентов
   - `test_*_properties.py` - для property-based тестов
   - `test_integration*.py` - для интеграционных тестов

2. **Используйте существующие паттерны:**
   ```bash
   # Изучите похожие тесты
   ls tests/test_*_view.py
   
   # Скопируйте структуру существующего теста
   cp tests/test_home_view.py tests/test_new_view.py
   ```

3. **Проверьте новый тест:**
   ```bash
   # Запустите изолированно
   pytest tests/test_new_file.py -v
   
   # Проверьте покрытие
   pytest tests/test_new_file.py --cov=src/finance_tracker/your_module
   ```

**Подробное руководство:** См. `.kiro/steering/ui-testing.md` → "Adding New Tests to the System"

## Мобильный функционал

Проект поддерживает работу с мобильными данными через два уровня функциональности:

### Публичный функционал (всегда доступен)

Базовый функционал экспорта и импорта данных в JSON файлы:

```python
from finance_tracker.mobile import ExportService, ImportService

# Экспорт данных
export_path = ExportService.export_to_file()
print(f"Данные экспортированы в: {export_path}")

# Импорт данных
stats = ImportService.import_from_file("backup_2024_12_07.json")
print(f"Импортировано транзакций: {stats['transactions']}")
```

Экспортированные файлы сохраняются в `.finance_tracker_data/exports/` рядом с приложением

### Расширенный функционал (через Git submodule)

Облачная синхронизация и real-time обмен данными доступны при установке приватного submodule:

```python
from finance_tracker.mobile import CloudSyncService, RealtimeSyncService, PROPRIETARY_AVAILABLE

if PROPRIETARY_AVAILABLE:
    # Облачная синхронизация доступна
    sync = CloudSyncService()
    sync.sync_to_cloud()
else:
    # Используем базовый функционал
    print("Используйте ExportService/ImportService для базового функционала")
```

**Для получения доступа к расширенному функционалу:**

1. Клонируйте проект с submodules (см. раздел "Установка")
2. Или добавьте submodule вручную:

```bash
git submodule add https://github.com/BarykinME/finance-tracker-sync-proprietary.git src/finance_tracker/mobile/sync_proprietary
git submodule update --init --recursive
```

**Обновление расширенного функционала:**

```bash
git submodule update --remote src/finance_tracker/mobile/sync_proprietary
```

## Структура проекта

```
finance-tracker-flet/
├── src/
│   └── finance_tracker/           # Основной пакет приложения
│       ├── __init__.py
│       ├── __main__.py            # Точка входа (python -m finance_tracker)
│       ├── app.py                 # Главная логика приложения
│       ├── config.py              # Конфигурация
│       ├── database.py            # Управление БД
│       ├── components/            # UI компоненты (модальные окна, виджеты)
│       │   ├── calendar_legend.py
│       │   ├── calendar_widget.py
│       │   ├── transaction_modal.py
│       │   └── ...
│       ├── models/                # Модели данных (SQLAlchemy)
│       │   ├── enums.py
│       │   └── models.py
│       ├── services/              # Бизнес-логика
│       │   ├── transaction_service.py
│       │   ├── loan_service.py
│       │   └── ...
│       ├── utils/                 # Утилиты
│       │   ├── logger.py
│       │   ├── error_handler.py
│       │   └── ...
│       ├── views/                 # UI представления (экраны)
│       │   ├── main_window.py
│       │   ├── home_view.py
│       │   └── ...
│       └── mobile/                # Мобильный функционал
│           ├── __init__.py
│           ├── export_service.py  # Публичный: экспорт в файлы
│           ├── import_service.py  # Публичный: импорт из файлов
│           └── sync_proprietary/  # Git submodule (приватный)
│               ├── cloud_sync.py
│               └── realtime_sync.py
├── tests/                         # Тесты (unit + property-based)
│   ├── conftest.py
│   ├── test_transaction_properties.py
│   ├── test_home_view.py
│   └── ...
├── assets/                        # Статические ресурсы
│   ├── icon.ico
│   ├── icon.png
│   └── prompts/
├── .kiro/                         # Спецификации Kiro
│   └── specs/
├── .gitmodules                    # Конфигурация Git submodules
├── main.py                        # Launcher для разработки
├── pyproject.toml                 # Конфигурация проекта
├── finance_tracker.spec           # Конфигурация PyInstaller
├── .gitignore                     # Git ignore правила
├── LICENSE                        # AGPL-3.0 лицензия
└── README.md                      # Документация
```

## Сборка .exe файла

Для создания standalone исполняемого файла используется PyInstaller:

### Установка PyInstaller

```bash
pip install pyinstaller
```

### Сборка приложения

```bash
pyinstaller finance_tracker.spec
```

Готовый .exe файл будет находиться в директории `dist/FinanceTracker.exe`

### Особенности .exe версии

- Все пользовательские данные сохраняются в `.finance_tracker_data/` рядом с .exe (портативность)
- Assets (иконки, изображения) упаковываются в .exe
- Размер файла: ~50-70 MB (включая Python runtime и все зависимости)
- Не требует установленного Python на целевой системе

### Тестирование .exe

После сборки рекомендуется протестировать .exe на чистой системе:

1. Скопируйте `dist/finance_tracker.exe` на другой компьютер
2. Запустите приложение
3. Проверьте создание `.finance_tracker_data/` рядом с .exe
4. Проверьте основные функции (создание транзакций, кредитов, экспорт)

## Лицензия

Этот проект распространяется под лицензией **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### Что это означает

- ✅ **Свободное использование**: Вы можете свободно использовать, изучать и модифицировать код
- ✅ **Открытый исходный код**: Все модификации должны оставаться открытыми
- ✅ **Network Copyleft**: Даже при использовании через сеть (SaaS) исходный код должен быть доступен
- ⚠️ **Обязательное раскрытие**: Любые производные работы должны распространяться под той же лицензией
- ⚠️ **Сохранение авторства**: Необходимо сохранять копирайты и указывать авторство

### Почему AGPL-3.0?

AGPL-3.0 выбрана для обеспечения того, чтобы:
1. Код всегда оставался открытым и доступным сообществу
2. Любые улучшения возвращались в проект
3. Даже облачные сервисы на базе этого кода делились исходниками

### Приватные компоненты

Расширенный функционал синхронизации (`sync_proprietary/`) находится в отдельном приватном репозитории и не распространяется под AGPL-3.0. Базовый функционал (экспорт/импорт) полностью открыт.

### Полный текст лицензии

Полный текст лицензии доступен в файле [LICENSE](LICENSE) или на [gnu.org](https://www.gnu.org/licenses/agpl-3.0.html)

**Copyright © 2024 BarykinME**
