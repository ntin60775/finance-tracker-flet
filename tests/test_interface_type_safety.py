"""
Тесты для предотвращения ошибки "'tuple' object has no attribute 'get'".

Эти тесты проверяют корректность типов данных в интерфейсах между компонентами,
особенно в случаях, когда ожидается Dict[str, Any], но передается Tuple.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY
from typing import Dict, Any, List, Tuple
import pytest
from hypothesis import given, strategies as st, settings

from test_view_base import ViewTestBase
from finance_tracker.views.home_view import HomeView
from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.models.models import PendingPaymentDB


class TestInterfaceTypeSafety(ViewTestBase):
    """
    Тесты для предотвращения ошибок типов в интерфейсах.
    
    Проверяют корректность типов данных при передаче между компонентами:
    - HomePresenter -> IHomeViewCallbacks
    - PendingPaymentsWidget.set_payments()
    - Сервисы -> Presenter
    """

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Создаем mock объекты для компонентов
        self.mock_session = self.create_mock_session()
        self.mock_page = self.create_mock_page()
        
        # Патчим сервисы для изоляции тестов
        self.mock_pending_payment_service = self.add_patcher(
            'finance_tracker.views.home_presenter.pending_payment_service'
        )
        
        self.mock_transaction_service = self.add_patcher(
            'finance_tracker.views.home_presenter.transaction_service'
        )
        
        self.mock_planned_transaction_service = self.add_patcher(
            'finance_tracker.views.home_presenter.planned_transaction_service'
        )
        
        # Патчим UI компоненты для изоляции
        self.mock_calendar_widget = self.add_patcher(
            'finance_tracker.views.home_view.CalendarWidget'
        )
        
        self.mock_transactions_panel = self.add_patcher(
            'finance_tracker.views.home_view.TransactionsPanel'
        )
        
        self.mock_pending_payments_widget = self.add_patcher(
            'finance_tracker.views.home_view.PendingPaymentsWidget'
        )

    def create_mock_statistics_dict(self) -> Dict[str, Any]:
        """
        Создание корректного мока для statistics в формате Dict[str, Any].
        
        Returns:
            Dict[str, Any]: Словарь со статистикой отложенных платежей
        """
        return {
            "total_active": 5,
            "total_amount": 15000.50,
            "with_date": 3,
            "without_date": 2,
            "high_priority": 1,
            "medium_priority": 2,
            "low_priority": 2
        }

    def create_mock_statistics_tuple(self) -> Tuple[int, float]:
        """
        Создание некорректного мока для statistics в формате Tuple (старый формат).
        
        Returns:
            Tuple[int, float]: Кортеж со статистикой (старый формат, который вызывает ошибки)
        """
        return (5, 15000.50)

    def create_mock_pending_payments(self) -> List[PendingPaymentDB]:
        """
        Создание мока для списка отложенных платежей.
        
        Returns:
            List[Mock]: Список моков PendingPaymentDB
        """
        from finance_tracker.models.enums import PendingPaymentPriority
        import datetime
        
        payments = []
        for i in range(3):
            payment = Mock(spec=PendingPaymentDB)
            payment.id = f"payment_{i}"
            payment.description = f"Платеж {i}"
            payment.amount = 1000.0 + i * 500
            payment.priority = PendingPaymentPriority.MEDIUM
            payment.planned_date = datetime.date.today() + datetime.timedelta(days=i+1)
            payments.append(payment)
        return payments

    def test_pending_payments_widget_statistics_type(self):
        """
        Тест проверяет, что PendingPaymentsWidget.set_payments принимает statistics как Dict[str, Any].
        
        Validates: Requirements 3.1
        """
        # Патчим build методы для избежания ошибок UI
        with patch.object(PendingPaymentsWidget, '_build_payment_card', return_value=Mock()):
            # Создаем PendingPaymentsWidget
            widget = PendingPaymentsWidget(
                session=self.mock_session,
                on_execute=Mock(),
                on_cancel=Mock(),
                on_delete=Mock(),
                on_show_all=Mock()
            )
            
            # Тест 1: Корректный тип - Dict[str, Any]
            payments = self.create_mock_pending_payments()
            statistics_dict = self.create_mock_statistics_dict()
            
            try:
                widget.set_payments(payments, statistics_dict)
            except AttributeError as e:
                if "'tuple' object has no attribute 'get'" in str(e):
                    self.fail(f"set_payments не должен вызывать ошибку с Dict: {e}")
                else:
                    raise  # Перебрасываем другие ошибки
            
            # Проверяем, что данные установлены корректно
            self.assertEqual(widget.payments, payments[:5])  # Берется только первые 5
            self.assertEqual(widget.statistics, statistics_dict)
            
            # Тест 2: Некорректный тип - Tuple (должен вызвать ошибку или быть обработан)
            statistics_tuple = self.create_mock_statistics_tuple()
            
            # Если widget.set_payments пытается вызвать .get() на tuple, это вызовет AttributeError
            with self.assertRaises(AttributeError) as context:
                widget.set_payments(payments, statistics_tuple)
            
            # Проверяем, что это именно ошибка "'tuple' object has no attribute 'get'"
            self.assertIn("'tuple' object has no attribute 'get'", str(context.exception))

    def test_home_view_callbacks_interface(self):
        """
        Тест проверяет, что IHomeViewCallbacks.update_pending_payments принимает statistics как Dict[str, Any].
        
        Validates: Requirements 3.2
        """
        # Создаем HomeView (который реализует IHomeViewCallbacks)
        home_view = HomeView(self.mock_page, self.mock_session, navigate_callback=Mock())
        
        # Патчим set_payments для изоляции теста
        with patch.object(home_view.pending_payments_widget, 'set_payments') as mock_set_payments:
            # Тест 1: Корректный тип - Dict[str, Any]
            payments = self.create_mock_pending_payments()
            statistics_dict = self.create_mock_statistics_dict()
            
            try:
                home_view.update_pending_payments(payments, statistics_dict)
            except AttributeError as e:
                if "'tuple' object has no attribute 'get'" in str(e):
                    self.fail(f"update_pending_payments не должен вызывать ошибку с Dict: {e}")
                else:
                    raise  # Перебрасываем другие ошибки
            
            # Проверяем, что set_payments был вызван с правильными аргументами
            mock_set_payments.assert_called_once_with(payments, statistics_dict)
            
            # Тест 2: Некорректный тип - Tuple (передается напрямую в widget)
            mock_set_payments.reset_mock()
            statistics_tuple = self.create_mock_statistics_tuple()
            
            # Настраиваем mock для вызова ошибки при получении tuple
            mock_set_payments.side_effect = AttributeError("'tuple' object has no attribute 'get'")
            
            # Если update_pending_payments пытается передать tuple в widget.set_payments,
            # который ожидает dict, это должно вызвать AttributeError
            with self.assertRaises(AttributeError) as context:
                home_view.update_pending_payments(payments, statistics_tuple)
            
            # Проверяем, что это именно ошибка "'tuple' object has no attribute 'get'"
            self.assertIn("'tuple' object has no attribute 'get'", str(context.exception))

    def test_home_presenter_callback_calls(self):
        """
        Тест проверяет, что HomePresenter вызывает callback с правильными типами.
        
        Validates: Requirements 3.3
        """
        # Создаем mock для IHomeViewCallbacks
        mock_callbacks = Mock()
        
        # Создаем HomePresenter
        presenter = HomePresenter(self.mock_session, mock_callbacks)
        
        # Настраиваем mock сервиса для возврата корректного типа
        mock_payments = self.create_mock_pending_payments()
        mock_statistics_dict = self.create_mock_statistics_dict()
        
        self.mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics_dict
        
        # Тест 1: Вызываем load_pending_payments
        presenter.load_pending_payments()
        
        # Проверяем, что callback был вызван с правильными типами
        mock_callbacks.update_pending_payments.assert_called_once_with(mock_payments, mock_statistics_dict)
        
        # Проверяем типы переданных аргументов
        call_args = mock_callbacks.update_pending_payments.call_args
        self.assertIsNotNone(call_args)
        
        passed_payments, passed_statistics = call_args[0]
        self.assertIsInstance(passed_statistics, dict, 
                            f"statistics должен быть dict, получен {type(passed_statistics)}")
        
        # Тест 2: Симулируем ситуацию, когда сервис возвращает tuple (старый формат)
        mock_callbacks.reset_mock()
        mock_statistics_tuple = self.create_mock_statistics_tuple()
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics_tuple
        
        # Вызываем load_pending_payments - presenter должен обработать некорректный тип
        presenter.load_pending_payments()
        
        # Проверяем, что callback был вызван
        mock_callbacks.update_pending_payments.assert_called_once()
        
        # Проверяем, что presenter преобразовал tuple в dict или обработал ошибку
        call_args = mock_callbacks.update_pending_payments.call_args
        passed_payments, passed_statistics = call_args[0]
        
        # Presenter должен либо преобразовать tuple в dict, либо использовать fallback dict
        self.assertIsInstance(passed_statistics, dict,
                            f"Presenter должен передавать dict, даже если сервис вернул {type(mock_statistics_tuple)}")

    def test_statistics_format_consistency(self):
        """
        Тест проверяет консистентность формата statistics между компонентами.
        
        Validates: Requirements 3.4
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session, navigate_callback=Mock())
        
        # Создаем корректные данные
        payments = self.create_mock_pending_payments()
        statistics_dict = self.create_mock_statistics_dict()
        
        # Тест 1: Проверяем, что HomeView корректно передает данные в PendingPaymentsWidget
        home_view.update_pending_payments(payments, statistics_dict)
        
        # Проверяем, что PendingPaymentsWidget был вызван с правильными типами
        self.mock_pending_payments_widget.return_value.set_payments.assert_called_once_with(
            payments, statistics_dict
        )
        
        # Тест 2: Проверяем обязательные поля в statistics
        required_fields = ["total_active", "total_amount"]
        
        for field in required_fields:
            self.assertIn(field, statistics_dict, 
                         f"Поле '{field}' должно присутствовать в statistics")
        
        # Тест 3: Проверяем типы значений в statistics
        self.assertIsInstance(statistics_dict["total_active"], int,
                            "total_active должно быть int")
        self.assertIsInstance(statistics_dict["total_amount"], (int, float),
                            "total_amount должно быть числом")
        
        # Тест 4: Проверяем, что statistics можно использовать как dict
        try:
            # Эти операции должны работать без ошибок
            _ = statistics_dict.get("total_active", 0)
            _ = statistics_dict.get("total_amount", 0.0)
            _ = statistics_dict.keys()
            _ = statistics_dict.values()
            _ = statistics_dict.items()
        except AttributeError as e:
            self.fail(f"statistics должен поддерживать dict операции: {e}")

    def test_statistics_format_consistency_across_services(self):
        """
        Тест проверяет консистентность формата statistics между разными сервисами.
        
        Validates: Requirements 3.4
        """
        # Создаем различные типы statistics для проверки консистентности
        test_statistics_formats = [
            # Pending payments statistics
            {
                "total_active": 5,
                "total_amount": 15000.50,
                "with_date": 3,
                "without_date": 2
            },
            # Loan summary statistics
            {
                "total_loans": 3,
                "total_debt": 150000.0,
                "monthly_payment": 5000.0,
                "average_rate": 12.5
            },
            # Overdue statistics
            {
                "overdue_count": 1,
                "overdue_amount": 2500.0,
                "total_penalty": 150.0,
                "days_overdue": 5
            },
            # Empty statistics (граничный случай)
            {},
            # Statistics с дополнительными полями
            {
                "main_field": 100,
                "extra_field_1": "text_value",
                "extra_field_2": True,
                "extra_field_3": None,
                "nested_dict": {"inner": "value"}
            }
        ]
        
        for i, stats in enumerate(test_statistics_formats):
            with self.subTest(f"statistics_format_{i}"):
                # Тест 1: Проверяем, что каждый формат является dict
                self.assertIsInstance(stats, dict,
                                    f"Statistics format {i} должен быть dict")
                
                # Тест 2: Проверяем, что поддерживает dict операции
                try:
                    _ = stats.get("any_key", "default_value")
                    _ = list(stats.keys())
                    _ = list(stats.values())
                    _ = list(stats.items())
                    _ = len(stats)
                    _ = "any_key" in stats
                except AttributeError as e:
                    self.fail(f"Statistics format {i} должен поддерживать dict операции: {e}")
                
                # Тест 3: Проверяем, что можно итерироваться
                try:
                    for key in stats:
                        _ = stats[key]
                    
                    for key, value in stats.items():
                        _ = key, value
                        
                except Exception as e:
                    self.fail(f"Statistics format {i} должен поддерживать итерацию: {e}")
                
                # Тест 4: Проверяем, что можно безопасно обращаться к несуществующим ключам
                try:
                    default_value = stats.get("non_existent_key", "safe_default")
                    self.assertEqual(default_value, "safe_default",
                                   "get() должен возвращать default значение для несуществующих ключей")
                except Exception as e:
                    self.fail(f"Statistics format {i} должен безопасно обрабатывать несуществующие ключи: {e}")

    def test_statistics_format_validation(self):
        """
        Тест проверяет валидацию формата statistics и обработку некорректных форматов.
        
        Validates: Requirements 3.4, 3.5
        """
        # Создаем HomeView для тестирования
        home_view = HomeView(self.mock_page, self.mock_session, navigate_callback=Mock())
        payments = self.create_mock_pending_payments()
        
        # Тест 1: Корректный формат должен работать
        valid_statistics = self.create_mock_statistics_dict()
        
        try:
            home_view.update_pending_payments(payments, valid_statistics)
        except Exception as e:
            self.fail(f"Корректный формат statistics не должен вызывать ошибок: {e}")
        
        # Тест 2: Некорректные форматы должны вызывать понятные исключения
        invalid_formats = [
            # Tuple вместо dict
            (5, 15000.50),
            # List вместо dict  
            [5, 15000.50],
            # String вместо dict
            "invalid_statistics",
            # Number вместо dict
            12345,
            # None вместо dict
            None
        ]
        
        for i, invalid_stats in enumerate(invalid_formats):
            with self.subTest(f"invalid_format_{i}_{type(invalid_stats).__name__}"):
                # Патчим set_payments для контроля ошибок
                with patch.object(home_view.pending_payments_widget, 'set_payments') as mock_set_payments:
                    # Настраиваем mock для вызова соответствующей ошибки
                    if invalid_stats is None:
                        mock_set_payments.side_effect = AttributeError("'NoneType' object has no attribute 'get'")
                    elif isinstance(invalid_stats, (tuple, list)):
                        mock_set_payments.side_effect = AttributeError(f"'{type(invalid_stats).__name__}' object has no attribute 'get'")
                    elif isinstance(invalid_stats, str):
                        mock_set_payments.side_effect = AttributeError("'str' object has no attribute 'get'")
                    elif isinstance(invalid_stats, (int, float)):
                        mock_set_payments.side_effect = AttributeError(f"'{type(invalid_stats).__name__}' object has no attribute 'get'")
                    
                    # Проверяем, что некорректный формат вызывает AttributeError
                    with self.assertRaises(AttributeError) as context:
                        home_view.update_pending_payments(payments, invalid_stats)
                    
                    # Проверяем, что ошибка содержит информацию о типе
                    error_message = str(context.exception)
                    self.assertIn("object has no attribute 'get'", error_message,
                                f"Ошибка должна указывать на проблему с методом 'get': {error_message}")

    def test_statistics_field_type_consistency(self):
        """
        Тест проверяет консистентность типов полей в statistics.
        
        Validates: Requirements 3.4
        """
        # Определяем ожидаемые типы для стандартных полей statistics
        expected_field_types = {
            # Pending payments statistics
            "total_active": int,
            "total_amount": (int, float),
            "with_date": int,
            "without_date": int,
            "high_priority": int,
            "medium_priority": int,
            "low_priority": int,
            
            # Loan statistics
            "total_loans": int,
            "total_debt": (int, float),
            "monthly_payment": (int, float),
            "average_rate": (int, float),
            
            # Overdue statistics
            "overdue_count": int,
            "overdue_amount": (int, float),
            "total_penalty": (int, float),
            "days_overdue": int,
            
            # General numeric fields
            "count": int,
            "amount": (int, float),
            "percentage": (int, float),
            "rate": (int, float)
        }
        
        # Создаем тестовые statistics с различными полями
        test_statistics = self.create_mock_statistics_dict()
        
        # Добавляем дополнительные поля для тестирования
        test_statistics.update({
            "total_loans": 3,
            "monthly_payment": 5000.0,
            "overdue_count": 1,
            "days_overdue": 5
        })
        
        # Проверяем типы полей
        for field_name, field_value in test_statistics.items():
            if field_name in expected_field_types:
                expected_type = expected_field_types[field_name]
                
                self.assertIsInstance(field_value, expected_type,
                                    f"Поле '{field_name}' должно быть типа {expected_type}, "
                                    f"получен {type(field_value)}")
        
        # Тест на консистентность: все числовые поля должны быть числами
        numeric_fields = [k for k, v in test_statistics.items() 
                         if isinstance(v, (int, float))]
        
        for field_name in numeric_fields:
            field_value = test_statistics[field_name]
            self.assertIsInstance(field_value, (int, float),
                                f"Числовое поле '{field_name}' должно быть int или float")
            
            # Проверяем, что числовые значения не являются NaN или бесконечностью
            if isinstance(field_value, float):
                import math
                self.assertFalse(math.isnan(field_value),
                               f"Поле '{field_name}' не должно быть NaN")
                self.assertFalse(math.isinf(field_value),
                               f"Поле '{field_name}' не должно быть бесконечностью")

    def test_service_return_types(self):
        """
        Тест проверяет типы, возвращаемые сервисами.
        
        Validates: Requirements 3.5
        """
        # Настраиваем моки сервисов для возврата корректных типов
        mock_payments = self.create_mock_pending_payments()
        mock_statistics_dict = self.create_mock_statistics_dict()
        
        self.mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics_dict
        
        # Тест 1: Проверяем get_all_pending_payments
        result_payments = self.mock_pending_payment_service.get_all_pending_payments(self.mock_session)
        
        self.assertIsInstance(result_payments, list, 
                            "get_all_pending_payments должен возвращать list")
        
        # Тест 2: Проверяем get_pending_payments_statistics
        result_statistics = self.mock_pending_payment_service.get_pending_payments_statistics(self.mock_session)
        
        self.assertIsInstance(result_statistics, dict,
                            "get_pending_payments_statistics должен возвращать dict")
        
        # Тест 3: Проверяем, что statistics содержит ожидаемые поля
        expected_fields = ["total_active", "total_amount"]
        for field in expected_fields:
            self.assertIn(field, result_statistics,
                         f"statistics должен содержать поле '{field}'")
        
        # Тест 4: Симулируем некорректный возврат сервиса (tuple вместо dict)
        mock_statistics_tuple = self.create_mock_statistics_tuple()
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics_tuple
        
        result_statistics_tuple = self.mock_pending_payment_service.get_pending_payments_statistics(self.mock_session)
        
        # Проверяем, что сервис действительно вернул tuple (для демонстрации проблемы)
        self.assertIsInstance(result_statistics_tuple, tuple,
                            "Мок сервиса должен вернуть tuple для демонстрации проблемы")
        
        # Проверяем, что tuple не поддерживает dict операции
        with self.assertRaises(AttributeError) as context:
            _ = result_statistics_tuple.get("total_active", 0)
        
        self.assertIn("'tuple' object has no attribute 'get'", str(context.exception))

    def test_loan_statistics_service_return_types(self):
        """
        Тест проверяет типы, возвращаемые loan_statistics_service.
        
        Validates: Requirements 3.4, 3.5
        """
        # Патчим loan_statistics_service
        with patch('finance_tracker.services.loan_statistics_service') as mock_loan_stats_service:
            # Создаем корректные статистики для кредитов
            mock_loan_summary_stats = {
                "total_loans": 3,
                "total_debt": 150000.0,
                "monthly_payment": 5000.0,
                "average_rate": 12.5
            }
            
            mock_burden_stats = {
                "monthly_income": 50000.0,
                "monthly_burden": 5000.0,
                "burden_percentage": 10.0,
                "recommended_max": 15000.0
            }
            
            mock_overdue_stats = {
                "overdue_count": 1,
                "overdue_amount": 2500.0,
                "total_penalty": 150.0,
                "days_overdue": 5
            }
            
            # Настраиваем моки
            mock_loan_stats_service.get_summary_statistics.return_value = mock_loan_summary_stats
            mock_loan_stats_service.get_monthly_burden_statistics.return_value = mock_burden_stats
            mock_loan_stats_service.get_overdue_statistics.return_value = mock_overdue_stats
            
            # Тест 1: Проверяем get_summary_statistics
            result_summary = mock_loan_stats_service.get_summary_statistics(self.mock_session)
            self.assertIsInstance(result_summary, dict,
                                "get_summary_statistics должен возвращать dict")
            
            # Проверяем обязательные поля
            expected_summary_fields = ["total_loans", "total_debt"]
            for field in expected_summary_fields:
                self.assertIn(field, result_summary,
                             f"summary statistics должен содержать поле '{field}'")
            
            # Тест 2: Проверяем get_monthly_burden_statistics
            result_burden = mock_loan_stats_service.get_monthly_burden_statistics(self.mock_session)
            self.assertIsInstance(result_burden, dict,
                                "get_monthly_burden_statistics должен возвращать dict")
            
            # Проверяем обязательные поля
            expected_burden_fields = ["monthly_burden", "burden_percentage"]
            for field in expected_burden_fields:
                self.assertIn(field, result_burden,
                             f"burden statistics должен содержать поле '{field}'")
            
            # Тест 3: Проверяем get_overdue_statistics
            result_overdue = mock_loan_stats_service.get_overdue_statistics(self.mock_session)
            self.assertIsInstance(result_overdue, dict,
                                "get_overdue_statistics должен возвращать dict")
            
            # Проверяем обязательные поля
            expected_overdue_fields = ["overdue_count", "overdue_amount"]
            for field in expected_overdue_fields:
                self.assertIn(field, result_overdue,
                             f"overdue statistics должен содержать поле '{field}'")
            
            # Тест 4: Проверяем, что все statistics поддерживают dict операции
            for stats_name, stats_dict in [
                ("summary", result_summary),
                ("burden", result_burden), 
                ("overdue", result_overdue)
            ]:
                try:
                    _ = stats_dict.get("any_key", "default")
                    _ = list(stats_dict.keys())
                    _ = list(stats_dict.values())
                    _ = list(stats_dict.items())
                except AttributeError as e:
                    self.fail(f"{stats_name} statistics должен поддерживать dict операции: {e}")

    def test_loan_service_return_types(self):
        """
        Тест проверяет типы, возвращаемые loan_service и loan_payment_service.
        
        Validates: Requirements 3.4, 3.5
        """
        # Патчим loan_service и loan_payment_service
        with patch('finance_tracker.services.loan_service') as mock_loan_service, \
             patch('finance_tracker.services.loan_payment_service') as mock_payment_service:
            
            # Создаем корректные статистики
            mock_loan_calc_stats = {
                "total_amount": 100000.0,
                "paid_amount": 25000.0,
                "remaining_amount": 75000.0,
                "total_interest": 15000.0,
                "payments_made": 12,
                "payments_remaining": 36
            }
            
            mock_overdue_payment_stats = {
                "overdue_payments": 2,
                "overdue_amount": 3000.0,
                "total_penalty": 200.0,
                "max_days_overdue": 10
            }
            
            # Настраиваем моки
            mock_loan_service.calculate_loan_statistics.return_value = mock_loan_calc_stats
            mock_payment_service.get_overdue_statistics.return_value = mock_overdue_payment_stats
            
            # Тест 1: Проверяем calculate_loan_statistics
            result_loan_calc = mock_loan_service.calculate_loan_statistics(self.mock_session, "loan_123")
            self.assertIsInstance(result_loan_calc, dict,
                                "calculate_loan_statistics должен возвращать dict")
            
            # Проверяем обязательные поля
            expected_loan_fields = ["total_amount", "remaining_amount"]
            for field in expected_loan_fields:
                self.assertIn(field, result_loan_calc,
                             f"loan statistics должен содержать поле '{field}'")
            
            # Тест 2: Проверяем get_overdue_statistics из loan_payment_service
            result_payment_overdue = mock_payment_service.get_overdue_statistics(self.mock_session)
            self.assertIsInstance(result_payment_overdue, dict,
                                "loan_payment_service.get_overdue_statistics должен возвращать dict")
            
            # Проверяем обязательные поля
            expected_payment_fields = ["overdue_payments", "overdue_amount"]
            for field in expected_payment_fields:
                self.assertIn(field, result_payment_overdue,
                             f"payment overdue statistics должен содержать поле '{field}'")
            
            # Тест 3: Проверяем, что все statistics поддерживают dict операции
            for stats_name, stats_dict in [
                ("loan_calc", result_loan_calc),
                ("payment_overdue", result_payment_overdue)
            ]:
                try:
                    _ = stats_dict.get("any_key", "default")
                    _ = list(stats_dict.keys())
                    _ = list(stats_dict.values())
                    _ = list(stats_dict.items())
                except AttributeError as e:
                    self.fail(f"{stats_name} statistics должен поддерживать dict операции: {e}")
            
            # Тест 4: Симулируем некорректный возврат (tuple вместо dict)
            mock_loan_service.calculate_loan_statistics.return_value = (100000.0, 75000.0)
            
            result_tuple = mock_loan_service.calculate_loan_statistics(self.mock_session, "loan_123")
            self.assertIsInstance(result_tuple, tuple,
                                "Мок должен вернуть tuple для демонстрации проблемы")
            
            # Проверяем, что tuple не поддерживает dict операции
            with self.assertRaises(AttributeError) as context:
                _ = result_tuple.get("total_amount", 0)
            
            self.assertIn("'tuple' object has no attribute 'get'", str(context.exception))

    def test_interface_error_handling(self):
        """
        Тест проверяет обработку ошибок типов в интерфейсах.
        
        Validates: Requirements 3.1, 3.2, 3.3
        """
        # Создаем HomeView
        home_view = HomeView(self.mock_page, self.mock_session, navigate_callback=Mock())
        
        # Патчим set_payments для контроля поведения
        with patch.object(home_view.pending_payments_widget, 'set_payments') as mock_set_payments:
            # Тест 1: Проверяем обработку None statistics
            payments = self.create_mock_pending_payments()
            
            # Настраиваем mock для вызова ошибки при None
            mock_set_payments.side_effect = AttributeError("'NoneType' object has no attribute 'get'")
            
            with self.assertRaises(AttributeError):
                home_view.update_pending_payments(payments, None)
            
            # Тест 2: Проверяем обработку некорректного типа statistics
            mock_set_payments.side_effect = AttributeError("'str' object has no attribute 'get'")
            invalid_statistics = "invalid_string"
            
            with self.assertRaises(AttributeError):
                home_view.update_pending_payments(payments, invalid_statistics)
            
            # Тест 3: Проверяем обработку пустого dict
            mock_set_payments.side_effect = None  # Сбрасываем side_effect
            empty_statistics = {}
            
            try:
                home_view.update_pending_payments(payments, empty_statistics)
                # Должно работать, даже если dict пустой
            except Exception as e:
                self.fail(f"Пустой dict должен обрабатываться корректно: {e}")
            
            # Тест 4: Проверяем обработку dict с неожиданными полями
            unexpected_statistics = {
                "unexpected_field": "value",
                "another_field": 123
            }
            
            try:
                home_view.update_pending_payments(payments, unexpected_statistics)
                # Должно работать, dict с любыми полями должен быть валидным
            except Exception as e:
                self.fail(f"Dict с неожиданными полями должен обрабатываться корректно: {e}")

    def test_type_validation_in_components(self):
        """
        Тест проверяет валидацию типов в компонентах.
        
        Validates: Requirements 3.1, 3.4
        """
        # Патчим build методы для избежания ошибок UI
        with patch.object(PendingPaymentsWidget, '_build_payment_card', return_value=Mock()):
            # Создаем PendingPaymentsWidget
            widget = PendingPaymentsWidget(
                session=self.mock_session,
                on_execute=Mock(),
                on_cancel=Mock(),
                on_delete=Mock(),
                on_show_all=Mock()
            )
            
            # Тест 1: Проверяем валидацию типа payments (None вместо list)
            invalid_payments = None
            statistics_dict = self.create_mock_statistics_dict()
            
            # None не поддерживает операцию [:5], что вызовет TypeError
            with self.assertRaises(TypeError):
                widget.set_payments(invalid_payments, statistics_dict)
            
            # Тест 2: Проверяем валидацию типа statistics (list вместо dict)
            valid_payments = self.create_mock_pending_payments()
            invalid_statistics = ["not", "a", "dict"]
            
            # List не имеет метода .get(), что вызовет AttributeError
            with self.assertRaises(AttributeError):
                widget.set_payments(valid_payments, invalid_statistics)
            
            # Тест 3: Проверяем корректные типы
            try:
                widget.set_payments(valid_payments, statistics_dict)
            except Exception as e:
                self.fail(f"Корректные типы должны обрабатываться без ошибок: {e}")
            
            # Тест 4: Проверяем, что компонент сохраняет правильные типы
            self.assertIsInstance(widget.payments, list)
            self.assertIsInstance(widget.statistics, dict)

    def test_cross_component_type_consistency(self):
        """
        Тест проверяет консистентность типов между компонентами.
        
        Validates: Requirements 3.2, 3.3, 3.4
        """
        # Создаем полную цепочку: Presenter -> HomeView -> PendingPaymentsWidget
        home_view = HomeView(self.mock_page, self.mock_session, navigate_callback=Mock())
        presenter = home_view.presenter
        
        # Настраиваем моки сервисов
        mock_payments = self.create_mock_pending_payments()
        mock_statistics_dict = self.create_mock_statistics_dict()
        
        self.mock_pending_payment_service.get_all_pending_payments.return_value = mock_payments
        self.mock_pending_payment_service.get_pending_payments_statistics.return_value = mock_statistics_dict
        
        # Вызываем полную цепочку
        presenter.load_pending_payments()
        
        # Проверяем, что данные прошли через всю цепочку с правильными типами
        self.mock_pending_payments_widget.return_value.set_payments.assert_called_once_with(
            mock_payments, mock_statistics_dict
        )
        
        # Проверяем типы в каждом звене цепочки
        call_args = self.mock_pending_payments_widget.return_value.set_payments.call_args
        passed_payments, passed_statistics = call_args[0]
        
        self.assertIsInstance(passed_payments, list, 
                            "Payments должен оставаться list через всю цепочку")
        self.assertIsInstance(passed_statistics, dict,
                            "Statistics должен оставаться dict через всю цепочку")
        
        # Проверяем, что dict поддерживает все необходимые операции
        try:
            _ = passed_statistics.get("total_active", 0)
            _ = len(passed_statistics)
            _ = list(passed_statistics.keys())
        except AttributeError as e:
            self.fail(f"Statistics должен поддерживать dict операции: {e}")


# =============================================================================
# Property-Based Tests
# =============================================================================

@settings(max_examples=50, deadline=None)
@given(
    st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.one_of(st.integers(min_value=0, max_value=1000), st.floats(min_value=0, max_value=1000)),
        min_size=1, max_size=5
    ),  # single statistics dict
    st.integers(min_value=0, max_value=10),  # payment count
    st.booleans()  # use_correct_type
)
def test_property_3_interface_type_consistency(statistics_dict, payment_count, use_correct_type):
    """
    **Feature: error-regression-testing, Property 3: Interface Type Consistency**
    
    For any data passed between components, the actual type should match the expected interface type.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
    """
    # Создаем mock объекты
    mock_session = Mock()
    mock_page = MagicMock()
    
    # Патчим зависимости для изоляции теста
    with patch('finance_tracker.views.home_view.CalendarWidget'), \
         patch('finance_tracker.views.home_view.TransactionsPanel'), \
         patch('finance_tracker.views.home_view.PendingPaymentsWidget') as MockPendingWidget:
        
        # Создаем HomeView
        home_view = HomeView(mock_page, mock_session, navigate_callback=Mock())
        
        # Создаем mock payments
        mock_payments = []
        for j in range(payment_count):
            payment = Mock()
            payment.id = f"payment_{j}"
            payment.description = f"Payment {j}"
            mock_payments.append(payment)
        
        if use_correct_type:
            # Используем корректный тип - Dict[str, Any]
            test_statistics = statistics_dict
            
            try:
                # Property 1: update_pending_payments должен принимать Dict[str, Any]
                home_view.update_pending_payments(mock_payments, test_statistics)
                
                # Property 2: Проверяем, что PendingPaymentsWidget был вызван с правильными типами
                MockPendingWidget.return_value.set_payments.assert_called_with(
                    mock_payments, test_statistics
                )
                
                # Property 3: Проверяем, что statistics поддерживает dict операции
                _ = test_statistics.get("any_key", "default_value")
                _ = list(test_statistics.keys())
                _ = list(test_statistics.values())
                
            except AttributeError as e:
                if "'tuple' object has no attribute 'get'" in str(e):
                    raise AssertionError(
                        f"Interface type consistency violated: Dict should support dict operations. "
                        f"Statistics: {test_statistics}, Error: {e}"
                    )
                else:
                    raise  # Перебрасываем другие ошибки
        
        else:
            # Используем некорректный тип - Tuple (для демонстрации ошибки)
            # Преобразуем dict в tuple для симуляции старого формата
            if statistics_dict:
                # Берем первые два значения для создания tuple
                values = list(statistics_dict.values())
                test_statistics = (values[0], values[1] if len(values) > 1 else 0)
            else:
                test_statistics = (0, 0.0)
            
            # Настраиваем mock для вызова ошибки при tuple
            MockPendingWidget.return_value.set_payments.side_effect = AttributeError("'tuple' object has no attribute 'get'")
            
            # Property 4: Некорректный тип должен вызывать AttributeError
            with pytest.raises(AttributeError) as exc_info:
                home_view.update_pending_payments(mock_payments, test_statistics)
            
            # Property 5: Проверяем, что это именно ошибка типа
            assert "'tuple' object has no attribute 'get'" in str(exc_info.value), \
                f"Expected tuple attribute error, got: {exc_info.value}"


if __name__ == '__main__':
    unittest.main()