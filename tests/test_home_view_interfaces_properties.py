import pytest
from hypothesis import given, strategies as st
from datetime import date
from typing import List, Tuple, Any
from finance_tracker.views.interfaces import IHomeViewCallbacks

class MockHomeView(IHomeViewCallbacks):
    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        pass
    
    def update_transactions(self, date_obj: date, transactions: List[Any], occurrences: List[Any]) -> None:
        pass
    
    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None:
        pass
    
    def update_pending_payments(self, payments: List[Any], statistics: Tuple[int, float]) -> None:
        pass
    
    def show_message(self, message: str) -> None:
        pass
    
    def show_error(self, error: str) -> None:
        pass
    
    def update_calendar_selection(self, date_obj: date) -> None:
        pass

@given(
    st.lists(st.integers()), 
    st.lists(st.integers())
)
def test_callback_interface_consistency_update_calendar_data(transactions, occurrences):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks update_calendar_data signature compatibility.
    """
    view = MockHomeView()
    view.update_calendar_data(transactions, occurrences)

@given(
    st.dates(),
    st.lists(st.integers()),
    st.lists(st.integers())
)
def test_callback_interface_consistency_update_transactions(date_obj, transactions, occurrences):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks update_transactions signature compatibility.
    """
    view = MockHomeView()
    view.update_transactions(date_obj, transactions, occurrences)

@given(
    st.lists(st.tuples(st.integers(), st.text(), st.text()))
)
def test_callback_interface_consistency_update_planned_occurrences(occurrences):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks update_planned_occurrences signature compatibility.
    """
    view = MockHomeView()
    view.update_planned_occurrences(occurrences)

@given(
    st.lists(st.integers()),
    st.tuples(st.integers(), st.floats())
)
def test_callback_interface_consistency_update_pending_payments(payments, statistics):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks update_pending_payments signature compatibility.
    """
    view = MockHomeView()
    view.update_pending_payments(payments, statistics)

@given(st.text())
def test_callback_interface_consistency_show_message(message):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks show_message signature compatibility.
    """
    view = MockHomeView()
    view.show_message(message)

@given(st.text())
def test_callback_interface_consistency_show_error(error):
    """
    **Feature: home-view-testability-refactoring, Property 19: Callback interface consistency**
    Checks show_error signature compatibility.
    """
    view = MockHomeView()
    view.show_error(error)
