# AGENTS.md - finance-tracker-flet
Practical guide for coding agents in this repository.
Derived from `README.md`, `pyproject.toml`, `BUILD.md`, `tests/README_UI_Testing.md`, and `.kiro/steering/*.md`.

## 1) Project Snapshot
- Language: Python (>= 3.9)
- UI: Flet (~= 0.80.5)
- DB: SQLAlchemy (>= 2.0.0) + SQLite
- Validation: Pydantic (>= 2.0.0)
- Test stack: pytest, pytest-cov, hypothesis, pytest-asyncio
- Package root: `src/finance_tracker`

## 2) Read Before Editing
Use these as source of truth:
- `.kiro/steering/tech.md`
- `.kiro/steering/structure.md`
- `.kiro/steering/ui-testing.md`
- `.kiro/steering/build-deployment.md`
- `README.md`

Conflict priority: explicit user request -> repository code -> this file.

## 3) Setup and Run
### Install
```bash
pip install -e .
pip install -e ".[dev]"
```

### Run app
```bash
python -m finance_tracker
python main.py
finance-tracker
```

## 4) Build, Test, Lint, Typecheck
### Build
```bash
pyinstaller finance_tracker.spec
pyinstaller finance_tracker.spec --clean --noconfirm
pyinstaller finance_tracker_linux.spec --clean --noconfirm
```

### Tests (full)
```bash
pytest tests/
pytest tests/ -v
pytest tests/ --cov=src/finance_tracker --cov-report=html
pytest tests/ --cov=src/finance_tracker --cov-fail-under=80
```

### Tests (single test focus)
```bash
pytest tests/test_home_view.py
pytest tests/test_home_view.py::TestHomeView::test_initialization
pytest tests/test_transaction_modal.py::TestTransactionModal::test_save_button -v
pytest tests/ -k "add_transaction"
pytest tests/ --lf
pytest tests/ --ff
```

### Tests by category
```bash
pytest tests/test_*_service.py
pytest tests/test_*_view.py tests/test_*_modal.py
pytest tests/test_*_properties.py
pytest tests/test_integration*.py
```

### Lint / typecheck status
Ruff linting is configured via `pyproject.toml`.

```bash
ruff check src tests
ruff check src tests --fix
```

No strict typecheck command is configured in repo files.
- No `mypy`/`pyright` config found
- No `pre-commit` config found

### Dependency pin policy
- keep Flet pinned to compatible minor series: `flet~=0.80.5`
- for upgrades, test UI runtime flows before widening constraints

## 5) Architecture and Layering
Primary folders:
- `models/`: SQLAlchemy + Pydantic models
- `services/`: business logic and CRUD
- `views/`: screen-level UI
- `components/`: reusable UI widgets/modals
- `utils/`: logger, errors, validation, cache

Dependency direction:
- views/components -> services -> models
- avoid reverse coupling (models -> services, services -> views)

## 6) Coding Style
### Imports
- order: standard library -> third-party -> `finance_tracker.*`
- prefer absolute imports from `finance_tracker`

### Naming
- files/modules: `snake_case.py`
- functions/variables: `snake_case`
- classes: `PascalCase`
- constants: `UPPER_SNAKE_CASE`
- SQLAlchemy entities: `*DB` suffix (`TransactionDB`)
- Pydantic DTOs: `Create` / `Update` suffixes

### Formatting and comments
- follow existing formatting in touched files
- keep comments/docstrings short and useful
- keep changes focused and minimal

### Typing
- preserve existing annotations and return types
- avoid broad `Any` when concrete types are available
- keep service signatures typed, especially `session: Session`

### UUID domain rule
- IDs are UUID strings (not ints)
- validate UUIDs in service layer and Pydantic validators

## 7) Error Handling and Logging
- use explicit try/except in DB/service boundaries
- include context in log messages
- typical pattern: rollback on DB errors, then re-raise/map error
- use custom exceptions from `utils/exceptions.py` when relevant
- never swallow exceptions silently

## 8) Flet UI Rule (Critical)
Use modern dialog/overlay API only:
- open: `page.open(dialog_or_snackbar)`
- close: `page.close(dialog_or_snackbar)`

Avoid deprecated patterns:
- `page.dialog = ...`
- `dialog.open = True/False`

For UI tests, mock `page.open` and `page.close` explicitly.

## 9) Testing Conventions
- test file pattern: `test_*.py`
- UI tests: `test_*_view.py`, `test_*_modal.py`
- property-based tests: `test_*_properties.py`
- integration tests: `test_integration*.py`
- prefer Arrange-Act-Assert structure
- if UI changes, update/add UI tests in same change
- do not stop long-running Hypothesis tests early

## 10) Cursor/Copilot Rules
Checked paths:
- `.cursor/rules/`
- `.cursorrules`
- `.github/copilot-instructions.md`

Result: no Cursor/Copilot instruction files found in this repository.

## 11) Agent Final Checklist
Before finishing:
1. run targeted tests for changed area
2. if UI changed, include UI interaction tests
3. keep layering and naming conventions intact
4. ensure no deprecated Flet dialog API was introduced
5. keep changes surgical and scope-limited
