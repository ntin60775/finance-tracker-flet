# Design Document

## Overview

Документ описывает техническую реализацию реорганизации структуры проекта Finance Tracker Flet с переходом на стандартную src-layout архитектуру. Миграция включает перемещение всех исходных модулей в `src/finance_tracker/`, обновление импортов, изоляцию пользовательских данных в `~/.finance_tracker_data/`, создание правильной конфигурации сборки и добавление лицензии AGPL-3.0.

Ключевые цели:
- Чистая корневая директория с конфигурационными файлами
- Стандартная src-layout структура для упрощения тестирования и распространения
- Изоляция пользовательских данных от кода приложения
- Корректная работа в режимах разработки и .exe
- Сохранение всей существующей функциональности

## Architecture

### Текущая структура (проблемная)

```
finance-tracker-flet/
├── app.py                    # В корне
├── config.py                 # В корне
├── database.py               # В корне
├── main.py                   # Launcher в корне
├── components/               # Модули в корне
├── models/
├── services/
├── utils/
├── views/
├── tests/                    # Тесты в корне
├── assets/
├── build/                    # Build-артефакты
├── dist/
├── finance.db                # БД создаётся в корне
├── finance_tracker.log       # Логи в корне
└── pyproject.toml
```

Проблемы:
- Модули смешаны с конфигурационными файлами
- Пользовательские данные (БД, логи) в корне проекта
- Сложно тестировать (импорты из корня)
- Не соответствует стандартам Python packaging

### Целевая структура (стандартная)

```
finance-tracker-flet/
├── src/
│   └── finance_tracker/           # Основной пакет
│       ├── __init__.py
│       ├── __main__.py            # Точка входа (python -m finance_tracker)
│       ├── app.py                 # Главная логика приложения
│       ├── config.py              # Конфигурация
│       ├── database.py            # Управление БД
│       ├── components/            # UI компоненты
│       │   ├── __init__.py
│       │   ├── calendar_legend.py
│       │   ├── calendar_widget.py
│       │   └── ...
│       ├── models/                # Модели данных
│       │   ├── __init__.py
│       │   ├── enums.py
│       │   └── models.py
│       ├── services/              # Бизнес-логика
│       │   ├── __init__.py
│       │   ├── category_service.py
│       │   └── ...
│       ├── utils/                 # Утилиты
│       │   ├── __init__.py
│       │   ├── logger.py
│       │   └── ...
│       ├── views/                 # UI представления
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   └── ...
│       └── mobile/                # Мобильный функционал (заглушки)
│           ├── __init__.py
│           ├── export_service.py  # Публичный: экспорт в файлы
│           ├── import_service.py  # Публичный: импорт из файлов
│           └── sync_proprietary/  # Git submodule → приватный репозиторий
│               ├── __init__.py
│               ├── cloud_sync.py  # Приватный: синхронизация через облако
│               └── realtime_sync.py # Приватный: real-time синхронизация
├── tests/                         # Тесты на уровне с src/
│   ├── conftest.py
│   ├── test_transaction_properties.py
│   ├── test_mobile_export.py      # Тесты публичного функционала
│   └── ...
├── assets/                        # Статические ресурсы
│   ├── icon.ico
│   ├── icon.png
│   └── prompts/
├── .kiro/                         # Спецификации Kiro
│   └── specs/
├── .gitmodules                    # Конфигурация Git submodules
├── main.py                        # Простой launcher (опционально)
├── pyproject.toml                 # Конфигурация проекта
├── .gitignore                     # Git ignore правила
├── LICENSE                        # AGPL-3.0 лицензия
└── README.md                      # Документация

# Пользовательские данные (вне проекта)
~/.finance_tracker_data/
├── finance.db                     # База данных
├── config.json                    # Настройки пользователя
├── exports/                       # Экспортированные файлы
│   └── backup_2024_12_07.json
└── logs/                          # Логи приложения
    └── finance_tracker.log

# Приватный репозиторий (submodule)
finance-tracker-sync-proprietary/
├── __init__.py
├── cloud_sync.py                  # Синхронизация через облако
├── realtime_sync.py               # Real-time синхронизация
├── encryption.py                  # Шифрование данных
└── README.md
```

Преимущества:
- ✅ Чистая корневая директория
- ✅ Стандартная структура для Python проектов
- ✅ Изоляция пользовательских данных
- ✅ Простое тестирование через установленный пакет
- ✅ Корректная работа pip install -e .

## Components and Interfaces

### 1. Структура пакета

**src/finance_tracker/mobile/__init__.py**
```python
"""
Модуль мобильного функционала.

Содержит:
- Публичный функционал: экспорт/импорт в файлы
- Приватный функционал (опционально): облачная синхронизация
"""

# Публичный функционал (всегда доступен)
from finance_tracker.mobile.export_service import ExportService
from finance_tracker.mobile.import_service import ImportService

# Приватный функционал (доступен только если submodule установлен)
try:
    from finance_tracker.mobile.sync_proprietary import CloudSyncService, RealtimeSyncService
    PROPRIETARY_AVAILABLE = True
except ImportError:
    # Заглушки для работы без приватного модуля
    CloudSyncService = None
    RealtimeSyncService = None
    PROPRIETARY_AVAILABLE = False

__all__ = [
    "ExportService",
    "ImportService",
    "CloudSyncService",
    "RealtimeSyncService",
    "PROPRIETARY_AVAILABLE",
]
```

**src/finance_tracker/mobile/export_service.py (публичный)**
```python
"""
Сервис экспорта данных в файлы.

Публичный функционал - доступен всем пользователям.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """
    Сервис для экспорта данных приложения в JSON файлы.
    
    Экспортирует:
    - Транзакции
    - Категории
    - Кредиты
    - Настройки
    """
    
    @staticmethod
    def export_to_file(filepath: str = None) -> str:
        """
        Экспортирует все данные в JSON файл.
        
        Args:
            filepath: Путь к файлу экспорта. Если None - создаётся автоматически
            
        Returns:
            str: Путь к созданному файлу
            
        Raises:
            IOError: Ошибка записи файла
        """
        if filepath is None:
            # Создаём директорию для экспортов
            export_dir = settings.user_data_dir / "exports"
            export_dir.mkdir(exist_ok=True)
            
            # Генерируем имя файла с датой
            timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
            filepath = str(export_dir / f"backup_{timestamp}.json")
        
        logger.info(f"Начало экспорта данных в {filepath}")
        
        # TODO: Реализовать экспорт данных из БД
        data = {
            "version": "2.0.0",
            "export_date": datetime.now().isoformat(),
            "transactions": [],
            "categories": [],
            "loans": [],
            "settings": {},
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Экспорт завершён: {filepath}")
        return filepath
```

**src/finance_tracker/mobile/import_service.py (публичный)**
```python
"""
Сервис импорта данных из файлов.

Публичный функционал - доступен всем пользователям.
"""

import json
from typing import Dict, Any

from finance_tracker.database import get_db_session
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ImportService:
    """
    Сервис для импорта данных из JSON файлов.
    """
    
    @staticmethod
    def import_from_file(filepath: str) -> Dict[str, int]:
        """
        Импортирует данные из JSON файла.
        
        Args:
            filepath: Путь к файлу импорта
            
        Returns:
            Dict[str, int]: Статистика импорта (количество импортированных записей)
            
        Raises:
            FileNotFoundError: Файл не найден
            ValueError: Некорректный формат файла
        """
        logger.info(f"Начало импорта данных из {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверка версии
        if data.get("version") != "2.0.0":
            raise ValueError(f"Неподдерживаемая версия файла: {data.get('version')}")
        
        # TODO: Реализовать импорт данных в БД
        stats = {
            "transactions": 0,
            "categories": 0,
            "loans": 0,
        }
        
        logger.info(f"Импорт завершён: {stats}")
        return stats
```

**src/finance_tracker/mobile/sync_proprietary/__init__.py (приватный submodule)**
```python
"""
Приватный модуль расширенной синхронизации.

Доступен только при наличии лицензии.
"""

# Заглушки - реальная реализация в приватном репозитории
class CloudSyncService:
    """Заглушка для облачной синхронизации."""
    
    def __init__(self):
        raise NotImplementedError(
            "CloudSyncService доступен только в расширенной версии. "
            "Используйте ExportService/ImportService для базового функционала."
        )


class RealtimeSyncService:
    """Заглушка для real-time синхронизации."""
    
    def __init__(self):
        raise NotImplementedError(
            "RealtimeSyncService доступен только в расширенной версии. "
            "Используйте ExportService/ImportService для базового функционала."
        )


__all__ = ["CloudSyncService", "RealtimeSyncService"]
```

**.gitmodules**
```ini
[submodule "src/finance_tracker/mobile/sync_proprietary"]
    path = src/finance_tracker/mobile/sync_proprietary
    url = https://github.com/BarykinME/finance-tracker-sync-proprietary.git
    branch = main
```

### 2. Структура пакета (основная)

**src/finance_tracker/__init__.py**
```python
"""
Finance Tracker Flet - десктопное приложение для учёта финансов.

Основной пакет приложения.
"""

__version__ = "2.0.0"
__author__ = "BarykinME"
__license__ = "AGPL-3.0"
```

**src/finance_tracker/__main__.py**
```python
"""
Точка входа для запуска через python -m finance_tracker
"""
import flet as ft
from finance_tracker.app import main

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
```

**main.py (launcher в корне)**
```python
"""
Простой launcher для запуска из корня проекта в режиме разработки.
"""
from finance_tracker.__main__ import main as run_app
import flet as ft

if __name__ == "__main__":
    ft.app(target=run_app, assets_dir="assets")
```

### 2. Обновление импортов

Все импорты должны использовать полный путь от корня пакета:

**Было (относительные импорты):**
```python
from config import settings
from database import get_db_session
from models import TransactionDB
from services.transaction_service import TransactionService
```

**Стало (абсолютные импорты):**
```python
from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.models import TransactionDB
from finance_tracker.services.transaction_service import TransactionService
```

### 3. Управление путями к ресурсам

**Проблема:** Текущий код использует `__file__` для определения путей, что работает только в режиме разработки.

**Решение:** Использовать `importlib.resources` (Python 3.9+) или `pkg_resources` для корректного разрешения путей.

**src/finance_tracker/config.py - обновлённая логика путей:**

```python
import os
from pathlib import Path
from typing import Optional

class Config:
    """Конфигурация приложения с поддержкой пользовательской директории данных."""
    
    _instance = None
    
    APP_NAME = "Finance Tracker"
    VERSION = "2.0.0"
    
    # Директория для пользовательских данных
    @staticmethod
    def get_user_data_dir() -> Path:
        """
        Возвращает путь к директории пользовательских данных.
        
        Returns:
            Path: ~/.finance_tracker_data/
        """
        home = Path.home()
        data_dir = home / ".finance_tracker_data"
        
        # Создаём директорию, если не существует
        data_dir.mkdir(exist_ok=True)
        
        # Создаём поддиректорию для логов
        logs_dir = data_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        return data_dir
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Получаем директорию пользовательских данных
        self.user_data_dir = self.get_user_data_dir()
        
        # Пути к файлам
        self.db_path = str(self.user_data_dir / "finance.db")
        self.config_file = str(self.user_data_dir / "config.json")
        self.log_file = str(self.user_data_dir / "logs" / "finance_tracker.log")
        
        # Остальные настройки...
        self.theme_mode = "light"
        self.window_width = 1200
        self.window_height = 800
        # ...
        
        # Загрузка настроек
        self.load()
```

**src/finance_tracker/database.py - обновлённая логика путей:**

```python
from finance_tracker.config import settings

def get_database_path() -> str:
    """
    Возвращает путь к файлу базы данных из конфигурации.
    
    Returns:
        str: Путь к finance.db в ~/.finance_tracker_data/
    """
    return settings.db_path
```

### 4. Обновление конфигурации сборки

**pyproject.toml:**

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "finance_tracker_flet"
version = "2.0.0"
description = "Finance Tracker desktop application built with Flet"
authors = [{name = "BarykinME"}]
license = {text = "AGPL-3.0"}
requires-python = ">=3.9"
dependencies = [
    "flet>=0.25.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.21.0",
    "hypothesis>=6.80.0",
]

[project.scripts]
finance-tracker = "finance_tracker.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["finance_tracker*"]
namespaces = false
```

**finance_tracker.spec (для PyInstaller):**

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/finance_tracker/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'finance_tracker.models',
        'finance_tracker.services',
        'finance_tracker.views',
        'finance_tracker.components',
        'finance_tracker.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FinanceTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
```

## Data Models

Модели данных остаются без изменений, только обновляются импорты:

**src/finance_tracker/models/__init__.py:**
```python
"""Модели данных приложения."""

from finance_tracker.models.enums import TransactionType, RecurrenceType, LoanType
from finance_tracker.models.models import (
    Base,
    CategoryDB,
    TransactionDB,
    LenderDB,
    LoanDB,
    LoanPaymentDB,
    PlannedTransactionDB,
    PendingPaymentDB,
)

__all__ = [
    "TransactionType",
    "RecurrenceType",
    "LoanType",
    "Base",
    "CategoryDB",
    "TransactionDB",
    "LenderDB",
    "LoanDB",
    "LoanPaymentDB",
    "PlannedTransactionDB",
    "PendingPaymentDB",
]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Структура директорий соответствует стандарту

*For any* момент после миграции, корневая директория проекта должна содержать только конфигурационные файлы (pyproject.toml, .gitignore, LICENSE, README.md), директории src/, tests/, assets/, .kiro/ и опциональный main.py launcher. Все исходные модули Python должны находиться в src/finance_tracker/.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: Импорты используют абсолютные пути

*For any* Python файл в проекте, все импорты модулей приложения должны использовать полный путь от корня пакета (начинаться с `finance_tracker.`), а не относительные импорты.

**Validates: Requirements 2.2, 4.2**

### Property 3: Пользовательские данные изолированы

*For any* файл пользовательских данных (база данных, логи, настройки), он должен находиться в директории `~/.finance_tracker_data/`, а не в корне проекта или рядом с исполняемым файлом.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 4: Приложение запускается из разных точек входа

*For any* способ запуска (`python -m finance_tracker`, `python main.py`, или .exe файл), приложение должно корректно запускаться и находить все ресурсы (assets, база данных, конфигурация).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 5: Существующая функциональность сохранена

*For any* функция приложения (создание транзакций, работа с БД, UI, логирование), она должна работать идентично до и после рефакторинга структуры.

**Validates: Requirements 4.1, 4.3**

### Property 6: Тесты проходят после миграции

*For any* существующий тест в директории tests/, он должен успешно проходить после обновления импортов и структуры проекта.

**Validates: Requirements 2.3, 4.4**

### Property 7: Build-артефакты игнорируются Git

*For any* build-артефакт (dist/, build/, *.egg-info/, __pycache__/, *.pyc), он должен быть добавлен в .gitignore и не попадать в репозиторий.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6**

### Property 8: Лицензия корректно применена

*For any* файл LICENSE в корне проекта, он должен содержать полный текст лицензии AGPL-3.0 с указанием автора (BarykinME) и года создания (2024).

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 9: Мобильный функционал работает без submodule

*For any* запуск приложения без установленного submodule sync_proprietary, публичный функционал (ExportService, ImportService) должен работать корректно, а попытка использования приватного функционала должна выдавать понятное сообщение об ошибке.

**Validates: Requirements 10.3, 10.5**

### Property 10: Submodule корректно настроен

*For any* клонирование проекта с флагом --recurse-submodules, директория src/finance_tracker/mobile/sync_proprietary/ должна содержать код из приватного репозитория, и приватный функционал должен быть доступен.

**Validates: Requirements 10.2, 10.4, 10.6**

## Error Handling

### Миграция файлов

**Проблема:** При перемещении файлов могут возникнуть конфликты или потеря данных.

**Решение:**
- Создать резервную копию проекта перед миграцией
- Использовать `shutil.move()` для атомарного перемещения
- Логировать каждое перемещение файла
- В случае ошибки - откатить изменения из резервной копии

### Обновление импортов

**Проблема:** Пропущенные импорты приведут к ошибкам во время выполнения.

**Решение:**
- Использовать автоматический поиск и замену импортов
- Проверить все файлы с помощью `grep` или `rg`
- Запустить статический анализ (mypy, pylint)
- Запустить все тесты для проверки

### Пути к ресурсам

**Проблема:** Неправильные пути к assets или БД приведут к ошибкам запуска.

**Решение:**
- Использовать `Path` из `pathlib` для кроссплатформенности
- Создавать директории с `mkdir(exist_ok=True)`
- Логировать все используемые пути при запуске
- Добавить fallback для режима .exe

### Совместимость с существующими данными

**Проблема:** Пользователи могут иметь существующую БД в старом месте.

**Решение:**
- При первом запуске проверить наличие старой БД в корне проекта
- Если найдена - предложить миграцию в новую директорию
- Скопировать (не переместить) данные для безопасности
- Логировать процесс миграции

## Testing Strategy

### Unit Tests

Существующие unit тесты должны быть обновлены для работы с новой структурой:

1. **Обновление импортов в тестах**
   - Заменить все импорты на абсолютные от `finance_tracker.`
   - Обновить `conftest.py` для корректной настройки путей

2. **Тестирование путей к ресурсам**
   - Проверить, что `Config.get_user_data_dir()` возвращает правильный путь
   - Проверить создание директорий при первом запуске
   - Проверить работу в режиме .exe (мокировать `sys.frozen`)

3. **Тестирование импортов**
   - Проверить, что все модули импортируются без ошибок
   - Проверить, что `python -m finance_tracker` запускается

### Property-Based Tests

Для проверки корректности миграции используем property-based тесты:

1. **Property Test: Все импорты абсолютные**
   - Сгенерировать список всех .py файлов в src/finance_tracker/
   - Для каждого файла проверить, что импорты начинаются с `finance_tracker.` или являются стандартными библиотеками
   - Использовать регулярные выражения для парсинга импортов

2. **Property Test: Структура директорий корректна**
   - Проверить наличие всех обязательных директорий (src/, tests/, assets/)
   - Проверить отсутствие модулей Python в корне (кроме main.py)
   - Проверить наличие __init__.py во всех пакетах

3. **Property Test: Пользовательские данные изолированы**
   - Запустить приложение в тестовом режиме
   - Проверить, что БД создаётся в ~/.finance_tracker_data/
   - Проверить, что логи создаются в ~/.finance_tracker_data/logs/
   - Проверить, что в корне проекта нет .db или .log файлов

### Integration Tests

1. **Тест полного цикла запуска**
   - Запустить приложение через `python -m finance_tracker`
   - Проверить инициализацию БД
   - Создать тестовую транзакцию
   - Проверить сохранение в БД
   - Закрыть приложение
   - Проверить, что данные сохранились

2. **Тест сборки .exe**
   - Собрать .exe через PyInstaller
   - Запустить .exe
   - Проверить создание пользовательских данных
   - Проверить работу основных функций

### Manual Testing Checklist

После автоматических тестов необходимо выполнить ручное тестирование:

- [ ] Запуск через `python -m finance_tracker`
- [ ] Запуск через `python main.py`
- [ ] Создание транзакции
- [ ] Создание кредита
- [ ] Просмотр статистики
- [ ] Изменение настроек
- [ ] Перезапуск приложения (проверка сохранения настроек)
- [ ] Сборка .exe
- [ ] Запуск .exe на чистой системе

## Implementation Notes

### Порядок миграции

1. **Создание новой структуры**
   - Создать src/finance_tracker/
   - Создать все необходимые __init__.py

2. **Перемещение модулей**
   - Переместить app.py, config.py, database.py в src/finance_tracker/
   - Переместить директории components/, models/, services/, utils/, views/ в src/finance_tracker/

3. **Обновление импортов**
   - Обновить импорты во всех файлах src/finance_tracker/
   - Обновить импорты в tests/

4. **Создание точек входа**
   - Создать src/finance_tracker/__main__.py
   - Обновить main.py в корне

5. **Обновление конфигурации**
   - Обновить pyproject.toml
   - Обновить finance_tracker.spec
   - Создать .gitignore
   - Создать LICENSE

6. **Обновление путей к данным**
   - Обновить config.py для использования ~/.finance_tracker_data/
   - Обновить database.py

7. **Тестирование**
   - Запустить все тесты
   - Выполнить ручное тестирование
   - Собрать .exe и протестировать

### Обратная совместимость

Для обеспечения плавного перехода:

1. **Миграция существующих данных**
   - При первом запуске проверить наличие finance.db в корне
   - Если найдена - скопировать в ~/.finance_tracker_data/
   - Показать пользователю уведомление о миграции

2. **Сохранение старого launcher**
   - Оставить main.py в корне для удобства разработки
   - Добавить комментарий о рекомендуемом способе запуска

### Работа с Git Submodules

**Клонирование проекта с submodules:**
```bash
# Полное клонирование (с приватным функционалом)
git clone --recurse-submodules https://github.com/BarykinME/finance-tracker-flet.git

# Или после обычного клонирования
git clone https://github.com/BarykinME/finance-tracker-flet.git
cd finance-tracker-flet
git submodule init
git submodule update
```

**Обновление submodules:**
```bash
# Обновить все submodules до последней версии
git submodule update --remote

# Обновить конкретный submodule
git submodule update --remote src/finance_tracker/mobile/sync_proprietary
```

**Добавление submodule (для первоначальной настройки):**
```bash
# Добавить приватный репозиторий как submodule
git submodule add https://github.com/BarykinME/finance-tracker-sync-proprietary.git src/finance_tracker/mobile/sync_proprietary

# Закоммитить изменения
git add .gitmodules src/finance_tracker/mobile/sync_proprietary
git commit -m "Add proprietary sync submodule"
```

### Документация

После миграции обновить README.md:

1. **Структура проекта**
   - Описать новую организацию директорий
   - Объяснить назначение каждой директории
   - Описать разделение на публичный и приватный код

2. **Установка и запуск**
   - Команды для установки зависимостей
   - Способы запуска приложения
   - Сборка .exe
   - Работа с Git submodules

3. **Разработка**
   - Как добавлять новые модули
   - Как запускать тесты
   - Как собирать проект
   - Как работать с приватным функционалом

4. **Мобильный функционал**
   - Описание публичного функционала (экспорт/импорт)
   - Описание приватного функционала (синхронизация)
   - Как получить доступ к расширенным возможностям

5. **Лицензия**
   - Информация об AGPL-3.0
   - Условия использования
   - Контакты автора
   - Информация о приватных компонентах
