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
