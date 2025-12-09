# Requirements Document

## Introduction

Переход системы идентификаторов базы данных Finance Tracker с Integer ID на UUID (Universally Unique Identifier) и добавление колонки `updated_at` во все таблицы. Цель — обеспечить глобальную уникальность идентификаторов для будущей синхронизации между устройствами и полное отслеживание времени изменения записей.

**Текущее состояние:**
- Все таблицы используют Integer ID с автоинкрементом
- Только некоторые таблицы имеют колонку `updated_at` (transactions, planned_transactions, lenders, loans, loan_payments, pending_payments)
- Таблицы без `updated_at`: categories, recurrence_rules, planned_occurrences
- Продовой базы данных нет, миграция существующих данных не требуется

**Целевое состояние:**
- Все таблицы используют UUID как первичный ключ
- Все внешние ключи используют UUID
- Все таблицы имеют колонку `updated_at` с автоматическим обновлением
- База данных пересоздаётся с новой схемой

## Glossary

- **UUID**: Universally Unique Identifier — 128-битный идентификатор, гарантирующий глобальную уникальность
- **Integer ID**: Целочисленный идентификатор с автоинкрементом (текущий подход)
- **Primary Key (PK)**: Первичный ключ таблицы
- **Foreign Key (FK)**: Внешний ключ, ссылающийся на первичный ключ другой таблицы
- **Migration**: Процесс преобразования структуры и данных базы данных
- **SQLAlchemy**: ORM библиотека для работы с базой данных
- **Pydantic**: Библиотека для валидации данных
- **updated_at**: Колонка с датой и временем последнего изменения записи
- **created_at**: Колонка с датой и временем создания записи

## Requirements

### Requirement 1: Миграция первичных ключей на UUID

**User Story:** Как разработчик, я хочу использовать UUID вместо Integer ID во всех таблицах, чтобы обеспечить глобальную уникальность идентификаторов для будущей синхронизации между устройствами.

#### Acceptance Criteria

1. WHEN система создаёт новую запись THEN THE System SHALL генерировать UUID автоматически
2. THE System SHALL использовать UUID версии 4 (случайный UUID)
3. THE System SHALL хранить UUID в формате строки (VARCHAR(36)) в SQLite
4. THE System SHALL индексировать UUID колонки для быстрого поиска
5. THE System SHALL обновлять все SQLAlchemy модели для использования UUID как первичного ключа
6. THE System SHALL обеспечивать уникальность UUID на уровне базы данных
7. THE System SHALL генерировать UUID на стороне приложения (не на стороне БД)

### Requirement 2: Миграция внешних ключей на UUID

**User Story:** Как разработчик, я хочу обновить все внешние ключи для использования UUID, чтобы сохранить целостность связей между таблицами.

#### Acceptance Criteria

1. WHEN система обновляет внешний ключ THEN THE System SHALL использовать UUID вместо Integer
2. THE System SHALL обновлять все relationship определения в SQLAlchemy моделях
3. THE System SHALL сохранять каскадные правила удаления (CASCADE, SET NULL)
4. THE System SHALL обновлять все индексы на внешних ключах
5. THE System SHALL валидировать существование связанных записей по UUID
6. THE System SHALL обновлять следующие внешние ключи:
   - CategoryDB: нет внешних ключей
   - PlannedTransactionDB: category_id → UUID
   - RecurrenceRuleDB: planned_transaction_id → UUID
   - PlannedOccurrenceDB: planned_transaction_id → UUID, actual_transaction_id → UUID
   - TransactionDB: category_id → UUID, planned_occurrence_id → UUID
   - LenderDB: нет внешних ключей
   - LoanDB: lender_id → UUID, disbursement_transaction_id → UUID
   - LoanPaymentDB: loan_id → UUID, planned_transaction_id → UUID, actual_transaction_id → UUID
   - PendingPaymentDB: category_id → UUID, actual_transaction_id → UUID

### Requirement 3: Добавление колонки updated_at во все таблицы

**User Story:** Как разработчик, я хочу отслеживать время последнего изменения каждой записи, чтобы реализовать синхронизацию и аудит изменений.

#### Acceptance Criteria

1. WHEN система создаёт новую запись THEN THE System SHALL устанавливать updated_at равным текущему времени
2. WHEN система обновляет запись THEN THE System SHALL автоматически обновлять updated_at на текущее время
3. THE System SHALL использовать тип DateTime для колонки updated_at
4. THE System SHALL использовать UTC время для всех временных меток
5. THE System SHALL добавлять updated_at в следующие таблицы (где её ещё нет):
   - CategoryDB
   - RecurrenceRuleDB
   - PlannedOccurrenceDB
6. THE System SHALL сохранять существующую колонку updated_at в таблицах:
   - PlannedTransactionDB
   - TransactionDB
   - LenderDB
   - LoanDB
   - LoanPaymentDB
   - PendingPaymentDB

### Requirement 4: Пересоздание базы данных

**User Story:** Как разработчик, я хочу пересоздать базу данных с новой схемой UUID, чтобы начать работу с правильной структурой.

#### Acceptance Criteria

1. WHEN система запускается с новой схемой THEN THE System SHALL удалять старую базу данных (если существует)
2. THE System SHALL создавать новую базу данных с UUID схемой
3. THE System SHALL инициализировать предопределённые категории с UUID
4. THE System SHALL валидировать структуру созданных таблиц
5. THE System SHALL логировать процесс пересоздания базы данных
6. THE System SHALL создавать все необходимые индексы для UUID колонок

### Requirement 5: Обновление сервисного слоя

**User Story:** Как разработчик, я хочу обновить все сервисы для работы с UUID, чтобы бизнес-логика корректно работала с новыми идентификаторами.

#### Acceptance Criteria

1. WHEN сервис принимает ID параметр THEN THE System SHALL использовать тип str (UUID) вместо int
2. THE System SHALL обновлять сигнатуры всех функций, работающих с ID
3. THE System SHALL обновлять следующие сервисы:
   - transaction_service.py: delete_transaction(transaction_id: str)
   - loan_service.py: get_loan_by_id(loan_id: str), update_loan_status(loan_id: str), calculate_loan_balance(loan_id: str), calculate_loan_statistics(loan_id: str), delete_loan(loan_id: str)
   - loan_payment_service.py: delete_payment(payment_id: str)
   - lender_service.py: get_lender_by_id(lender_id: str), delete_lender(lender_id: str)
   - category_service.py: все функции с category_id
   - planned_transaction_service.py: все функции с planned_transaction_id
   - pending_payment_service.py: все функции с payment_id
4. THE System SHALL валидировать формат UUID перед выполнением операций
5. THE System SHALL возвращать понятные ошибки при невалидном UUID

### Requirement 6: Обновление Pydantic моделей

**User Story:** Как разработчик, я хочу обновить Pydantic модели для валидации UUID, чтобы обеспечить корректность данных на уровне API.

#### Acceptance Criteria

1. WHEN Pydantic модель содержит ID поле THEN THE System SHALL использовать тип str с валидацией UUID
2. THE System SHALL обновлять все модели Create/Update/Response
3. THE System SHALL валидировать формат UUID при создании/обновлении записей
4. THE System SHALL возвращать UUID в строковом формате в API ответах
5. THE System SHALL обновлять следующие модели:
   - TransactionCreate, TransactionUpdate, Transaction: category_id → str (UUID)
   - PlannedTransactionCreate, PlannedTransaction: category_id → str (UUID)
   - Category: id → str (UUID)
   - Все остальные модели с ID полями

### Requirement 7: Обновление UI компонентов

**User Story:** Как разработчик, я хочу обновить UI компоненты для работы с UUID, чтобы интерфейс корректно отображал и передавал идентификаторы.

#### Acceptance Criteria

1. WHEN UI компонент хранит ID THEN THE System SHALL использовать строковый тип
2. THE System SHALL обновлять все обработчики событий для передачи UUID
3. THE System SHALL обновлять все вызовы сервисов с UUID параметрами
4. THE System SHALL не отображать UUID пользователю (использовать только внутренне)
5. THE System SHALL обновлять следующие компоненты:
   - TransactionModal: передача category_id как UUID
   - PlannedTransactionModal: передача category_id как UUID
   - LoanModal: передача lender_id как UUID
   - Все списки и таблицы с ID записей

### Requirement 8: Обновление тестов

**User Story:** Как разработчик, я хочу обновить все тесты для работы с UUID, чтобы гарантировать корректность работы системы после миграции.

#### Acceptance Criteria

1. WHEN тест создаёт тестовые данные THEN THE System SHALL генерировать валидные UUID
2. THE System SHALL обновлять все фикстуры для использования UUID
3. THE System SHALL обновлять все assertions для проверки UUID
4. THE System SHALL обновлять property-based тесты для генерации UUID
5. THE System SHALL проверять, что все существующие тесты проходят после миграции
6. THE System SHALL добавлять новые тесты для валидации UUID:
   - Тест генерации UUID
   - Тест уникальности UUID
   - Тест валидации формата UUID
   - Тест миграции данных

### Requirement 9: Инициализация базы данных

**User Story:** Как разработчик, я хочу, чтобы база данных автоматически создавалась с правильной схемой, чтобы не выполнять ручные действия.

#### Acceptance Criteria

1. WHEN приложение запускается впервые THEN THE System SHALL создавать базу данных с UUID схемой
2. THE System SHALL инициализировать предопределённые категории
3. THE System SHALL создавать все необходимые таблицы и индексы
4. THE System SHALL валидировать структуру базы данных
5. THE System SHALL логировать процесс инициализации
6. IF база данных уже существует с Integer ID THEN THE System SHALL выводить предупреждение о необходимости удаления старой БД

### Requirement 10: Производительность

**User Story:** Как пользователь, я хочу, чтобы приложение работало быстро после миграции на UUID, чтобы не замечать разницы в производительности.

#### Acceptance Criteria

1. WHEN система выполняет поиск по UUID THEN THE System SHALL использовать индексы для быстрого поиска
2. THE System SHALL обеспечивать время поиска по UUID не более чем на 10% медленнее Integer ID
3. THE System SHALL оптимизировать JOIN операции с UUID внешними ключами
4. THE System SHALL кэшировать часто используемые UUID (категории, займодатели)
5. THE System SHALL измерять производительность критических операций до и после миграции

### Requirement 11: Логирование

**User Story:** Как разработчик, я хочу иметь подробное логирование работы с UUID, чтобы отлаживать проблемы.

#### Acceptance Criteria

1. WHEN система создаёт запись с UUID THEN THE System SHALL логировать генерацию UUID
2. THE System SHALL логировать ошибки валидации UUID с полным контекстом
3. THE System SHALL логировать операции с базой данных (создание, обновление, удаление)
4. THE System SHALL логировать на русском языке
5. THE System SHALL включать UUID в логи для трассировки операций

### Requirement 12: Документация

**User Story:** Как разработчик, я хочу иметь документацию по переходу на UUID, чтобы понимать изменения в системе.

#### Acceptance Criteria

1. THE System SHALL документировать изменения в структуре базы данных
2. THE System SHALL документировать изменения в API (сигнатуры функций)
3. THE System SHALL документировать на русском языке

