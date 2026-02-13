# Иерархия категорий расходов и split-экран категорий

## TL;DR

> **Quick Summary**: Добавляем 1-уровневую иерархию только для расходных категорий (`parent -> child`) и перестраиваем экран категорий в split-режим (слева доходы, справа расходы). Во всех формах выбора категории внедряем правило `leaf-only`.
>
> **Deliverables**:
> - Обновленная доменная модель категорий с `parent_id` и инвариантами 1 уровня
> - Иерархический `category_service` + leaf-only проверки в сервисах транзакций/планов/отложенных платежей
> - Новый split UI экрана категорий без вкладок
> - Обновленные селекторы категорий и фильтры истории/план-факт
> - Совместимость snapshot export/import с parent-child категориями
> - TDD-покрытие и регрессионный прогон
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 -> Task 2 -> Task 4 -> Task 7

---

## Context

### Original Request
- Добавить поддержку иерархии для категорий расходов.
- Изменить UI: разделить экран на две части, чтобы одновременно видеть доходы (слева) и расходы (справа).

### Interview Summary
**Подтверждено пользователем**:
- Глубина дерева: строго 1 уровень (`родитель -> подкатегории`).
- Иерархия только для расходов.
- Транзакции/планы/отложенные платежи: выбор только листовых категорий.
- Экран категорий: 2 колонки без вкладок.
- Нужно обновить не только экран категорий, но и селекторы категорий в формах.
- БД сейчас пустая, отдельная миграция legacy-данных не требуется.
- Подкатегории у системных расходных категорий разрешены.
- Стратегия тестирования: TDD.

**Исследование по коду**:
- `CategoryDB` сейчас плоская: `src/finance_tracker/models/models.py`.
- CRUD категорий плоский: `src/finance_tracker/services/category_service.py`.
- Экран категорий основан на табах и одном списке: `src/finance_tracker/views/categories_view.py`.
- Селекторы категорий есть в:
  - `src/finance_tracker/components/transaction_modal.py`
  - `src/finance_tracker/components/planned_transaction_modal.py`
  - `src/finance_tracker/components/pending_payment_modal.py`
- Категории также используются в фильтрах:
  - `src/finance_tracker/views/transaction_history_view.py`
  - `src/finance_tracker/views/plan_fact_view.py`

### Metis Review
**Гэп-риски, закрытые в плане**:
- Риск расползания leaf-only: валидация будет и в UI, и в сервисах (hard guard).
- Риск self-FK в snapshot import/export: добавлены отдельные задачи и критерии parent-first вставки.
- Риск усложнения UI: фиксируем scope без drag&drop, без глубины >1, без возврата табов.
- Риск detached ORM-кэша: иерархия вычисляется по плоскому набору (`parent_id`) без lazy traversal.

**Defaults Applied (можно переопределить позже)**:
- Уникальность имени категории остается глобальной (как сейчас).
- В фильтрах истории/план-факт выбор родителя трактуется как агрегат по родителю + детям.
- Запрещаем делать категорию родителем, если она уже используется в транзакциях/планах/платежах.

---

## Work Objectives

### Core Objective
Внедрить безопасную и тестируемую 1-уровневую иерархию расходных категорий и новый split-интерфейс экрана категорий, сохранив целостность данных и единое правило `leaf-only` во всех точках выбора категории.

### Concrete Deliverables
- Обновленная модель `CategoryDB` + Pydantic-контракты категорий.
- Иерархические операции в `category_service`.
- Split-layout в `CategoriesView` и расширенный `CategoryDialog`.
- Leaf-only поведение в формах:
  - Transaction modal
  - Planned transaction modal
  - Pending payment modal
- Иерархическая логика фильтров в истории и план-факт.
- Snapshot export/import с корректной обработкой parent-child.
- Обновленные/новые тесты (unit + property + integration-targeted).

### Definition of Done
- [x] Для EXPENSE работает 1 уровень иерархии, для INCOME иерархия не поддерживается.
- [x] Категория с детьми не может быть выбрана в транзакцию/план/отложенный платеж.
- [x] Экран категорий показывает 2 колонки без вкладок (доходы слева, расходы справа).
- [x] Все релевантные тесты проходят (`pytest`), линтер чистый (`ruff`).
- [x] Snapshot export/import корректно работает с parent-child категориями.

### Must Have
- Инварианты иерархии в сервисном слое (не только UI).
- Явные негативные тесты на глубину, leaf-only и запрет опасных операций.
- Современный Flet API для overlay (`page.open/page.close`).

### Must NOT Have (Guardrails)
- Без глубины >1.
- Без иерархии для доходов.
- Без drag&drop дерева и без расширенного визуального редактора структуры.
- Без восстановления табов на экране категорий.
- Без ручной пользовательской верификации в acceptance criteria.
- Без изменения бизнес-логики вне области категорий (кроме необходимых leaf-only guards и фильтров).

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> Все критерии приемки в этом плане должны проверяться агентом автоматически: через `pytest`, `ruff`, и детерминированные команды/ассерты. Никаких шагов вида "пользователь вручную проверяет".

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: TDD
- **Framework**: pytest (+ hypothesis для property-based)

### TDD Flow (для каждого TODO)
1. **RED**: сначала добавить/обновить тест(ы), которые падают на текущем коде.
2. **GREEN**: минимальная реализация до passing.
3. **REFACTOR**: упрощение/чистка без регрессии.

### Agent-Executed QA Scenarios
- Основная верификация по UI/domain сценариям выполняется запуском `pytest` с конкретными тест-кейсами.
- Для каждого TODO предусмотрены happy-path + negative-path сценарии с конкретными командами и артефактами в `.sisyphus/evidence/`.

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1:
└── Task 1 (модель/контракты)

Wave 2 (после Task 1):
└── Task 2 (service-инварианты категорий)

Wave 3 (после Task 2, параллельно):
├── Task 3 (split UI категорий)
├── Task 4 (leaf-only селекторы + сервисы транзакций/планов/платежей)
├── Task 5 (фильтры истории/план-факт)
└── Task 6 (snapshot export/import)

Wave 4 (после Wave 3):
└── Task 7 (регрессия, стабилизация, финальная проверка)

Critical Path: 1 -> 2 -> 4 -> 7
Parallel Speedup: ~35-45% против полностью последовательного выполнения
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 2, 6 | None |
| 2 | 1 | 3, 4, 5 | None |
| 3 | 2 | 7 | 4, 5, 6 |
| 4 | 2 | 7 | 3, 5, 6 |
| 5 | 2 | 7 | 3, 4, 6 |
| 6 | 1 (и частично 2 по инвариантам) | 7 | 3, 4, 5 |
| 7 | 3, 4, 5, 6 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|--------------------|
| 1 | 1 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` |
| 2 | 2 | `task(category="unspecified-high", load_skills=["git-master"], run_in_background=false)` |
| 3 | 3,4,5,6 | По одному агенту на задачу, запускать параллельно после Wave 2 |
| 4 | 7 | Интеграционный агент для финального прогона и стабилизации |

---

## TODOs

- [x] 1. Обновить модель категорий и контракты под 1-уровневую иерархию расходов

  **What to do**:
  - Добавить `parent_id` (nullable self-FK) в `CategoryDB`.
  - Добавить self-relationship (`parent` / `children`) без lazy-зависимостей в бизнес-логике.
  - Обновить `Category`/`CategoryCreate` модели (Pydantic) с учетом `parent_id`.
  - Зафиксировать инварианты структуры:
    - `INCOME` всегда `parent_id = None`
    - `EXPENSE` child может ссылаться только на `EXPENSE` root
    - глубина только 1 уровень
  - Сохранить поведение инициализации дефолтных категорий как корневых.

  **Must NOT do**:
  - Не добавлять миграцию существующей БД (по договоренности БД пустая).
  - Не менять UUID-модель идентификаторов.
  - Не добавлять nullable/типовые обходы через `Any`.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: доменные инварианты + self-FK + совместимость с существующими сервисами.
  - **Skills**: [`git-master`]
    - `git-master`: полезен для безопасной поэтапной фиксации и проверки влияния по истории.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: не нужен на уровне модели/схемы.
    - `playwright`: UI-автоматизация не является ядром этой задачи.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: 2, 6
  - **Blocked By**: None

  **References**:
  - `src/finance_tracker/models/models.py` - текущий `CategoryDB` и Pydantic-модели категорий.
  - `src/finance_tracker/models/__init__.py` - экспорт типов, чтобы не сломать импорты.
  - `src/finance_tracker/database.py` - инициализация baseline/system категорий.
  - `tests/test_uuid_migration_models.py` - регрессионные ожидания по UUID-модели.
  - `tests/test_factories.py` - фабрики категорий, которые нужно синхронизировать с новым полем.
  - `src/finance_tracker/models/enums.py` - корректная типизация `TransactionType`.
  - External: `https://docs.sqlalchemy.org/en/20/orm/self_referential.html` - паттерн self-referential relationship в SQLAlchemy 2.x.

  **Acceptance Criteria**:
  - [ ] RED: добавлены тесты модели/инвариантов, которые падают без `parent_id`-логики.
  - [ ] GREEN: `pytest tests/test_category_hierarchy_model.py -v` -> PASS.
  - [ ] REFACTOR: код модели и Pydantic-контракты приведены к единообразному стилю.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: EXPENSE parent-child создаются и читаются корректно
    Tool: Bash (pytest)
    Preconditions: Тестовая SQLite in-memory БД, применена новая модель CategoryDB
    Steps:
      1. pytest tests/test_category_hierarchy_model.py -k "expense_parent_child_happy" -v | tee .sisyphus/evidence/task-1-expense-parent-child.txt
      2. Assert: exit code = 0
      3. Assert: output содержит "1 passed"
    Expected Result: Тест подтверждает валидную связку root EXPENSE -> child EXPENSE
    Failure Indicators: IntegrityError/AssertionError/DetachedInstanceError в выводе
    Evidence: .sisyphus/evidence/task-1-expense-parent-child.txt

  Scenario: Запрет недопустимой структуры (INCOME child и глубина > 1)
    Tool: Bash (pytest)
    Preconditions: Добавлены негативные тест-кейсы модели
    Steps:
      1. pytest tests/test_category_hierarchy_model.py -k "reject_income_parent or reject_grandchild" -v | tee .sisyphus/evidence/task-1-invalid-structure.txt
      2. Assert: exit code = 0
      3. Assert: output содержит оба кейса как passed
    Expected Result: Негативные кейсы корректно ловят нарушения инвариантов
    Failure Indicators: Тесты проходят без ошибок там, где ожидался ValueError/валидационная ошибка
    Evidence: .sisyphus/evidence/task-1-invalid-structure.txt
  ```

  **Commit**: YES
  - Message: `feat(categories): add expense hierarchy model primitives`
  - Files: `src/finance_tracker/models/models.py`, `src/finance_tracker/models/__init__.py`, `src/finance_tracker/database.py`, `tests/test_category_hierarchy_model.py`
  - Pre-commit: `pytest tests/test_category_hierarchy_model.py -v`

---

- [x] 2. Расширить category_service инвариантами и операциями иерархии

  **What to do**:
  - Обновить `create_category`/`update_category` для работы с `parent_id`.
  - Реализовать сервисные проверки:
    - parent существует
    - parent типа `EXPENSE`
    - parent сам корневой (глубина = 1)
    - child только для `EXPENSE`
    - запрет цикла/самоссылки
  - Ввести helper-и:
    - получить expense tree для UI
    - получить selectable leaf categories для форм
  - Удаление:
    - запрет удалять родителя с детьми
  - Защитный default из Metis:
    - запрет создавать child у категории, которая уже используется в транзакциях/планах/платежах.
  - Сохранять текущую глобальную уникальность имени.
  - Обеспечить корректную инвалидацию кэша категорий.

  **Must NOT do**:
  - Не ослаблять текущие проверки системных категорий.
  - Не переносить бизнес-валидацию исключительно в UI.
  - Не разрешать обход leaf-only через прямой вызов сервиса.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: сложные доменные ограничения и влияние на несколько бизнес-сервисов.
  - **Skills**: [`git-master`]
    - `git-master`: помогает безопасно проверить влияние и структурировать атомарные коммиты.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: UI в этой задаче вторичен.
    - `playwright`: verification через pytest достаточен.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: 3, 4, 5
  - **Blocked By**: 1

  **References**:
  - `src/finance_tracker/services/category_service.py` - текущие create/update/delete/get_all и кэш.
  - `src/finance_tracker/models/models.py` - связи категорий и связанные таблицы (`TransactionDB`, `PlannedTransactionDB`, `PendingPaymentDB`).
  - `src/finance_tracker/utils/cache.py` - текущая модель инвалидации и хранения кэша категорий.
  - `tests/test_category_properties.py` - property-тесты уникальности/защит и удалений.
  - `tests/test_integration.py` - интеграционные сценарии, где категория участвует в бизнес-потоке.
  - External: `https://docs.sqlalchemy.org/en/20/orm/cascades.html` - контроль удалений и self-FK рисков.

  **Acceptance Criteria**:
  - [ ] RED: добавлены тесты на сервисные инварианты и они падают до реализации.
  - [ ] GREEN: `pytest tests/test_category_hierarchy_service.py -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_category_properties.py -k "unique_name or system_category_protection or linked_transaction_protection" -v` -> PASS.
  - [ ] REFACTOR: сервис читается линейно, инварианты вынесены в маленькие приватные проверки.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Создание child у системного expense родителя разрешено
    Tool: Bash (pytest)
    Preconditions: Есть системная EXPENSE категория без дочерних узлов
    Steps:
      1. pytest tests/test_category_hierarchy_service.py -k "create_child_under_system_parent" -v | tee .sisyphus/evidence/task-2-child-under-system-parent.txt
      2. Assert: exit code = 0
      3. Assert: output содержит "1 passed"
    Expected Result: child создается успешно, parent остается неизменяемым/неудаляемым по старым правилам
    Failure Indicators: ValueError/IntegrityError при валидном сценарии
    Evidence: .sisyphus/evidence/task-2-child-under-system-parent.txt

  Scenario: Нельзя удалить родителя с дочерними категориями
    Tool: Bash (pytest)
    Preconditions: Созданы root + child
    Steps:
      1. pytest tests/test_category_hierarchy_service.py -k "reject_delete_parent_with_children" -v | tee .sisyphus/evidence/task-2-delete-parent-block.txt
      2. Assert: exit code = 0
      3. Assert: в тесте зафиксирован ValueError с понятным сообщением
    Expected Result: Удаление родителя заблокировано
    Failure Indicators: Родитель удаляется или сообщение ошибки неинформативно
    Evidence: .sisyphus/evidence/task-2-delete-parent-block.txt

  Scenario: Запрет делать родителем категорию, уже используемую в транзакциях
    Tool: Bash (pytest)
    Preconditions: Категория привязана хотя бы к одной транзакции
    Steps:
      1. pytest tests/test_category_hierarchy_service.py -k "reject_add_child_to_used_category" -v | tee .sisyphus/evidence/task-2-used-category-parenting.txt
      2. Assert: exit code = 0
      3. Assert: тест подтверждает отказ с явной причиной
    Expected Result: Сервис не позволяет нарушить leaf-only инвариант задним числом
    Failure Indicators: Ребенок создается у используемой категории
    Evidence: .sisyphus/evidence/task-2-used-category-parenting.txt
  ```

  **Commit**: YES
  - Message: `feat(categories): enforce hierarchy invariants in service layer`
  - Files: `src/finance_tracker/services/category_service.py`, `tests/test_category_hierarchy_service.py`, `tests/test_category_properties.py`
  - Pre-commit: `pytest tests/test_category_hierarchy_service.py -v`

---

- [x] 3. Перестроить CategoriesView в split-layout и обновить CategoryDialog

  **What to do**:
  - Убрать tab-фильтры из `CategoriesView`.
  - Построить экран на двух явных зонах:
    - Левая колонка: доходы (плоский список)
    - Правая колонка: расходы (root + child визуально с отступом/группировкой)
  - Добавить явные точки создания:
    - доходной категории
    - расходной root категории
    - расходной subcategory (через parent selector)
  - В `CategoryDialog`:
    - добавить поле выбора parent только для расходных child
    - для edit-режима поддержать смену parent в рамках инвариантов
  - Обновить empty state и сервисные вызовы в новом layout.
  - Сохранить modern Flet overlay API (`page.open`, `page.close`).

  **Must NOT do**:
  - Не возвращать вкладки как основной паттерн.
  - Не добавлять drag&drop иерархии.
  - Не использовать deprecated API диалогов.

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: комплексная переработка экрана и UX-потока модалки.
  - **Skills**: [`frontend-ui-ux`, `playwright`]
    - `frontend-ui-ux`: для качественного split-layout и четкой визуальной иерархии.
    - `playwright`: для сценарной агентской проверки UI-поведения (если доступен веб-раннер).
  - **Skills Evaluated but Omitted**:
    - `git-master`: полезен, но не основной для UI-проектирования.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 4, 5, 6)
  - **Blocks**: 7
  - **Blocked By**: 2

  **References**:
  - `src/finance_tracker/views/categories_view.py` - текущая реализация с tabs и single-list.
  - `tests/test_categories_view.py` - unit-тесты экрана категорий.
  - `tests/test_categories_view_properties.py` - property-тесты фильтрации (переписать под split).
  - `tests/test_view_base.py` - паттерны моков `page.open/page.close`.
  - `.kiro/steering/ui-testing.md` - обязательные правила UI-тестов.
  - `AGENTS.md` - проектное правило modern Flet dialog API.
  - External: `https://flet.dev/docs/controls/responsiverow` - responsive split layout.

  **Acceptance Criteria**:
  - [ ] RED: тесты `CategoriesView` обновлены под split-layout и сначала падают.
  - [ ] GREEN: `pytest tests/test_categories_view.py -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_categories_view_properties.py -v` -> PASS.
  - [ ] REFACTOR: UI-код разбит на небольшие private helpers для читаемости.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Split layout отображает доходы слева и расходы справа без вкладок
    Tool: Bash (pytest)
    Preconditions: Обновлены тесты и мок-страница
    Steps:
      1. pytest tests/test_categories_view.py -k "split_layout or no_tabs" -v | tee .sisyphus/evidence/task-3-split-layout.txt
      2. Assert: exit code = 0
      3. Assert: тесты подтверждают наличие двух секций и отсутствие Tab-компонента
    Expected Result: Новый layout стабильно рендерится
    Failure Indicators: Использование legacy tab-flow или падения рендера
    Evidence: .sisyphus/evidence/task-3-split-layout.txt

  Scenario: Создание расходной подкатегории через parent selector
    Tool: Bash (pytest)
    Preconditions: Категории root EXPENSE доступны в данных
    Steps:
      1. pytest tests/test_categories_view.py -k "create_expense_subcategory_with_parent" -v | tee .sisyphus/evidence/task-3-create-subcategory.txt
      2. Assert: exit code = 0
      3. Assert: сервис вызван с parent_id и корректным типом EXPENSE
    Expected Result: child создается в правильной ветке
    Failure Indicators: parent_id не передается или child создается как root
    Evidence: .sisyphus/evidence/task-3-create-subcategory.txt

  Scenario: Нельзя создать вторую глубину из UI-потока
    Tool: Bash (pytest)
    Preconditions: Есть child-категория и попытка выбрать ее как parent
    Steps:
      1. pytest tests/test_categories_view.py -k "reject_second_level_from_dialog" -v | tee .sisyphus/evidence/task-3-reject-second-level.txt
      2. Assert: exit code = 0
      3. Assert: UI показывает понятную ошибку и не вызывает save
    Expected Result: Ограничение глубины соблюдается
    Failure Indicators: Создается grandchild или silent failure без ошибки
    Evidence: .sisyphus/evidence/task-3-reject-second-level.txt
  ```

  **Commit**: YES
  - Message: `feat(categories-ui): split income-expense layout and hierarchy dialog`
  - Files: `src/finance_tracker/views/categories_view.py`, `tests/test_categories_view.py`, `tests/test_categories_view_properties.py`
  - Pre-commit: `pytest tests/test_categories_view.py tests/test_categories_view_properties.py -v`

---

- [x] 4. Внедрить leaf-only селекторы в модалках и сервисные guards для транзакций/планов/платежей

  **What to do**:
  - Обновить загрузку категорий в модалках:
    - `transaction_modal.py`
    - `planned_transaction_modal.py`
    - `pending_payment_modal.py`
  - Для `EXPENSE` показывать только leaf-категории; для `INCOME` показывать доходные root.
  - В label использовать путь для child (`Parent / Child`) для читаемости.
  - Добавить backend-защиту (hard guard) в:
    - `transaction_service.create_transaction/update_transaction`
    - `planned_transaction_service.create_planned_transaction/update_planned_transaction`
    - `pending_payment_service.create_pending_payment/update_pending_payment`
  - Ошибки делать явными и одинаковыми по смыслу (например: "Выберите листовую категорию расходов").

  **Must NOT do**:
  - Не полагаться только на то, что dropdown "не показал" невалидную категорию.
  - Не ломать существующие сценарии выбора доходной категории.
  - Не менять несвязанные валидации форм.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: кросс-срез UI + сервисы + инварианты домена.
  - **Skills**: [`git-master`, `playwright`]
    - `git-master`: контролируемые изменения в нескольких модулях.
    - `playwright`: при наличии web-раннера можно прогнать UI flow дополнительно.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: здесь важнее бизнес-валидация, не визуальная стилизация.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 3, 5, 6)
  - **Blocks**: 7
  - **Blocked By**: 2

  **References**:
  - `src/finance_tracker/components/transaction_modal.py` - текущая загрузка dropdown категорий.
  - `src/finance_tracker/components/planned_transaction_modal.py` - аналогичный flow выбора категории.
  - `src/finance_tracker/components/pending_payment_modal.py` - расходный selector для отложенных платежей.
  - `src/finance_tracker/services/transaction_service.py` - create/update транзакций.
  - `src/finance_tracker/services/planned_transaction_service.py` - create/update плановых транзакций.
  - `src/finance_tracker/services/pending_payment_service.py` - create/update отложенных платежей.
  - `tests/test_transaction_modal.py` - большая база UI/валидационных тестов modal.
  - `tests/test_planned_transaction_modal.py` - тесты modal плановых транзакций.
  - `tests/test_pending_payment_properties.py` - свойства создания/обновления pending payments.
  - `tests/test_integration.py` - end-to-end сценарии ввода транзакций.

  **Acceptance Criteria**:
  - [ ] RED: добавлены тесты leaf-only в модалках и сервисах, падают до реализации.
  - [ ] GREEN: `pytest tests/test_transaction_modal.py -k "leaf" -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_planned_transaction_modal.py -k "leaf" -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_pending_payment_properties.py -k "category" -v` -> PASS.
  - [ ] REFACTOR: общая логика подготовки selectable categories вынесена в переиспользуемый helper.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Expense dropdown показывает только leaf-категории
    Tool: Bash (pytest)
    Preconditions: Есть root и child категории расходов
    Steps:
      1. pytest tests/test_transaction_modal.py -k "expense_dropdown_contains_only_leaf" -v | tee .sisyphus/evidence/task-4-leaf-dropdown.txt
      2. Assert: exit code = 0
      3. Assert: в тесте проверено отсутствие root в options и формат label "Parent / Child"
    Expected Result: Пользователь может выбрать только leaf категорию расходов
    Failure Indicators: root-категории попадают в selectable options
    Evidence: .sisyphus/evidence/task-4-leaf-dropdown.txt

  Scenario: Сервис отклоняет parent category при создании транзакции
    Tool: Bash (pytest)
    Preconditions: Есть root EXPENSE с дочерними категориями
    Steps:
      1. pytest tests/test_transaction_service_hierarchy.py -k "reject_parent_category_for_transaction" -v | tee .sisyphus/evidence/task-4-reject-parent-service.txt
      2. Assert: exit code = 0
      3. Assert: зафиксирован ValueError с сообщением про листовую категорию
    Expected Result: Backend не принимает parent category даже при прямом вызове
    Failure Indicators: create/update проходит с parent category
    Evidence: .sisyphus/evidence/task-4-reject-parent-service.txt

  Scenario: Pending payment create/update отклоняет non-leaf категорию
    Tool: Bash (pytest)
    Preconditions: Подготовлен non-leaf EXPENSE id
    Steps:
      1. pytest tests/test_pending_payment_properties.py -k "reject_non_leaf_category" -v | tee .sisyphus/evidence/task-4-pending-non-leaf.txt
      2. Assert: exit code = 0
      3. Assert: тест подтверждает блокировку и неизменность данных
    Expected Result: pending payment flow соблюдает leaf-only правило
    Failure Indicators: pending payment сохраняется с parent category
    Evidence: .sisyphus/evidence/task-4-pending-non-leaf.txt
  ```

  **Commit**: YES
  - Message: `feat(category-selection): enforce leaf-only across forms and services`
  - Files: `src/finance_tracker/components/*modal*.py`, `src/finance_tracker/services/*transaction*service.py`, `src/finance_tracker/services/pending_payment_service.py`, тесты
  - Pre-commit: `pytest tests/test_transaction_modal.py tests/test_planned_transaction_modal.py -k "leaf" -v`

---

- [x] 5. Обновить фильтры истории и план-факт под иерархию категорий

  **What to do**:
  - `transaction_history_view.py`:
    - обновить dropdown labels (path для child)
    - при выборе parent включать транзакции детей (aggregate default)
  - `plan_fact_view.py`:
    - аналогичная логика parent aggregate
    - исправить обработчик `selected_category_id` (UUID string, без `int(val)`)
  - Сохранить опцию `all` и стабильное поведение при восстановлении фильтров.

  **Must NOT do**:
  - Не ломать фильтрацию по доходам.
  - Не менять несвязанные вычисления аналитики.
  - Не вводить ручные post-processing шаги для пользователя.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: влияет на аналитические экраны и корректность выборки данных.
  - **Skills**: [`git-master`]
    - `git-master`: поможет проверить, где еще используется `selected_category_id`.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: визуальный апгрейд не является основным драйвером задачи.
    - `playwright`: можно обойтись детерминированными unit/integration тестами.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 3, 4, 6)
  - **Blocks**: 7
  - **Blocked By**: 2

  **References**:
  - `src/finance_tracker/views/transaction_history_view.py` - загрузка и применение category filter.
  - `src/finance_tracker/views/plan_fact_view.py` - category filter + текущий `int(val)` баг для UUID.
  - `src/finance_tracker/services/transaction_service.py` - источник данных для history/filtering.
  - `tests/test_transaction_history_view.py` - существующие тесты фильтра истории.
  - `tests/test_plan_fact_view.py` - тесты plan/fact фильтров и dropdown.

  **Acceptance Criteria**:
  - [ ] RED: добавлены тесты на parent-aggregate фильтрацию и UUID-safe выбор категории.
  - [ ] GREEN: `pytest tests/test_transaction_history_view.py -k "category" -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_plan_fact_view.py -k "category" -v` -> PASS.
  - [ ] REFACTOR: общая логика "parent включает детей" вынесена в helper (без дублирования).

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Выбор parent в истории включает дочерние транзакции
    Tool: Bash (pytest)
    Preconditions: В фикстуре есть parent + child и транзакции только на child
    Steps:
      1. pytest tests/test_transaction_history_view.py -k "parent_filter_includes_children" -v | tee .sisyphus/evidence/task-5-history-parent-aggregate.txt
      2. Assert: exit code = 0
      3. Assert: тест подтверждает, что parent-фильтр возвращает child-транзакции
    Expected Result: Агрегирующая фильтрация работает корректно
    Failure Indicators: parent фильтр возвращает пусто при наличии child-транзакций
    Evidence: .sisyphus/evidence/task-5-history-parent-aggregate.txt

  Scenario: Plan-fact фильтр работает с UUID и не падает на int cast
    Tool: Bash (pytest)
    Preconditions: Dropdown key категорий содержит UUID string
    Steps:
      1. pytest tests/test_plan_fact_view.py -k "uuid_category_filter" -v | tee .sisyphus/evidence/task-5-plan-fact-uuid.txt
      2. Assert: exit code = 0
      3. Assert: в логах теста нет ValueError от int conversion
    Expected Result: Выбор категории устойчив к UUID идентификаторам
    Failure Indicators: ValueError/TypeError при смене фильтра
    Evidence: .sisyphus/evidence/task-5-plan-fact-uuid.txt
  ```

  **Commit**: YES
  - Message: `fix(filters): support hierarchy and uuid-safe category selection`
  - Files: `src/finance_tracker/views/transaction_history_view.py`, `src/finance_tracker/views/plan_fact_view.py`, соответствующие тесты
  - Pre-commit: `pytest tests/test_transaction_history_view.py tests/test_plan_fact_view.py -k "category" -v`

---

- [x] 6. Обеспечить корректность snapshot export/import для parent-child категорий

  **What to do**:
  - В export обеспечить стабильный порядок категорий parent-before-child.
  - В import обеспечить вставку категорий в безопасном порядке (топологически или 2-фазно).
  - Добавить валидацию на неразрешимые parent-ссылки в snapshot.
  - Не ломать restore-only ограничения.
  - Обновить/добавить тесты roundtrip и validation для hierarchy-кейсов.

  **Must NOT do**:
  - Не ослаблять restore-only guard.
  - Не допускать silent skip некорректных категорий.
  - Не добавлять ручные post-fix шаги после импорта.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: затрагивается целостность snapshot данных и атомарность импорта.
  - **Skills**: [`git-master`]
    - `git-master`: полезен для безопасных изменений в критичном data path.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: задача полностью backend/data.
    - `playwright`: UI не участвует.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with 3, 4, 5)
  - **Blocks**: 7
  - **Blocked By**: 1

  **References**:
  - `src/finance_tracker/mobile/export_service.py` - `SNAPSHOT_TABLES` и сортировка при сериализации.
  - `src/finance_tracker/mobile/import_service.py` - `IMPORT_ORDER`, `_insert_snapshot_data`, restore-only checks.
  - `tests/test_export_import_unit.py` - unit-контракт экспорта/импорта snapshot.
  - `tests/test_export_import_roundtrip.py` - end-to-end roundtrip.
  - `tests/test_export_import_validation.py` - валидационные негативные кейсы.
  - `tests/test_import_restore_only_guards.py` - неизменность restore-only поведения.

  **Acceptance Criteria**:
  - [ ] RED: добавлены тесты parent-child snapshot, падают до реализации.
  - [ ] GREEN: `pytest tests/test_export_import_unit.py -k "category" -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_export_import_roundtrip.py -k "snapshot" -v` -> PASS.
  - [ ] GREEN: `pytest tests/test_export_import_validation.py -k "parent" -v` -> PASS.
  - [ ] REFACTOR: порядок вставки категорий читаем и покрыт отдельным helper-тестом.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Roundtrip snapshot сохраняет hierarchy категорий
    Tool: Bash (pytest)
    Preconditions: В source-сессии есть parent + child категории
    Steps:
      1. pytest tests/test_export_import_roundtrip.py -k "hierarchy_roundtrip" -v | tee .sisyphus/evidence/task-6-roundtrip-hierarchy.txt
      2. Assert: exit code = 0
      3. Assert: импортированные категории сохраняют parent_id связи
    Expected Result: Экспорт+импорт не разрушает структуру дерева
    Failure Indicators: Потеря parent_id или FK ошибка при импорте
    Evidence: .sisyphus/evidence/task-6-roundtrip-hierarchy.txt

  Scenario: Некорректная parent-ссылка в snapshot отклоняется
    Tool: Bash (pytest)
    Preconditions: Snapshot содержит child с несуществующим parent_id
    Steps:
      1. pytest tests/test_export_import_validation.py -k "invalid_parent_reference" -v | tee .sisyphus/evidence/task-6-invalid-parent.txt
      2. Assert: exit code = 0
      3. Assert: тест фиксирует явную ошибку валидации/импорта
    Expected Result: Импорт fail-fast с rollback
    Failure Indicators: Некорректный snapshot импортируется частично
    Evidence: .sisyphus/evidence/task-6-invalid-parent.txt
  ```

  **Commit**: YES
  - Message: `fix(snapshot): support parent-child category import/export ordering`
  - Files: `src/finance_tracker/mobile/export_service.py`, `src/finance_tracker/mobile/import_service.py`, export/import тесты
  - Pre-commit: `pytest tests/test_export_import_unit.py tests/test_export_import_roundtrip.py -k "category or hierarchy" -v`

---

- [x] 7. Финальная стабилизация, регрессия и проверка guardrails

  **What to do**:
  - Выполнить целевой регрессионный прогон по всем затронутым зонам.
  - Проверить lint (`ruff`) и отсутствие API-регрессий Flet диалогов.
  - Убедиться, что нет нарушений scope guardrails (нет глубины >1, нет табов, нет ручных шагов в acceptance).
  - Сверить логику leaf-only между UI и service.

  **Must NOT do**:
  - Не запускать нерелевантный full-suite без необходимости (сначала targeted regression).
  - Не пропускать негативные сценарии.
  - Не оставлять failing/skipped тесты без явной причины.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: интеграционный контроль качества по нескольким подсистемам.
  - **Skills**: [`git-master`]
    - `git-master`: полезен для финального упорядочивания изменений и проверки чистоты состояния.
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: финализация больше про QA/регрессию, чем про дизайн.
    - `playwright`: optional, если pytest покрывает сценарии.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final gate)
  - **Blocks**: None
  - **Blocked By**: 3, 4, 5, 6

  **References**:
  - `AGENTS.md` - финальный чеклист по слоям, UI API и тестам.
  - `.kiro/steering/ui-testing.md` - правила обязательного UI-тестирования.
  - `pyproject.toml` - test/lint инфраструктура.
  - Все файлы, затронутые в Tasks 1-6.

  **Acceptance Criteria**:
  - [ ] `ruff check src tests` -> PASS.
  - [ ] `pytest tests/test_category_properties.py tests/test_categories_view.py tests/test_categories_view_properties.py -v` -> PASS.
  - [ ] `pytest tests/test_transaction_modal.py tests/test_planned_transaction_modal.py tests/test_pending_payment_properties.py -v` -> PASS.
  - [ ] `pytest tests/test_transaction_history_view.py tests/test_plan_fact_view.py -v` -> PASS.
  - [ ] `pytest tests/test_export_import_unit.py tests/test_export_import_roundtrip.py tests/test_export_import_validation.py -v` -> PASS.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Полный targeted regression по иерархии категорий
    Tool: Bash (pytest + ruff)
    Preconditions: Все изменения Tasks 1-6 завершены
    Steps:
      1. ruff check src tests | tee .sisyphus/evidence/task-7-ruff.txt
      2. pytest tests/test_category_properties.py tests/test_categories_view.py tests/test_categories_view_properties.py -v | tee .sisyphus/evidence/task-7-categories-regression.txt
      3. pytest tests/test_transaction_modal.py tests/test_planned_transaction_modal.py tests/test_pending_payment_properties.py -v | tee .sisyphus/evidence/task-7-selectors-regression.txt
      4. pytest tests/test_transaction_history_view.py tests/test_plan_fact_view.py -v | tee .sisyphus/evidence/task-7-filters-regression.txt
      5. pytest tests/test_export_import_unit.py tests/test_export_import_roundtrip.py tests/test_export_import_validation.py -v | tee .sisyphus/evidence/task-7-snapshot-regression.txt
      6. Assert: все команды exit code = 0
    Expected Result: Весь затронутый функционал стабилен
    Failure Indicators: Любой failing test или lint error
    Evidence:
      - .sisyphus/evidence/task-7-ruff.txt
      - .sisyphus/evidence/task-7-categories-regression.txt
      - .sisyphus/evidence/task-7-selectors-regression.txt
      - .sisyphus/evidence/task-7-filters-regression.txt
      - .sisyphus/evidence/task-7-snapshot-regression.txt

  Scenario: Негативный gate на недопустимую глубину и non-leaf selection
    Tool: Bash (pytest)
    Preconditions: Негативные тесты из Tasks 2/4 добавлены
    Steps:
      1. pytest tests/ -k "reject_grandchild or reject_parent_category_for_transaction or reject_non_leaf_category" -v | tee .sisyphus/evidence/task-7-negative-gates.txt
      2. Assert: exit code = 0
      3. Assert: каждый негативный кейс завершился passed
    Expected Result: Ключевые инварианты защищены от регрессии
    Failure Indicators: Любой негативный кейс неожиданно проходит как валидный сценарий
    Evidence: .sisyphus/evidence/task-7-negative-gates.txt
  ```

  **Commit**: YES
  - Message: `test(categories): finalize hierarchy regression and quality gates`
  - Files: затронутые тесты/фиксы после интеграции
  - Pre-commit: команды из acceptance criteria этого таска

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(categories): add expense hierarchy model primitives` | `models.py`, `database.py`, model tests | `pytest tests/test_category_hierarchy_model.py -v` |
| 2 | `feat(categories): enforce hierarchy invariants in service layer` | `category_service.py`, service/property tests | `pytest tests/test_category_hierarchy_service.py -v` |
| 3 | `feat(categories-ui): split income-expense layout and hierarchy dialog` | `categories_view.py`, UI tests | `pytest tests/test_categories_view.py tests/test_categories_view_properties.py -v` |
| 4-5 | `feat(selection): leaf-only selectors and hierarchy-aware filters` | modal/view/service files + tests | targeted pytest for modals/history/plan-fact |
| 6 | `fix(snapshot): support hierarchy category import/export` | export/import services + tests | export/import pytest suite |
| 7 | `test(categories): finalize hierarchy regression and quality gates` | final test updates | `ruff check src tests` + targeted pytest matrix |

---

## Success Criteria

### Verification Commands

```bash
ruff check src tests
pytest tests/test_category_hierarchy_model.py -v
pytest tests/test_category_hierarchy_service.py -v
pytest tests/test_categories_view.py tests/test_categories_view_properties.py -v
pytest tests/test_transaction_modal.py tests/test_planned_transaction_modal.py tests/test_pending_payment_properties.py -v
pytest tests/test_transaction_history_view.py tests/test_plan_fact_view.py -v
pytest tests/test_export_import_unit.py tests/test_export_import_roundtrip.py tests/test_export_import_validation.py -v
```

### Final Checklist
- [x] Иерархия расходов реализована строго в 1 уровень
- [x] Для доходов иерархия не включена
- [x] Leaf-only enforced в UI и в backend сервисах
- [x] Экран категорий split-layout без вкладок
- [x] Snapshot export/import поддерживает parent-child
- [x] Все целевые тесты и линтер проходят
- [x] Нет deprecated Flet dialog API
