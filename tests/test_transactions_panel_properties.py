"""
Property-based тесты для TransactionsPanel.

Тестирует:
- Property 4: Button Initialization Robustness
"""

import pytest
from unittest.mock import Mock, MagicMock
from hypothesis import given, strategies as st, settings
from datetime import date, timedelta
from decimal import Decimal
import flet as ft

from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.models.models import TransactionDB
from finance_tracker.models.enums import TransactionType
from property_generators import (
    transaction_dates,
    valid_amounts,
    transaction_descriptions,
    callback_functions
)


class TestTransactionsPanelProperties:
    """Property-based тесты для TransactionsPanel."""

    @given(
        date_obj=transaction_dates(),
        callback=callback_functions()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_button_initialization_robustness(self, date_obj, callback):
        """
        **Feature: add-transaction-button-fix, Property 4: Button Initialization Robustness**
        **Validates: Requirements 4.1, 4.3**
        
        Property: Для любой валидной callback функции, когда TransactionsPanel создается 
        с этим callback, кнопка добавления должна быть правильно инициализирована и функциональна.
        """
        # Arrange - создаем TransactionsPanel с различными callback функциями
        transactions = []  # Пустой список транзакций для простоты
        
        # Act - создаем панель с сгенерированными параметрами
        panel = TransactionsPanel(
            date_obj=date_obj,
            transactions=transactions,
            on_add_transaction=callback
        )
        
        # Assert - проверяем правильную инициализацию кнопки
        # 1. Панель должна быть создана без ошибок
        assert panel is not None, "TransactionsPanel должна быть создана"
        
        # 2. Callback должен быть сохранен
        assert panel.on_add_transaction == callback, "Callback должен быть сохранен"
        
        # 3. Дата должна быть сохранена
        assert panel.date == date_obj, "Дата должна быть сохранена"
        
        # 4. Список транзакций должен быть сохранен
        assert panel.transactions == transactions, "Список транзакций должен быть сохранен"
        
        # 5. Получаем кнопку из заголовка для проверки её атрибутов
        header_row = panel._build_header()
        assert header_row is not None, "Заголовок должен быть создан"
        assert len(header_row.controls) >= 2, "Заголовок должен содержать минимум 2 элемента"
        
        # Кнопка добавления должна быть вторым элементом в заголовке
        add_button = header_row.controls[1]
        assert isinstance(add_button, ft.IconButton), "Второй элемент должен быть IconButton"
        
        # 6. Проверяем атрибуты кнопки
        assert add_button.icon == ft.Icons.ADD, "Кнопка должна иметь иконку ADD"
        assert add_button.tooltip == "Добавить транзакцию", "Кнопка должна иметь правильный tooltip"
        assert add_button.bgcolor == ft.Colors.PRIMARY, "Кнопка должна иметь PRIMARY цвет фона"
        assert add_button.icon_color == ft.Colors.ON_PRIMARY, "Иконка должна иметь ON_PRIMARY цвет"
        
        # 7. Проверяем состояние кнопки в зависимости от callback
        if callback is None:
            assert add_button.disabled == True, "Кнопка должна быть отключена при отсутствии callback"
        else:
            assert add_button.disabled != True, "Кнопка должна быть активна при наличии callback"
        
        # 8. Проверяем, что on_click установлен (всегда должен быть установлен для безопасности)
        assert add_button.on_click is not None, "on_click должен быть установлен"

    @given(
        date_obj=transaction_dates(),
        transactions=st.lists(
            st.fixed_dictionaries({
                'amount': valid_amounts(),
                'type': st.sampled_from(TransactionType),
                'description': transaction_descriptions()
            }),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_button_initialization_with_various_data(self, date_obj, transactions):
        """
        Property: Кнопка должна инициализироваться корректно независимо от количества 
        и содержимого транзакций.
        """
        # Arrange - создаем mock транзакции
        mock_transactions = []
        for tx_data in transactions:
            mock_tx = Mock(spec=TransactionDB)
            mock_tx.amount = tx_data['amount']
            mock_tx.type = tx_data['type']
            mock_tx.description = tx_data['description']
            mock_transactions.append(mock_tx)
        
        mock_callback = Mock()
        
        # Act - создаем панель
        panel = TransactionsPanel(
            date_obj=date_obj,
            transactions=mock_transactions,
            on_add_transaction=mock_callback
        )
        
        # Assert - кнопка должна быть инициализирована одинаково независимо от данных
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        # Атрибуты кнопки не должны зависеть от данных транзакций
        assert add_button.icon == ft.Icons.ADD
        assert add_button.tooltip == "Добавить транзакцию"
        assert add_button.bgcolor == ft.Colors.PRIMARY
        assert add_button.icon_color == ft.Colors.ON_PRIMARY
        assert add_button.disabled != True  # Должна быть активна с валидным callback
        assert add_button.on_click is not None

    @given(
        callback=st.one_of(
            st.just(Mock()),
            st.just(MagicMock()),
            st.just(lambda: None),
            st.just(lambda: "test_result"),
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_callback_integration(self, callback):
        """
        **Feature: add-transaction-button-fix, Property 2: Callback Integration**
        **Validates: Requirements 3.1, 3.2**
        
        Property: Для любой валидной callback функции, переданной в TransactionsPanel,
        при нажатии кнопки добавления callback должен быть вызван ровно один раз.
        """
        # Arrange - создаем TransactionsPanel с валидной callback функцией
        test_date = date.today()
        transactions = []
        
        # Если callback это Mock, сбрасываем его состояние
        if isinstance(callback, (Mock, MagicMock)):
            callback.reset_mock()
        
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=callback
        )
        
        # Act - симулируем нажатие кнопки добавления
        # Получаем кнопку из заголовка
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        # Проверяем, что кнопка правильно настроена
        assert add_button is not None, "Кнопка добавления должна существовать"
        assert add_button.on_click is not None, "У кнопки должен быть установлен on_click"
        assert add_button.disabled != True, "Кнопка должна быть активна с валидным callback"
        
        # Симулируем нажатие кнопки через _safe_add_transaction
        panel._safe_add_transaction(None)
        
        # Assert - проверяем, что callback был вызван ровно один раз
        if isinstance(callback, (Mock, MagicMock)):
            callback.assert_called_once()
            # Проверяем, что callback был вызван без параметров
            callback.assert_called_with()
        
        # Проверяем, что повторное нажатие также работает корректно
        if isinstance(callback, (Mock, MagicMock)):
            callback.reset_mock()
        
        # Второе нажатие
        panel._safe_add_transaction(None)
        
        if isinstance(callback, (Mock, MagicMock)):
            callback.assert_called_once()
            callback.assert_called_with()

    @given(
        callback=st.one_of(
            st.none(),
            st.just(lambda: None),
            st.just(lambda: "test"),
            st.just(Mock()),
            st.just(MagicMock())
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_button_callback_handling_robustness(self, callback):
        """
        Property: Кнопка должна безопасно обрабатывать различные типы callback функций.
        """
        # Arrange
        test_date = date.today()
        transactions = []
        
        # Act - создаем панель с различными типами callback
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=callback
        )
        
        # Assert - панель должна создаваться без ошибок
        assert panel is not None
        assert panel.on_add_transaction == callback
        
        # Получаем кнопку
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        # Проверяем состояние кнопки
        if callback is None:
            assert add_button.disabled == True
        else:
            assert add_button.disabled != True
        
        # on_click всегда должен быть установлен для безопасности
        assert add_button.on_click is not None
        
        # Тестируем безопасный вызов callback через _safe_add_transaction
        try:
            # Симулируем нажатие кнопки
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит ошибок не было
        except Exception as e:
            # Если возникла ошибка, она должна быть обработана внутри _safe_add_transaction
            # и не должна "всплывать" наружу
            pytest.fail(f"_safe_add_transaction не должен выбрасывать исключения: {e}")

    @given(
        date_obj=st.dates(min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
    )
    @settings(max_examples=30, deadline=None)
    def test_button_initialization_with_edge_case_dates(self, date_obj):
        """
        Property: Кнопка должна инициализироваться корректно с любыми граничными датами.
        """
        # Arrange
        mock_callback = Mock()
        transactions = []
        
        # Act
        panel = TransactionsPanel(
            date_obj=date_obj,
            transactions=transactions,
            on_add_transaction=mock_callback
        )
        
        # Assert - кнопка должна быть инициализирована независимо от даты
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        
        assert add_button.icon == ft.Icons.ADD
        assert add_button.tooltip == "Добавить транзакцию"
        assert add_button.disabled != True
        assert add_button.on_click is not None
        
        # Дата должна быть сохранена корректно
        assert panel.date == date_obj

    @given(
        callback=st.just(Mock()),
        click_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_multiple_callback_invocations(self, callback, click_count):
        """
        Property: При множественных нажатиях кнопки callback должен вызываться 
        соответствующее количество раз независимо.
        """
        # Arrange
        test_date = date.today()
        transactions = []
        callback.reset_mock()
        
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=callback
        )
        
        # Act - симулируем множественные нажатия
        for _ in range(click_count):
            panel._safe_add_transaction(None)
        
        # Assert - callback должен быть вызван точно click_count раз
        assert callback.call_count == click_count
        
        # Каждый вызов должен быть без параметров
        for call in callback.call_args_list:
            assert call == ((), {})  # Пустые args и kwargs

    @given(
        callback_result=st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.booleans(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text())
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_callback_return_value_handling(self, callback_result):
        """
        Property: Callback может возвращать любое значение, и это не должно влиять 
        на работу кнопки.
        """
        # Arrange - создаем callback, который возвращает различные значения
        mock_callback = Mock(return_value=callback_result)
        test_date = date.today()
        transactions = []
        
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=mock_callback
        )
        
        # Act - нажимаем кнопку
        panel._safe_add_transaction(None)
        
        # Assert - callback должен быть вызван независимо от возвращаемого значения
        mock_callback.assert_called_once()
        
        # Проверяем, что возвращаемое значение не влияет на состояние панели
        assert panel.on_add_transaction == mock_callback
        
        # Кнопка должна оставаться функциональной
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        assert add_button.disabled != True

    @given(
        exception_type=st.sampled_from([
            ValueError, TypeError, RuntimeError, AttributeError, KeyError
        ])
    )
    @settings(max_examples=20, deadline=None)
    def test_callback_exception_handling(self, exception_type):
        """
        Property: Если callback выбрасывает исключение, это должно быть безопасно 
        обработано без нарушения работы UI.
        """
        # Arrange - создаем callback, который выбрасывает исключение
        def failing_callback():
            raise exception_type("Test exception from callback")
        
        test_date = date.today()
        transactions = []
        
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=failing_callback
        )
        
        # Act & Assert - нажатие кнопки не должно вызывать необработанное исключение
        try:
            panel._safe_add_transaction(None)
            # Если дошли сюда, значит исключение было обработано корректно
        except Exception as e:
            pytest.fail(f"_safe_add_transaction должен обрабатывать исключения в callback, но получил: {e}")
        
        # Панель должна оставаться в рабочем состоянии
        assert panel.on_add_transaction == failing_callback
        
        # Кнопка должна оставаться функциональной
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        assert add_button.disabled != True

    @given(
        click_sequence=st.lists(
            st.integers(min_value=1, max_value=5),  # Количество нажатий в каждой серии
            min_size=1,
            max_size=10  # До 10 серий нажатий
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_multiple_click_handling(self, click_sequence):
        """
        **Feature: add-transaction-button-fix, Property 5: Multiple Click Handling**
        **Validates: Requirements 4.4**
        
        Property: Для любой последовательности нажатий кнопки, каждое нажатие должно 
        вызывать callback независимо без взаимного влияния.
        """
        # Arrange - создаем TransactionsPanel с mock callback
        test_date = date.today()
        transactions = []
        mock_callback = Mock()
        
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=transactions,
            on_add_transaction=mock_callback
        )
        
        # Проверяем, что кнопка правильно инициализирована
        header_row = panel._build_header()
        add_button = header_row.controls[1]
        assert add_button is not None, "Кнопка добавления должна существовать"
        assert add_button.disabled != True, "Кнопка должна быть активна"
        
        # Act - выполняем последовательность серий нажатий
        total_expected_calls = 0
        
        for series_index, clicks_in_series in enumerate(click_sequence):
            # Сбрасываем счетчик для отслеживания вызовов в этой серии
            calls_before_series = mock_callback.call_count
            
            # Выполняем серию нажатий
            for click_index in range(clicks_in_series):
                panel._safe_add_transaction(None)
                
                # Проверяем, что каждое нажатие увеличивает счетчик на 1
                expected_calls_so_far = calls_before_series + click_index + 1
                assert mock_callback.call_count == expected_calls_so_far, \
                    f"После {click_index + 1} нажатия в серии {series_index + 1} " \
                    f"ожидалось {expected_calls_so_far} вызовов, получено {mock_callback.call_count}"
            
            # Обновляем общий счетчик ожидаемых вызовов
            total_expected_calls += clicks_in_series
            
            # Проверяем, что общее количество вызовов соответствует ожидаемому
            assert mock_callback.call_count == total_expected_calls, \
                f"После серии {series_index + 1} ожидалось {total_expected_calls} вызовов, " \
                f"получено {mock_callback.call_count}"
            
            # Проверяем, что все вызовы были без параметров (независимые)
            for call in mock_callback.call_args_list:
                assert call == ((), {}), \
                    f"Каждый вызов callback должен быть без параметров, получен: {call}"
            
            # Проверяем, что состояние панели не изменилось
            assert panel.on_add_transaction == mock_callback, \
                "Callback должен оставаться неизменным после нажатий"
            assert panel.date == test_date, \
                "Дата панели должна оставаться неизменной после нажатий"
            
            # Проверяем, что кнопка остается функциональной
            current_header = panel._build_header()
            current_button = current_header.controls[1]
            assert current_button.disabled != True, \
                f"Кнопка должна оставаться активной после серии {series_index + 1}"
            assert current_button.on_click is not None, \
                f"on_click должен оставаться установленным после серии {series_index + 1}"
        
        # Assert - финальные проверки независимости нажатий
        # 1. Общее количество вызовов должно равняться сумме всех нажатий
        total_clicks = sum(click_sequence)
        assert mock_callback.call_count == total_clicks, \
            f"Общее количество вызовов {mock_callback.call_count} должно равняться " \
            f"общему количеству нажатий {total_clicks}"
        
        # 2. Каждый вызов должен быть независимым (без параметров)
        assert len(mock_callback.call_args_list) == total_clicks, \
            "Количество записанных вызовов должно соответствовать общему количеству нажатий"
        
        for i, call in enumerate(mock_callback.call_args_list):
            assert call == ((), {}), \
                f"Вызов {i + 1} должен быть без параметров (независимый), получен: {call}"
        
        # 3. Состояние панели должно оставаться стабильным
        assert panel.on_add_transaction == mock_callback, \
            "Callback не должен изменяться после множественных нажатий"
        assert panel.date == test_date, \
            "Дата не должна изменяться после множественных нажатий"
        assert panel.transactions == transactions, \
            "Список транзакций не должен изменяться после множественных нажатий"
        
        # 4. Кнопка должна оставаться функциональной
        final_header = panel._build_header()
        final_button = final_header.controls[1]
        assert final_button.disabled != True, \
            "Кнопка должна оставаться активной после всех нажатий"
        assert final_button.on_click is not None, \
            "on_click должен оставаться установленным после всех нажатий"