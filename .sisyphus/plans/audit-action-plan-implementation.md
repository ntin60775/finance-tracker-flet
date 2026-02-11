# Реализация AUDIT_ACTION_PLAN.md (релизы A–D)

## TL;DR

> Цель: закрыть P0/P1/P2 из `AUDIT_ACTION_PLAN.md` с релизной последовательностью A→B→C→D.
>
> Ключевой вектор: **сначала безопасность данных и честность UX/доков**, затем **экспорт/импорт snapshot**, затем **обязательства (issue #3) с изменением схемы БД**, затем **рефактор/наблюдаемость/UX**.

**Deliverables**:
- Рабочий экспорт/импорт snapshot в JSON (issue #4) + строгая валидация + атомарный импорт + отчет.
- UI/документация без “ложных обещаний”, плюс понятный backup-UX.
- CI quality gates: coverage gate (поэтапно), security job (`pip-audit`).
- Obligations (issue #3) внутри текущего контура плановых транзакций: schema + сервисы + UI + тесты.
- Снижение сложности крупных модулей + стандартизация ошибок/логов + журнал критических доменных событий.
- P2 UX улучшения (Today / guided flow / plan-fact улучшения) по списку.

**Estimated Effort**: XL

---

## Context

### Original Request
Подготовить единый план реализации задач из `AUDIT_ACTION_PLAN.md`.

### Repo Facts (подтверждено чтением)
- Публичный API экспорт/импорт сейчас заглушки с `NotImplementedError`:
  - `src/finance_tracker/mobile/export_service.py`
  - `src/finance_tracker/mobile/import_service.py`
- Директория данных пользователя: `.finance_tracker_data/` + `exports/` создается автоматически:
  - `src/finance_tracker/config.py`
- БД инициализируется через `init_db()` и сидит системные категории при пустой БД:
  - `src/finance_tracker/database.py`
- Контур плановых транзакций уже есть:
  - DB: `src/finance_tracker/models/models.py`
  - Services: `src/finance_tracker/services/planned_transaction_service.py`
  - UI: `src/finance_tracker/views/planned_transactions_view.py`, `src/finance_tracker/components/planned_transaction_modal.py`
- CI сейчас запускает только ruff+pytest:
  - `.github/workflows/ci.yml`

### Metis Review (учтено)
- Restore-only импорт конфликтует с сидингом категорий в `init_db()` → нужно формализовать, что значит “пустая БД”.
- JSON суммы нельзя надежно гонять через float → суммы сериализуем строкой (Decimal) и валидируем.
- Obligations сейчас отсутствуют в коде → фича будет с нуля, с риском double-counting.
- Coverage/security gate могут ломать CI → внедрять поэтапно.

---

## Work Objectives

### Core Objective
Сделать проект “честным и надежным” для критичных финансовых сценариев, закрыв P0/P1/P2 из `AUDIT_ACTION_PLAN.md` по релизам A–D.

### Scope Boundaries (Guardrails)
- IN: все пункты P0/P1/P2 из `AUDIT_ACTION_PLAN.md` и релизы A–D.
- OUT: приватные sync-функции в `src/finance_tracker/mobile/sync_proprietary/` (кроме сохранения публичного API export/import).
- OUT (явно): авто-перенос переплаты по obligations на будущие месяцы.
- OUT (явно): merge/import поверх существующих пользовательских данных (v1 импорт = restore-only).

---

## Verification Strategy (MANDATORY)

Универсальные команды (для каждого PR/задачи):
```bash
ruff check src tests
pytest tests/ -q
```

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-cov + hypothesis) — `pyproject.toml`
- **Automated tests**: TDD (по умолчанию)

### Agent-Executed QA Scenarios (общий формат)
Для каждой задачи ниже указаны конкретные сценарии, которые агент выполняет сам (pytest/CLI запуск), без “попросить пользователя проверить”.

---

## Execution Strategy

### Releases
- Release A (stability): честность UX/доков + каркас export/import + CI gates базового уровня.
- Release B (data safety): round-trip и негативные тесты export/import + формализация restore-only поведения.
- Release C (obligations): schema + сервисы + UI + тесты для issue #3.
- Release D (architecture + UX): рефактор кандидатов + наблюдаемость/ошибки + P2 UX.

### Parallelization Waves (ориентир)
- Wave 1: CI gates + экспорт/импорт сервисный слой (без UI)
- Wave 2: UI для backup/restore + тесты export/import
- Wave 3: obligations schema+service (ядро) + параллельно groundwork для observability
- Wave 4: obligations UI + интеграционные/UI тесты
- Wave 5: рефактор модулей и P2 UX (после стабилизации домена)

---

## TODOs

Принцип: “фича + тесты + QA сценарии” в одной задаче.

### Release A (stability)

- [x] 1. P0.2: Честность документации и UX-сообщений про экспорт/импорт

  **What to do**:
  - Пройтись по публичным упоминаниям export/import и привести формулировки к факту (до релиза A: “доступно” или “в разработке” в зависимости от готовности).
  - Добавить/обновить явный fallback: резервная копия `.finance_tracker_data/finance.db` (путь берется из `settings.db_path`).

  **References**:
  - `README.md` — есть упоминание “Экспорт и импорт данных (в разработке, см. issue #4)”.
  - `src/finance_tracker/mobile/export_service.py` — текущий текст ошибок.
  - `src/finance_tracker/mobile/import_service.py` — текущий текст ошибок.
  - `src/finance_tracker/config.py` — где находится `.finance_tracker_data/finance.db`.

  **Acceptance Criteria**:
  - `ruff check src tests` → PASS
  - `pytest tests/ -q` → PASS
  - Док-текст/UX-тексты не обещают “готово”, если функционал не реализован.

  **Recommended Agent Profile**:
  - Category: `writing`
  - Skills: `corp-kb-doc` (если нужно оформить как базу знаний), иначе без скиллов

  **Agent-Executed QA Scenarios**:
  - Scenario: Проверка README на честность
    - Tool: Bash (grep/pytest не требуется)
    - Steps: открыть `README.md`, убедиться, что экспорт/импорт описан корректно
    - Expected: нет противоречий текущей реализации

- [x] 2. P0.2: UX для резервного копирования (UI в Settings)

  **What to do**:
  - Добавить в `SettingsView` секцию “Резервное копирование”:
    - Кнопка “Экспорт (snapshot)” → вызывает ExportService и сохраняет файл в `.finance_tracker_data/exports/` по умолчанию.
    - Кнопка “Импорт (restore-only)” + FilePicker → выбирает snapshot файл и вызывает ImportService.
    - Перед импортом показать предупреждение “Импорт доступен только для пустой БД (restore-only).”
  - Все диалоги/уведомления — через `page.open/page.close`.

  **References**:
  - `src/finance_tracker/views/settings_view.py` — место для UI.
  - `src/finance_tracker/config.py` — exports dir.
  - `src/finance_tracker/mobile/export_service.py`
  - `src/finance_tracker/mobile/import_service.py`
  - `tests/conftest.py` — мок `page.open/page.close`.

  **Acceptance Criteria**:
  - `pytest tests/test_settings_backup_ui.py -q` → PASS
  - UI тест проверяет: нажатие кнопки экспорт вызывает сервис; импорт с выбранным файлом вызывает сервис; предупреждение отображается.

  **Recommended Agent Profile**:
  - Category: `visual-engineering`
  - Skills: `playwright` (только если будут e2e; иначе достаточно pytest UI tests)

  **Agent-Executed QA Scenarios**:
  - Scenario: Settings backup UI
    - Tool: Bash (pytest)
    - Steps: `pytest tests/test_settings_backup_ui.py -q`
    - Expected: PASS

- [x] 3. P0.1 (часть): Дизайн snapshot формата + минимальная реализация ExportService/ImportService (restore-only)

  **What to do**:
  - Специфицировать JSON формат snapshot (metadata + списки по всем доменным таблицам).
  - Реализовать export/import в `src/finance_tracker/mobile/export_service.py` и `src/finance_tracker/mobile/import_service.py`.
  - Сохранить публичные сигнатуры, но разрешить тестируемость через внутренние функции, принимающие `Session` (или keyword-only `session=` при сохранении совместимости).
  - Валидация import:
    - `schema_version` / `app_version` / `created_at`
    - UUID формат всех id
    - ссылки FK существуют
    - Decimal суммы сериализуются/парсятся как строки
  - Restore-only правило (v1): импорт разрешен только если **нет пользовательских данных**; допускается состояние “только системные категории” (из `init_db`) — остальные таблицы пустые.
  - Импорт атомарный: одна транзакция; при любой ошибке — rollback.
  - Импорт дает отчет: added/skipped/conflicts (для restore-only conflicts в идеале = 0; иначе ошибка/отказ).

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: (без специальных; по необходимости `finalize-sync` в конце для выравнивания доков/плана)

  **References**:
  - `src/finance_tracker/mobile/export_service.py` — текущая заглушка.
  - `src/finance_tracker/mobile/import_service.py` — текущая заглушка.
  - `src/finance_tracker/models/__init__.py` — список доменных DB моделей.
  - `src/finance_tracker/models/models.py` — таблицы: CategoryDB/TransactionDB/PlannedTransactionDB/RecurrenceRuleDB/PlannedOccurrenceDB/LenderDB/LoanDB/LoanPaymentDB/PendingPaymentDB/DebtTransferDB.
  - `src/finance_tracker/database.py` — init_db сидинг категорий и session rollback поведение.
  - `src/finance_tracker/config.py` — `exports/` каталог.

  **Acceptance Criteria**:
  - `pytest tests/ -q` → PASS
  - Добавлены unit-тесты (TDD) на:
    - сериализацию/десериализацию snapshot без потери Decimal точности
    - отказ импорта при неверной версии/структуре/UUID
    - отказ импорта при непустых таблицах (restore-only guard)

  **Agent-Executed QA Scenarios**:
  - Scenario: Export → Import на in-memory БД
    - Tool: Bash (pytest)
    - Steps: `pytest tests/test_export_import_unit.py -q`
    - Expected: PASS
  - Scenario: Restore-only guard
    - Tool: Bash (pytest)
    - Steps: `pytest tests/test_import_restore_only_guards.py -q`
    - Expected: PASS

- [x] 4. P1.3: CI quality gates (этап 1: coverage 65% + security job в “report mode”)

  **What to do**:
  - Обновить `.github/workflows/ci.yml`:
    - добавить запуск `pytest` с coverage и минимальным порогом (старт 65%).
    - добавить отдельный job `pip-audit` (на первом шаге допускается `continue-on-error: true`, чтобы не заблокировать релиз при внезапных транзитивных CVE).
  - Добавить `pip-audit` в dev deps или установить в CI job.
  - Зафиксировать в репо текстовую policy (в CONTRIBUTING или в README dev секции): новые сервисы/модули должны иметь тесты.

  **References**:
  - `.github/workflows/ci.yml` — текущий CI.
  - `pyproject.toml` — pytest/pytest-cov уже есть.

  **Acceptance Criteria**:
  - CI обновлен: lint + tests + coverage gate.
  - `pytest tests/ --cov=src/finance_tracker --cov-fail-under=65` → PASS (локально у агента).

  **Recommended Agent Profile**:
  - Category: `quick`
  - Skills: `git-master` (если нужно разбить на атомарные коммиты)

  **Agent-Executed QA Scenarios**:
  - Scenario: CI команды локально
    - Tool: Bash
    - Steps: выполнить команды lint/test/coverage
    - Expected: PASS

### Release B (data safety)

- [x] 5. P0.1 (полностью): Round-trip интеграционные тесты snapshot export/import + негативные сценарии

  **What to do**:
  - Добавить интеграционный тест “round-trip”:
    1) создать доменные данные во временной БД
    2) export snapshot в файл
    3) import snapshot в новую/пустую БД
    4) сверить инварианты: количество записей, суммы, ссылки FK
  - Добавить негативные тесты:
    - поврежденный JSON
    - неверная schema_version
    - невалидный UUID
    - FK ссылка на несуществующий объект
  - Закрепить семантику restore-only на “непустой БД”: импорт должен **предсказуемо отказать** и **не менять** данные.

  **References**:
  - `tests/conftest.py` — есть `db_session` (in-memory) и паттерны фикстур.
  - `src/finance_tracker/models/models.py` — где определены FK.

  **Acceptance Criteria**:
  - `pytest tests/test_export_import_roundtrip.py -q` → PASS
  - `pytest tests/test_export_import_validation.py -q` → PASS
  - `pytest tests/test_import_restore_only_guards.py -q` → PASS

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: (без специальных)

  **Agent-Executed QA Scenarios**:
  - Scenario: Round-trip
    - Tool: Bash
    - Steps: `pytest tests/test_export_import_roundtrip.py -q`
    - Expected: PASS
  - Scenario: Non-empty guard is non-destructive
    - Tool: Bash
    - Steps: `pytest tests/test_import_restore_only_guards.py -q`
    - Expected: PASS

- [x] 6. P1.3 (этап 2): Поднять coverage gate (65 → 70/75/80 по шагам)

  **What to do**:
  - После стабилизации export/import + obligations тестов — поэтапно повышать `--cov-fail-under`.
  - Цель из `AUDIT_ACTION_PLAN.md`: довести до 80%.

  **References**:
  - `.github/workflows/ci.yml`
  - `AUDIT_ACTION_PLAN.md` — требования по gate.

  **Acceptance Criteria**:
  - CI порог повышен минимум на один шаг без флапа тестов.

### Release C (obligations, issue #3)

- [x] 7. Issue #3: Доменная модель obligations (schema changes + миграция SQLite)

  **What to do**:
  - Ввести представление “Обязательство” как месячной цели расхода, покрываемой частями.
  - Изменения схемы (breaking change допустим) — предложенный конкретный минимум:
    - `PlannedTransactionDB`:
      - `parent_planned_transaction_id: Optional[str]` (FK на `planned_transactions.id`) — для child плановых транзакций (частей)
      - `is_obligation: bool` — отличать obligation parent от обычных planned transactions
      - `target_amount: Optional[Decimal]` — цель месяца (только для `is_obligation=True`)
      - `target_month: Optional[date]` — месяц цели (рекомендуется хранить как 1-е число месяца)
    - `TransactionDB`:
      - `obligation_id: Optional[str]` (FK на `planned_transactions.id`) — ручная/автоматическая привязка фактической транзакции к obligation parent
  - Миграция SQLite без alembic:
    - добавить контролируемый слой миграций (raw SQL `ALTER TABLE ... ADD COLUMN` для новых колонок) на старте приложения.
  - Правило переплаты (подтверждено пользователем):
    - запрещено привязывать фактическую транзакцию к obligation, если `amount > remaining`.
    - авто-перенос переплаты на будущий месяц = OUT.

  **References**:
  - `src/finance_tracker/models/models.py` — PlannedTransactionDB/TransactionDB.
  - `src/finance_tracker/database.py` — точка инициализации, куда можно встроить миграцию.
  - `AUDIT_ACTION_PLAN.md` — раздел P1.6.

  **Acceptance Criteria**:
  - Миграция работает на существующей БД (добавляет колонки/таблицы без потери данных).
  - `pytest tests/test_obligations_schema_migration.py -q` → PASS

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: (без специальных)

  **Agent-Executed QA Scenarios**:
  - Scenario: Migration smoke
    - Tool: Bash
    - Steps: `pytest tests/test_obligations_schema_migration.py -q`
    - Expected: PASS

- [x] 8. Issue #3: Сервисный слой obligations (target/paid/remaining + валидации)

  **What to do**:
  - Реализовать API расчета `target / paid / remaining` по месяцу.
  - Валидации:
    - запрет “amount > remaining” при линковке фактической транзакции
    - запрет дубликатов привязки (одна транзакция не может быть привязана к двум obligations)
    - корректная работа при нескольких obligations на категорию/месяц
  - Пересчет при изменении target: изменения отражаются сразу.
  - Исключить double-counting (если транзакция создана из planned occurrence и одновременно привязана — считать один раз).

  **References**:
  - `src/finance_tracker/services/planned_transaction_service.py` — текущий паттерн сервисов.
  - `src/finance_tracker/models/models.py` — TransactionDB.planned_occurrence_id и PlannedOccurrenceDB.actual_transaction_id.
  - `src/finance_tracker/utils/exceptions.py` — доменные исключения.

  **Acceptance Criteria**:
  - `pytest tests/test_obligations_service.py -q` → PASS
  - Есть тест-кейс: попытка привязки транзакции на сумму больше remaining → отказ с понятной ошибкой.

  **Recommended Agent Profile**:
  - Category: `deep`
  - Skills: (без специальных)

  **Agent-Executed QA Scenarios**:
  - Scenario: Remaining computation & guard
    - Tool: Bash
    - Steps: `pytest tests/test_obligations_service.py -q`
    - Expected: PASS

- [x] 9. Issue #3: UI в текущем контуре плановых транзакций (modal/view)

  **What to do**:
  - Расширить `PlannedTransactionModal` режимом “Обязательство” (создание/редактирование цели месяца).
  - В `PlannedTransactionsView` и/или виджетах: grouped-блок obligations с (цель/оплачено/остаток) + прогресс.
  - Добавить UI действие “Привязать транзакцию к обязательству” (ручная привязка) с правилом:
    - если amount > remaining → показывать предупреждение и инструкцию “разбейте транзакцию вручную”.
  - Соблюсти правило Flet overlay API: только `page.open/page.close`.

  **References**:
  - `src/finance_tracker/components/planned_transaction_modal.py` — текущая модалка.
  - `src/finance_tracker/views/planned_transactions_view.py` — экран списка/деталей.
  - `tests/conftest.py` — мок `page.open/page.close` для UI тестов.

  **Acceptance Criteria**:
  - `pytest tests/test_obligations_ui.py -q` → PASS
  - UI тест покрывает: создание obligation → отображение grouped блока → попытка привязки amount>remaining показывает предупреждение.

  **Recommended Agent Profile**:
  - Category: `visual-engineering`
  - Skills: (без специальных)

  **Agent-Executed QA Scenarios**:
  - Scenario: UI flow (unit UI tests)
    - Tool: Bash
    - Steps: `pytest tests/test_obligations_ui.py -q`
    - Expected: PASS

- [x] 10. Issue #3: Интеграционные тесты месячного цикла obligations

  **What to do**:
  - Тест “цель + частичные платежи + закрытие”: target=10000, платежи 4000+6000 → remaining=0.
  - Тест “несколько obligations в одной категории/месяце” (разные UUID) + независимый подсчет.
  - Тест “изменение target пересчитывает remaining”.

  **References**:
  - `tests/conftest.py` — `db_session`.
  - `AUDIT_ACTION_PLAN.md` — критерий Release C.

  **Acceptance Criteria**:
  - `pytest tests/test_obligations_integration.py -q` → PASS

  **Agent-Executed QA Scenarios**:
  - Scenario: Monthly cycle integration
    - Tool: Bash
    - Steps: `pytest tests/test_obligations_integration.py -q`
    - Expected: PASS

### Release D (architecture + observability + UX)

- [x] 11. P1.5: Ошибки и наблюдаемость (доменные исключения, контекстные логи, журнал событий)

  **What to do**:
  - Сократить широкие `except Exception` в доменных границах (services/db/UI handlers) в пользу:
    - `ValidationError` / `BusinessLogicError` / `DatabaseError` (`src/finance_tracker/utils/exceptions.py`)
  - Стандартизировать лог-контекст для операций денег/долгов/импорта (в `extra=` поля).
  - Добавить “журнал критических доменных событий” (минимум: импорт snapshot, удаление сущностей, перенос долга):
    - на первом шаге допускается журнал в логах (структурированно),
    - затем (опционально) — персистентная таблица (если нужно показывать в UI).

  **References**:
  - `src/finance_tracker/utils/error_handler.py` — текущий централизованный обработчик.
  - `src/finance_tracker/utils/logger.py` — JSON formatter.
  - `src/finance_tracker/views/*` и `src/finance_tracker/services/*` — много `except Exception`.

  **Acceptance Criteria**:
  - Добавлены тесты на ключевые доменные ошибки (минимум на import/obligations guards).
  - `pytest tests/ -q` → PASS

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: (без специальных)

- [x] 12. P1.4: Рефакторинг крупных модулей (декомпозиция без изменения поведения)

  **What to do**:
  - Итеративно декомпозировать кандидатов в меньшие компоненты/сервисы, сохраняя поведение:
    - `src/finance_tracker/views/loan_details_view.py`
    - `src/finance_tracker/views/transaction_history_view.py`
    - `src/finance_tracker/services/loan_payment_service.py`
    - `src/finance_tracker/components/transactions_panel.py`
  - В каждом модуле: выделить 2–4 подкомпонента/класса с единичной ответственностью.
  - Добавить/расширить тесты на извлеченные функции/сервисы.

  **Acceptance Criteria**:
  - `ruff check src tests` → PASS
  - `pytest tests/ -q` → PASS

- [x] 13. P2.7: UX экран “Сегодня” (минимальная версия)

  **What to do**:
  - Добавить экран (или секцию в HomeView): баланс на сегодня, обязательные платежи/просрочки, риск 7/30 дней.
  - Быстрые действия: добавить транзакцию, отметить оплату, открыть риск.
  - Определить минимальные метрики на основе существующих сервисов (balance_forecast/plan_fact/planned/pending).

  **References**:
  - `src/finance_tracker/views/home_view.py` — текущий главный экран.
  - `src/finance_tracker/services/balance_forecast_service.py` — прогноз.
  - `src/finance_tracker/views/pending_payments_view.py` — отложенные/просрочки.

  **Acceptance Criteria**:
  - Добавлены UI тесты на инициализацию/наличие ключевых контролов.
  - `pytest tests/test_today_view.py -q` → PASS

- [x] 14. P2.8: Guided-flow для сложных операций (досрочное погашение, передача долга)

  **What to do**:
  - Для досрочного погашения и передачи долга сделать “мастер” с:
    - шагами ввода
    - предпросмотром финансового эффекта до подтверждения
  - Переиспользовать существующие модалки/сервисы, избегая дублирования бизнес-логики.

  **References**:
  - `src/finance_tracker/components/early_repayment_modal.py`
  - `src/finance_tracker/components/debt_transfer_modal.py`
  - `src/finance_tracker/services/debt_transfer_service.py`
  - `src/finance_tracker/services/loan_payment_service.py`

  **Acceptance Criteria**:
  - UI тесты на happy path + отказ при невалидных данных.

- [x] 15. P2.9: План-факт и аналитика (улучшение DateRangePicker + сравнение периодов)

  **What to do**:
  - Доработать выбор периода в plan-fact: удобный диапазон, пресеты.
  - Добавить сценарии сравнения периодов и сохранение пользовательских фильтров.

  **References**:
  - `src/finance_tracker/views/plan_fact_view.py`
  - `src/finance_tracker/services/plan_fact_service.py`

  **Acceptance Criteria**:
  - `pytest tests/test_plan_fact_range.py -q` → PASS

---

## Defaults Applied (можно переопределить)
- Snapshot экспорт/импорт включает **только данные БД**, не `config.json` и не логи.
- Суммы в snapshot сериализуются строкой (Decimal), даты — ISO (`YYYY-MM-DD`).
- Restore-only: импорт отказывает на непустой БД (кроме допуска “только системные категории”).
- Paid по obligations считается по `transaction_date` внутри месяца; “зачет в прошлый месяц при дате следующего” = OUT (пока).

---

## Success Criteria

### Release A
- Нет ложных обещаний export/import в UX/доках.
- CI включает lint + tests + coverage gate (65%) + pip-audit (report mode).
- Экспорт/импорт реализован в сервисном слое и покрыт базовыми тестами.

### Release B
- Snapshot export/import проходит round-trip тесты; import атомарный; restore-only guard гарантирован.

### Release C
- Obligations доступны в текущем UI плановых транзакций; remaining считается корректно; переплата требует ручного split.

### Release D
- Снижена сложность ключевых модулей; логирование/ошибки стандартизированы; улучшен ежедневный UX.
