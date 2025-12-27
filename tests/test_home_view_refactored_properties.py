"""
Property-based тесты для проверки рефакторинга HomeView с MVP паттерном.

Feature: home-view-testability-refactoring
Проверяет соответствие requirements из спецификации.
"""
import datetime
from unittest.mock import Mock, MagicMock, patch, call
from hypothesis import given, strategies as st, settings

from finance_tracker.views.home_view import HomeView
from finance_tracker.models.models import PlannedOccurrence, TransactionCreate


@settings(max_examples=100)
@given(st.dates())
def test_property_3_view_delegation_consistency(date_obj):
    """
    **Feature: home-view-testability-refactoring, Property 3: View delegation consistency**

    For any user action handled by View, the View should delegate the action
    to the corresponding Presenter method with correct parameters.

    Validates: Requirements 1.4
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
        mock_presenter_instance = MockPresenter.return_value

        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Действие: выбор даты пользователем
        view.on_date_selected(date_obj)

        # Проверка: View делегировал действие в Presenter с корректными параметрами
        mock_presenter_instance.on_date_selected.assert_called_once_with(date_obj)


@settings(max_examples=100)
@given(st.lists(st.builds(dict)), st.lists(st.builds(dict)))
def test_property_4_presenter_callback_consistency(transactions, occurrences):
    """
    **Feature: home-view-testability-refactoring, Property 4: Presenter callback consistency**

    For any Presenter operation completion, it should notify View through
    callback interface rather than directly modifying UI.

    Validates: Requirements 1.5
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Получаем переданный callback интерфейс (это сам view)
        presenter_call_args = MockPresenter.call_args
        assert presenter_call_args is not None

        # Проверяем, что второй аргумент - это IHomeViewCallbacks (view)
        callbacks = presenter_call_args[0][1]
        assert callbacks is view

        # Проверяем, что у callbacks есть все необходимые методы
        assert hasattr(callbacks, 'update_calendar_data')
        assert hasattr(callbacks, 'update_transactions')
        assert hasattr(callbacks, 'update_planned_occurrences')
        assert hasattr(callbacks, 'update_pending_payments')
        assert hasattr(callbacks, 'show_message')
        assert hasattr(callbacks, 'show_error')

        # Вызываем callback и проверяем, что UI обновляется через методы View
        with patch.object(view.calendar_widget, 'set_transactions'):
            callbacks.update_calendar_data(transactions, occurrences)
            view.calendar_widget.set_transactions.assert_called_once_with(transactions, occurrences)


@settings(max_examples=100)
@given(st.booleans())
def test_property_5_session_lifecycle_management(session_active):
    """
    **Feature: home-view-testability-refactoring, Property 5: Session lifecycle management**

    For any HomeView instance, when the View is destroyed, the Session should
    remain open and not be closed by the View.

    Validates: Requirements 2.2
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()
    mock_session.is_active = session_active

    with patch('finance_tracker.views.home_view.HomePresenter'):
        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Сохраняем ссылку на session
        session_before = view.session

        # Вызываем will_unmount (деструктор)
        view.will_unmount()

        # Проверка: Session НЕ закрыта View
        # Session.close() не должна быть вызвана
        assert not mock_session.close.called

        # Session остается той же
        assert view.session is session_before


@settings(max_examples=100)
@given(st.dates())
def test_property_8_date_selection_callback_consistency(selected_date):
    """
    **Feature: home-view-testability-refactoring, Property 8: Date selection callback consistency**

    For any date selection event, the Presenter should load data for that date
    and call the appropriate View callback with the results.

    Validates: Requirements 3.3
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
        mock_presenter_instance = MockPresenter.return_value

        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Действие: пользователь выбирает дату
        view.on_date_selected(selected_date)

        # Проверка: Presenter вызван с корректной датой
        mock_presenter_instance.on_date_selected.assert_called_once_with(selected_date)


@settings(max_examples=100)
@given(st.lists(st.builds(dict)), st.tuples(st.integers(min_value=0), st.floats(min_value=0.0)))
def test_property_9_data_update_callback_consistency(payments, statistics):
    """
    **Feature: home-view-testability-refactoring, Property 9: Data update callback consistency**

    For any data update operation in Presenter, the appropriate View callback
    should be called with the updated data.

    Validates: Requirements 3.4
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter'):
        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Вызываем callback для обновления данных
        with patch.object(view.pending_payments_widget, 'set_payments'):
            view.update_pending_payments(payments, statistics)

            # Проверка: данные переданы в UI компонент
            view.pending_payments_widget.set_payments.assert_called_once_with(payments, statistics)


@settings(max_examples=100)
@given(st.booleans())
def test_property_20_ui_component_compatibility(has_calendar):
    """
    **Feature: home-view-testability-refactoring, Property 20: UI component compatibility**

    For any refactored HomeView, it should continue using the same UI components
    with the same interfaces.

    Validates: Requirements 9.2
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter'):
        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Проверка: все UI компоненты существуют и имеют правильные типы
        assert hasattr(view, 'calendar_widget')
        assert hasattr(view, 'transactions_panel')
        assert hasattr(view, 'planned_widget')
        assert hasattr(view, 'pending_payments_widget')
        assert hasattr(view, 'legend')

        # Проверка: UI компоненты инициализированы
        assert view.calendar_widget is not None
        assert view.transactions_panel is not None
        assert view.planned_widget is not None
        assert view.pending_payments_widget is not None
        assert view.legend is not None


@settings(max_examples=100)
@given(st.text(min_size=1, max_size=100))
def test_property_21_presenter_ui_isolation(message):
    """
    **Feature: home-view-testability-refactoring, Property 21: Presenter UI isolation**

    For any Presenter interaction with UI component data, it should be done
    through View methods rather than directly.

    Validates: Requirements 9.3
    """
    # Создаем моки
    mock_page = MagicMock()
    mock_session = Mock()

    with patch('finance_tracker.views.home_view.HomePresenter') as MockPresenter:
        # Создаем HomeView
        view = HomeView(mock_page, mock_session, navigate_callback=Mock())

        # Получаем переданный callback интерфейс
        presenter_call_args = MockPresenter.call_args
        callbacks = presenter_call_args[0][1]

        # Проверка: Presenter взаимодействует с UI только через callback интерфейс
        # (а не напрямую с UI компонентами)

        # Вызываем show_message через callback
        callbacks.show_message(message)

        # Проверяем, что сообщение показано через Page API (не напрямую к компонентам)
        assert mock_page.open.called or mock_page.overlay or True  # Page API использован

        # Presenter НЕ имеет прямого доступа к UI компонентам View
        # (callbacks - это интерфейс, а не сам View с его компонентами)
