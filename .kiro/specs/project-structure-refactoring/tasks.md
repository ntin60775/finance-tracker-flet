# Implementation Plan

- [x] 1. Подготовка к миграции
  - Создать резервную копию проекта
  - Зафиксировать текущее состояние в локальном Git
  - _Requirements: 4.1_

- [x] 2. Создание новой структуры директорий
  - Создать src/finance_tracker/ с __init__.py
  - Создать все поддиректории (components/, models/, services/, utils/, views/, mobile/)
  - Создать __init__.py во всех пакетах
  - _Requirements: 1.2, 2.1_

- [x] 3. Перемещение основных модулей
  - Переместить app.py, config.py, database.py в src/finance_tracker/
  - Переместить директории components/, models/, services/, utils/, views/ в src/finance_tracker/
  - _Requirements: 1.2, 4.1_

- [x] 4. Обновление config.py для пользовательской директории данных
  - Реализовать метод get_user_data_dir() для создания ~/.finance_tracker_data/
  - Обновить пути к БД, логам и конфигурации
  - Добавить создание поддиректорий (logs/, exports/)
  - _Requirements: 6.4, 7.1, 7.2, 7.3, 7.4_

- [x] 5. Обновление database.py для новых путей
  - Обновить get_database_path() для использования settings.db_path
  - Убрать логику определения пути из database.py (теперь в config.py)
  - _Requirements: 6.2, 7.2, 7.5_

- [x] 6. Обновление импортов в основных модулях
  - Обновить импорты в src/finance_tracker/app.py
  - Обновить импорты в src/finance_tracker/config.py
  - Обновить импорты в src/finance_tracker/database.py
  - _Requirements: 2.2, 4.2_

- [x] 7. Обновление импортов в components/
  - Обновить импорты во всех файлах components/ на абсолютные от finance_tracker
  - _Requirements: 2.2, 4.2_

- [ ] 8. Обновление импортов в models/
  - Обновить импорты в models/__init__.py
  - Обновить импорты в models/enums.py
  - Обновить импорты в models/models.py
  - _Requirements: 2.2, 4.2_

- [ ] 9. Обновление импортов в services/
  - Обновить импорты во всех сервисах на абсолютные от finance_tracker
  - _Requirements: 2.2, 4.2_

- [ ] 10. Обновление импортов в utils/
  - Обновить импорты во всех утилитах на абсолютные от finance_tracker
  - _Requirements: 2.2, 4.2_

- [ ] 11. Обновление импортов в views/
  - Обновить импорты во всех представлениях на абсолютные от finance_tracker
  - _Requirements: 2.2, 4.2_

- [ ] 12. Создание точки входа __main__.py
  - Создать src/finance_tracker/__main__.py с функцией запуска
  - Импортировать и запускать finance_tracker.app.main
  - _Requirements: 3.1_

- [ ] 13. Обновление launcher main.py в корне
  - Обновить main.py для импорта из finance_tracker.__main__
  - Добавить комментарии о способах запуска
  - _Requirements: 3.2_

- [ ] 14. Создание публичного мобильного функционала
  - Создать src/finance_tracker/mobile/__init__.py с импортами и PROPRIETARY_AVAILABLE
  - Создать src/finance_tracker/mobile/export_service.py с ExportService
  - Создать src/finance_tracker/mobile/import_service.py с ImportService
  - _Requirements: 10.5_

- [ ] 15. Создание заглушек для приватного submodule
  - Создать src/finance_tracker/mobile/sync_proprietary/__init__.py с заглушками
  - Добавить CloudSyncService и RealtimeSyncService с NotImplementedError
  - _Requirements: 10.1, 10.3_

- [ ] 16. Настройка Git submodule
  - Создать .gitmodules с конфигурацией submodule
  - Добавить путь к приватному репозиторию
  - _Requirements: 10.2, 10.6_

- [ ] 17. Обновление pyproject.toml
  - Обновить [tool.setuptools.packages.find] where = ["src"]
  - Добавить [project.scripts] для точки входа
  - Обновить версию до 2.0.0
  - Добавить license = {text = "AGPL-3.0"}
  - _Requirements: 5.1, 5.2_

- [ ] 18. Обновление finance_tracker.spec для PyInstaller
  - Обновить pathex на ['src']
  - Обновить точку входа на src/finance_tracker/__main__.py
  - Добавить hiddenimports для всех модулей
  - _Requirements: 3.3, 5.3, 5.4_

- [ ] 19. Создание .gitignore
  - Добавить Python-специфичные файлы (__pycache__/, *.pyc, *.pyo, *.pyd)
  - Добавить build-артефакты (dist/, build/, *.egg-info/, *.spec)
  - Добавить IDE файлы (.vscode/, .idea/, *.swp)
  - Добавить файлы тестирования (.pytest_cache/, .coverage, htmlcov/, .hypothesis/)
  - Добавить пользовательские данные (*.db, *.log, config.json)
  - Добавить виртуальные окружения (venv/, .venv/, env/)
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 20. Создание LICENSE файла
  - Скачать полный текст AGPL-3.0
  - Добавить Copyright 2024 BarykinME
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 21. Обновление импортов в тестах
  - Обновить импорты в tests/conftest.py
  - Обновить импорты во всех тестовых файлах на абсолютные от finance_tracker
  - _Requirements: 2.3, 4.2, 4.4_

- [ ] 22. Checkpoint - Запуск и проверка базового функционала
  - Запустить приложение через python -m finance_tracker
  - Проверить создание ~/.finance_tracker_data/
  - Проверить инициализацию БД
  - Проверить базовый UI
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 3.1, 4.3, 7.1_

- [ ] 23. Тестирование launcher
  - Запустить приложение через python main.py
  - Проверить идентичность работы с python -m finance_tracker
  - _Requirements: 3.2, 4.3_

- [ ] 24. Запуск всех тестов
  - Выполнить pytest для проверки всех тестов
  - Исправить найденные ошибки импортов
  - _Requirements: 2.3, 4.4_

- [ ] 25. Тестирование мобильного функционала без submodule
  - Проверить импорт finance_tracker.mobile
  - Проверить работу ExportService
  - Проверить работу ImportService
  - Проверить, что CloudSyncService выдаёт NotImplementedError
  - _Requirements: 10.3, 10.5_

- [ ] 26. Создание README.md
  - Добавить описание проекта
  - Добавить структуру директорий
  - Добавить инструкции по установке
  - Добавить способы запуска (python -m finance_tracker, python main.py)
  - Добавить инструкции по работе с Git submodules
  - Добавить описание мобильного функционала (публичный/приватный)
  - Добавить команды для тестирования
  - Добавить инструкции по сборке .exe
  - Добавить информацию о лицензии AGPL-3.0
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 27. Тестирование сборки .exe
  - Выполнить pyinstaller finance_tracker.spec
  - Запустить созданный .exe файл
  - Проверить создание ~/.finance_tracker_data/ в режиме .exe
  - Проверить работу всех функций
  - _Requirements: 3.3, 5.4, 7.5_

- [ ] 28. Очистка старых файлов
  - Удалить старые модули из корня (если остались)
  - Удалить старые build-артефакты
  - Удалить старые __pycache__ директории
  - _Requirements: 1.3_

- [ ] 29. Final Checkpoint - Полное тестирование
  - Запустить все тесты (pytest)
  - Запустить приложение всеми способами
  - Проверить работу экспорта/импорта
  - Проверить работу .exe
  - Проверить документацию
  - Ensure all tests pass, ask the user if questions arise.
  - Зафиксировать все изменения в локальном Git
  - Выполнить синхронизацию (создать удалённый репозиторий) с github
  - _Requirements: 4.3, 4.4_
