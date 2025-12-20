# Project Structure and Organization

## Directory Layout

```
finance-tracker-flet/
├── src/finance_tracker/        # Main application package
├── tests/                      # Test suite (65+ property-based, 110+ unit tests)
├── assets/                     # Static resources (icons, prompts)
├── concepts/                   # Future improvement concepts and roadmap
├── .kiro/                      # Kiro AI specifications and steering rules
├── .finance_tracker_data/      # User data (created at runtime)
├── build/                      # PyInstaller build artifacts
├── dist/                       # Distribution files (.exe)
├── htmlcov/                    # Coverage reports (82%+ coverage)
├── .hypothesis/                # Hypothesis test data
├── .pytest_cache/              # Pytest cache
├── .ruff_cache/                # Ruff linter cache
├── .git/                       # Git repository
├── .gitignore                  # Git ignore rules
├── .gitmodules                 # Git submodule configuration
├── LICENSE                     # AGPL-3.0 license
├── main.py                     # Development launcher
├── pyproject.toml              # Project configuration
├── finance_tracker.spec        # PyInstaller spec
├── README.md                   # Documentation
└── nul                         # System file (Windows)
```

## Source Code Organization

### Core Application (`src/finance_tracker/`)

**Entry Points:**
- `__main__.py` - Module entry point (`python -m finance_tracker`)
- `app.py` - Main application logic, initializes DB and UI
- `config.py` - Configuration singleton
- `database.py` - DB initialization and session management

### Models (`models/`)

**Purpose:** Data models and enums

- `models.py` - SQLAlchemy models (`*DB` classes) and Pydantic models
- `enums.py` - All enums (TransactionType, RecurrenceType, LoanStatus, etc.)

**Naming Convention:**
- SQLAlchemy models: `*DB` suffix (CategoryDB, TransactionDB, LoanDB)
- Pydantic models: descriptive names (TransactionCreate, TransactionUpdate, Transaction)

**Key Models:**
- `CategoryDB` - Transaction categories
- `TransactionDB` - Actual transactions
- `PlannedTransactionDB` - Planned transaction templates
- `RecurrenceRuleDB` - Recurrence rules for planned transactions
- `PlannedOccurrenceDB` - Generated occurrences from planned transactions
- `LenderDB` - Lenders/creditors
- `LoanDB` - Loans and credits
- `LoanPaymentDB` - Loan payment schedule
- `PendingPaymentDB` - Future pending payments

### Services (`services/`)

**Purpose:** Business logic layer (CRUD operations)

**Pattern:** Functional approach - functions, not classes

**Key Services:**
- `transaction_service.py` - Transaction CRUD and statistics
- `category_service.py` - Category management
- `planned_transaction_service.py` - Planned transactions and recurrence
- `recurrence_service.py` - Recurrence rule processing
- `loan_service.py` - Loan management
- `loan_payment_service.py` - Loan payment schedules
- `lender_service.py` - Lender management
- `pending_payment_service.py` - Pending payment management
- `plan_fact_service.py` - Plan vs fact analysis
- `balance_forecast_service.py` - Balance forecasting
- `loan_statistics_service.py` - Loan statistics

**Service Function Signature:**
```python
def service_function(session: Session, param1: Type1, param2: Type2) -> ReturnType:
    """
    Описание функции на русском.
    
    Args:
        session: Активная сессия БД
        param1: Описание параметра
        param2: Описание параметра
        
    Returns:
        Описание возвращаемого значения
        
    Raises:
        SQLAlchemyError: При ошибках работы с БД
    """
    try:
        logger.debug(f"Описание операции с параметрами: {param1}, {param2}")
        # Business logic
        logger.info(f"Операция успешно выполнена")
        return result
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при выполнении операции: {e}")
        raise
```

### Views (`views/`)

**Purpose:** UI screens (Flet views)

**Pattern:** Class-based, inherit from `ft.UserControl`

**Key Views:**
- `main_window.py` - Main application window with navigation
- `home_view.py` - Dashboard with balance and statistics
- `home_presenter.py` - Home view presenter (MVP pattern)
- `interfaces.py` - View interfaces and contracts
- `categories_view.py` - Category management
- `loans_view.py` - Loan list
- `loan_details_view.py` - Detailed loan view
- `lenders_view.py` - Lender management
- `planned_transactions_view.py` - Planned transactions
- `pending_payments_view.py` - Pending payments
- `plan_fact_view.py` - Plan vs fact analysis
- `settings_view.py` - Application settings

### Components (`components/`)

**Purpose:** Reusable UI components (modals, widgets)

**Pattern:** Class-based, inherit from `ft.UserControl`

**Key Components:**
- `transaction_modal.py` - Transaction create/edit modal
- `planned_transaction_modal.py` - Planned transaction modal
- `loan_modal.py` - Loan create/edit modal
- `lender_modal.py` - Lender modal
- `pending_payment_modal.py` - Pending payment modal
- `early_repayment_modal.py` - Early loan repayment modal
- `execute_occurrence_modal.py` - Execute planned occurrence modal
- `execute_pending_payment_modal.py` - Execute pending payment modal
- `occurrence_details_modal.py` - Planned occurrence details modal
- `calendar_widget.py` - Calendar visualization
- `calendar_legend.py` - Calendar legend
- `pending_payments_widget.py` - Pending payments widget
- `planned_transactions_widget.py` - Planned transactions widget
- `transactions_panel.py` - Transaction list panel

### Utilities (`utils/`)

**Purpose:** Cross-cutting concerns

- `logger.py` - Structured logging setup
- `error_handler.py` - Error handling utilities
- `cache.py` - Caching utilities
- `exceptions.py` - Custom exceptions
- `validation.py` - Validation utilities

### Mobile (`mobile/`)

**Purpose:** Data export/import and synchronization

**Public (always available):**
- `export_service.py` - Export to JSON files
- `import_service.py` - Import from JSON files

**Private (Git submodule):**
- `sync_proprietary/` - Cloud sync and real-time sync (optional)

## Testing Structure (`tests/`)

**Naming Convention:**
- `test_*_view.py` - UI component tests
- `test_*_properties.py` - Property-based tests (Hypothesis)
- `test_*_service.py` - Service layer tests
- `test_*.py` - Other tests

**Key Test Files:**
- `conftest.py` - Shared fixtures (db_session)
- `test_transaction_properties.py` - Transaction invariants
- `test_loan_properties.py` - Loan invariants
- `test_home_view.py` - Home view UI tests
- `test_integration.py` - Integration tests

## Configuration Files

- `pyproject.toml` - Python project configuration (dependencies, build, scripts)
- `finance_tracker.spec` - PyInstaller build specification
- `.gitignore` - Git ignore rules
- `.gitmodules` - Git submodule configuration

## Runtime Data (`.finance_tracker_data/`)

**Created automatically at runtime:**

```
.finance_tracker_data/
├── finance.db              # SQLite database
├── config.json             # User settings
├── logs/
│   └── finance_tracker.log # Application logs
└── exports/
    └── backup_*.json       # Exported data files
```

**Location:**
- Development: project root
- Production (.exe): next to executable

## Code Organization Principles

1. **Separation of Concerns:**
   - Models: data structure
   - Services: business logic
   - Views: UI presentation
   - Components: reusable UI elements

2. **Dependency Direction:**
   - Views → Services → Models
   - Components → Services → Models
   - Never: Models → Services or Services → Views

3. **Database Access:**
   - Only services interact with database
   - Views/Components call services, never query DB directly
   - Session passed as parameter (Dependency Injection)

4. **Naming Conventions:**
   - Files: snake_case (transaction_service.py)
   - Classes: PascalCase (TransactionService, TransactionDB)
   - Functions: snake_case (get_transactions_by_date)
   - Constants: UPPER_SNAKE_CASE (APP_NAME, VERSION)
   - Private: _leading_underscore (_internal_function)

5. **Import Organization:**
   ```python
   # Standard library
   from datetime import date
   from typing import List, Optional
   
   # Third-party
   from sqlalchemy.orm import Session
   from pydantic import BaseModel
   
   # Local application
   from finance_tracker.models import TransactionDB
   from finance_tracker.database import get_db_session
   ```

6. **Documentation:**
   - All modules: docstring at top
   - All public functions: docstring with Args/Returns/Raises
   - Complex logic: inline comments explaining "why", not "what"
   - Russian language for all documentation and comments
