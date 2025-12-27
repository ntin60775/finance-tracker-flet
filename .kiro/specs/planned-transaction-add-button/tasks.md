# Implementation Plan: Кнопка добавления плановых транзакций

## Обзор

План реализации функциональности добавления кнопки для создания новых плановых транзакций на панели плановых транзакций главного экрана.

## Задачи

- [x] 1. Модификация PlannedTransactionsWidget
  - [x] 1.1 Добавить параметр `on_add_planned_transaction` в конструктор
    - Добавить опциональный callback `on_add_planned_transaction: Optional[Callable[[], None]]`
    - Сохранить callback в атрибут экземпляра
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Добавить кнопку добавления в заголовок виджета
    - Создать `ft.IconButton` с иконкой `ft.Icons.ADD`
    - Установить `icon_color=ft.Colors.PRIMARY`
    - Установить `tooltip="Добавить плановую транзакцию"`
    - Привязать `on_click` к callback
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.3 Обновить layout заголовка
    - Изменить структуру Row в заголовке: [Title] [+Add] [Show All]
    - Кнопка добавления отображается только если callback задан
    - _Requirements: 2.1_

  - [x] 1.4 Написать unit тесты для PlannedTransactionsWidget
    - Тест наличия кнопки добавления при заданном callback
    - Тест отсутствия кнопки при callback=None
    - Тест атрибутов кнопки (icon, tooltip, color)
    - Тест вызова callback при нажатии
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Модификация HomePresenter
  - [x] 2.1 Добавить метод `create_planned_transaction`
    - Принимает `PlannedTransactionCreate` как параметр
    - Вызывает `planned_transaction_service.create_planned_transaction()`
    - Логирует операцию создания
    - _Requirements: 1.3, 3.2_

  - [x] 2.2 Реализовать обновление данных после создания
    - Вызывать `refresh_data()` после успешного создания
    - Вызывать `view.show_message()` с сообщением об успехе
    - _Requirements: 1.4, 1.5, 3.3, 4.1, 4.2, 4.4_

  - [x] 2.3 Реализовать обработку ошибок
    - Перехватывать исключения при создании
    - Логировать ошибки с полным контекстом
    - Вызывать `view.show_error()` с сообщением об ошибке
    - _Requirements: 3.4, 5.2_

  - [x] 2.4 Написать property test для создания плановой транзакции
    - **Property 2: Создание плановой транзакции сохраняет данные в БД**
    - **Validates: Requirements 1.3**

  - [x] 2.5 Написать property test для обновления компонентов
    - **Property 3: После создания транзакции обновляются все зависимые компоненты**
    - **Validates: Requirements 1.4, 3.3, 4.1, 4.2**

- [x] 3. Модификация HomeView
  - [x] 3.1 Добавить импорт PlannedTransactionModal
    - Импортировать `PlannedTransactionModal` из `finance_tracker.components`
    - Импортировать `PlannedTransactionCreate` из `finance_tracker.models`
    - _Requirements: 3.1_

  - [x] 3.2 Создать экземпляр PlannedTransactionModal
    - Инициализировать в `__init__` с `session` и `on_save` callback
    - Callback должен вызывать `on_planned_transaction_saved`
    - _Requirements: 3.1, 6.1, 6.2, 6.3_

  - [x] 3.3 Добавить метод `on_add_planned_transaction`
    - Проверять наличие `page`
    - Открывать модальное окно через `planned_transaction_modal.open()`
    - Передавать `selected_date` как начальную дату
    - Логировать операцию
    - _Requirements: 1.2, 6.1_

  - [x] 3.4 Добавить метод `on_planned_transaction_saved`
    - Принимать `PlannedTransactionCreate` как параметр
    - Делегировать в `presenter.create_planned_transaction()`
    - _Requirements: 3.2_

  - [x] 3.5 Обновить инициализацию PlannedTransactionsWidget
    - Передать `on_add_planned_transaction` callback в конструктор
    - _Requirements: 1.1, 1.2_

  - [x] 3.6 Написать unit тесты для HomeView
    - Тест инициализации PlannedTransactionModal
    - Тест открытия модального окна
    - Тест делегирования в Presenter
    - _Requirements: 3.1, 3.2, 6.1, 6.2_

  - [x] 3.7 Написать property test для callback цепочки
    - **Property 1: Callback вызывается при нажатии кнопки добавления**
    - **Validates: Requirements 1.2, 3.2**

- [x] 4. Checkpoint - Проверка базовой функциональности
  - Убедиться, что все тесты проходят
  - Проверить работу кнопки добавления в UI
  - Проверить открытие модального окна
  - Проверить создание плановой транзакции
  - Спросить пользователя при возникновении вопросов

- [x] 5. Написать property test для обработки ошибок
  - **Property 4: При ошибке создания показывается сообщение и модальное окно остаётся открытым**
  - **Validates: Requirements 3.4, 5.2, 5.3**

- [x] 6. Финальный checkpoint
  - Убедиться, что все тесты проходят
  - Проверить полный цикл создания плановой транзакции
  - Проверить обновление виджета и календаря
  - Спросить пользователя при возникновении вопросов

## Примечания

- Задачи с `*` являются опциональными (тесты)
- Каждая задача ссылается на конкретные требования для трассируемости
- Property tests используют библиотеку Hypothesis
- Checkpoints позволяют проверить промежуточные результаты
