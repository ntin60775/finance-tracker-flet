# План: reusable/repayment_only кредитки через исполнение плановых платежей

## TL;DR

> **Quick Summary**: Добавляем два режима кредитных карт (`reusable`, `repayment_only`) в текущий поток исполнения платежей по кредиту, чтобы в день исполнения можно было вручную фиксировать: (а) сумму возврата в активный баланс, (б) остаток долга после списания процентов.
>
> **Deliverables**:
> - Расширенная доменная модель (режим карты + ручные состояния)
> - Механизм корректировки общего баланса для `reusable` без загрязнения аналитики доходов/расходов
> - Обновленный UI исполнения платежа (Home + Loan Details) с mode-specific полями
> - TDD-покрытие (unit/integration/UI) + регрессии по классическим кредитам
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 4 волны
> **Critical Path**: Task 1 -> Task 2 -> Task 4 -> Task 5

---

## Context

### Original Request
- Нужно поддержать сценарий минимальных платежей по кредиткам в двух режимах:
  - `reusable`: после исполнения платежа часть суммы возвращается в активный баланс.
  - `repayment_only`: после исполнения платежа фиксируется остаток к погашению.
- Все платежи по картам должны оставаться подмножеством текущего потока плановых платежей.
- Детальный учет покупок по кредитке не нужен.

### Interview Summary
**Подтвержденные решения пользователя**:
- Для `reusable` значение `returned_to_active_balance` вводится вручную в день исполнения.
- Для `reusable` это именно **корректировка баланса**, а не обычный доход.
- Для `repayment_only` в день исполнения вводится `remaining_debt_after_payment`.
- Отдельное хранение `credit_limit` не требуется.
- Тестовая стратегия: **TDD (RED-GREEN-REFACTOR)**.

### Research Findings
- `LoanDB` описывает классический кредит и не хранит режим кредитки/ручные поля состояния (`src/finance_tracker/models/models.py:427`).
- `LoanType` не содержит кредитную карту как отдельный тип (`src/finance_tracker/models/enums.py:104`).
- Исполнение платежа по кредиту сейчас создает только `EXPENSE` транзакцию (`src/finance_tracker/services/loan_service.py:565`).
- Общий баланс считается как `income - expense` без отдельного канала корректировок (`src/finance_tracker/services/transaction_service.py:38`).
- UI исполнения платежа в `HomeView` уже содержит диалог и ввод даты/суммы (`src/finance_tracker/views/home_view.py:989`), а `LoanDetailsView` исполняет платеж без модалки параметров (`src/finance_tracker/views/loan_details_view.py:565`).

### Metis Review
**Identified gaps (addressed in this plan)**:
- Риск загрязнения аналитики при реализации через обычный `INCOME`: закрываем отдельной сущностью баланс-корректировок.
- Риск регрессии по обычным кредитам: закрываем строгим ветвлением по card-mode + регрессионными тестами.
- Невалидные ручные значения (`> payment`, `< 0`, пустые): закрываем явной валидацией + негативными тестами.
- Идемпотентность исполнения: запрещаем повторное применение корректировки к уже исполненному платежу.

---

## Work Objectives

### Core Objective
Добавить поддержку ручного учета состояния кредитных карт в момент исполнения планового платежа без изменения базового UX для обычных кредитов и без искажения отчетов доходов/расходов.

### Concrete Deliverables
- Обновленные модели и enum для card-mode сценариев.
- Миграция схемы SQLite (добавление колонок/таблицы без потери данных).
- Обновленный сервис исполнения платежа с mode-specific входом.
- Обновленный расчет общего баланса с учетом `reusable`-корректировок.
- Обновленный UI исполнения платежа в Home и Loan Details.
- Полный TDD-комплект тестов + регрессии.

### Definition of Done
- [ ] Для `reusable` после исполнения платежа с `returned_to_active_balance` общий баланс увеличивается на эту сумму, но доходная аналитика не меняется.
- [ ] Для `repayment_only` после исполнения платежа сохраняется `remaining_debt_after_payment` на кредите.
- [ ] Поведение исполнения для обычного кредита (без card-mode) не изменено.
- [ ] Все новые и затронутые тесты проходят, покрытие не ниже 66%.

### Must Have
- Ручной ввод mode-specific значений в момент исполнения платежа.
- Валидация входа (диапазоны, обязательность по режиму).
- Нулевая ручная проверка: все acceptance criteria проверяются агентом командами/тестами.

### Must NOT Have (Guardrails)
- Не внедрять учет покупок по кредитке и выписочные циклы банка.
- Не добавлять `credit_limit` и связанные расчеты.
- Не превращать `returned_to_active_balance` в обычный `INCOME`.
- Не менять UX/логику обычных кредитов вне необходимых ветвлений по card-mode.

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> Каждая проверка выполняется агентом автоматически (pytest/ruff/tmux). Ручная верификация пользователем не допускается.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD
- **Framework**: pytest + pytest-cov + hypothesis + pytest-asyncio

### TDD Protocol (для каждой задачи)
1. **RED**: добавляем/обновляем тесты, убеждаемся что сценарий падает.
2. **GREEN**: минимальная реализация до прохождения тестов.
3. **REFACTOR**: упрощение кода без изменения поведения, повторный прогон тестов.

### Agent-Executed QA Scenarios (общие)

Scenario: RED phase действительно красная
  Tool: Bash
  Preconditions: Изменения тестов применены, реализация еще не внесена
  Steps:
    1. Запустить `pytest tests/ -k "credit_card and (reusable or repayment_only)" -v`
    2. Зафиксировать минимум один FAIL по новому сценарию
    3. Сохранить вывод в `.sisyphus/evidence/red-phase-credit-card.txt`
  Expected Result: Есть прогнозируемые падения новых тестов
  Failure Indicators: Все тесты PASS до реализации
  Evidence: `.sisyphus/evidence/red-phase-credit-card.txt`

Scenario: GREEN+REFACTOR стабильно зеленые
  Tool: Bash
  Preconditions: Реализация и рефактор завершены
  Steps:
    1. Запустить `pytest tests/ -k "loan or credit_card" -v`
    2. Запустить `pytest tests/ --cov=src/finance_tracker --cov-fail-under=66`
    3. Сохранить выводы в `.sisyphus/evidence/green-phase-credit-card.txt` и `.sisyphus/evidence/coverage-credit-card.txt`
  Expected Result: Все тесты PASS, покрытие >= 66%
  Failure Indicators: Есть FAIL/ERROR или coverage ниже порога
  Evidence: `.sisyphus/evidence/green-phase-credit-card.txt`, `.sisyphus/evidence/coverage-credit-card.txt`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation):
└── Task 1: Модель и схема card-mode + balance-adjustment

Wave 2 (Core service):
└── Task 2: Сервис исполнения платежа с mode-specific вводом

Wave 3 (Parallel after Wave 2):
├── Task 3: Интеграция в общий баланс без загрязнения аналитики
└── Task 4: UI исполнения платежа (Home + Loan Details)

Wave 4 (Final):
└── Task 5: Сквозные интеграции, регрессии, стабилизация

Critical Path: Task 1 -> Task 2 -> Task 4 -> Task 5
Parallel Speedup: ~20-25% быстрее последовательного выполнения
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 4 | None |
| 2 | 1 | 3, 4, 5 | None |
| 3 | 1, 2 | 5 | 4 |
| 4 | 1, 2 | 5 | 3 |
| 5 | 3, 4 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` |
| 2 | 2 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` |
| 3 | 3, 4 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` and `task(category="visual-engineering", load_skills=["frontend-ui-ux"], run_in_background=false)` |
| 4 | 5 | `task(category="deep", load_skills=["git-master"], run_in_background=false)` |

---

## TODOs

- [ ] 1. Расширить доменную модель: card-mode и отдельная сущность balance adjustment

  **What to do**:
  - RED: добавить тесты на новые enum/поля и инварианты модели.
  - GREEN:
    - добавить enum режима карты (например, `LoanCardMode`) в `src/finance_tracker/models/enums.py`.
    - добавить в `LoanDB` поля для card-mode сценариев (режим + поле ручного остатка для `repayment_only`).
    - добавить новую таблицу `BalanceAdjustmentDB` (связь с `loan_id` и `loan_payment_id`, сумма, дата, причина/тип).
    - обновить экспорт в `src/finance_tracker/models/__init__.py`.
    - добавить миграцию схемы в `src/finance_tracker/database.py` (ALTER для новых колонок + create table при отсутствии).
  - REFACTOR: унифицировать именование и индексы, убрать дубли в валидации.

  **Must NOT do**:
  - Не добавлять `credit_limit`.
  - Не добавлять учет покупок по карте.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: затрагиваются ORM-модели + миграция схемы + обратная совместимость.
  - **Skills**: [`git-master`]
    - `git-master`: нужен для аккуратной фиксации атомарных изменений модели/миграции.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: не нужен, UI не является ядром этой задачи.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: 2, 3, 4
  - **Blocked By**: None

  **References**:
  - `src/finance_tracker/models/enums.py:104` - текущие enum кредитов/платежей, точка добавления card-mode.
  - `src/finance_tracker/models/models.py:427` - `LoanDB`, куда добавляются режим и ручной остаток.
  - `src/finance_tracker/models/models.py:566` - `LoanPaymentDB`, привязка для `BalanceAdjustmentDB.loan_payment_id`.
  - `src/finance_tracker/models/__init__.py:8` - централизованный экспорт новых enum/моделей.
  - `src/finance_tracker/database.py:42` - существующий паттерн миграции через idempotent ALTER.
  - `README.md` (раздел про UUID migration) - требования к совместимости схемы.
  - External: `https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html` - корректное объявление новых таблиц/индексов.

  **Acceptance Criteria**:
  - [ ] Новый enum режима карты доступен в `finance_tracker.models` и используется в `LoanDB`.
  - [ ] Таблица `balance_adjustments` создается в новой БД и не ломает инициализацию существующей.
  - [ ] Миграция существующей SQLite БД добавляет новые колонки без удаления данных.

  **Agent-Executed QA Scenarios**:

  Scenario: Миграция добавляет новые поля в существующую схему
    Tool: Bash
    Preconditions: Тестовая SQLite БД создана по старой схеме
    Steps:
      1. Запустить `pytest tests/ -k "migration and credit_card" -v`
      2. Проверить assert наличия новых колонок через SQLAlchemy inspector в тесте
      3. Сохранить вывод в `.sisyphus/evidence/task-1-migration.txt`
    Expected Result: Тест миграции PASS
    Failure Indicators: Отсутствуют новые колонки или падает init_db
    Evidence: `.sisyphus/evidence/task-1-migration.txt`

  Scenario: Негативный - невалидный режим карты отклоняется
    Tool: Bash
    Preconditions: Добавлены валидации модели/enum
    Steps:
      1. Запустить `pytest tests/ -k "invalid_card_mode" -v`
      2. Проверить, что тест ожидает `ValueError`/validation error
      3. Сохранить вывод в `.sisyphus/evidence/task-1-invalid-mode.txt`
    Expected Result: Невалидный режим не сохраняется
    Failure Indicators: Невалидное значение проходит в БД
    Evidence: `.sisyphus/evidence/task-1-invalid-mode.txt`

  **Commit**: YES
  - Message: `feat(loans): add card mode and balance adjustment schema`
  - Files: `src/finance_tracker/models/enums.py`, `src/finance_tracker/models/models.py`, `src/finance_tracker/models/__init__.py`, `src/finance_tracker/database.py`, `tests/*credit_card*`
  - Pre-commit: `pytest tests/ -k "credit_card and migration" -v`

---

- [ ] 2. Расширить сервис исполнения платежа mode-specific входом и валидацией

  **What to do**:
  - RED: написать тесты на `reusable`/`repayment_only` сценарии в сервисном слое.
  - GREEN:
    - расширить контракт исполнения платежа для приема `returned_to_active_balance` и `remaining_debt_after_payment`.
    - в `reusable` создавать запись в `balance_adjustments`.
    - в `repayment_only` сохранять ручной остаток в поле кредита.
    - для обычного кредита поведение оставить прежним.
    - запретить повторное применение mode-specific эффектов к уже исполненному платежу.
  - REFACTOR: вынести валидацию mode-specific значений в отдельные helper-функции.

  **Must NOT do**:
  - Не изменять бизнес-логику процентов/графика платежей.
  - Не создавать обычные доходные транзакции для `reusable`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: критическая бизнес-логика с риском регрессии по платежам.
  - **Skills**: [`git-master`]
    - `git-master`: контроль атомарности изменений в сервисах и тестах.
  - **Skills Evaluated but Omitted**:
    - `playwright`: не нужен, задача backend/service.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: 3, 4, 5
  - **Blocked By**: 1

  **References**:
  - `src/finance_tracker/services/loan_service.py:565` - текущая реализация `execute_payment`.
  - `src/finance_tracker/services/loan_payment_service.py:885` - facade-обертка исполнения.
  - `src/finance_tracker/views/home_presenter.py:383` - текущий вызов сервиса и игнор `amount`.
  - `src/finance_tracker/models/models.py:566` - `LoanPaymentDB` статусы/поля факта исполнения.
  - `tests/test_loan_payment_properties.py:36` - существующий паттерн property-тестов execute_payment.
  - External: `https://docs.pydantic.dev/latest/concepts/validators/` - валидация входного payload.

  **Acceptance Criteria**:
  - [ ] `reusable`: `returned_to_active_balance` валидируется в диапазоне `0..transaction_amount`.
  - [ ] `repayment_only`: `remaining_debt_after_payment` обязателен и `>= 0`.
  - [ ] Обычный кредит исполняется как раньше (без дополнительных обязательных полей).
  - [ ] Повторное исполнение платежа не создает повторных side-effects.

  **Agent-Executed QA Scenarios**:

  Scenario: reusable-платеж создает balance adjustment
    Tool: Bash
    Preconditions: Тестовые данные `LoanDB(card_mode=reusable)` и `LoanPaymentDB(PENDING)`
    Steps:
      1. Запустить `pytest tests/ -k "reusable and execute_payment" -v`
      2. Проверить assert, что запись balance adjustment создана и связана с payment.id
      3. Сохранить вывод в `.sisyphus/evidence/task-2-reusable.txt`
    Expected Result: PASS, adjustment создан ровно один раз
    Failure Indicators: Нет adjustment или создано >1 записи
    Evidence: `.sisyphus/evidence/task-2-reusable.txt`

  Scenario: Негативный - returned_to_active_balance больше суммы платежа
    Tool: Bash
    Preconditions: Тестовый reusable payment
    Steps:
      1. Запустить `pytest tests/ -k "returned_to_active_balance and invalid" -v`
      2. Проверить assert на ожидаемый `ValueError`
      3. Сохранить вывод в `.sisyphus/evidence/task-2-invalid-returned.txt`
    Expected Result: Ошибка валидации, платеж не исполняется
    Failure Indicators: Платеж исполняется с невалидным значением
    Evidence: `.sisyphus/evidence/task-2-invalid-returned.txt`

  **Commit**: YES
  - Message: `feat(loans): support card-mode execution inputs`
  - Files: `src/finance_tracker/services/loan_service.py`, `src/finance_tracker/services/loan_payment_service.py`, `tests/test_loan_payment_*`
  - Pre-commit: `pytest tests/ -k "loan_payment and (reusable or repayment_only)" -v`

---

- [ ] 3. Включить reusable-корректировки в общий баланс без влияния на аналитику

  **What to do**:
  - RED: добавить тесты, что `get_total_balance` учитывает balance adjustments.
  - GREEN:
    - расширить `get_total_balance` суммой из `balance_adjustments`.
    - убедиться, что месячная/категорийная аналитика остается на транзакциях и не включает adjustments.
  - REFACTOR: вынести суммирование balance adjustments в helper-функцию сервиса.

  **Must NOT do**:
  - Не менять семантику статистики доходов/расходов.
  - Не изменять enum `TransactionType` без необходимости.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: изменения затрагивают глобальную финансовую метрику приложения.
  - **Skills**: [`git-master`]
    - `git-master`: помогает изолировать балансные изменения от UI-фич.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: не требуется для сервисной метрики.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (с Task 4)
  - **Blocks**: 5
  - **Blocked By**: 1, 2

  **References**:
  - `src/finance_tracker/services/transaction_service.py:38` - точка расчета общего баланса.
  - `src/finance_tracker/views/main_window.py:95` - UI-потребитель общего баланса.
  - `tests/test_transaction_deletion_comprehensive.py:83` - существующие инварианты `get_total_balance`.
  - `tests/test_main_window.py:406` - проверка корректного вывода баланса в UI.

  **Acceptance Criteria**:
  - [ ] `get_total_balance` = `income - expense + sum(balance_adjustments.amount)`.
  - [ ] Старые тесты на доход/расход продолжают проходить без правки бизнес-смысла.
  - [ ] Новые adjustment-значения видны в `MainWindow.update_balance` через существующий вызов.

  **Agent-Executed QA Scenarios**:

  Scenario: balance adjustment влияет на общий баланс
    Tool: Bash
    Preconditions: В БД есть income/expense + один reusable adjustment
    Steps:
      1. Запустить `pytest tests/ -k "total_balance and adjustment" -v`
      2. Проверить assert формулы расчета
      3. Сохранить вывод в `.sisyphus/evidence/task-3-total-balance.txt`
    Expected Result: PASS, формула расчета совпадает
    Failure Indicators: adjustment не учтен или учтен с неверным знаком
    Evidence: `.sisyphus/evidence/task-3-total-balance.txt`

  Scenario: Негативный - аналитика доходов/расходов не включает adjustment
    Tool: Bash
    Preconditions: Есть adjustment и транзакции в одном месяце
    Steps:
      1. Запустить `pytest tests/ -k "month_stats and adjustment_excluded" -v`
      2. Проверить assert, что monthly/category stats не изменились из-за adjustment
      3. Сохранить вывод в `.sisyphus/evidence/task-3-analytics-excluded.txt`
    Expected Result: PASS, аналитика чистая
    Failure Indicators: adjustment попал в доходы/расходы
    Evidence: `.sisyphus/evidence/task-3-analytics-excluded.txt`

  **Commit**: YES
  - Message: `feat(balance): include reusable adjustments in total balance`
  - Files: `src/finance_tracker/services/transaction_service.py`, `tests/test_*balance*`
  - Pre-commit: `pytest tests/ -k "total_balance or month_stats" -v`

---

- [ ] 4. Обновить UI исполнения платежа (Home + Loan Details) для mode-specific полей

  **What to do**:
  - RED: добавить UI-тесты на отображение/валидацию полей для `reusable` и `repayment_only`.
  - GREEN:
    - в `HomeView.on_execute_loan_payment` добавить условные поля:
      - `reusable`: поле `Сумма возврата в активный баланс`.
      - `repayment_only`: поле `Остаток к погашению после платежа`.
    - передавать mode-specific payload через `HomePresenter.execute_loan_payment` в сервис.
    - привести `LoanDetailsView.execute_payment_action` к тому же потоку ввода (через модалку/общий helper), убрать "слепое" исполнение без параметров.
  - REFACTOR: вынести повторяющийся код диалога в отдельный UI-компонент.

  **Must NOT do**:
  - Не ломать текущую дату/сумму исполнения для обычных кредитов.
  - Не использовать deprecated Flet API (`page.dialog`, `dialog.open`).

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: правки в пользовательском сценарии исполнения платежа и модальных формах.
  - **Skills**: [`frontend-ui-ux`, `git-master`]
    - `frontend-ui-ux`: аккуратно оформить mode-specific форму без UX-регрессий.
    - `git-master`: держать изменения UI атомарными и связными с сервисным контрактом.
  - **Skills Evaluated but Omitted**:
    - `playwright`: проект опирается на pytest UI-тесты с моками Flet.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (с Task 3)
  - **Blocks**: 5
  - **Blocked By**: 1, 2

  **References**:
  - `src/finance_tracker/views/home_view.py:989` - текущий диалог исполнения с суммой и датой.
  - `src/finance_tracker/views/home_presenter.py:383` - место передачи данных исполнения в сервис.
  - `src/finance_tracker/views/loan_details_view.py:565` - текущий путь исполнения без mode-specific ввода.
  - `tests/test_home_view.py` - паттерны UI тестов для HomeView.
  - `tests/test_loan_details_view.py:336` - существующие тесты исполнения платежа в LoanDetailsView.
  - `AGENTS.md` (repo): правило Flet `page.open/page.close`.

  **Acceptance Criteria**:
  - [ ] Для `reusable` в модалке есть дополнительное поле возврата и оно валидируется.
  - [ ] Для `repayment_only` в модалке есть поле остатка и оно валидируется.
  - [ ] Для обычного кредита UI не требует новых полей.
  - [ ] Presenter передает mode-specific данные в сервис исполнения.

  **Agent-Executed QA Scenarios**:

  Scenario: HomeView показывает поле возврата для reusable
    Tool: Bash
    Preconditions: UI-тест с mock payment.loan.card_mode = reusable
    Steps:
      1. Запустить `pytest tests/test_home_view.py -k "execute_loan_payment and reusable" -v`
      2. Проверить assert наличия нужного TextField и корректной передачи в presenter
      3. Сохранить вывод в `.sisyphus/evidence/task-4-home-reusable.txt`
    Expected Result: PASS, поле есть и payload передается
    Failure Indicators: Поле отсутствует или presenter вызван без значения
    Evidence: `.sisyphus/evidence/task-4-home-reusable.txt`

  Scenario: Негативный - repayment_only отклоняет отрицательный остаток
    Tool: Bash
    Preconditions: UI-тест с mock payment.loan.card_mode = repayment_only
    Steps:
      1. Запустить `pytest tests/ -k "repayment_only and negative_remaining_debt" -v`
      2. Проверить assert, что сервис не вызывается и показывается ошибка валидации
      3. Сохранить вывод в `.sisyphus/evidence/task-4-invalid-remaining.txt`
    Expected Result: PASS, невалидный ввод блокирует исполнение
    Failure Indicators: Сервис вызван при невалидных данных
    Evidence: `.sisyphus/evidence/task-4-invalid-remaining.txt`

  **Commit**: YES
  - Message: `feat(ui): add card-mode fields to loan payment execution`
  - Files: `src/finance_tracker/views/home_view.py`, `src/finance_tracker/views/home_presenter.py`, `src/finance_tracker/views/loan_details_view.py`, `tests/test_home_view.py`, `tests/test_loan_details_view.py`
  - Pre-commit: `pytest tests/ -k "home_view or loan_details_view" -v`

---

- [ ] 5. Сквозная интеграция, регрессии и стабилизация

  **What to do**:
  - RED: добавить интеграционные сценарии end-to-end по двум режимам карт.
  - GREEN:
    - проверить цепочку: UI -> presenter -> service -> DB -> total balance.
    - добавить регрессию по обычному кредиту (без card-mode).
    - убедиться, что CI-порог покрытия выдержан.
  - REFACTOR: сократить дубли тест-фикстур, оставить только стабильные сценарии.

  **Must NOT do**:
  - Не менять требования по покрытию/линтингу.
  - Не отключать существующие тесты регрессии.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: сквозная проверка нескольких слоев и стабилизация без регрессий.
  - **Skills**: [`git-master`]
    - `git-master`: удобен для раздельных фикс-коммитов по найденным регрессиям.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: здесь фокус на интеграции и тестовой стабильности.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None (final)
  - **Blocked By**: 3, 4

  **References**:
  - `tests/test_loan_payment_integration.py:20` - шаблон интеграционных тестов по кредитным платежам.
  - `tests/test_loan_payment_properties.py:194` - pattern-based проверки `execute_payment`.
  - `tests/test_main_window.py:406` - проверка, что UI берет баланс из сервиса.
  - `.github/workflows/ci.yml` - обязательные команды CI.
  - `pyproject.toml` - pytest/coverage настройки и порог.

  **Acceptance Criteria**:
  - [ ] Добавлены интеграционные тесты для `reusable` и `repayment_only`.
  - [ ] Регрессия: старые сценарии обычного кредита PASS.
  - [ ] `ruff check src tests` PASS.
  - [ ] `pytest tests/ --cov=src/finance_tracker --cov-fail-under=66` PASS.

  **Agent-Executed QA Scenarios**:

  Scenario: End-to-end reusable flow
    Tool: Bash
    Preconditions: Интеграционные тесты для reusable добавлены
    Steps:
      1. Запустить `pytest tests/ -k "integration and reusable and loan_payment" -v`
      2. Проверить assert, что после исполнения меняется total balance и создается adjustment
      3. Сохранить вывод в `.sisyphus/evidence/task-5-e2e-reusable.txt`
    Expected Result: PASS по сквозному reusable сценарию
    Failure Indicators: Баланс/adjustment не соответствуют ожиданиям
    Evidence: `.sisyphus/evidence/task-5-e2e-reusable.txt`

  Scenario: End-to-end repayment_only + regression classic loan
    Tool: Bash
    Preconditions: Интеграционные и регрессионные тесты добавлены/обновлены
    Steps:
      1. Запустить `pytest tests/ -k "repayment_only or classic_loan_regression" -v`
      2. Проверить assert, что repayment_only обновляет остаток долга, а classic loan работает без новых обязательных полей
      3. Сохранить вывод в `.sisyphus/evidence/task-5-e2e-repayment-only.txt`
    Expected Result: PASS для обоих сценариев
    Failure Indicators: Ломается старое поведение или не сохраняется ручной остаток
    Evidence: `.sisyphus/evidence/task-5-e2e-repayment-only.txt`

  **Commit**: YES
  - Message: `test(loans): add integration coverage for card-mode execution`
  - Files: `tests/test_*credit_card*`, `tests/test_*loan_payment*`, `tests/test_main_window.py` (при необходимости)
  - Pre-commit: `ruff check src tests && pytest tests/ --cov=src/finance_tracker --cov-fail-under=66`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(loans): add card mode and balance adjustment schema` | models + database + model tests | `pytest tests/ -k "credit_card and migration" -v` |
| 2 | `feat(loans): support card-mode execution inputs` | loan services + service tests | `pytest tests/ -k "loan_payment and (reusable or repayment_only)" -v` |
| 3 | `feat(balance): include reusable adjustments in total balance` | transaction service + balance tests | `pytest tests/ -k "total_balance or month_stats" -v` |
| 4 | `feat(ui): add card-mode fields to loan payment execution` | home/loan details views + UI tests | `pytest tests/ -k "home_view or loan_details_view" -v` |
| 5 | `test(loans): add integration coverage for card-mode execution` | integration/regression tests | `ruff check src tests && pytest tests/ --cov=src/finance_tracker --cov-fail-under=66` |

---

## Success Criteria

### Verification Commands

```bash
ruff check src tests
pytest tests/ -k "credit_card or reusable or repayment_only" -v
pytest tests/ -k "loan_payment and not slow" -v
pytest tests/ --cov=src/finance_tracker --cov-fail-under=66
```

### Final Checklist
- [ ] Все Must Have реализованы.
- [ ] Все Must NOT Have соблюдены.
- [ ] `reusable` корректировки влияют на общий баланс и не попадают в доходную аналитику.
- [ ] `repayment_only` сохраняет ручной остаток к погашению после исполнения.
- [ ] Обычные кредиты работают без регрессии.
- [ ] Полный тестовый прогон зеленый.
