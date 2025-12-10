# Requirements Document

## Introduction

Текущая архитектура `HomeView` имеет низкую тестируемость из-за тесной связанности с Flet UI компонентами, прямого управления сессией БД внутри view, и смешивания бизнес-логики с UI-логикой. Необходимо провести рефакторинг для достижения полного покрытия тестами всего основного функционала.

## Glossary

- **HomeView**: Главный экран приложения, отображающий календарь, транзакции и плановые операции
- **Presenter**: Компонент, содержащий бизнес-логику и координацию между сервисами и view
- **View**: UI-компонент, отвечающий только за отображение данных и делегирование действий пользователя
- **Session**: Сессия SQLAlchemy для работы с базой данных
- **Service Layer**: Слой бизнес-логики (transaction_service, loan_service и т.д.)
- **UI Component**: Flet-компонент (CalendarWidget, TransactionsPanel и т.д.)
- **Modal**: Модальное окно для взаимодействия с пользователем
- **Dependency Injection**: Паттерн передачи зависимостей через параметры конструктора

## Requirements

### Requirement 1

**User Story:** Как разработчик, я хочу иметь возможность тестировать бизнес-логику HomeView независимо от UI-фреймворка, чтобы обеспечить надёжность и упростить поддержку кода.

#### Acceptance Criteria

1. WHEN HomeView инициализируется THEN вся бизнес-логика SHALL быть изолирована в отдельном Presenter классе
2. WHEN Presenter выполняет операции с данными THEN он SHALL использовать только Service Layer и не SHALL напрямую взаимодействовать с UI компонентами
3. WHEN тесты запускаются для Presenter THEN они SHALL выполняться без инициализации Flet Page или UI компонентов
4. WHEN View получает события от пользователя THEN он SHALL делегировать обработку Presenter через чётко определённые методы
5. WHEN Presenter завершает операцию THEN он SHALL уведомлять View через callback интерфейс, а не напрямую модифицировать UI

### Requirement 2

**User Story:** Как разработчик, я хочу управлять жизненным циклом сессии БД вне View компонента, чтобы избежать утечек ресурсов и упростить тестирование.

#### Acceptance Criteria

1. WHEN HomeView создаётся THEN Session SHALL передаваться через Dependency Injection, а не создаваться внутри View
2. WHEN HomeView уничтожается THEN он SHALL NOT закрывать Session (это ответственность создателя)
3. WHEN Presenter выполняет операции с БД THEN он SHALL использовать переданную Session
4. WHEN тесты создают Presenter THEN они SHALL передавать mock Session без реального подключения к БД
5. WHEN происходит ошибка в операции с БД THEN Presenter SHALL корректно обрабатывать исключение и уведомлять View

### Requirement 3

**User Story:** Как разработчик, я хочу иметь чёткое разделение между координацией данных и их отображением, чтобы каждый компонент имел единственную ответственность.

#### Acceptance Criteria

1. WHEN Presenter загружает данные THEN он SHALL координировать вызовы к нескольким сервисам и агрегировать результаты
2. WHEN View отображает данные THEN он SHALL получать готовые данные от Presenter и только отображать их
3. WHEN пользователь выбирает дату THEN View SHALL вызвать метод Presenter, который загрузит данные и вернёт их через callback
4. WHEN данные обновляются THEN Presenter SHALL вызывать callback методы View для обновления UI
5. WHEN View создаёт дочерние UI компоненты THEN он SHALL передавать им callback функции, которые делегируют в Presenter

### Requirement 4

**User Story:** Как разработчик, я хочу тестировать обработку модальных окон без реального UI, чтобы проверить корректность бизнес-логики диалогов.

#### Acceptance Criteria

1. WHEN пользователь открывает модальное окно THEN Presenter SHALL подготовить данные для модального окна
2. WHEN пользователь подтверждает действие в модальном окне THEN Presenter SHALL обработать данные и выполнить операцию через Service Layer
3. WHEN модальное окно закрывается THEN Presenter SHALL обновить данные и уведомить View
4. WHEN тесты проверяют логику модальных окон THEN они SHALL вызывать методы Presenter напрямую без открытия реальных диалогов
5. WHEN происходит ошибка в модальном окне THEN Presenter SHALL обработать её и передать сообщение об ошибке через callback

### Requirement 5

**User Story:** Как разработчик, я хочу иметь возможность тестировать загрузку данных для календаря, транзакций и плановых операций независимо, чтобы изолировать проблемы.

#### Acceptance Criteria

1. WHEN Presenter загружает данные календаря THEN он SHALL вызывать get_by_date_range и get_occurrences_by_date_range с корректными параметрами
2. WHEN Presenter загружает транзакции для выбранной даты THEN он SHALL вызывать get_transactions_by_date и get_occurrences_by_date
3. WHEN Presenter загружает плановые транзакции THEN он SHALL вызывать get_pending_occurrences и преобразовывать данные в формат для UI
4. WHEN Presenter загружает отложенные платежи THEN он SHALL вызывать get_all_pending_payments и get_pending_payments_statistics
5. WHEN любая операция загрузки данных завершается THEN Presenter SHALL передать результаты через соответствующий callback

### Requirement 6

**User Story:** Как разработчик, я хочу тестировать обработку действий пользователя (исполнение платежей, пропуск операций) без UI, чтобы гарантировать корректность бизнес-логики.

#### Acceptance Criteria

1. WHEN пользователь исполняет плановое вхождение THEN Presenter SHALL вызвать execute_occurrence с корректными параметрами
2. WHEN пользователь пропускает плановое вхождение THEN Presenter SHALL вызвать skip_occurrence
3. WHEN пользователь исполняет отложенный платёж THEN Presenter SHALL вызвать execute_pending_payment
4. WHEN пользователь отменяет отложенный платёж THEN Presenter SHALL вызвать cancel_pending_payment с причиной отмены
5. WHEN пользователь удаляет отложенный платёж THEN Presenter SHALL вызвать delete_pending_payment
6. WHEN пользователь исполняет платёж по кредиту THEN Presenter SHALL вызвать execute_loan_payment_service с корректными параметрами
7. WHEN любое действие завершается успешно THEN Presenter SHALL обновить данные и уведомить View через success callback
8. WHEN любое действие завершается с ошибкой THEN Presenter SHALL уведомить View через error callback с описанием ошибки

### Requirement 7

**User Story:** Как разработчик, я хочу иметь интерфейс для взаимодействия между Presenter и View, чтобы обеспечить слабую связанность и возможность замены реализации.

#### Acceptance Criteria

1. WHEN Presenter создаётся THEN он SHALL принимать интерфейс IHomeViewCallbacks через конструктор
2. WHEN Presenter обновляет данные календаря THEN он SHALL вызывать callback метод update_calendar_data
3. WHEN Presenter обновляет транзакции THEN он SHALL вызывать callback метод update_transactions
4. WHEN Presenter обновляет плановые операции THEN он SHALL вызывать callback метод update_planned_occurrences
5. WHEN Presenter обновляет отложенные платежи THEN он SHALL вызывать callback метод update_pending_payments
6. WHEN Presenter показывает сообщение пользователю THEN он SHALL вызывать callback метод show_message
7. WHEN Presenter показывает ошибку THEN он SHALL вызывать callback метод show_error
8. WHEN тесты проверяют Presenter THEN они SHALL использовать mock реализацию IHomeViewCallbacks

### Requirement 8

**User Story:** Как разработчик, я хочу иметь возможность тестировать обработку ошибок на всех уровнях, чтобы гарантировать устойчивость приложения.

#### Acceptance Criteria

1. WHEN Service Layer выбрасывает исключение THEN Presenter SHALL перехватить его, залогировать и передать в View через error callback
2. WHEN операция с БД завершается с ошибкой THEN Presenter SHALL NOT выполнять commit и SHALL передать ошибку в View
3. WHEN валидация данных не проходит THEN Presenter SHALL передать сообщение об ошибке валидации в View
4. WHEN тесты проверяют обработку ошибок THEN они SHALL имитировать исключения из Service Layer и проверять корректность обработки
5. WHEN происходит критическая ошибка THEN Presenter SHALL залогировать полный контекст (параметры, состояние) для отладки

### Requirement 9

**User Story:** Как разработчик, я хочу минимизировать изменения в существующих UI компонентах, чтобы снизить риск регрессии.

#### Acceptance Criteria

1. WHEN рефакторинг выполняется THEN существующие UI компоненты (CalendarWidget, TransactionsPanel и т.д.) SHALL оставаться без изменений
2. WHEN HomeView рефакторится THEN он SHALL продолжать использовать те же UI компоненты с теми же интерфейсами
3. WHEN Presenter взаимодействует с данными UI компонентов THEN он SHALL делать это через методы View, а не напрямую
4. WHEN модальные окна используются THEN они SHALL оставаться в View, но их логика SHALL делегироваться в Presenter
5. WHEN рефакторинг завершён THEN визуальное поведение приложения SHALL остаться идентичным

### Requirement 10

**User Story:** Как разработчик, я хочу иметь полное покрытие тестами для всех публичных методов Presenter, чтобы гарантировать корректность бизнес-логики.

#### Acceptance Criteria

1. WHEN тесты запускаются THEN каждый публичный метод Presenter SHALL иметь как минимум один unit тест
2. WHEN тесты проверяют загрузку данных THEN они SHALL проверять корректность вызовов к Service Layer
3. WHEN тесты проверяют обработку действий THEN они SHALL проверять корректность параметров и результатов
4. WHEN тесты проверяют обработку ошибок THEN они SHALL покрывать все возможные исключения
5. WHEN тесты проверяют callbacks THEN они SHALL проверять, что корректные данные передаются в View
