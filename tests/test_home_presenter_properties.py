import pytest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Tuple

from sqlalchemy.orm import Session

from finance_tracker.views.interfaces import IHomeViewCallbacks
from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.models.models import TransactionCreate, PendingPaymentExecute, PendingPaymentCancel
from finance_tracker.models.enums import TransactionType

# Mock for IHomeViewCallbacks (to ensure presenter calls its methods)
# This class is no longer strictly necessary if Mock(spec=IHomeViewCallbacks) is used directly.
# Keeping it for reference or if specific mock behavior is needed later.
class MockHomeViewCallbacks(IHomeViewCallbacks):
    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None: pass
    def update_transactions(self, date_obj: date, transactions: List[Any], occurrences: List[Any]) -> None: pass
    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None: pass
    def update_pending_payments(self, payments: List[Any], statistics: Tuple[int, float]) -> None: pass
    def show_message(self, message: str) -> None: pass
    def show_error(self, error: str) -> None: pass

# Helper strategy for Decimal
@st.composite
def decimals_strategy(draw):
    return draw(st.decimals(min_value=Decimal('0.01'), max_value=Decimal('1000000.00'), places=2))

# Strategy for TransactionCreate
st_transaction_create = st.builds(TransactionCreate,
                                  amount=decimals_strategy(),
                                  category_id=st.uuids().map(str),
                                  description=st.text(min_size=1, max_size=50),
                                  type=st.sampled_from(TransactionType),
                                  transaction_date=st.dates(min_value=date(2000,1,1), max_value=date(2050,12,31)))


# Property 1: Business logic isolation - HomePresenter is initialized correctly and doesn't
# try to manage its own dependencies or directly access UI components.
def test_presenter_initialization_uses_injected_dependencies():
    """
    **Feature: home-view-testability-refactoring, Property 1: Business logic isolation**
    Verifies that HomePresenter is initialized with and correctly stores the injected session and callbacks,
    confirming its reliance on dependency injection for its core functionalities and isolation from UI specifics.
    """
    session = Mock(spec=Session)
    session.is_active = True # Simulate active session
    session.commit = Mock()
    session.rollback = Mock()
    callbacks = Mock(spec=IHomeViewCallbacks)
    presenter = HomePresenter(session, callbacks)
    
    assert presenter.session is session
    assert presenter.callbacks is callbacks
    assert isinstance(presenter.selected_date, date)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st_transaction_create)
def test_create_transaction_calls_service_and_refreshes(transaction_data):
    """
    **Feature: home-view-testability-refactoring, Property 2: Service layer dependency consistency**
    Verifies that create_transaction delegates to transaction_service, commits session,
    refreshes data, and shows a success message.
    """
    # Arrange - Mocks for services are created and patched where they are looked up in HomePresenter
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for refresh_data calls to avoid infinite loops or complex mock setups
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {"total_active": 0, "total_amount": Decimal('0.0')}
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)
        
        # Act
        presenter.create_transaction(transaction_data)
        
        # Assert
        mock_transaction_service.create_transaction.assert_called_once_with(session, transaction_data)
        session.commit.assert_called_once()
        session.rollback.assert_not_called()
        callbacks.show_message.assert_called_once()
        
        # Verify refresh_data calls (indirectly through service calls within _refresh_data)
        assert mock_transaction_service.get_by_date_range.call_count >= 1
        assert mock_planned_transaction_service.get_occurrences_by_date_range.call_count >= 1
        assert mock_planned_transaction_service.get_pending_occurrences.call_count >= 1
        assert mock_pending_payment_service.get_all_pending_payments.call_count >= 1
        assert mock_pending_payment_service.get_pending_payments_statistics.call_count >= 1
        assert mock_transaction_service.get_transactions_by_date.call_count >= 1
        assert mock_planned_transaction_service.get_occurrences_by_date.call_count >= 1


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.integers())
def test_planned_transaction_data_loading_consistency(unused_arg):
    """
    **Feature: home-view-testability-refactoring, Property 14: Planned transaction data consistency**
    Verifies that load_planned_occurrences calls service and updates view.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        callbacks = Mock(spec=IHomeViewCallbacks)
        presenter = HomePresenter(session, callbacks)

        mock_planned_transaction_service.get_pending_occurrences.return_value = ["pending_occ1"]

        # Act
        presenter.load_planned_occurrences()

        # Assert
        mock_planned_transaction_service.get_pending_occurrences.assert_called_once_with(session)
        # Note: We can't strictly assert the exact arguments to update_planned_occurrences
        # because the formatting logic is internal to Presenter for now.
        callbacks.update_planned_occurrences.assert_called_once()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.integers())
def test_data_loading_coordination_consistency(unused_arg):
    """
    **Feature: home-view-testability-refactoring, Property 7: Data loading coordination**
    Verifies that load_initial_data coordinates calls to multiple services
    (load_calendar_data, load_planned_occurrences, load_pending_payments, on_date_selected)
    and aggregates results before calling callbacks.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for all service calls
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Act
        presenter.load_initial_data()

        # Assert - verify coordination: all services called
        # load_calendar_data calls:
        mock_transaction_service.get_by_date_range.assert_called()
        mock_planned_transaction_service.get_occurrences_by_date_range.assert_called()
        callbacks.update_calendar_data.assert_called()

        # load_planned_occurrences calls:
        mock_planned_transaction_service.get_pending_occurrences.assert_called_once_with(session)
        callbacks.update_planned_occurrences.assert_called()

        # load_pending_payments calls:
        mock_pending_payment_service.get_all_pending_payments.assert_called_once_with(session)
        mock_pending_payment_service.get_pending_payments_statistics.assert_called_once_with(session)
        callbacks.update_pending_payments.assert_called()

        # on_date_selected calls:
        mock_transaction_service.get_transactions_by_date.assert_called()
        mock_planned_transaction_service.get_occurrences_by_date.assert_called()
        callbacks.update_transactions.assert_called()

        # Verify no errors shown
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_calendar_data_loading_consistency(calendar_date):
    """
    **Feature: home-view-testability-refactoring, Property 12: Calendar data loading consistency**
    Verifies that load_calendar_data calls get_by_date_range and get_occurrences_by_date_range
    with correct date range parameters (first and last day of month).
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Act
        presenter.load_calendar_data(calendar_date)

        # Assert - verify correct date range calculation
        # Calculate expected date range (first and last day of month)
        first_day_of_month = date(calendar_date.year, calendar_date.month, 1)
        next_month = calendar_date.replace(day=28) + timedelta(days=4)
        last_day_of_month = next_month - timedelta(days=next_month.day)

        # Verify service calls with correct parameters
        mock_transaction_service.get_by_date_range.assert_called_once_with(
            session, first_day_of_month, last_day_of_month
        )
        mock_planned_transaction_service.get_occurrences_by_date_range.assert_called_once_with(
            session, first_day_of_month, last_day_of_month
        )

        # Verify callback called with aggregated results
        callbacks.update_calendar_data.assert_called_once_with([], [])

        # Verify no errors shown
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_transaction_data_loading_consistency(selected_date):
    """
    **Feature: home-view-testability-refactoring, Property 13: Transaction data loading consistency**
    Verifies that on_date_selected calls get_transactions_by_date and get_occurrences_by_date
    with the selected date and updates view through callback.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values
        mock_transactions = [Mock(id="txn1"), Mock(id="txn2")]
        mock_occurrences = [Mock(id="occ1")]
        mock_transaction_service.get_transactions_by_date.return_value = mock_transactions
        mock_planned_transaction_service.get_occurrences_by_date.return_value = mock_occurrences

        presenter = HomePresenter(session, callbacks)

        # Act
        presenter.on_date_selected(selected_date)

        # Assert - verify service calls with correct date
        mock_transaction_service.get_transactions_by_date.assert_called_once_with(session, selected_date)
        mock_planned_transaction_service.get_occurrences_by_date.assert_called_once_with(session, selected_date)

        # Verify callback called with aggregated results
        callbacks.update_transactions.assert_called_once_with(selected_date, mock_transactions, mock_occurrences)

        # Verify presenter stored selected date
        assert presenter.selected_date == selected_date

        # Verify no errors shown
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.integers())
def test_pending_payment_data_loading_consistency(unused_arg):
    """
    **Feature: home-view-testability-refactoring, Property 15: Pending payment data consistency**
    Verifies that load_pending_payments calls get_all_pending_payments and get_pending_payments_statistics
    and passes results to view callback with correct structure.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values
        mock_payments = [Mock(id="payment1"), Mock(id="payment2")]
        mock_statistics = {
            "total_active": 5,
            "total_amount": Decimal('1500.50')
        }
        mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics

        presenter = HomePresenter(session, callbacks)

        # Act
        presenter.load_pending_payments()

        # Assert - verify service calls
        mock_pending_payment_service.get_all_pending_payments.assert_called_once_with(session)
        mock_pending_payment_service.get_pending_payments_statistics.assert_called_once_with(session)

        # Verify callback called with correct structure (payments list and dict of statistics)
        callbacks.update_pending_payments.assert_called_once_with(
            mock_payments,
            {'total_active': 5, 'total_amount': Decimal('1500.50')}  # dict format
        )

        # Verify no errors shown
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    decimals_strategy(),
    st.uuids().map(str),
    st.text(min_size=0, max_size=100)
)
def test_user_action_service_invocation_consistency(execution_date, amount, entity_id, reason):
    """
    **Feature: home-view-testability-refactoring, Property 17: User action service invocation consistency**
    Verifies that user actions (execute_occurrence, skip_occurrence, execute_pending_payment,
    cancel_pending_payment, delete_pending_payment, execute_loan_payment) call corresponding
    Service Layer methods with correct parameters.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for refresh_data calls
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Test execute_occurrence
        mock_occurrence = Mock(id=entity_id)
        presenter.execute_occurrence(mock_occurrence, execution_date, amount)
        mock_planned_transaction_service.execute_occurrence.assert_called_once_with(
            session, entity_id, execution_date, amount
        )
        session.commit.assert_called()
        session.rollback.assert_not_called()
        callbacks.show_message.assert_called()

        # Reset mocks
        session.commit.reset_mock()
        session.rollback.reset_mock()
        callbacks.show_message.reset_mock()
        mock_planned_transaction_service.execute_occurrence.reset_mock()

        # Test skip_occurrence
        presenter.skip_occurrence(mock_occurrence)
        mock_planned_transaction_service.skip_occurrence.assert_called_once_with(session, entity_id)
        session.commit.assert_called()
        callbacks.show_message.assert_called()

        # Reset mocks
        session.commit.reset_mock()
        callbacks.show_message.reset_mock()

        # Test execute_pending_payment
        presenter.execute_pending_payment(entity_id, amount, execution_date)
        mock_pending_payment_service.execute_pending_payment.assert_called_once()
        call_args = mock_pending_payment_service.execute_pending_payment.call_args
        assert call_args[0][0] == session
        assert call_args[0][1] == entity_id
        # Verify PendingPaymentExecute object
        execute_data = call_args[0][2]
        assert execute_data.executed_date == execution_date
        assert execute_data.executed_amount == amount
        session.commit.assert_called()
        callbacks.show_message.assert_called()

        # Reset mocks
        session.commit.reset_mock()
        callbacks.show_message.reset_mock()
        mock_pending_payment_service.execute_pending_payment.reset_mock()

        # Test cancel_pending_payment
        presenter.cancel_pending_payment(entity_id, reason if reason else None)
        mock_pending_payment_service.cancel_pending_payment.assert_called_once()
        call_args = mock_pending_payment_service.cancel_pending_payment.call_args
        assert call_args[0][0] == session
        assert call_args[0][1] == entity_id
        # Verify PendingPaymentCancel object
        cancel_data = call_args[0][2]
        assert cancel_data.cancel_reason == (reason if reason else "Не указана")
        session.commit.assert_called()
        callbacks.show_message.assert_called()

        # Reset mocks
        session.commit.reset_mock()
        callbacks.show_message.reset_mock()
        mock_pending_payment_service.cancel_pending_payment.reset_mock()

        # Test delete_pending_payment
        presenter.delete_pending_payment(entity_id)
        mock_pending_payment_service.delete_pending_payment.assert_called_once_with(session, entity_id)
        session.commit.assert_called()
        callbacks.show_message.assert_called()

        # Reset mocks
        session.commit.reset_mock()
        callbacks.show_message.reset_mock()

        # Test execute_loan_payment
        mock_payment = Mock(id=entity_id)
        presenter.execute_loan_payment(mock_payment, amount, execution_date)
        mock_loan_payment_service.execute_payment.assert_called_once_with(
            session, entity_id, transaction_date=execution_date
        )
        session.commit.assert_called()
        callbacks.show_message.assert_called()

        # Verify no errors shown in any operation
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.text(min_size=1, max_size=50), decimals_strategy())
def test_service_layer_parameter_consistency(entity_id, amount):
    """
    **Feature: home-view-testability-refactoring, Property 6: Service layer parameter consistency**
    Verifies that for any Presenter operation that calls Service Layer, the operation uses
    the injected Session and passes correct parameters.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for refresh_data calls
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Act - test execute_pending_payment operation
        execution_date = date.today()
        presenter.execute_pending_payment(entity_id, amount, execution_date)

        # Assert - verify Service Layer called with injected session and correct parameters
        mock_pending_payment_service.execute_pending_payment.assert_called_once()
        call_args = mock_pending_payment_service.execute_pending_payment.call_args
        
        # Verify first parameter is the injected session
        assert call_args[0][0] is session
        
        # Verify second parameter is the entity_id
        assert call_args[0][1] == entity_id
        
        # Verify third parameter is PendingPaymentExecute with correct data
        execute_data = call_args[0][2]
        assert execute_data.executed_date == execution_date
        assert execute_data.executed_amount == amount

        # Verify session operations
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

        # Verify success callback
        callbacks.show_message.assert_called()
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.integers())
def test_operation_result_callback_consistency(unused_arg):
    """
    **Feature: home-view-testability-refactoring, Property 16: Operation result callback consistency**
    Verifies that for any completed data loading operation, the Presenter calls the appropriate
    callback to pass results to View.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values
        mock_transactions = [Mock(id="txn1")]
        mock_occurrences = [Mock(id="occ1")]
        mock_payments = [Mock(id="payment1")]
        mock_statistics = {"total_active": 2, "total_amount": Decimal('500.00')}

        mock_transaction_service.get_by_date_range.return_value = mock_transactions
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = mock_occurrences
        mock_planned_transaction_service.get_pending_occurrences.return_value = mock_occurrences
        mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics

        presenter = HomePresenter(session, callbacks)

        # Act - test different data loading operations
        
        # Test load_calendar_data
        test_date = date.today()
        presenter.load_calendar_data(test_date)
        
        # Assert - verify appropriate callback called with results
        callbacks.update_calendar_data.assert_called_once_with(mock_transactions, mock_occurrences)

        # Reset and test load_planned_occurrences
        callbacks.reset_mock()
        presenter.load_planned_occurrences()
        
        # Assert - verify callback called with formatted results
        callbacks.update_planned_occurrences.assert_called_once()
        # Verify the call was made with formatted data (list of tuples)
        call_args = callbacks.update_planned_occurrences.call_args[0][0]
        assert isinstance(call_args, list)
        if call_args:  # If not empty
            assert isinstance(call_args[0], tuple)
            assert len(call_args[0]) == 3  # (occurrence, color, text_color)

        # Reset and test load_pending_payments
        callbacks.reset_mock()
        presenter.load_pending_payments()
        
        # Assert - verify callback called with payments and statistics dict
        callbacks.update_pending_payments.assert_called_once_with(
            mock_payments, 
            {'total_active': 2, 'total_amount': Decimal('500.00')}  # dict format
        )

        # Verify no errors shown
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st_transaction_create)
def test_success_operation_callback_consistency(transaction_data):
    """
    **Feature: home-view-testability-refactoring, Property 18: Success operation callback consistency**
    Verifies that for any successfully completed operation, the Presenter updates data
    and calls success callback.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for refresh_data calls
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Act - perform successful operation
        presenter.create_transaction(transaction_data)

        # Assert - verify success callback called
        callbacks.show_message.assert_called_once()
        success_message = callbacks.show_message.call_args[0][0]
        assert "успешно" in success_message.lower()

        # Verify data was updated (refresh_data calls these callbacks)
        callbacks.update_calendar_data.assert_called()
        callbacks.update_transactions.assert_called()
        callbacks.update_planned_occurrences.assert_called()
        callbacks.update_pending_payments.assert_called()

        # Verify transaction committed
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

        # Verify no error callback called
        callbacks.show_error.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.text(min_size=1, max_size=100))
def test_validation_error_handling_consistency(error_message):
    """
    **Feature: home-view-testability-refactoring, Property 23: Validation error handling consistency**
    Verifies that for any validation error, the Presenter calls error callback with validation message.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service, \
         patch("finance_tracker.views.home_presenter.logger") as mock_logger:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure service to raise validation error (using ValueError as validation error)
        validation_error = ValueError(f"Validation failed: {error_message}")
        mock_transaction_service.create_transaction.side_effect = validation_error

        presenter = HomePresenter(session, callbacks)

        # Act - attempt operation that will fail validation
        test_transaction = TransactionCreate(
            amount=Decimal('100.00'),
            category_id="550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            description="Test transaction",
            type=TransactionType.EXPENSE,
            transaction_date=date.today()
        )
        presenter.create_transaction(test_transaction)

        # Assert - verify validation error handling
        # 1. Error callback was called with validation message
        callbacks.show_error.assert_called_once()
        error_callback_message = callbacks.show_error.call_args[0][0]
        assert "Ошибка создания транзакции" in error_callback_message
        assert error_message in error_callback_message

        # 2. Error was logged
        mock_logger.error.assert_called_once()
        logged_message = mock_logger.error.call_args[0][0]
        assert error_message in logged_message

        # 3. Session was rolled back (not committed)
        session.rollback.assert_called_once()
        session.commit.assert_not_called()

        # 4. Success callback was NOT called
        callbacks.show_message.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.text(min_size=1, max_size=100))
def test_error_handling_consistency(error_message):
    """
    **Feature: home-view-testability-refactoring, Property 22: Error handling consistency**
    Verifies that when Service Layer raises exception, Presenter catches it, logs with context,
    calls error callback, and does NOT perform commit.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service, \
         patch("finance_tracker.views.home_presenter.logger") as mock_logger:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure service to raise exception
        test_exception = Exception(error_message)
        mock_transaction_service.get_by_date_range.side_effect = test_exception

        presenter = HomePresenter(session, callbacks)

        # Act - test error handling in load_calendar_data
        presenter.load_calendar_data(date.today())

        # Assert - verify error handling
        # 1. Logger was called with error
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args
        assert error_message in str(error_call_args[0][0])
        # Verify context in extra parameter
        assert "extra" in error_call_args[1]
        assert "selected_date" in error_call_args[1]["extra"]
        assert "session_active" in error_call_args[1]["extra"]

        # 2. Error callback was called
        callbacks.show_error.assert_called_once()
        error_callback_args = callbacks.show_error.call_args[0][0]
        assert "Ошибка загрузки данных календаря" in error_callback_args
        assert error_message in error_callback_args

        # 3. Commit was NOT called (error occurred before commit)
        session.commit.assert_not_called()

        # 4. Success message was NOT shown
        callbacks.show_message.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st_transaction_create)
def test_transaction_rollback_consistency(transaction_data):
    """
    **Feature: home-view-testability-refactoring, Property 24: Transaction rollback consistency**
    Verifies that when operation fails that modifies database state, Presenter ensures
    session rollback is performed.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service, \
         patch("finance_tracker.views.home_presenter.logger") as mock_logger:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure service to raise exception during transaction creation
        test_exception = Exception("Database error")
        mock_transaction_service.create_transaction.side_effect = test_exception

        presenter = HomePresenter(session, callbacks)

        # Act - attempt to create transaction (will fail)
        presenter.create_transaction(transaction_data)

        # Assert - verify rollback was called
        session.rollback.assert_called_once()

        # Verify commit was NOT called
        session.commit.assert_not_called()

        # Verify error was logged and shown to user
        mock_logger.error.assert_called_once()
        callbacks.show_error.assert_called_once()

        # Verify success message was NOT shown
        callbacks.show_message.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_context_logging_consistency(selected_date):
    """
    **Feature: home-view-testability-refactoring, Property 25: Context logging consistency**
    Verifies that when error occurs, Presenter logs full context including parameters,
    system state, and user session information.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service, \
         patch("finance_tracker.views.home_presenter.logger") as mock_logger:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure service to raise exception
        test_exception = Exception("Test error for context logging")
        mock_transaction_service.get_transactions_by_date.side_effect = test_exception

        presenter = HomePresenter(session, callbacks)
        presenter.selected_date = selected_date

        # Act - trigger error in on_date_selected
        presenter.on_date_selected(selected_date)

        # Assert - verify context logging
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args

        # 1. Verify error message contains context description
        error_message = error_call_args[0][0]
        assert "Ошибка загрузки данных для выбранной даты" in error_message
        assert "Test error for context logging" in error_message

        # 2. Verify extra context includes system state
        assert "extra" in error_call_args[1]
        extra_context = error_call_args[1]["extra"]

        # Verify context contains selected_date
        assert "selected_date" in extra_context
        assert extra_context["selected_date"] == selected_date

        # Verify context contains session state
        assert "session_active" in extra_context
        assert extra_context["session_active"] == True

        # 3. Verify error was shown to user
        callbacks.show_error.assert_called_once()

        # 4. Verify no success messages shown
        callbacks.show_message.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(
    st.sampled_from(["transaction", "occurrence", "unknown"]),
    st.one_of(st.none(), st.uuids().map(str))
)
def test_modal_data_preparation_consistency(modal_type, entity_id):
    """
    **Feature: home-view-testability-refactoring, Property 10: Modal data preparation consistency**
    Verifies that prepare_modal_data prepares required data for different modal types
    and returns appropriate data structure or None for unknown types.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        callbacks = Mock(spec=IHomeViewCallbacks)

        presenter = HomePresenter(session, callbacks)

        # Act
        result = presenter.prepare_modal_data(modal_type, entity_id)

        # Assert - verify behavior based on modal type
        if modal_type in ["transaction", "occurrence"]:
            # Known modal types should return data (even if empty dict for placeholder)
            assert result is not None
            # Verify result is a dict (placeholder implementation returns {})
            assert isinstance(result, dict)
        else:
            # Unknown modal types should return None
            assert result is None

        # Verify no errors were shown during data preparation
        callbacks.show_error.assert_not_called()
        callbacks.show_message.assert_not_called()


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(
    st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
    decimals_strategy(),
    st.uuids().map(str)
)
def test_modal_operation_consistency(execution_date, amount, entity_id):
    """
    **Feature: home-view-testability-refactoring, Property 11: Modal operation consistency**
    Verifies that modal operations (execute, skip, cancel) process data through Service Layer
    and update View via callbacks after successful completion.
    """
    # Arrange
    with patch("finance_tracker.views.home_presenter.transaction_service") as mock_transaction_service, \
         patch("finance_tracker.views.home_presenter.planned_transaction_service") as mock_planned_transaction_service, \
         patch("finance_tracker.views.home_presenter.pending_payment_service") as mock_pending_payment_service, \
         patch("finance_tracker.views.home_presenter.loan_payment_service") as mock_loan_payment_service:

        session = Mock(spec=Session)
        session.is_active = True
        session.commit = Mock()
        session.rollback = Mock()
        callbacks = Mock(spec=IHomeViewCallbacks)

        # Configure mock return values for refresh_data calls
        mock_transaction_service.get_by_date_range.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        mock_planned_transaction_service.get_pending_occurrences.return_value = []
        mock_pending_payment_service.get_all_pending_payments.return_value = []
        mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        mock_transaction_service.get_transactions_by_date.return_value = []
        mock_planned_transaction_service.get_occurrences_by_date.return_value = []

        presenter = HomePresenter(session, callbacks)

        # Act - execute modal operation (execute occurrence)
        mock_occurrence = Mock(id=entity_id)
        presenter.execute_occurrence(mock_occurrence, execution_date, amount)

        # Assert - verify operation processed through Service Layer
        mock_planned_transaction_service.execute_occurrence.assert_called_once_with(
            session, entity_id, execution_date, amount
        )

        # Verify transaction committed
        session.commit.assert_called()

        # Verify View updated via callbacks (refresh_data calls these)
        callbacks.update_calendar_data.assert_called()  # From refresh_data
        callbacks.update_transactions.assert_called()    # From refresh_data
        callbacks.update_planned_occurrences.assert_called()  # From refresh_data
        callbacks.update_pending_payments.assert_called()     # From refresh_data

        # Verify success message shown
        callbacks.show_message.assert_called()

        # Verify no errors shown
        callbacks.show_error.assert_not_called()
        session.rollback.assert_not_called()