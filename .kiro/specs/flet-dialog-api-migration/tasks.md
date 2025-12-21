# Implementation Plan: Миграция на современный Flet Dialog API

## Overview

План миграции всей кодовой базы Finance Tracker с устаревшего Flet Dialog API (`page.dialog =`, `dialog.open = True`) на современный подход через `page.open()` и `page.close()`.

Миграция выполняется в три этапа:
1. Миграция production кода (components и views)
2. Обновление тестов для удаления устаревших mock атрибутов
3. Обновление steering правил и документации

## Tasks

### Этап 1: Миграция Components (Модальные окна)

- [x] 1. Мигрировать planned_transaction_modal.py на современный API
  - Заменить `self.page.dialog = self.dialog` на использование `page.open(self.dialog)`
  - Заменить `self.dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 2. Мигрировать pending_payment_modal.py на современный API
  - Заменить `self.page.dialog = self.dialog` на использование `page.open(self.dialog)`
  - Заменить `self.dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 3. Мигрировать occurrence_details_modal.py на современный API
  - Заменить `page.dialog = self` на использование `page.open(self)`
  - Заменить `self.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 4. Мигрировать execute_pending_payment_modal.py на современный API
  - Заменить `self.page.dialog = self.dialog` на использование `page.open(self.dialog)`
  - Заменить `self.dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 5. Мигрировать execute_occurrence_modal.py на современный API
  - Заменить `self.page.dialog = self.dialog` на использование `page.open(self.dialog)`
  - Заменить `self.dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [x] 6. Мигрировать early_repayment_modal.py на современный API
  - Заменить `page.dialog = self.dialog` на использование `page.open(self.dialog)`
  - Заменить `self.dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2_

- [ ] 7. Checkpoint - Запустить тесты после миграции components
  - Запустить полный набор тестов: `pytest tests/ -v`
  - Убедиться, что все тесты проходят
  - Если тесты падают - исправить проблемы
  - _Requirements: 4.5, 4.6_

### Этап 2: Миграция Views (Представления)

- [ ] 8. Мигрировать pending_payments_view.py на современный API
  - Заменить `self.page.dialog = dialog` на использование `self.page.open(dialog)`
  - Заменить `dialog.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 9. Мигрировать planned_transactions_view.py на современный API
  - Заменить `self.page.dialog = dlg` на использование `self.page.open(dlg)`
  - Заменить `dlg.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 10. Мигрировать categories_view.py на современный API
  - Заменить `self.page.dialog = dlg` на использование `self.page.open(dlg)`
  - Заменить `dlg.open = True` на вызов `page.open()`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 11. Мигрировать loans_view.py на современный API
  - Заменить использование `confirm_dialog.open = True` на `page.open(confirm_dialog)`
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 12. Мигрировать lenders_view.py на современный API
  - Заменить использование `confirm_dialog.open = True` на `page.open(confirm_dialog)`
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 13. Мигрировать loan_details_view.py на современный API
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 14. Мигрировать settings_view.py на современный API
  - Обновить использование SnackBar на `page.open(snack)` вместо `snack.open = True`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 15. Checkpoint - Запустить тесты после миграции views
  - Запустить полный набор тестов: `pytest tests/ -v`
  - Убедиться, что все тесты проходят
  - Если тесты падают - исправить проблемы
  - _Requirements: 5.5, 5.6_

### Этап 3: Миграция Utilities

- [ ] 16. Мигрировать error_handler.py на современный API
  - Обновить использование SnackBar на `page.open(snack_bar)` вместо `snack_bar.open = True`
  - Удалить избыточные вызовы `page.update()` после работы с диалогами
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 17. Checkpoint - Запустить тесты после миграции utilities
  - Запустить полный набор тестов: `pytest tests/ -v`
  - Убедиться, что все тесты проходят
  - Если тесты падают - исправить проблемы
  - _Requirements: 5.5, 5.6_

### Этап 4: Обновление Тестов

- [ ] 18. Обновить mock объекты в conftest.py
  - Убедиться, что все mock объекты Page имеют методы `open()` и `close()`
  - Удалить устаревший атрибут `page.dialog = None` из mock объектов (оставить только для обратной совместимости, если нужно)
  - Добавить комментарии о современном API
  - _Requirements: 3.2, 3.3, 3.4_

- [ ] 19. Обновить тесты в test_calendar_legend_ui.py
  - Заменить `modal.open = True` на использование `page.open(modal)`
  - Обновить проверки для использования современного API
  - _Requirements: 4.1, 4.2_

- [ ] 20. Проверить и обновить остальные тестовые файлы
  - Проверить test_view_base.py, test_ui_helpers.py, test_offstage_control_prevention.py
  - Убедиться, что все mock объекты используют современный API
  - Обновить комментарии в тестах для указания на современный API
  - _Requirements: 3.2, 3.3, 3.4_

- [ ] 21. Checkpoint - Запустить полный набор тестов
  - Запустить все тесты: `pytest tests/ -v`
  - Проверить покрытие кода: `pytest tests/ --cov=src/finance_tracker --cov-report=html`
  - Убедиться, что покрытие не снизилось
  - _Requirements: 7.1, 7.2, 7.3_

### Этап 5: Валидация и Документация

- [ ] 22. Создать скрипт проверки использования API
  - Создать Python скрипт для поиска устаревших паттернов в коде
  - Скрипт должен искать `page.dialog =`, `dialog.open = True`, `dialog.open = False`
  - Скрипт должен выводить список файлов и строк с устаревшим API
  - _Requirements: 1.1, 1.6, 2.1, 2.5, 9.1_

- [ ] 23. Запустить скрипт проверки на всей кодовой базе
  - Выполнить скрипт проверки
  - Убедиться, что не осталось устаревших паттернов в production коде
  - Если найдены - исправить
  - _Requirements: 1.6, 2.5, 2.6_

- [ ] 24. Обновить steering правила в ui-testing.md
  - Добавить раздел о обязательном использовании `page.open()` и `page.close()`
  - Добавить примеры правильного и неправильного использования API
  - Добавить checklist для проверки нового кода
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 25. Обновить tech.md с требованиями к Dialog API
  - Добавить раздел "Dialog Management Standard"
  - Указать обязательное использование современного API
  - Добавить примеры кода
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 26. Final Checkpoint - Полная валидация
  - Запустить все тесты: `pytest tests/ -v`
  - Запустить приложение и проверить все модальные окна вручную
  - Проверить, что все диалоги открываются и закрываются корректно
  - Убедиться, что не осталось регрессий
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

## Notes

### Порядок миграции

Миграция выполняется в следующем порядке:
1. **Components** - модальные окна, которые используются в разных местах
2. **Views** - представления, которые используют модальные окна
3. **Utilities** - вспомогательные модули
4. **Tests** - обновление тестов для соответствия новому API

### Критические точки

- После каждого этапа обязательно запускать тесты
- При падении тестов - немедленно исправлять проблемы
- Не переходить к следующему этапу, пока не пройдут все тесты текущего

### Откат изменений

Если после миграции обнаружены критические проблемы:
1. Откатить изменения через Git: `git revert <commit>`
2. Проанализировать причину проблемы
3. Исправить и повторить миграцию

### Проверка после миграции

После завершения всех задач необходимо:
- Запустить приложение и проверить все функции вручную
- Убедиться, что все модальные окна открываются корректно
- Проверить, что SnackBar сообщения отображаются правильно
- Убедиться, что нет регрессий в функциональности
