# Implementation Plan: Исправление кнопки "Показать все" в виджете плановых транзакций

## Overview

Реализация навигации при нажатии кнопки "Показать все" в PlannedTransactionsWidget на главном экране. Включает передачу метода навигации из MainWindow в HomeView и реализацию метода on_show_all_occurrences с обработкой ошибок.

## Tasks

- [x] 1. Обновить HomeView для поддержки navigate_callback
  - Добавить параметр `navigate_callback: Optional[Callable[[int], None]]` в конструктор
  - Сохранить callback как атрибут экземпляра `self.navigate_callback`
  - Обновить docstring конструктора с описанием нового параметра
  - _Requirements: 2.1_

- [x] 2. Реализовать метод on_show_all_occurrences в HomeView
  - Удалить TODO комментарий
  - Реализовать проверку наличия navigate_callback
  - Добавить вызов navigate_callback(1) в try-except блоке
  - Добавить логирование успешной навигации
  - Добавить логирование предупреждения при отсутствии callback
  - Добавить логирование ошибок при исключениях
  - _Requirements: 1.1, 3.1, 3.2_

- [x] 2.1 Написать unit тест для on_show_all_occurrences с callback
  - Создать HomeView с mock navigate_callback
  - Вызвать on_show_all_occurrences()
  - Проверить вызов navigate_callback с аргументом 1
  - _Requirements: 1.1, 2.2_

- [x] 2.2 Написать unit тест для on_show_all_occurrences без callback
  - Создать HomeView с navigate_callback=None
  - Вызвать on_show_all_occurrences()
  - Проверить логирование предупреждения
  - Проверить отсутствие исключений
  - _Requirements: 3.1, 3.3_

- [x] 2.3 Написать unit тест для обработки ошибок навигации
  - Создать HomeView с mock navigate_callback, выбрасывающим исключение
  - Вызвать on_show_all_occurrences()
  - Проверить логирование ошибки
  - Проверить, что исключение не распространяется
  - _Requirements: 3.2_

- [x] 3. Обновить MainWindow для передачи navigate в HomeView
  - Изменить создание HomeView в методе init_ui()
  - Добавить параметр `navigate_callback=self.navigate`
  - _Requirements: 2.1_

- [x] 3.1 Написать unit тест для передачи navigate в HomeView
  - Создать MainWindow
  - Проверить, что HomeView создан с navigate_callback
  - Проверить, что navigate_callback является callable
  - _Requirements: 2.1_

- [x] 4. Checkpoint - Проверить базовую функциональность
  - Убедиться, что все unit тесты проходят
  - Убедиться, что приложение запускается без ошибок
  - Спросить пользователя, если возникли вопросы

- [x] 5. Написать property-based тест для навигации
  - **Property 1: Навигация вызывается при нажатии кнопки**
  - **Validates: Requirements 1.1, 2.2**
  - Генерировать случайные mock callbacks
  - Создавать HomeView с этими callbacks
  - Вызывать on_show_all_occurrences()
  - Проверять вызов callback с индексом 1

- [x] 6. Написать property-based тест для безопасности
  - **Property 2: Безопасность при отсутствии навигации**
  - **Validates: Requirements 3.1, 3.3**
  - Создавать HomeView с navigate_callback=None
  - Вызывать on_show_all_occurrences() множество раз
  - Проверять отсутствие исключений

- [x] 7. Написать property-based тест для логирования ошибок
  - **Property 3: Логирование при ошибках навигации**
  - **Validates: Requirements 3.2**
  - Генерировать случайные исключения
  - Создавать mock callbacks, выбрасывающие исключения
  - Вызывать on_show_all_occurrences()
  - Проверять логирование ошибок

- [x] 8. Написать интеграционный тест для полного сценария
  - Создать MainWindow с реальными компонентами
  - Получить HomeView из content_area
  - Вызвать on_show_all_occurrences()
  - Проверить rail.selected_index = 1
  - Проверить content_area.content является PlannedTransactionsView
  - Проверить settings.last_selected_index = 1
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 9. Обновить существующие тесты HomeView
  - Найти тесты, создающие HomeView
  - Добавить параметр navigate_callback=Mock() где необходимо
  - Убедиться, что все тесты проходят
  - _Requirements: 2.1_

- [x] 10. Final checkpoint - Проверить всю функциональность
  - Убедиться, что все тесты проходят (unit, property-based, integration)
  - Запустить приложение и вручную проверить кнопку "Показать все"
  - Проверить, что навигация работает корректно
  - Проверить логирование в разных сценариях
  - Спросить пользователя, если возникли вопросы

## Notes

- Все задачи являются обязательными для полного покрытия тестами
- Каждая задача ссылается на конкретные требования для отслеживаемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property-based тесты валидируют универсальные свойства корректности
- Unit тесты валидируют конкретные примеры и граничные случаи
- Интеграционный тест проверяет end-to-end сценарий
