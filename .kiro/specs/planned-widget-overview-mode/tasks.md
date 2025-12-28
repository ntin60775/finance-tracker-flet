# Implementation Plan: Planned Widget Overview Mode

## Overview

Рефакторинг виджета плановых транзакций для преобразования в обзорный режим. Убираем кнопки действий из карточек, добавляем навигацию по клику.

## Tasks

- [x] 1. Модификация PlannedTransactionsWidget
  - [x] 1.1 Добавить новый параметр on_occurrence_click в конструктор
    - Добавить опциональный параметр `on_occurrence_click: Optional[Callable[[PlannedOccurrence], None]] = None`
    - Сохранить обратную совместимость с существующими параметрами
    - _Requirements: 5.1, 5.3_

  - [x] 1.2 Удалить кнопки действий из карточек вхождений
    - Изменить метод `_build_action_buttons` чтобы возвращал пустой список
    - Убрать Row с кнопками из `_build_occurrence_card`
    - _Requirements: 1.1, 5.2_

  - [x] 1.3 Добавить клик на карточку вхождения
    - Добавить `on_click` в Container карточки
    - Реализовать метод `_on_card_click` для вызова callback
    - Добавить hover-эффект для индикации кликабельности
    - _Requirements: 2.1, 2.3_

  - [x] 1.4 Улучшить сортировку просроченных вхождений
    - Просроченные вхождения должны отображаться первыми в списке
    - Сортировка: просроченные по дате (старые первыми), затем будущие по дате
    - _Requirements: 4.3_

  - [x] 1.5 Написать unit тесты для PlannedTransactionsWidget
    - Тест инициализации с новым callback
    - Тест что карточки не содержат кнопок действий
    - Тест вызова callback при клике
    - Тест сортировки просроченных вхождений
    - _Requirements: 1.1, 2.1, 4.3, 5.3_

- [x] 2. Интеграция с HomeView
  - [x] 2.1 Добавить обработчик on_occurrence_clicked в HomeView
    - Реализовать метод `on_occurrence_clicked(occurrence: PlannedOccurrence)`
    - Вызывать `self.presenter.on_date_selected(occurrence.occurrence_date)`
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Обновить инициализацию PlannedTransactionsWidget в HomeView
    - Передать новый callback `on_occurrence_click=self.on_occurrence_clicked`
    - _Requirements: 2.1_

  - [x] 2.3 Написать unit тесты для интеграции
    - Тест что клик на вхождение вызывает presenter.on_date_selected
    - Тест что календарь обновляется при клике
    - _Requirements: 2.1, 2.2_

- [x] 3. Property-based тесты
  - [x] 3.1 Написать property тест для отсутствия кнопок действий
    - **Property 1: Карточки вхождений не содержат кнопок действий**
    - **Validates: Requirements 1.1, 5.2**

  - [x] 3.2 Написать property тест для просроченных вхождений
    - **Property 4: Просроченные вхождения визуально выделены**
    - **Validates: Requirements 4.1, 4.2**

  - [x] 3.3 Написать property тест для сортировки
    - **Property 5: Просроченные вхождения сортируются первыми**
    - **Validates: Requirements 4.3**

- [x] 4. Checkpoint - Проверка функционала
  - Ensure all tests pass, ask the user if questions arise.
  - Запустить приложение и проверить:
    - Карточки в левой панели не содержат кнопок
    - Клик на карточку переключает календарь на дату
    - Правая панель обновляется с данными для выбранной даты
    - Кнопки "+" и "Показать все" работают

## Notes

- Все задачи обязательны для полного покрытия тестами
- Обратная совместимость сохраняется — существующие callbacks принимаются, но игнорируются
- Визуальное выделение просроченных вхождений уже реализовано в текущей версии
