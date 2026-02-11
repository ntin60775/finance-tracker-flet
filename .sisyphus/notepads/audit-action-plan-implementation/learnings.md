# Learnings (append-only)

Append notes here as we discover conventions, patterns, and gotchas while implementing the plan.

## Codebase Analysis for Release A (Tasks 1-4)
**Date**: 2026-02-11
**Scope**: Docs/UX honesty, Settings backup UI, export/import services, CI gates

---

### 1. ExportService / ImportService Public API

**Files:**
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/export_service.py` — class `ExportService`
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/import_service.py` — class `ImportService`
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/__init__.py` — exports both classes

**Current Public API:**
```python
class ExportService:
    @staticmethod
    def export_to_file(filepath: str | None = None) -> str:
        raise NotImplementedError("...")

class ImportService:
    @staticmethod
    def import_from_file(filepath: str) -> dict[str, int]:
        raise NotImplementedError("...")
```

**Key constants:**
- `EXPORT_IMPORT_ISSUE_URL = "https://github.com/ntin60775/finance-tracker-flet/issues/4"`
- Tests use marker `ISSUE_MARKER = "issues/4"` to match NotImplementedError

**Where to implement:**
- Replace `raise NotImplementedError(...)` in both methods with actual logic
- Return types already defined: `export_to_file` returns `str` (filepath), `import_from_file` returns `dict[str, int]` (report counters)

---

### 2. SettingsView Structure

**File:** `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/views/settings_view.py`

**Key UI components (already present):**
- `theme_dropdown` — ft.Dropdown for light/dark theme
- `db_path_field` — ft.TextField (read-only) showing current DB path
- `date_format_dropdown` — ft.Dropdown for date formats
- `save_button` — ft.Button to save settings

**Important comments in code (line 61-63):**
```python
# FilePicker для выбора БД (пока не реализован полностью, так как это сложнее)
# self.file_picker = ft.FilePicker(on_result=self._on_db_file_picked)
# self._page.overlay.append(self.file_picker)
```

**For Backup UI (Release A task):**
- Add backup section after line 78 (after database_section)
- Add backup/restore buttons that call ExportService/ImportService
- Add FilePicker for selecting import file (similar to commented-out pattern)

---

### 3. UI Testing Patterns for page.open/page.close

**Primary fixtures/helpers:**
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/conftest.py` — `mock_page` fixture (lines 36-69)
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/test_view_base.py` — `ViewTestBase` class (lines 16-456)
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/ui_test_helpers.py` — helper functions

**Standard page mock setup:**
```python
from unittest.mock import MagicMock
import flet as ft

page = MagicMock(spec=ft.Page)
page.overlay = []
page.update = MagicMock()
page.open = MagicMock()   # <-- Modern Flet API
page.close = MagicMock()  # <-- Modern Flet API
```

**Key assertion patterns:**
```python
# Check modal opened
page.open.assert_called()
page.open.assert_called_once_with(modal.dialog)

# Check SnackBar shown
snack_bar = page.open.call_args[0][0]
assert isinstance(snack_bar, ft.SnackBar)

# Check modal closed
page.close.assert_called()
page.close.assert_called_once_with(modal.dialog)
```

**Best test to mirror for SettingsView:**
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/test_settings_view.py` — already tests SettingsView
- Uses `ViewTestBase` (line 19)
- Pattern: mock settings, create view, trigger handlers, assert page.open called

---

### 4. README/Docs Mentions of Export/Import

**File:** `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/README.md`

**Lines to update (Release A Task 1 - docs honesty):**
- Line 15: "- Экспорт и импорт данных (в разработке, см. issue #4)"
- Lines 425-437: Mobile API section showing NotImplementedError stubs
- Line 584: License section mentioning issue #4

**Lines about data directory (for backup fallback docs):**
- Line 85: User data location `.finance_tracker_data/`
- Line 93: `exports/` directory reserved for future export

**File:** `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/ROADMAP.md`
- Lines 24-28: Export/Import task description
- Lines 48, 52: Release criteria mentioning export/import

---

### 5. CI Gates

**File:** `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/.github/workflows/ci.yml`

**Current jobs:**
1. Lint: `ruff check src tests`
2. Test: `pytest tests/ -q`

**Missing for Release A (Task 4):**
- Coverage gate (suggested: start at 65%, then increment)
- `pip-audit` job for security scanning
- Add `--cov-fail-under=65` to pytest command

---

### 6. Test Shortlist to Mirror

**For SettingsView backup UI:**
| Test File | What to Mirror |
|-----------|----------------|
| `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/test_settings_view.py` | Structure, settings patching, page.open assertions |
| `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/test_mobile_functionality.py` | NotImplementedError patterns, API availability tests |

**For page.open/page.close mocking:**
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/conftest.py` — `mock_page` fixture
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/tests/test_transaction_modal.py` — extensive modal testing patterns

---

### 7. Existing TODOs/NotImplemented Patterns

**NotImplementedError locations:**
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/export_service.py` (lines 25, 33)
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/import_service.py` (lines 25, 33)
- `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/mobile/sync_proprietary/__init__.py` (lines 21, 36)

**Note:** The proprietary submodule raises NotImplementedError separately—do not touch.

---

### 8. FilePicker Pattern (for Settings backup UI)

**Location:** `/home/prog7/BarykinME/ПетПроекты/finance-tracker-flet/src/finance_tracker/views/settings_view.py` (lines 61-63)

**Pattern (commented out but correct):**
```python
self.file_picker = ft.FilePicker(on_result=self._on_db_file_picked)
self._page.overlay.append(self.file_picker)
# Trigger: self.file_picker.pick_files(allowed_extensions=["db"])
```

For export/import, use:
- Export: `pick_files(dialog_type=ft.FilePickerDialogType.SAVE_FILE, allowed_extensions=["json"])`
- Import: `pick_files(allowed_extensions=["json"])`

---

### 9. UI String Patterns to Update

**For Release A Task 1 (UX honesty):**
- All user-facing strings claiming export/import is available need explicit "(в разработке)" or similar
- Current README already has this pattern (line 15)
- Update any modal/button labels to match current capability

---

### Summary: Where to Change for Release A

| Task | File(s) | Notes |
|------|---------|-------|
| 1. Docs honesty | README.md, ROADMAP.md | Mark export/import as WIP, add fallback backup instructions |
| 2. Settings backup UI | settings_view.py | Add backup/restore buttons, FilePicker integration |
| 3. Export/Import services | export_service.py, import_service.py | Replace NotImplementedError with implementation |
| 4. CI gates | ci.yml | Add coverage threshold, pip-audit job |


---

## Authoritative References for Snapshot Export/Import and Settings Backup UI

### Flet FilePicker Usage Patterns

**1. Official Flet FilePicker Examples**
- **URL**: https://github.com/flet-dev/flet
- **Example Files**:
  - `/sdk/python/examples/services/file_picker/pick_and_upload.py` — upload with progress
  - `/sdk/python/examples/services/file_picker/pick_save_and_get_directory_path.py` — save/load patterns
- **Commit SHA**: `3b8644f07ba5f5f94ba4dc2df76ae28e9678efd5`

**Key Patterns from Examples:**
```python
# For picking multiple files
files = await ft.FilePicker().pick_files(allow_multiple=True)

# For saving files (desktop only)
save_file_path.value = await ft.FilePicker().save_file()

# For getting directory path (desktop only)
directory_path.value = await ft.FilePicker().get_directory_path()
```

**2. Flet Dialog/Snackbar Overlay API (page.open/page.close)**
- **Example**: `/sdk/python/examples/apps/trolli/src/board.py` (lines 109-130)
- **Permalink**: https://github.com/flet-dev/flet/blob/3b8644f07ba5f5f94ba4dc2df76ae28e9678efd5/sdk/python/examples/apps/trolli/src/board.py#L109-L130

**Key Pattern:**
```python
# Create dialog
dialog = ft.AlertDialog(
    title=ft.Text("Name your new list"),
    content=ft.Column([...]),
)

# Open dialog (modern overlay API - NOT deprecated page.dialog = ...)
self.page.open(dialog)

# Close dialog
self.page.close(dialog)
```

**Note**: The comment pattern in `settings_view.py` (lines 61-63) uses deprecated `page.overlay.append()` pattern - should use `page.open(dialog)` instead.

### JSON Serialization for Decimal + Date in Python

**Recommended Patterns for Snapshot Export:**

1. **Use Custom JSON Encoder for non-serializable types:**
```python
import json
from datetime import datetime, date
from decimal import Decimal

class FinanceSnapshotEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Or str(obj) for precision
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Usage
data = {"amount": Decimal("123.45"), "date": date(2024, 1, 15)}
json_str = json.dumps(data, cls=FinanceSnapshotEncoder, indent=2)
```

2. **Pydantic Model for Type-Safe Serialization:**
```python
from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import date

class SnapshotMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    export_date: date
    version: str = "1.0"

class TransactionSnapshot(BaseModel):
    id: str
    amount: Decimal
    date: date
    
    class Config:
        # Pydantic v2 style
        json_encoders = {
            Decimal: float,
            date: lambda v: v.isoformat(),
        }
```

### SQLAlchemy Atomic Transaction Import Patterns

**Repository**: https://github.com/sqlalchemy/sqlalchemy
**Commit SHA**: `cf0cc646d6700b25a0c7314ec1f9fe75ef1692ab`

**Documentation**: 
- `/doc/build/tutorial/dbapi_transactions.rst` — Official transaction docs
- `/doc/build/tutorial/orm_data_manipulation.rst` — ORM bulk operations

**Atomic Import Pattern for Snapshot Restore:**
```python
from sqlalchemy.orm import Session
from contextlib import contextmanager

@contextmanager
def atomic_transaction(session: Session):
    """Provides atomic transaction with automatic rollback on error."""
    try:
        yield session.begin()
        session.commit()
    except Exception:
        session.rollback()
        raise

# Usage in ImportService:
def import_from_file(filepath: str, session: Session) -> dict[str, int]:
    with open(filepath) as f:
        snapshot_data = json.load(f)
    
    with atomic_transaction(session):
        # Clear existing data (atomic)
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        
        # Import new data (all or nothing)
        for tx_data in snapshot_data["transactions"]:
            tx = TransactionDB(**tx_data)
            session.add(tx)
        for cat_data in snapshot_data["categories"]:
            cat = CategoryDB(**cat_data)
            session.add(cat)
    
    return {"transactions_imported": len(snapshot_data["transactions"])}
```

### Pydantic v2 Nested Model Validation

**Repository**: https://github.com/pydantic/pydantic
**Commit SHA**: `1642c892c498f4626fbb68ba74b03c7e9c86756c`

**Suggested Data Validation Approaches for Nested Snapshot Schemas:**

**Approach 1: Explicit Nested Models with Type Annotations**
```python
from pydantic import BaseModel, field_validator
from typing import List
from decimal import Decimal

class SnapshotTransaction(BaseModel):
    id: str
    amount: Decimal
    category_id: str | None = None
    description: str = ""

class SnapshotCategory(BaseModel):
    id: str
    name: str
    type: str  # "income" | "expense"

class FinanceSnapshot(BaseModel):
    version: str = "2.0"
    export_date: date
    transactions: List[SnapshotTransaction]
    categories: List[SnapshotCategory]
    
    @field_validator("transactions", "categories", mode="before")
    @classmethod
    def validate_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Snapshot must contain at least one record")
        return v
```

**Approach 2: Model-First with Schema Validation**
```python
from pydantic import BaseModel, model_validator

class FinanceSnapshot(BaseModel):
    transactions: List[SnapshotTransaction]
    categories: List[SnapshotCategory]
    
    @model_validator(mode="after")
    @classmethod
    def validate_consistency(cls, m):
        # Ensure all category references exist
        category_ids = {cat.id for cat in m.categories}
        tx_missing_cats = [
            tx.id for tx in m.transactions 
            if tx.category_id and tx.category_id not in category_ids
        ]
        if tx_missing_cats:
            raise ValueError(f"Transactions reference missing categories: {tx_missing_cats}")
        return m
```

### Summary of Key References (5-10 Citations)

1. **Flet FilePicker Save/Load**: https://github.com/flet-dev/flet/blob/3b8644f/sdk/python/examples/services/file_picker/pick_save_and_get_directory_path.py
2. **Flet page.open/close Pattern**: https://github.com/flet-dev/flet/blob/3b8644f/sdk/python/examples/apps/trolli/src/board.py#L109-L130
3. **SQLAlchemy Transactions Docs**: https://github.com/sqlalchemy/sqlalchemy/blob/cf0cc64/doc/build/tutorial/dbapi_transactions.rst
4. **Pydantic v2 Validation Patterns**: https://github.com/pydantic/pydantic/blob/1642c89/tests/types/test_union.py
5. **Flet Read/Write Files Guide**: https://docs.flet.dev/cookbook/read-and-write-files

### Additional Notes for Implementation

- **Flet Version**: Ensure Flet ~= 0.80.5 compatibility (project constraint)
- **FilePicker Mode**: Use `pick_files(dialog_type=ft.FilePickerDialogType.SAVE_FILE)` for export
- **Atomic Rollback**: Critical for snapshot import to prevent partial database corruption
- **Pydantic Config**: Use `ConfigDict(populate_by_name=True)` for backwards compatibility with v1 JSON
- **Decimal Precision**: For financial data, serialize as string in JSON to preserve precision, convert to Decimal on import

---

## Release A Reconnaissance Results (Tasks 1-4)
**Date**: 2026-02-11
**Scope**: Complete codebase mapping for P0.2 documentation/UX honesty, Settings backup UI, export/import services, CI gates

---

### TASK 1: P0.2 Documentation/UX Honesty — Exact Locations

**Files to modify:**

1. **README.md** (lines 15, 425-437, 584)
   - Line 15: Already has "в разработке, см. issue #4" pattern - KEEP but verify consistency
   - Lines 425-437: Mobile API section - ENSURE wording matches stub reality
   - Line 584: License section - VERIFY no promises made

2. **ROADMAP.md** (lines 24-28, 48, 52)
   - Lines 24-28: Export/Import task description
   - Line 48, 52: Release criteria mentioning export/import

**Verification command:**
```bash
grep -n "export\|import\|Экспорт\|Импорт" README.md ROADMAP.md
```

---

### TASK 2: P0.2 UX for Backup in Settings — Exact Anchor Points

**Primary file:** `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/src/finance_tracker/views/settings_view.py`

**Extension points (line-level):**

| Line | Anchor | Action |
|------|--------|--------|
| 78 | After `database_section` closing | INSERT backup section here |
| 61-63 | Commented FilePicker pattern | USE as template for FilePicker setup |
| 108-119 | Controls list | APPEND backup controls before save button |

**FilePicker pattern to replicate (lines 61-63):**
```python
# FilePicker для выбора БД (пока не реализован полностью, так как это сложнее)
# self.file_picker = ft.FilePicker(on_result=self._on_db_file_picked)
# self._page.overlay.append(self.file_picker)
```

**Modern Flet API to use (verified in conftest.py):**
- `page.open(dialog)` — NOT `page.dialog = dialog; dialog.open = True`
- `page.close(dialog)` — for closing
- `ft.FilePicker` with `on_result` callback

**SettingsView existing components (accessible for tests):**
- `self.header` — ft.Text (line 30)
- `self.theme_dropdown` — ft.Dropdown (line 33)
- `self.db_path_field` — ft.TextField (line 54)
- `self.date_format_dropdown` — ft.Dropdown (line 81)
- `self.save_button` — ft.Button (line 102)

**New components to add (suggested naming):**
- `self.backup_section` — ft.Column with backup UI
- `self.export_button` — ft.Button("Экспорт (snapshot)")
- `self.import_button` — ft.Button("Импорт (restore-only)")
- `self.file_picker` — ft.FilePicker for import file selection

---

### TASK 3: P0.1 Export/Import Service Implementation — Exact Stubs

**Files to implement:**

1. `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/src/finance_tracker/mobile/export_service.py`
   - Line 18-33: `export_to_file()` method — REPLACE NotImplementedError
   - Return type: `str` (filepath)
   - Default export path: `settings.user_data_dir / "exports"`

2. `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/src/finance_tracker/mobile/import_service.py`
   - Line 18-33: `import_from_file()` method — REPLACE NotImplementedError
   - Return type: `dict[str, int]` (report counters: added/skipped/conflicts)
   - Must validate restore-only guard (empty DB check)

**Public API signatures (MUST preserve):**
```python
class ExportService:
    @staticmethod
    def export_to_file(filepath: str | None = None) -> str: ...

class ImportService:
    @staticmethod
    def import_from_file(filepath: str) -> dict[str, int]: ...
```

**Internal implementation extension (for testability):**
```python
# Add keyword-only session parameter for testing
def import_from_file(filepath: str, *, session: Session | None = None) -> dict[str, int]:
    if session is None:
        with get_db_session() as session:
            return _import_with_session(filepath, session)
    return _import_with_session(filepath, session)
```

**Domain models to serialize (from models.py):**
| Table | Model Class | Line |
|-------|-------------|------|
| categories | CategoryDB | 33 |
| planned_transactions | PlannedTransactionDB | 60 |
| recurrence_rules | RecurrenceRuleDB | 98 |
| planned_occurrences | PlannedOccurrenceDB | 138 |
| transactions | TransactionDB | 262 |
| lenders | LenderDB | 328 |
| loans | LoanDB | 379 |
| loan_payments | LoanPaymentDB | 510 |
| pending_payments | PendingPaymentDB | 569 |
| debt_transfers | DebtTransferDB | 629 |

**Database init for restore-only guard:**
- File: `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/src/finance_tracker/database.py`
- Function: `init_default_categories()` (lines 37-102)
- System categories seeded on empty DB — import should allow this state

---

### TASK 4: P1.3 CI Quality Gates — Current vs Target

**Current CI:** `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/.github/workflows/ci.yml`

| Job | Lines | Current | Target |
|-----|-------|---------|--------|
| test | 9-32 | `pytest tests/ -q --cov=src/finance_tracker --cov-fail-under=65` | Already has 65% gate! |
| security | 34-55 | `pip-audit` with `continue-on-error: true` | Already implemented! |

**Observation:** CI already meets Task 4 requirements! Verify:
1. Coverage gate at 65% — PRESENT (line 32)
2. pip-audit job in report mode — PRESENT (lines 34-55)
3. `continue-on-error: true` — PRESENT (line 36)

**Dependencies check:**
- `pytest-cov>=4.0.0` — in pyproject.toml dev deps (line 22)
- `pip-audit` — installed in CI job (line 52), NOT in pyproject.toml

---

### Test Infrastructure for Tasks 1-4

**Existing tests to mirror:**

| Test File | Purpose | Key Patterns |
|-----------|---------|--------------|
| `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/tests/test_mobile_functionality.py` | Export/Import API availability | `pytest.raises(NotImplementedError, match=ISSUE_MARKER)` |
| `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/tests/test_settings_view.py` | SettingsView UI testing | `ViewTestBase`, `page.open` assertions |
| `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/tests/conftest.py` | Fixtures | `mock_page`, `db_session`, `sample_categories` |
| `/home/prog7/BarykinME/PetProjects/finance-tracker-flet/tests/test_view_base.py` | Base test class | `ViewTestBase.create_mock_page()` with `page.open/close` |

**New test files needed:**

1. `tests/test_settings_backup_ui.py` — Task 2 acceptance test
   - Test export button triggers ExportService
   - Test import button with FilePicker
   - Test restore-only warning dialog

2. `tests/test_export_import_unit.py` — Task 3 unit tests
   - Test serialization round-trip
   - Test Decimal precision preservation
   - Test UUID validation

3. `tests/test_import_restore_only_guards.py` — Task 3 guards
   - Test import rejection on non-empty DB
   - Test atomic rollback on error

**pytest target from plan:**
```bash
pytest tests/test_mobile_functionality.py -q
```
This test file exists and validates:
- ExportService/ImportService are importable
- Both raise NotImplementedError with "issues/4" marker
- CloudSyncService/RealtimeSyncService stubs behave correctly

---

### Key Implementation Decisions (Pre-Confirmed)

1. **Flet Dialog API**: Modern `page.open/page.close` verified in:
   - `tests/conftest.py` lines 63-64
   - `tests/test_view_base.py` lines 75-76
   - `src/finance_tracker/views/settings_view.py` line 149

2. **FilePicker location**: Add to `self._page.overlay` (commented pattern in settings_view.py is correct approach)

3. **Session injection**: Use keyword-only `session=` parameter for testability while preserving public API

4. **Decimal serialization**: Serialize as string in JSON to preserve precision (per plan Metis Review)

5. **Snapshot format version**: Start with "2.0" (matching app version)

---

### File Manifest for Release A

**Source files (modify):**
- `src/finance_tracker/mobile/export_service.py` — implement export
- `src/finance_tracker/mobile/import_service.py` — implement import
- `src/finance_tracker/views/settings_view.py` — add backup UI

**Documentation files (modify):**
- `README.md` — verify honesty of export/import mentions
- `ROADMAP.md` — verify release criteria

**Test files (create/modify):**
- `tests/test_settings_backup_ui.py` — NEW
- `tests/test_export_import_unit.py` — NEW
- `tests/test_import_restore_only_guards.py` — NEW
- `tests/test_mobile_functionality.py` — UPDATE when stubs implemented

**CI files (verify):**
- `.github/workflows/ci.yml` — ALREADY has 65% gate and pip-audit

---

## Task 2 Implementation Notes (Settings backup UI)
**Date**: 2026-02-11

- Flet `FilePicker` in this repo/runtime does not accept `on_result=` in the constructor; set callback via `file_picker.on_result = handler`.
- Keep dialogs/snackbars strictly via `page.open(...)` / `page.close(...)` (tests mock these methods).
- If venv wrapper scripts have a stale shebang, use `.venv/bin/python3 -m pip` / `.venv/bin/python3 -m pytest` instead of `.venv/bin/pip` / `.venv/bin/pytest`.

## Task 3 Snapshot Export/Import Notes
**Date**: 2026-02-11

- Snapshot v1 structure stabilized as `{metadata, categories, planned_transactions, recurrence_rules, planned_occurrences, transactions, lenders, loans, loan_payments, pending_payments, debt_transfers}`.
- Financial precision rule enforced: all `Numeric` fields are serialized as JSON strings and parsed back via `Decimal`.
- Restore-only guard works as intended when DB has only system categories and all other domain tables are empty.
- Import atomicity kept with single transaction semantics (`commit` once, full `rollback` on any validation/DB error).
- FK pre-validation against snapshot ID sets catches broken links before DB writes.

## Task 1 P0.2 Docs/UX Honesty Notes
**Date**: 2026-02-11

- Документацию синхронизировали с фактом: `ExportService`/`ImportService` реализованы, убраны формулировки про `NotImplementedError` и "в разработке" в целевых местах.
- В README и ROADMAP явно зафиксировано текущее ограничение: импорт только в пустую пользовательскую БД, при этом системные baseline-категории допустимы.
- Сохранена fallback-рекомендация для ручного бэкапа: копирование `.finance_tracker_data/finance.db` с явной привязкой к `settings.db_path`.

## Task 5 P0.1 Round-trip/Validation Tests Notes
**Date**: 2026-02-11

- Для round-trip теста важно использовать отдельные in-memory engine для source/target, иначе restore-only guard срабатывает из-за общего состояния.
- Проверка `Decimal` round-trip корректно делается через сравнение `TransactionDB.amount == Decimal("123.45")` после полного export->import.
- FK-целостность в интеграции удобно валидировать не только по `category_id`, но и через relationship (`imported_transaction.category.id`).
- Для negative coverage достаточно опереться на стабильные сообщения `ImportService`: corrupted JSON, schema mismatch, invalid UUID (`categories.id`), missing FK (`FK ссылка`).
- Дополнительно закреплен non-destructive restore-only кейс: при reject состояние БД (count + id + amount) остается без изменений.

## Task 6 P1.3 Stage 2 Coverage Gate Notes
**Date**: 2026-02-11

- CI coverage gate поднят с 65 до 66 как первый консервативный шаг, согласованный с текущим фактом покрытия около 66.6%.
- Для консистентности обновлены явные пороговые упоминания в README (политика + команда ).
- Верификация выполнена полным прогоном: 918 passed, Total coverage 66.64%, порог 66 пройден стабильно.

## Task 6 P1.3 Stage 2 Coverage Gate Notes
**Date**: 2026-02-11

- CI coverage gate поднят с 65 до 66 как первый консервативный шаг, согласованный с текущим фактом покрытия около 66.6%.
- Для консистентности обновлены явные пороговые упоминания в README (политика + команда --cov-fail-under=66).
- Верификация выполнена полным прогоном: 918 passed, Total coverage 66.64%, порог 66 пройден стабильно.

## Task 7 Obligations Schema Migration Notes
**Date**: 2026-02-11

- Для SQLite-миграции без Alembic рабочий паттерн: `Base.metadata.create_all()` + идемпотентные `ALTER TABLE ... ADD COLUMN` только для отсутствующих колонок.
- Проверка наличия колонок через `PRAGMA table_info(<table>)` обеспечивает безопасный повторный запуск `init_db()` без duplicate-column ошибок.
- Для backward compatibility поле `is_obligation` добавлено как `BOOLEAN NOT NULL DEFAULT 0`, а остальные новые поля оставлены nullable.
- Smoke-тест подтвердил два сценария: миграция legacy-схемы с сохранением данных и повторный запуск миграции (idempotent path).

## Task 7.1 Import Nullable Field Backward Compatibility
**Date**: 2026-02-11

- В парсере snapshot missing-ключи теперь допускаются только для nullable колонок (`raw_value=None`), что сохраняет совместимость старых snapshot без `transactions[*].obligation_id`.
- Для non-nullable колонок поведение не менялось: отсутствие ключа по-прежнему дает `ValueError` с `Отсутствует обязательное поле ...`.
- UUID/FK проверки остаются прежними и выполняются после парсинга, поэтому сценарий с пропущенным FK `category_id` снова валидируется на ожидаемом этапе.

## Task 8 Obligations Service Layer Notes
**Date**: 2026-02-11

- Добавлен выделенный сервис `obligations_service` с детерминированным API для `target/paid/remaining` и отдельной функцией линковки транзакции к обязательству.
- Валидации домена маппятся в `ValidationError`/`BusinessLogicError`: невалидный UUID, отсутствие obligation, дублирующая привязка, `amount > remaining`.
- `paid` считается как объединение (по уникальному `transaction.id`) трёх источников: явная привязка `obligation_id`, связь через `planned_occurrence_id`, и `PlannedOccurrence.actual_transaction_id`; это устраняет double-counting.
- Добавлен API `get_obligations_metrics_for_month(...)`, который корректно разделяет несколько obligations в одной категории и месяце (агрегация по `obligation_id`, а не по категории).
- Пересчёт остатка после изменения цели выполняется сразу через `update_obligation_target(...)`, без кэширования и без отложенных пересчётов.

## Task 9 Obligations UI (planned modal/view)
**Date**: 2026-02-11

- В `PlannedTransactionModal` добавлен режим `mode="obligation"`: создаёт/редактирует месячную цель, при редактировании блокирует изменение месяца/категории/типа.
- В `PlannedTransactionsView` добавлен блок "Обязательства" с метриками `цель/оплачено/остаток` + `ProgressBar`, данные берутся из `get_obligations_metrics_for_month(...)`.
- Ручная привязка транзакции к обязательству сделана через действие "LINK" в истории исполненных вхождений (по `actual_transaction_id`).
- Для кейса `amount > remaining` предупреждение показывается через `SnackBar` и содержит обязательную фразу "разбейте транзакцию вручную".

## Task 9 Finalization Verification
**Date**: 2026-02-11T12:46:07+02:00

- Plan tracking finalized: checkbox for Task 9 switched to `[x]` in `.sisyphus/plans/audit-action-plan-implementation.md`.
- Verification command: `./.venv/bin/python3 -m pytest tests/test_obligations_ui.py -q`.
- Result: `3 passed`; acceptance behavior covered in suite includes grouped obligations block and warning flow for `amount > remaining` with manual split guidance.

## Task 10 Monthly Obligations Integration Verification
**Date**: 2026-02-11

- Added `tests/test_obligations_integration.py` with deterministic UUID/date/Decimal integration scenarios for monthly obligations cycle.
- Scenarios covered: target close by partial payments (`10000 = 4000 + 6000`), independent accounting for two obligations in same category/month, and remaining recalculation after target update.
- Verification command: `./.venv/bin/python3 -m pytest tests/test_obligations_integration.py -q`.
- Result: `3 passed in 0.24s`.

## Task 11 P1.5 Observability and Domain Errors
**Date**: 2026-02-11

- В `ImportService` добавлено журналирование `snapshot_import` (start/success/failure) через `extra` со стабильными ключами (`event_type`, `operation`, `entity`, `entity_id`, `status`).
- Широкие обработчики заменены: импорт теперь различает `ValidationError` и `DatabaseError`, при этом наружу сохраняется совместимость через `ValueError` для существующих тестов/вызовов.
- В `debt_transfer_service` убраны `except Exception`, введены доменные исключения (`InvalidTransferError`, `ValidationError`, `DatabaseError`) и структурированный лог-контекст для операций валидации/создания передачи.
- Для события удаления сущности добавлен fallback-доменный журнал в `JsonFormatter` по сообщениям удаления плановой транзакции, чтобы фиксировать `planned_transaction_delete` с ключами журнала без широкого рефакторинга UI/сервиса.

## Task 11 Completion Sync
**Date**: 2026-02-11

- Стандартизовано: доменные исключения на границах import/debt (`ValidationError`/`InvalidTransferError`/`DatabaseError`) с сохранением совместимости внешних `ValueError` в import API.
- Стандартизовано: структурированный `extra`-контекст логов для `snapshot_import` и `debt_transfer` (`event_type`, `operation`, `entity`, `entity_id`, `status`).
- Журнал событий: зафиксированы критичные события import snapshot (start/success/failure), transfer create и delete planned transaction (domain journal fallback в formatter).
- Verification context: `./.venv/bin/python3 -m pytest tests/test_import_restore_only_guards.py -q`; `./.venv/bin/python3 -m pytest tests/test_obligations_service.py -q`; `./.venv/bin/python3 -m pytest tests/test_logger_domain_events.py -q`; `./.venv/bin/python3 -m pytest tests/ -q` (все PASS).

## Task 12 P1.4 Refactor Decomposition
**Date**: 2026-02-11

- В `loan_details_view.py`, `transaction_history_view.py`, `loan_payment_service.py`, `transactions_panel.py` вынесены малые helper-юниты (2-4 на модуль) для форматирования, фильтрации, расчётов и повторяющихся сервисных операций без изменения внешних интерфейсов.
- Добавлено покрытие извлеченной логики: обновлены `tests/test_loan_details_view.py`, `tests/test_transactions_panel.py`; добавлены `tests/test_transaction_history_view.py` и `tests/test_loan_payment_service_refactor.py`.
- Полная верификация Task 12: `./.venv/bin/python3 -m ruff check src tests` и `./.venv/bin/python3 -m pytest tests/ -q` проходят стабильно.

## Task 13 P2.7 Today UX (минимальная версия)
**Date**: 2026-02-11

- В `src/finance_tracker/views/home_view.py` добавлен минимальный блок "Сегодня" (баланс, обязательные/просроченные, риск 7/30) + 3 быстрых действия.
- Для тестируемости UI использованы стабильные `key=` на контролах (например: `today_section`, `today_action_add_tx`).
- Обновление метрик выполняется в `HomeView.did_mount()` и в `HomeView.update_transactions()` только для `date==today`.

## Task 13 Regression Fix (layout order)
**Date**: 2026-02-11

- В тестах layout/интеграции закреплен контракт: `HomeView.controls[0]` должен быть основным `ft.Row` с 4 колонками.
- Today-блок оставлен в HomeView, но перенесен в конец `self.controls` (после основного Row), чтобы не ломать существующие тесты/контракты.

## Task 14 P2.8 Guided-flow (early repayment + debt transfer)
**Date**: 2026-02-11

- Для `EarlyRepaymentModal` добавлен обязательный preview/confirmation шаг перед фактическим вызовом `on_repay(...)`; основной callback и сигнатуры сохранены.
- Preview показывает ключевой финансовый контекст: тип операции, дата, сумма и влияние на баланс (`-amount`) + текст эффекта (закрытие кредита для full, неизменный график для partial).
- Для `DebtTransferModal` отдельная доработка не понадобилась: в текущей реализации уже есть подтверждение с предварительным просмотром данных и сценарии happy-path/invalid в тестах.

## Task 15 P2.9 Plan-fact range and comparison
**Date**: 2026-02-11

- В `PlanFactView` реализован рабочий диалог диапазона дат вместо stub: ручной ввод `YYYY-MM-DD`, валидация и пресеты (`Текущий месяц`, `Прошлый месяц`, `Последние 30 дней`).
- Добавлен режим сравнения с предыдущим периодом той же длительности (`comparison_start_date/comparison_end_date`) и отображение сравниваемого интервала в тексте кнопки периода.
- Добавлено сохранение/восстановление фильтров в состоянии view (`start/end`, category, comparison flags), чтобы последующая загрузка данных использовала восстановленные параметры.
- Добавлен acceptance-набор `tests/test_plan_fact_range.py` на пресеты, comparison toggle и restore saved filters.
