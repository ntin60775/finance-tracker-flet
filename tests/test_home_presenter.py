"""
Unit тесты для HomePresenter.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Tuple
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.views.interfaces import IHomeViewCallbacks
from finance_tracker.models.models import TransactionCreate, PendingPaymentExecute, PendingPaymentCancel
from finance_tracker.models.enums import TransactionType


class TestHomePresenter(unittest.TestCase):
    """Unit тесты для HomePresenter."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.session = Mock(spec=Session)
        self.session.is_active = True
        self.session.commit = Mock()
        self.session.rollback = Mock()
        
        self.callbacks = Mock(spec=IHomeViewCallbacks)
        
        # Патчим все сервисы
        self.transaction_service_patcher = patch('finance_tracker.views.home_presenter.transaction_service')
        self.planned_transaction_service_patcher = patch('finance_tracker.views.home_presenter.planned_transaction_service')
        self.pending_payment_service_patcher = patch('finance_tracker.views.home_presenter.pending_payment_service')
        self.loan_payment_service_patcher = patch('finance_tracker.views.home_presenter.loan_payment_service')
        
        self.mock_transaction_service = self.transaction_service_patcher.start()
        self.mock_planned_transaction_service = self.planned_transaction_service_patcher.start()
        self.mock_pending_payment_service = self.pending_payment_service_patcher.start()
        self.mock_loan_payment_service = self.loan_payment_service_patcher.start()
        
        # Настраиваем возвращаемые значения для методов загрузки данных
        self.mock_transaction_service.get_by_date_range.return_value = []
        self.mock_planned_transaction_service.get_occurrences_by_date_range.return_value = []
        self.mock_planned_transaction_service.get_pending_occurrences.return_value = []
        self.mock_pending_payment_service.get_all_pending_payments.return_value = []
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = {
            "total_active": 0,
            "total_amount": Decimal('0.0')
        }
        self.mock_transaction_service.get_transactions_by_date.return_value = []
        self.mock_planned_transaction_service.get_occurrences_by_date.return_value = []
        
        self.presenter = HomePresenter(self.session, self.callbacks)

    def tearDown(self):
        """Очистка после каждого теста."""
        self.transaction_service_patcher.stop()
        self.planned_transaction_service_patcher.stop()
        self.pending_payment_service_patcher.stop()
        self.loan_payment_service_patcher.stop()

    # Тесты инициализации
    def test_initialization(self):
        """Тест корректной инициализации HomePresenter."""
        self.assertEqual(self.presenter.session, self.session)
        self.assertEqual(self.presenter.callbacks, self.callbacks)
        self.assertIsInstance(self.presenter.selected_date, date)
        self.assertEqual(self.presenter.selected_date, date.today())

    # Тесты методов загрузки данных
    def test_load_initial_data_success(self):
        """Тест успешной загрузки начальных данных."""
        self.presenter.load_initial_data()
        
        # Проверяем, что вызваны все методы загрузки
        self.mock_transaction_service.get_by_date_range.assert_called()
        self.mock_planned_transaction_service.get_occurrences_by_date_range.assert_called()
        self.mock_planned_transaction_service.get_pending_occurrences.assert_called()
        self.mock_pending_payment_service.get_all_pending_payments.assert_called()
        self.mock_pending_payment_service.get_pending_payments_statistics.assert_called()
        self.mock_transaction_service.get_transactions_by_date.assert_called()
        self.mock_planned_transaction_service.get_occurrences_by_date.assert_called()
        
        # Проверяем, что вызваны соответствующие callbacks
        self.callbacks.update_calendar_data.assert_called()
        self.callbacks.update_planned_occurrences.assert_called()
        self.callbacks.update_pending_payments.assert_called()
        self.callbacks.update_transactions.assert_called()
        
        # Проверяем, что ошибки не показаны
        self.callbacks.show_error.assert_not_called()

    def test_load_calendar_data_success(self):
        """Тест успешной загрузки данных календаря."""
        test_date = date(2024, 10, 15)
        expected_first_day = date(2024, 10, 1)
        expected_last_day = date(2024, 10, 31)
        
        mock_transactions = [Mock(id="txn1")]
        mock_occurrences = [Mock(id="occ1")]
        self.mock_transaction_service.get_by_date_range.return_value = mock_transactions
        self.mock_planned_transaction_service.get_occurrences_by_date_range.return_value = mock_occurrences
        
        self.presenter.load_calendar_data(test_date)
        
        # Проверяем корректность вызовов сервисов
        self.mock_transaction_service.get_by_date_range.assert_called_once_with(
            self.session, expected_first_day, expected_last_day
        )
        self.mock_planned_transaction_service.get_occurrences_by_date_range.assert_called_once_with(
            self.session, expected_first_day, expected_last_day
        )
        
        # Проверяем вызов callback
        self.callbacks.update_calendar_data.assert_called_once_with(mock_transactions, mock_occurrences)
        self.callbacks.show_error.assert_not_called()

    def test_on_date_selected_success(self):
        """Тест успешного выбора даты."""
        test_date = date(2024, 10, 15)
        mock_transactions = [Mock(id="txn1")]
        mock_occurrences = [Mock(id="occ1")]
        
        self.mock_transaction_service.get_transactions_by_date.return_value = mock_transactions
        self.mock_planned_transaction_service.get_occurrences_by_date.return_value = mock_occurrences
        
        self.presenter.on_date_selected(test_date)
        
        # Проверяем, что дата сохранена
        self.assertEqual(self.presenter.selected_date, test_date)
        
        # Проверяем вызовы сервисов
        self.mock_transaction_service.get_transactions_by_date.assert_called_once_with(self.session, test_date)
        self.mock_planned_transaction_service.get_occurrences_by_date.assert_called_once_with(self.session, test_date)
        
        # Проверяем callback
        self.callbacks.update_transactions.assert_called_once_with(test_date, mock_transactions, mock_occurrences)
        self.callbacks.show_error.assert_not_called()

    def test_load_planned_occurrences_success(self):
        """Тест успешной загрузки плановых операций."""
        mock_occurrences = [Mock(id="occ1"), Mock(id="occ2")]
        self.mock_planned_transaction_service.get_pending_occurrences.return_value = mock_occurrences
        
        self.presenter.load_planned_occurrences()
        
        # Проверяем вызов сервиса
        self.mock_planned_transaction_service.get_pending_occurrences.assert_called_once_with(self.session)
        
        # Проверяем callback (данные форматируются в _format_occurrences_for_ui)
        self.callbacks.update_planned_occurrences.assert_called_once()
        call_args = self.callbacks.update_planned_occurrences.call_args[0][0]
        self.assertIsInstance(call_args, list)
        self.assertEqual(len(call_args), 2)  # Два occurrence
        # Проверяем формат: список кортежей (occurrence, color, text_color)
        for item in call_args:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)
        
        self.callbacks.show_error.assert_not_called()

    def test_load_pending_payments_success(self):
        """Тест успешной загрузки отложенных платежей."""
        mock_payments = [Mock(id="payment1")]
        mock_statistics = {"total_active": 5, "total_amount": Decimal('1500.50')}
        
        self.mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics
        
        self.presenter.load_pending_payments()
        
        # Проверяем вызовы сервисов
        self.mock_pending_payment_service.get_all_pending_payments.assert_called_once_with(self.session)
        self.mock_pending_payment_service.get_pending_payments_statistics.assert_called_once_with(self.session)
        
        # Проверяем callback с правильным форматом (payments, dict)
        self.callbacks.update_pending_payments.assert_called_once_with(
            mock_payments, {'total_active': 5, 'total_amount': Decimal('1500.50')}
        )
        self.callbacks.show_error.assert_not_called()

    # Тесты обработчиков пользовательских действий
    def test_create_transaction_success(self):
        """Тест успешного создания транзакции."""
        transaction_data = TransactionCreate(
            amount=Decimal('100.50'),
            type=TransactionType.EXPENSE,
            category_id=str(uuid.uuid4()),
            description="Test transaction",
            transaction_date=date.today()
        )
        
        self.presenter.create_transaction(transaction_data)
        
        # Проверяем вызов сервиса
        self.mock_transaction_service.create_transaction.assert_called_once_with(self.session, transaction_data)
        
        # Проверяем commit и отсутствие rollback
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Транзакция успешно создана")
        self.callbacks.show_error.assert_not_called()

    def test_execute_occurrence_success(self):
        """Тест успешного исполнения планового вхождения."""
        mock_occurrence = Mock(id="occurrence-id")
        execution_date = date(2024, 10, 15)
        amount = Decimal('250.00')
        
        self.presenter.execute_occurrence(mock_occurrence, execution_date, amount)
        
        # Проверяем вызов сервиса
        self.mock_planned_transaction_service.execute_occurrence.assert_called_once_with(
            self.session, "occurrence-id", execution_date, amount
        )
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Плановая операция успешно исполнена")
        self.callbacks.show_error.assert_not_called()

    def test_skip_occurrence_success(self):
        """Тест успешного пропуска планового вхождения."""
        mock_occurrence = Mock(id="occurrence-id")
        
        self.presenter.skip_occurrence(mock_occurrence)
        
        # Проверяем вызов сервиса
        self.mock_planned_transaction_service.skip_occurrence.assert_called_once_with(
            self.session, "occurrence-id"
        )
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Плановая операция пропущена")
        self.callbacks.show_error.assert_not_called()

    def test_execute_pending_payment_success(self):
        """Тест успешного исполнения отложенного платежа."""
        payment_id = "payment-id"
        executed_amount = Decimal('500.00')
        executed_date = date(2024, 10, 15)
        
        self.presenter.execute_pending_payment(payment_id, executed_amount, executed_date)
        
        # Проверяем вызов сервиса
        self.mock_pending_payment_service.execute_pending_payment.assert_called_once()
        call_args = self.mock_pending_payment_service.execute_pending_payment.call_args
        
        # Проверяем параметры
        self.assertEqual(call_args[0][0], self.session)
        self.assertEqual(call_args[0][1], payment_id)
        execute_data = call_args[0][2]
        self.assertIsInstance(execute_data, PendingPaymentExecute)
        self.assertEqual(execute_data.executed_date, executed_date)
        self.assertEqual(execute_data.executed_amount, executed_amount)
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Отложенный платёж успешно исполнен")
        self.callbacks.show_error.assert_not_called()

    def test_cancel_pending_payment_success(self):
        """Тест успешной отмены отложенного платежа."""
        payment_id = "payment-id"
        reason = "Test cancellation reason"
        
        self.presenter.cancel_pending_payment(payment_id, reason)
        
        # Проверяем вызов сервиса
        self.mock_pending_payment_service.cancel_pending_payment.assert_called_once()
        call_args = self.mock_pending_payment_service.cancel_pending_payment.call_args
        
        # Проверяем параметры
        self.assertEqual(call_args[0][0], self.session)
        self.assertEqual(call_args[0][1], payment_id)
        cancel_data = call_args[0][2]
        self.assertIsInstance(cancel_data, PendingPaymentCancel)
        self.assertEqual(cancel_data.cancel_reason, reason)
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Отложенный платёж отменён")
        self.callbacks.show_error.assert_not_called()

    def test_cancel_pending_payment_without_reason(self):
        """Тест отмены отложенного платежа без указания причины."""
        payment_id = "payment-id"
        
        self.presenter.cancel_pending_payment(payment_id)
        
        # Проверяем вызов сервиса
        call_args = self.mock_pending_payment_service.cancel_pending_payment.call_args
        cancel_data = call_args[0][2]
        self.assertEqual(cancel_data.cancel_reason, "Не указана")

    def test_delete_pending_payment_success(self):
        """Тест успешного удаления отложенного платежа."""
        payment_id = "payment-id"
        
        self.presenter.delete_pending_payment(payment_id)
        
        # Проверяем вызов сервиса
        self.mock_pending_payment_service.delete_pending_payment.assert_called_once_with(
            self.session, payment_id
        )
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Отложенный платёж удалён")
        self.callbacks.show_error.assert_not_called()

    def test_execute_loan_payment_success(self):
        """Тест успешного исполнения платежа по кредиту."""
        mock_payment = Mock(id="payment-id")
        amount = Decimal('1000.00')
        execution_date = date(2024, 10, 15)
        
        self.presenter.execute_loan_payment(mock_payment, amount, execution_date)
        
        # Проверяем вызов сервиса
        self.mock_loan_payment_service.execute_payment.assert_called_once_with(
            self.session, "payment-id", transaction_date=execution_date
        )
        
        # Проверяем commit
        self.session.commit.assert_called_once()
        self.session.rollback.assert_not_called()
        
        # Проверяем success callback
        self.callbacks.show_message.assert_called_once_with("Платёж по кредиту успешно исполнен")
        self.callbacks.show_error.assert_not_called()

    # Тесты обработки ошибок
    def test_create_transaction_error_handling(self):
        """Тест обработки ошибки при создании транзакции."""
        transaction_data = TransactionCreate(
            amount=Decimal('100.50'),
            type=TransactionType.EXPENSE,
            category_id=str(uuid.uuid4()),
            description="Test transaction",
            transaction_date=date.today()
        )
        
        # Настраиваем исключение
        test_error = SQLAlchemyError("Database error")
        self.mock_transaction_service.create_transaction.side_effect = test_error
        
        with patch('finance_tracker.views.home_presenter.logger') as mock_logger:
            self.presenter.create_transaction(transaction_data)
        
        # Проверяем rollback
        self.session.rollback.assert_called_once()
        self.session.commit.assert_not_called()
        
        # Проверяем логирование
        mock_logger.error.assert_called_once()
        
        # Проверяем error callback
        self.callbacks.show_error.assert_called_once()
        error_message = self.callbacks.show_error.call_args[0][0]
        self.assertIn("Ошибка создания транзакции", error_message)
        
        # Проверяем, что success callback не вызван
        self.callbacks.show_message.assert_not_called()

    def test_load_calendar_data_error_handling(self):
        """Тест обработки ошибки при загрузке данных календаря."""
        test_date = date(2024, 10, 15)
        test_error = SQLAlchemyError("Database error")
        self.mock_transaction_service.get_by_date_range.side_effect = test_error
        
        with patch('finance_tracker.views.home_presenter.logger') as mock_logger:
            self.presenter.load_calendar_data(test_date)
        
        # Проверяем логирование
        mock_logger.error.assert_called_once()
        
        # Проверяем error callback
        self.callbacks.show_error.assert_called_once()
        error_message = self.callbacks.show_error.call_args[0][0]
        self.assertIn("Ошибка загрузки данных календаря", error_message)
        
        # Проверяем, что update callback не вызван
        self.callbacks.update_calendar_data.assert_not_called()

    def test_execute_occurrence_error_handling(self):
        """Тест обработки ошибки при исполнении планового вхождения."""
        mock_occurrence = Mock(id="occurrence-id")
        execution_date = date(2024, 10, 15)
        amount = Decimal('250.00')
        
        test_error = SQLAlchemyError("Database error")
        self.mock_planned_transaction_service.execute_occurrence.side_effect = test_error
        
        with patch('finance_tracker.views.home_presenter.logger') as mock_logger:
            self.presenter.execute_occurrence(mock_occurrence, execution_date, amount)
        
        # Проверяем rollback
        self.session.rollback.assert_called_once()
        self.session.commit.assert_not_called()
        
        # Проверяем логирование
        mock_logger.error.assert_called_once()
        
        # Проверяем error callback
        self.callbacks.show_error.assert_called_once()
        error_message = self.callbacks.show_error.call_args[0][0]
        self.assertIn("Ошибка исполнения плановой операции", error_message)
        
        # Проверяем, что success callback не вызван
        self.callbacks.show_message.assert_not_called()

    # Тесты модальных окон
    def test_prepare_modal_data_transaction(self):
        """Тест подготовки данных для модального окна транзакции."""
        result = self.presenter.prepare_modal_data("transaction", "transaction-id")
        
        # Проверяем, что возвращается словарь (placeholder)
        self.assertEqual(result, {})

    def test_prepare_modal_data_occurrence(self):
        """Тест подготовки данных для модального окна планового вхождения."""
        result = self.presenter.prepare_modal_data("occurrence", "occurrence-id")
        
        # Проверяем, что возвращается словарь (placeholder)
        self.assertEqual(result, {})

    def test_prepare_modal_data_unknown_type(self):
        """Тест подготовки данных для неизвестного типа модального окна."""
        result = self.presenter.prepare_modal_data("unknown", "entity-id")
        
        # Проверяем, что возвращается None
        self.assertIsNone(result)

    def test_prepare_modal_data_error_handling(self):
        """Тест обработки ошибки при подготовке данных модального окна."""
        with patch.object(self.presenter, '_prepare_transaction_modal_data', side_effect=Exception("Test error")):
            with patch('finance_tracker.views.home_presenter.logger') as mock_logger:
                result = self.presenter.prepare_modal_data("transaction", "transaction-id")
        
        # Проверяем, что возвращается None при ошибке
        self.assertIsNone(result)
        
        # Проверяем логирование
        mock_logger.error.assert_called_once()
        
        # Проверяем error callback
        self.callbacks.show_error.assert_called_once()

    # Тесты приватных методов
    def test_refresh_data(self):
        """Тест обновления всех данных."""
        test_date = date(2024, 10, 15)
        self.presenter.selected_date = test_date
        
        self.presenter._refresh_data()
        
        # Проверяем, что вызваны все методы загрузки данных
        self.mock_transaction_service.get_by_date_range.assert_called()
        self.mock_transaction_service.get_transactions_by_date.assert_called_with(self.session, test_date)
        self.mock_planned_transaction_service.get_pending_occurrences.assert_called()
        self.mock_pending_payment_service.get_all_pending_payments.assert_called()

    def test_handle_error_logging_and_callback(self):
        """Тест обработки ошибки с логированием и callback."""
        test_message = "Test error message"
        test_exception = Exception("Test exception")
        
        with patch('finance_tracker.views.home_presenter.logger') as mock_logger:
            self.presenter._handle_error(test_message, test_exception)
        
        # Проверяем логирование с контекстом
        mock_logger.error.assert_called_once()
        log_call_args = mock_logger.error.call_args
        self.assertIn(test_message, log_call_args[0][0])
        self.assertIn("selected_date", log_call_args[1]["extra"])
        self.assertIn("session_active", log_call_args[1]["extra"])
        
        # Проверяем error callback
        self.callbacks.show_error.assert_called_once()
        error_message = self.callbacks.show_error.call_args[0][0]
        self.assertIn(test_message, error_message)
        self.assertIn(str(test_exception), error_message)

    def test_format_occurrences_for_ui(self):
        """Тест форматирования плановых операций для UI."""
        mock_occurrences = [Mock(id="occ1"), Mock(id="occ2")]
        
        result = self.presenter._format_occurrences_for_ui(mock_occurrences)
        
        # Проверяем формат результата
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)  # (occurrence, color, text_color)
            self.assertEqual(item[1], "blue")  # color
            self.assertEqual(item[2], "white")  # text_color


if __name__ == '__main__':
    unittest.main()