# Design Document

## Overview

Данный дизайн описывает рефакторинг архитектуры `HomeView` с применением паттерна MVP (Model-View-Presenter) для достижения полной тестируемости. Основная идея - разделить бизнес-логику (Presenter) от UI-логики (View), обеспечив слабую связанность через интерфейсы и Dependency Injection.

## Architecture

### Current Architecture Problems

1. **Тесная связанность**: HomeView напрямую управляет сессией БД и содержит бизнес-логику
2. **Низкая тестируемость**: Невозможно тестировать логику без инициализации Flet UI
3. **Смешанные ответственности**: View одновременно отображает данные и координирует бизнес-операции
4. **Сложность тестирования**: Модальные окна и UI взаимодействия сложно изолировать

### Target Architecture (MVP Pattern)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HomeView      │    │  HomePresenter   │    │  Service Layer  │
│   (UI Logic)    │◄──►│ (Business Logic) │───►│   (Data Layer)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐            ┌─────▼─────┐           ┌─────▼─────┐
    │ Flet UI │            │Callbacks  │           │ Database  │
    │Components│            │Interface  │           │ Session   │
    └─────────┘            └───────────┘           └───────────┘
```

## Components and Interfaces

### IHomeViewCallbacks Interface

Интерфейс для взаимодействия Presenter с View:

```python
from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from datetime import date

class IHomeViewCallbacks(ABC):
    """Интерфейс для обратных вызовов от Presenter к View."""
    
    @abstractmethod
    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        """Обновить данные календаря."""
        pass
    
    @abstractmethod
    def update_transactions(self, date_obj: date, transactions: List[Any], occurrences: List[Any]) -> None:
        """Обновить список транзакций для выбранной даты."""
        pass
    
    @abstractmethod
    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None:
        """Обновить список плановых операций."""
        pass
    
    @abstractmethod
    def update_pending_payments(self, payments: List[Any], statistics: Tuple[int, float]) -> None:
        """Обновить список отложенных платежей."""
        pass
    
    @abstractmethod
    def show_message(self, message: str) -> None:
        """Показать информационное сообщение."""
        pass
    
    @abstractmethod
    def show_error(self, error: str) -> None:
        """Показать сообщение об ошибке."""
        pass
```

### HomePresenter Class

Основной класс, содержащий всю бизнес-логику:

```python
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, Any
from decimal import Decimal

class HomePresenter:
    """Presenter для HomeView, содержит всю бизнес-логику."""
    
    def __init__(self, session: Session, callbacks: IHomeViewCallbacks):
        self.session = session
        self.callbacks = callbacks
        self.selected_date = date.today()
    
    # Data Loading Methods
    def load_initial_data(self) -> None:
        """Загрузить все данные при инициализации."""
        try:
            # Координация вызовов к нескольким сервисам
            self.load_calendar_data(date.today())
            self.load_planned_occurrences()
            self.load_pending_payments()
        except Exception as e:
            self._handle_error("Ошибка загрузки начальных данных", e)
    
    def load_calendar_data(self, calendar_date: date) -> None:
        """Загрузить данные для календаря."""
        try:
            # Вызов get_by_date_range и get_occurrences_by_date_range
            transactions = transaction_service.get_by_date_range(self.session, start_date, end_date)
            occurrences = planned_transaction_service.get_occurrences_by_date_range(self.session, start_date, end_date)
            self.callbacks.update_calendar_data(transactions, occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки данных календаря", e)
    
    def on_date_selected(self, selected_date: date) -> None:
        """Обработать выбор даты."""
        try:
            self.selected_date = selected_date
            # Вызов get_transactions_by_date и get_occurrences_by_date
            transactions = transaction_service.get_transactions_by_date(self.session, selected_date)
            occurrences = planned_transaction_service.get_occurrences_by_date(self.session, selected_date)
            self.callbacks.update_transactions(selected_date, transactions, occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки данных для выбранной даты", e)
    
    def load_planned_occurrences(self) -> None:
        """Загрузить плановые операции."""
        try:
            # Вызов get_pending_occurrences и преобразование данных
            occurrences = planned_transaction_service.get_pending_occurrences(self.session)
            formatted_occurrences = self._format_occurrences_for_ui(occurrences)
            self.callbacks.update_planned_occurrences(formatted_occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки плановых операций", e)
    
    def load_pending_payments(self) -> None:
        """Загрузить отложенные платежи."""
        try:
            # Вызов get_all_pending_payments и get_pending_payments_statistics
            payments = pending_payment_service.get_all_pending_payments(self.session)
            statistics = pending_payment_service.get_pending_payments_statistics(self.session)
            self.callbacks.update_pending_payments(payments, statistics)
        except Exception as e:
            self._handle_error("Ошибка загрузки отложенных платежей", e)
    
    # Transaction Operations
    def create_transaction(self, transaction_data: Any) -> None:
        """Создать новую транзакцию."""
        try:
            transaction = transaction_service.create_transaction(self.session, transaction_data)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Транзакция успешно создана")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка создания транзакции", e)
    
    # Planned Occurrence Operations
    def execute_occurrence(self, occurrence: Any, execution_date: date, amount: float) -> None:
        """Исполнить плановое вхождение."""
        try:
            planned_transaction_service.execute_occurrence(self.session, occurrence.id, execution_date, amount)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Плановая операция успешно исполнена")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения плановой операции", e)
    
    def skip_occurrence(self, occurrence: Any, reason: Optional[str] = None) -> None:
        """Пропустить плановое вхождение."""
        try:
            planned_transaction_service.skip_occurrence(self.session, occurrence.id, reason)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Плановая операция пропущена")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка пропуска плановой операции", e)
    
    # Pending Payment Operations
    def execute_pending_payment(self, payment_id: int, executed_amount: float, executed_date: date) -> None:
        """Исполнить отложенный платёж."""
        try:
            pending_payment_service.execute_pending_payment(self.session, payment_id, executed_amount, executed_date)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж успешно исполнен")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения отложенного платежа", e)
    
    def cancel_pending_payment(self, payment_id: int, reason: Optional[str] = None) -> None:
        """Отменить отложенный платёж."""
        try:
            pending_payment_service.cancel_pending_payment(self.session, payment_id, reason)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж отменён")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка отмены отложенного платежа", e)
    
    def delete_pending_payment(self, payment_id: int) -> None:
        """Удалить отложенный платёж."""
        try:
            pending_payment_service.delete_pending_payment(self.session, payment_id)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж удалён")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка удаления отложенного платежа", e)
    
    # Loan Payment Operations
    def execute_loan_payment(self, payment: Any, amount: Decimal, execution_date: date) -> None:
        """Исполнить платёж по кредиту."""
        try:
            loan_payment_service.execute_loan_payment_service(self.session, payment.id, amount, execution_date)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Платёж по кредиту успешно исполнен")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения платежа по кредиту", e)
    
    # Modal Operations
    def prepare_modal_data(self, modal_type: str, entity_id: Optional[int] = None) -> Any:
        """Подготовить данные для модального окна."""
        try:
            if modal_type == "transaction":
                return self._prepare_transaction_modal_data(entity_id)
            elif modal_type == "occurrence":
                return self._prepare_occurrence_modal_data(entity_id)
            # ... другие типы модальных окон
        except Exception as e:
            self._handle_error("Ошибка подготовки данных для модального окна", e)
            return None
    
    # Private Methods
    def _refresh_data(self) -> None:
        """Обновить все данные после изменений."""
        self.load_calendar_data(self.selected_date)
        self.load_planned_occurrences()
        self.load_pending_payments()
    
    def _handle_error(self, message: str, exception: Exception) -> None:
        """Обработать ошибку с логированием и уведомлением View."""
        logger.error(f"{message}: {exception}", extra={
            "selected_date": self.selected_date,
            "session_active": self.session.is_active
        })
        self.callbacks.show_error(f"{message}: {str(exception)}")
    
    def _format_occurrences_for_ui(self, occurrences: List[Any]) -> List[Tuple[Any, str, str]]:
        """Преобразовать данные плановых операций для UI."""
        # Логика преобразования данных
        return formatted_occurrences
    
    def _prepare_transaction_modal_data(self, transaction_id: Optional[int]) -> Any:
        """Подготовить данные для модального окна транзакции."""
        # Логика подготовки данных
        pass
    
    def _prepare_occurrence_modal_data(self, occurrence_id: Optional[int]) -> Any:
        """Подготовить данные для модального окна планового вхождения."""
        # Логика подготовки данных
        pass
```

### Refactored HomeView Class

Упрощённый View, содержащий только UI-логику:

```python
import flet as ft
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Any, Tuple

class HomeView(ft.Column, IHomeViewCallbacks):
    """Главный экран приложения - только UI логика."""
    
    def __init__(self, page: ft.Page, session: Session):
        super().__init__(expand=True, alignment=ft.MainAxisAlignment.START)
        self.page = page
        # Session передается через Dependency Injection, не создается внутри View
        
        # Создаем Presenter с инжекцией зависимостей
        self.presenter = HomePresenter(session, self)
        
        # Инициализируем UI компоненты (существующие компоненты остаются без изменений)
        self._init_ui_components()
        self._setup_layout()
        
        # Загружаем начальные данные
        self.presenter.load_initial_data()
    
    def __del__(self):
        """Деструктор - НЕ закрывает Session (ответственность создателя)."""
        # Session остается открытой - это ответственность создателя View
        pass
    
    def _init_ui_components(self) -> None:
        """Инициализация UI компонентов."""
        # Создание всех существующих UI компонентов с callback'ами в presenter
        self.calendar_widget = CalendarWidget(
            on_date_selected=self._on_date_selected  # Делегирует в presenter
        )
        
        self.transactions_panel = TransactionsPanel(
            on_create_transaction=self._on_create_transaction  # Делегирует в presenter
        )
        
        self.planned_transactions_widget = PlannedTransactionsWidget(
            on_execute_occurrence=self._on_execute_occurrence,  # Делегирует в presenter
            on_skip_occurrence=self._on_skip_occurrence  # Делегирует в presenter
        )
        
        self.pending_payments_widget = PendingPaymentsWidget(
            on_execute_payment=self._on_execute_payment,  # Делегирует в presenter
            on_cancel_payment=self._on_cancel_payment,  # Делегирует в presenter
            on_delete_payment=self._on_delete_payment  # Делегирует в presenter
        )
    
    def _setup_layout(self) -> None:
        """Настройка макета - использует те же UI компоненты."""
        self.controls = [
            self.calendar_widget,
            self.transactions_panel,
            self.planned_transactions_widget,
            self.pending_payments_widget
        ]
    
    # IHomeViewCallbacks Implementation
    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        """Реализация callback для обновления календаря."""
        self.calendar_widget.update_data(transactions, occurrences)
        self.update()
    
    def update_transactions(self, date_obj: date, transactions: List[Any], occurrences: List[Any]) -> None:
        """Реализация callback для обновления транзакций."""
        self.transactions_panel.update_transactions(date_obj, transactions, occurrences)
        self.update()
    
    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None:
        """Реализация callback для обновления плановых операций."""
        self.planned_transactions_widget.update_occurrences(occurrences)
        self.update()
    
    def update_pending_payments(self, payments: List[Any], statistics: Tuple[int, float]) -> None:
        """Реализация callback для обновления отложенных платежей."""
        self.pending_payments_widget.update_payments(payments, statistics)
        self.update()
    
    def show_message(self, message: str) -> None:
        """Реализация callback для показа сообщений."""
        self.page.show_snack_bar(ft.SnackBar(content=ft.Text(message)))
    
    def show_error(self, error: str) -> None:
        """Реализация callback для показа ошибок."""
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(error),
                bgcolor=ft.Colors.ERROR
            )
        )
    
    # UI Event Handlers (все делегируют в presenter)
    def _on_date_selected(self, date_obj: date) -> None:
        """Обработчик выбора даты - делегирует в presenter."""
        self.presenter.on_date_selected(date_obj)
    
    def _on_create_transaction(self, transaction_data: Any) -> None:
        """Обработчик создания транзакции - делегирует в presenter."""
        self.presenter.create_transaction(transaction_data)
    
    def _on_execute_occurrence(self, occurrence: Any, execution_date: date, amount: float) -> None:
        """Обработчик исполнения планового вхождения - делегирует в presenter."""
        self.presenter.execute_occurrence(occurrence, execution_date, amount)
    
    def _on_skip_occurrence(self, occurrence: Any, reason: str = None) -> None:
        """Обработчик пропуска планового вхождения - делегирует в presenter."""
        self.presenter.skip_occurrence(occurrence, reason)
    
    def _on_execute_payment(self, payment_id: int, amount: float, date_obj: date) -> None:
        """Обработчик исполнения отложенного платежа - делегирует в presenter."""
        self.presenter.execute_pending_payment(payment_id, amount, date_obj)
    
    def _on_cancel_payment(self, payment_id: int, reason: str = None) -> None:
        """Обработчик отмены отложенного платежа - делегирует в presenter."""
        self.presenter.cancel_pending_payment(payment_id, reason)
    
    def _on_delete_payment(self, payment_id: int) -> None:
        """Обработчик удаления отложенного платежа - делегирует в presenter."""
        self.presenter.delete_pending_payment(payment_id)
    
    def _on_execute_loan_payment(self, payment: Any, amount: float, date_obj: date) -> None:
        """Обработчик исполнения платежа по кредиту - делегирует в presenter."""
        self.presenter.execute_loan_payment(payment, amount, date_obj)
    
    def _on_open_modal(self, modal_type: str, entity_id: int = None) -> None:
        """Обработчик открытия модального окна - подготавливает данные через presenter."""
        modal_data = self.presenter.prepare_modal_data(modal_type, entity_id)
        if modal_data:
            # Модальные окна остаются в View, но данные подготавливаются в Presenter
            self._show_modal(modal_type, modal_data)
    
    def _show_modal(self, modal_type: str, modal_data: Any) -> None:
        """Показать модальное окно с подготовленными данными."""
        # Логика показа модального окна остается в View
        pass
```

## Data Models

Используются существующие модели из `finance_tracker.models`:

- **TransactionDB**: Модель транзакций
- **PlannedOccurrence**: Модель плановых вхождений  
- **PendingPaymentDB**: Модель отложенных платежей
- **LoanPaymentDB**: Модель платежей по кредитам
- **TransactionCreate**: Pydantic модель для создания транзакций

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

После анализа всех требований выявлены следующие группы свойств, которые можно объединить:

**Группа 1: Callback Properties** - Свойства callback'ов можно объединить в одно свойство о том, что Presenter всегда вызывает соответствующие callbacks при обновлении данных.

**Группа 2: Service Layer Invocation** - Свойства вызовов Service Layer можно объединить в свойства о корректности параметров и результатов.

**Группа 3: Error Handling** - Свойства обработки ошибок можно объединить в общие свойства обработки исключений и логирования.

**Группа 4: Data Loading Coordination** - Свойства координации загрузки данных можно объединить в свойства о корректности агрегации результатов от нескольких сервисов.

**Property 1: Business logic isolation**
*For any* HomeView instance, all business logic should be contained in the Presenter class and not in the View
**Validates: Requirements 1.1**

**Property 2: Service layer dependency consistency**
*For any* Presenter operation, it should only interact with Service Layer and callback interface, never directly with UI components
**Validates: Requirements 1.2**

**Property 3: View delegation consistency**
*For any* user action handled by View, the View should delegate the action to the corresponding Presenter method with correct parameters
**Validates: Requirements 1.4**

**Property 4: Presenter callback consistency**
*For any* Presenter operation completion, it should notify View through callback interface rather than directly modifying UI
**Validates: Requirements 1.5**

**Property 5: Session lifecycle management**
*For any* HomeView instance, when the View is destroyed, the Session should remain open and not be closed by the View
**Validates: Requirements 2.2**

**Property 6: Service layer parameter consistency**
*For any* Presenter operation that calls Service Layer, the operation should use the injected Session and pass correct parameters
**Validates: Requirements 2.3**

**Property 7: Data loading coordination**
*For any* data loading operation, the Presenter should coordinate calls to multiple services and aggregate results before calling callbacks
**Validates: Requirements 3.1**

**Property 8: Date selection callback consistency**
*For any* date selection event, the Presenter should load data for that date and call the appropriate View callback with the results
**Validates: Requirements 3.3**

**Property 9: Data update callback consistency**
*For any* data update operation in Presenter, the appropriate View callback should be called with the updated data
**Validates: Requirements 3.4**

**Property 10: Modal data preparation consistency**
*For any* modal window opening, the Presenter should prepare the required data for the modal
**Validates: Requirements 4.1**

**Property 11: Modal operation consistency**
*For any* modal operation (execute, skip, cancel), the Presenter should process the data through Service Layer and update View via callbacks
**Validates: Requirements 4.2, 4.3**

**Property 12: Calendar data loading consistency**
*For any* calendar data loading request, the Presenter should call get_by_date_range and get_occurrences_by_date_range with date range parameters
**Validates: Requirements 5.1**

**Property 13: Transaction data loading consistency**
*For any* selected date, the Presenter should call get_transactions_by_date and get_occurrences_by_date with that date
**Validates: Requirements 5.2**

**Property 14: Planned transaction data consistency**
*For any* planned transaction loading, the Presenter should call get_pending_occurrences and transform data to UI format
**Validates: Requirements 5.3**

**Property 15: Pending payment data consistency**
*For any* pending payment loading, the Presenter should call get_all_pending_payments and get_pending_payments_statistics
**Validates: Requirements 5.4**

**Property 16: Operation result callback consistency**
*For any* completed data loading operation, the Presenter should call the appropriate callback to pass results to View
**Validates: Requirements 5.5**

**Property 17: User action service invocation consistency**
*For any* user action (execute occurrence, skip occurrence, execute payment, etc.), the Presenter should call the corresponding Service Layer method with correct parameters
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**

**Property 18: Success operation callback consistency**
*For any* successfully completed operation, the Presenter should update data and call success callback
**Validates: Requirements 6.7**

**Property 19: Callback interface consistency**
*For any* Presenter data update, the appropriate IHomeViewCallbacks method should be called with correct data
**Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

**Property 20: UI component compatibility**
*For any* refactored HomeView, it should continue using the same UI components with the same interfaces
**Validates: Requirements 9.2**

**Property 21: Presenter UI isolation**
*For any* Presenter interaction with UI component data, it should be done through View methods rather than directly
**Validates: Requirements 9.3**

**Property 22: Error handling consistency**
*For any* Service Layer exception, the Presenter should catch it, log with context, and call error callback without performing commit
**Validates: Requirements 2.5, 6.8, 8.1, 8.2, 8.5**

**Property 23: Validation error handling consistency**
*For any* validation error, the Presenter should call error callback with validation message
**Validates: Requirements 8.3**

**Property 24: Transaction rollback consistency**
*For any* failed operation that modifies database state, the Presenter should ensure session rollback is performed
**Validates: Requirements 8.2**

**Property 25: Context logging consistency**
*For any* error that occurs, the Presenter should log full context including parameters, system state, and user session information
**Validates: Requirements 8.5**

## Error Handling

### Exception Handling Strategy

1. **Service Layer Exceptions**: Presenter перехватывает все исключения от Service Layer
2. **Logging**: Все ошибки логируются с полным контекстом (параметры, состояние)
3. **User Feedback**: Ошибки передаются в View через error callback
4. **Transaction Safety**: При ошибках commit не выполняется
5. **Graceful Degradation**: UI остается функциональным даже при ошибках

### Error Categories

- **Database Errors**: SQLAlchemy исключения
- **Validation Errors**: Pydantic validation errors
- **Business Logic Errors**: Custom exceptions от Service Layer
- **UI Errors**: Flet-специфичные ошибки (обрабатываются в View)

## Testing Strategy

### Dual Testing Approach

**Unit Testing**:
- Тестирование каждого метода Presenter изолированно
- Mock объекты для Session и IHomeViewCallbacks
- Проверка корректности вызовов Service Layer
- Проверка обработки ошибок

**Property-Based Testing**:
- Использование Hypothesis для генерации тестовых данных
- Проверка инвариантов поведения Presenter
- Тестирование граничных случаев
- Минимум 100 итераций для каждого property теста

### Testing Framework

- **Unit Tests**: pytest
- **Property-Based Tests**: Hypothesis (минимум 100 итераций для каждого property теста)
- **Mocking**: unittest.mock для Session и IHomeViewCallbacks
- **Coverage**: pytest-cov (цель: 100% покрытие Presenter)
- **Test Database**: In-memory SQLite для изоляции тестов

### Property-Based Testing Requirements

- Каждый property-based тест должен запускаться минимум 100 итераций
- Каждый property-based тест должен быть помечен комментарием, явно ссылающимся на correctness property из дизайн-документа
- Формат комментария: `**Feature: home-view-testability-refactoring, Property {number}: {property_text}**`
- Каждое correctness property должно быть реализовано ОДНИМ property-based тестом

### Test Structure

```python
# Unit Tests
class TestHomePresenter:
    def test_load_initial_data_calls_all_services(self):
        """Тест загрузки начальных данных."""
        pass
    
    def test_on_date_selected_updates_transactions(self):
        """Тест выбора даты."""
        pass

# Property-Based Tests  
class TestHomePresenterProperties:
    @given(st.dates())
    def test_date_selection_consistency(self, date_obj):
        """**Feature: home-view-testability-refactoring, Property 5: Date selection callback consistency**"""
        pass
    
    @given(st.text(), st.floats(min_value=0))
    def test_error_handling_consistency(self, error_msg, amount):
        """**Feature: home-view-testability-refactoring, Property 16: Error handling consistency**"""
        pass
```

### Mock Strategy

- **Session Mock**: Имитация SQLAlchemy Session с контролем commit/rollback
- **Service Layer Mocks**: Имитация всех service функций с возможностью генерации исключений
- **Callbacks Mock**: Имитация IHomeViewCallbacks для проверки вызовов
- **Exception Simulation**: Имитация SQLAlchemyError, ValidationError и других исключений
- **Data Generation**: Использование Hypothesis для генерации тестовых данных

### Coverage Requirements

- **Presenter**: 100% покрытие всех публичных методов
- **Error Paths**: Покрытие всех exception handlers и rollback сценариев
- **Callback Invocations**: Проверка всех callback вызовов с корректными параметрами
- **Service Integration**: Проверка всех вызовов к Service Layer с правильными параметрами
- **Edge Cases**: Покрытие граничных случаев через property-based тесты
- **UI Compatibility**: Проверка совместимости с существующими UI компонентами