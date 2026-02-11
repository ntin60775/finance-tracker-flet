# Issues (append-only)

Track blockers, failing tests, unexpected interactions, and follow-ups.

---

## Reconnaissance Blockers/Issues (Release A Tasks 1-4)
**Date**: 2026-02-11

### Resolved Issues

1. **CI Already Implemented** (Task 4)
   - Finding: `.github/workflows/ci.yml` already has 65% coverage gate and pip-audit job
   - Impact: Task 4 may be already complete — verify with test run
   - Action: Run `pytest tests/ --cov=src/finance_tracker --cov-fail-under=65` to confirm

2. **FilePicker Pattern Confirmed**
   - Finding: settings_view.py lines 61-63 has commented but correct FilePicker pattern
   - Impact: No research needed for Flet FilePicker API
   - Action: Uncomment and adapt for backup UI

### Potential Risks

1. **SettingsView Control Coupling**
   - Risk: Adding backup section may require restructuring controls list (line 108-119)
   - Mitigation: Insert backup section as new Column before save_button row

2. **Decimal JSON Serialization**
   - Risk: Float conversion loses precision for financial data
   - Mitigation: Serialize Decimal as string, parse with Decimal() on import
   - Reference: Plan Metis Review confirms this requirement

3. **Restore-Only Guard Definition**
   - Risk: "Empty DB" vs "only system categories" ambiguity
   - Current behavior: `init_db()` seeds system categories on startup
   - Required behavior: Import should allow "only system categories" state
   - Implementation: Check user data tables (transactions, loans, etc.) for non-zero count

### No Blockers Identified

All required patterns, APIs, and test infrastructure confirmed available.
Ready for implementation delegation.

---

## Task 2 Implementation Issues (Settings backup UI)
**Date**: 2026-02-11

### Resolved Issues

1. **FilePicker callback wiring mismatch**
   - Symptom: `FilePicker.__init__()` raised `TypeError: unexpected keyword argument 'on_result'`
   - Fix: create `ft.FilePicker()` and assign `file_picker.on_result = handler`

---

## Task 3 Snapshot Export/Import Issues
**Date**: 2026-02-11

### Resolved Issues

1. **Restore-only test used shared in-memory engine**
   - Symptom: import test failed with restore-only guard because source and target sessions shared one DB state.
   - Fix: switched target import session to a separate in-memory engine.

2. **Legacy mobile API expectations outdated**
   - Symptom: `tests/test_mobile_functionality.py` expected `NotImplementedError`, but services now require initialized DB and raise `RuntimeError` in that context.
   - Fix: updated only the two export/import assertions to match current Task 3 behavior.

### Open Issues

- None identified for Task 3 scope after targeted test run.

---

## Task 1 P0.2 Docs/UX Honesty Issues
**Date**: 2026-02-11

### Resolved Issues

1. **Устаревшие формулировки в документации про экспорт/импорт**
   - Symptom: в `README.md`, `ROADMAP.md` и `src/finance_tracker/mobile/__init__.py` оставались утверждения про "в разработке"/`NotImplementedError`.
   - Fix: обновлены формулировки на фактическое поведение snapshot export + restore-only import.

### Open Issues

- Blockers не выявлены в рамках P0.2 wording alignment.

---

## Task 5 P0.1 Round-trip/Validation Issues
**Date**: 2026-02-11

### Resolved Issues

1. **Отсутствовали выделенные test-файлы под Task 5 scope**
   - Symptom: round-trip и негативные проверки были в `tests/test_export_import_unit.py`, но не в отдельных файлах из плана.
   - Fix: добавлены `tests/test_export_import_roundtrip.py` и `tests/test_export_import_validation.py` с требуемым покрытием.

### Open Issues

- Blockers не выявлены, три целевых pytest-команды проходят стабильно.

## Task 6 P1.3 Stage 2 Coverage Gate Risks
**Date**: 2026-02-11

- Residual risk: запас над порогом небольшой (66.64% vs 66), поэтому при следующих изменениях возможны просадки; следующий шаг выше 66 требует предварительного наращивания тестов.

## Task 10 Obligations Integration
**Date**: 2026-02-11

- Blockers: none.
- Verification command: `./.venv/bin/python3 -m pytest tests/test_obligations_integration.py -q`.
- Result: `3 passed in 0.24s`.

## Task 8 Obligations Service Layer Risks
**Date**: 2026-02-11

### Resolved Issues

1. **Double-counting при смешанном учёте planned+linked транзакций**
   - Symptom: при одновременном наличии `planned_occurrence_id` и `obligation_id` одна транзакция могла учитываться дважды.
   - Fix: агрегация paid переведена на дедупликацию по `transaction.id` до суммирования.

2. **Отсутствовали сервисные guard-валидации линковки obligation**
   - Symptom: не было явного отказа для `amount > remaining` и для повторной привязки транзакции к другому obligation.
   - Fix: добавлены проверки в `link_transaction_to_obligation(...)` с `BusinessLogicError` и понятными сообщениями.

### Residual Risks

- Пока нет отдельного DB-level уникального/проверочного ограничения для `transactions.obligation_id`; контроль дубликатов реализован на сервисном уровне и требует использования только сервисного API для линковки.

## Task 7 Obligations Schema Migration Risks
**Date**: 2026-02-11

### Resolved Issues

1. **Отсутствие obligations-колонок в существующих SQLite БД**
   - Symptom: legacy таблицы `planned_transactions`/`transactions` не содержали новых полей доменной модели obligations.
   - Fix: добавлена контролируемая миграция в `init_db()` с `ALTER TABLE ... ADD COLUMN` только для отсутствующих колонок.

### Residual Risks

- SQLite не создает отдельные FK-индексы автоматически для новых nullable FK-колонок; при росте объема данных возможна потребность в явной индексации в отдельной задаче производительности.

## Task 7.1 Import Nullable Field Regression
**Date**: 2026-02-11

### Resolved Issues

1. **Регрессия backward compatibility на nullable поле `transactions.obligation_id`**
   - Symptom: импорт падал на `Отсутствует обязательное поле transactions[0].obligation_id` для старых snapshot без этого ключа.
   - Fix: в `import_service` отсутствующие ключи допускаются как `None` только для nullable колонок; non-nullable поля остались строго обязательными.

### Open Issues

- По текущему фикс-скоупу открытых блокеров не выявлено.

---

## Task 9 Obligations UI
**Date**: 2026-02-11

- При обновлениях файлов с SQLAlchemy-моделями статический анализатор иногда репортит ложные type-ошибки вида "Column[str] не является str" для атрибутов ORM; на текущем стеке LSP-диагностика ошибок не показывает и pytest-проверка UI сценариев проходит.

- 2026-02-11: Отменено случайное удаление `KODA.md`, файл восстановлен из HEAD.

## Task 6 P1.3 Stage 2 Coverage Gate Risks
**Date**: 2026-02-11

- Residual risk: запас над порогом небольшой (66.64% vs 66), поэтому при следующих изменениях возможны просадки; следующий шаг выше 66 требует предварительного наращивания тестов.

## Task 11 P1.5 Notes
**Date**: 2026-02-11

- Блокеров не было; полный `pytest tests/ -q` прошел (934 passed).
- LSP по измененным исходникам Task 11 (`import_service.py`, `debt_transfer_service.py`, `logger.py`) без ошибок.

## Task 11 Residual Risk
**Date**: 2026-02-11

- Domain journal для удаления planned transaction частично опирается на pattern matching текста лога; при изменении формулировки сообщений потребуется синхронно обновить matcher в formatter.

---

## Task 13 P2.7 Today UX (минимальная версия)
**Date**: 2026-02-11

- Для HomeView статический анализ (Flet Page.open/close + SQLAlchemy Column typing) шумит; чтобы держать LSP без ошибок, добавлена директива `# pyright: ignore` в `src/finance_tracker/views/home_view.py` (на runtime не влияет, но снижает пользу типизации в файле).

## Task 13 Regression Fix (layout order)
**Date**: 2026-02-11

- Выявлена регрессия: часть тестов ожидает `HomeView.controls[0]` как основной 4-колоночный `ft.Row`; добавление Today-блока в начало нарушило этот контракт.
- Фикс: порядок `self.controls` восстановлен (Row снова первый), Today-блок перенесен после Row.
- Директива `# pyright: ignore` в `src/finance_tracker/views/home_view.py` убрана как не требующаяся для LSP в текущей среде.

## Task 14 P2.8 Guided-flow
**Date**: 2026-02-11

- Открытых блокеров нет.
- Риск, учтенный при реализации: не ломать существующий callback-контракт `on_repay(is_full, amount, repayment_date)` и текущие unit-тесты модалки.

## Task 15 P2.9 Plan-fact range/comparison
**Date**: 2026-02-11

- Блокеров не выявлено.
- Потенциальный риск: сохранение фильтров сейчас реализовано на уровне состояния экземпляра view (без персистентного storage между перезапусками приложения).
