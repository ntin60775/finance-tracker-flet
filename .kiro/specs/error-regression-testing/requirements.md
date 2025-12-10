# Requirements Document

## Introduction

Создание регрессионных тестов для предотвращения повторного появления критических ошибок, которые были обнаружены и исправлены в процессе разработки Finance Tracker Flet. Также необходимо исправить существующие тесты, которые сломались из-за изменений в интерфейсах и поведении компонентов.

## Glossary

- **Regression Test**: Тест, который проверяет, что исправленная ошибка не появится снова
- **Offstage Control Error**: Ошибка Flet, когда пытаемся показать диалог до добавления контрола на страницу
- **JSON Serialization Error**: Ошибка сериализации объектов date/datetime в JSON логах
- **Interface Mismatch**: Несоответствие между ожидаемым и фактическим типом данных в интерфейсе
- **Initialization Order**: Порядок инициализации компонентов UI для предотвращения ошибок
- **HomePresenter**: Presenter для главного экрана, содержит бизнес-логику
- **HomeView**: View для главного экрана, отвечает за UI
- **PendingPaymentsWidget**: Виджет для отображения отложенных платежей
- **MainWindow**: Главное окно приложения с навигацией

## Requirements

### Requirement 1

**User Story:** Как разработчик, я хочу иметь тесты для предотвращения ошибки "Offstage Control must be added to the page first", чтобы убедиться, что диалоги не открываются до инициализации страницы.

#### Acceptance Criteria

1. WHEN HomeView инициализируется THEN load_initial_data SHALL НЕ вызываться в конструкторе
2. WHEN MainWindow добавляется на страницу THEN did_mount SHALL вызвать load_initial_data
3. WHEN показывается SnackBar THEN страница SHALL быть полностью инициализирована
4. WHEN открывается любой диалог THEN контрол SHALL быть добавлен на страницу первым
5. WHEN происходит ошибка инициализации THEN она SHALL обрабатываться корректно без показа диалогов

### Requirement 2

**User Story:** Как разработчик, я хочу иметь тесты для предотвращения ошибки JSON сериализации в логах, чтобы убедиться, что все объекты корректно сериализуются.

#### Acceptance Criteria

1. WHEN логируется объект date THEN он SHALL сериализоваться в ISO формат
2. WHEN логируется объект datetime THEN он SHALL сериализоваться в ISO формат  
3. WHEN логируется объект Decimal THEN он SHALL сериализоваться в float
4. WHEN логируется объект с атрибутами THEN он SHALL сериализоваться в строку
5. WHEN происходит ошибка с контекстом THEN все поля SHALL быть сериализуемы в JSON

### Requirement 3

**User Story:** Как разработчик, я хочу иметь тесты для предотвращения ошибки "'tuple' object has no attribute 'get'", чтобы убедиться в корректности типов данных в интерфейсах.

#### Acceptance Criteria

1. WHEN PendingPaymentsWidget.set_payments вызывается THEN statistics SHALL быть Dict[str, Any]
2. WHEN IHomeViewCallbacks.update_pending_payments вызывается THEN statistics SHALL быть Dict[str, Any]
3. WHEN HomePresenter.load_pending_payments выполняется THEN statistics SHALL передаваться как словарь
4. WHEN get_pending_payments_statistics возвращает данные THEN они SHALL быть в формате словаря
5. WHEN происходит несоответствие типов THEN SHALL быть выброшено понятное исключение

### Requirement 4

**User Story:** Как разработчик, я хочу исправить существующие тесты HomePresenter, которые сломались из-за изменения интерфейса statistics.

#### Acceptance Criteria

1. WHEN тест test_load_pending_payments_success выполняется THEN он SHALL ожидать Dict вместо Tuple
2. WHEN тест test_pending_payment_data_loading_consistency выполняется THEN он SHALL ожидать Dict вместо Tuple
3. WHEN тест test_operation_result_callback_consistency выполняется THEN он SHALL ожидать Dict вместо Tuple
4. WHEN все тесты HomePresenter выполняются THEN они SHALL проходить успешно
5. WHEN изменяется интерфейс THEN соответствующие тесты SHALL быть обновлены

### Requirement 5

**User Story:** Как разработчик, я хочу исправить существующие тесты HomeView, которые сломались из-за изменения порядка инициализации.

#### Acceptance Criteria

1. WHEN тест test_initialization выполняется THEN он SHALL НЕ ожидать вызов load_initial_data в конструкторе
2. WHEN тест test_load_data_calls_services выполняется THEN он SHALL тестировать правильный момент загрузки данных
3. WHEN HomeView создается THEN load_initial_data SHALL вызываться через MainWindow.did_mount
4. WHEN тестируется инициализация THEN SHALL проверяться создание компонентов, а не загрузка данных
5. WHEN все тесты HomeView выполняются THEN они SHALL проходить успешно

### Requirement 6

**User Story:** Как разработчик, я хочу создать property-based тесты для проверки корректности инициализации UI компонентов, чтобы предотвратить ошибки порядка инициализации.

#### Acceptance Criteria

1. WHEN любой View создается THEN все обязательные атрибуты SHALL быть установлены
2. WHEN View добавляется на страницу THEN did_mount SHALL вызываться корректно
3. WHEN происходит навигация между View THEN инициализация SHALL происходить в правильном порядке
4. WHEN View удаляется со страницы THEN will_unmount SHALL вызываться корректно
5. WHEN тестируется любая комбинация View THEN ошибки инициализации SHALL отсутствовать

### Requirement 7

**User Story:** Как разработчик, я хочу создать property-based тесты для проверки корректности сериализации в логах, чтобы предотвратить ошибки JSON сериализации.

#### Acceptance Criteria

1. WHEN логируется любой объект date/datetime THEN сериализация SHALL быть успешной
2. WHEN логируется любой объект Decimal THEN сериализация SHALL быть успешной
3. WHEN логируется объект с произвольными атрибутами THEN сериализация SHALL быть успешной
4. WHEN происходит исключение с контекстом THEN логирование SHALL работать без ошибок
5. WHEN генерируются случайные данные для логирования THEN JSON сериализация SHALL всегда работать

### Requirement 8

**User Story:** Как разработчик, я хочу создать property-based тесты для проверки корректности интерфейсов между компонентами, чтобы предотвратить ошибки несоответствия типов.

#### Acceptance Criteria

1. WHEN HomePresenter вызывает callback THEN типы данных SHALL соответствовать интерфейсу
2. WHEN PendingPaymentsWidget получает данные THEN типы SHALL соответствовать ожиданиям
3. WHEN любой сервис возвращает статистику THEN формат SHALL быть консистентным
4. WHEN происходит обмен данными между слоями THEN типы SHALL быть валидными
5. WHEN генерируются случайные данные THEN интерфейсы SHALL работать корректно

### Requirement 9

**User Story:** Как разработчик, я хочу создать интеграционные тесты для проверки полного цикла инициализации приложения, чтобы предотвратить ошибки взаимодействия компонентов.

#### Acceptance Criteria

1. WHEN приложение запускается THEN MainWindow SHALL инициализироваться без ошибок
2. WHEN MainWindow добавляется на страницу THEN HomeView SHALL загружаться корректно
3. WHEN происходит навигация THEN все View SHALL инициализироваться без ошибок Offstage
4. WHEN показываются диалоги THEN они SHALL открываться только после полной инициализации
5. WHEN происходят ошибки THEN они SHALL логироваться без ошибок сериализации

### Requirement 10

**User Story:** Как разработчик, я хочу создать mock-тесты для изоляции компонентов при тестировании, чтобы точно определить источник ошибок.

#### Acceptance Criteria

1. WHEN тестируется HomePresenter THEN сервисы SHALL быть замокированы
2. WHEN тестируется HomeView THEN Presenter SHALL быть замокирован
3. WHEN тестируется PendingPaymentsWidget THEN данные SHALL быть замокированы
4. WHEN происходит ошибка в одном компоненте THEN она SHALL НЕ влиять на тесты других
5. WHEN изменяется один компонент THEN тесты других SHALL продолжать работать

### Requirement 11

**User Story:** Как разработчик, я хочу создать тесты для проверки обработки ошибок в критических местах, чтобы убедиться в graceful degradation.

#### Acceptance Criteria

1. WHEN происходит ошибка в load_initial_data THEN приложение SHALL продолжать работать
2. WHEN сервис возвращает ошибку THEN View SHALL показать понятное сообщение
3. WHEN происходит ошибка сериализации THEN логирование SHALL использовать fallback
4. WHEN компонент не может инициализироваться THEN SHALL показываться сообщение об ошибке
5. WHEN происходят множественные ошибки THEN каждая SHALL обрабатываться независимо

### Requirement 12

**User Story:** Как разработчик, я хочу создать тесты производительности для критических операций инициализации, чтобы убедиться в отсутствии деградации.

#### Acceptance Criteria

1. WHEN инициализируется HomeView THEN время SHALL быть менее 1 секунды
2. WHEN загружаются данные календаря THEN время SHALL быть менее 500мс
3. WHEN происходит навигация между View THEN время SHALL быть менее 200мс
4. WHEN логируются данные THEN сериализация SHALL быть менее 10мс
5. WHEN выполняются все тесты THEN общее время SHALL быть приемлемым
