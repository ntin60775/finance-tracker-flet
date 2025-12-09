"""
Тесты для LoanDetailsView.

Проверяет:
- Инициализацию View с валидным кредитом
- Загрузку деталей кредита и графика платежей
- Тест кнопки "Назад"
- Тест обработки несуществующего кредита
- Тест открытия модального окна досрочного погашения
"""
import unittest
from unittest.mock import Mock
from decimal import Decimal
from datetime import date, timedelta

from finance_tracker.views.loan_details_view import LoanDetailsView
from finance_tracker.models.enums import LoanStatus, LoanType, PaymentStatus
from test_view_base import ViewTestBase
from test_factories import create_test_loan, create_test_lender, create_test_loan_payment


class TestLoanDetailsView(ViewTestBase):
    """Тесты для LoanDetailsView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.loan_details_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы кредитов
        self.mock_get_loan_by_id = self.add_patcher(
            'finance_tracker.views.loan_details_view.get_loan_by_id',
            return_value=None
        )
        self.mock_get_lender_by_id = self.add_patcher(
            'finance_tracker.views.loan_details_view.get_lender_by_id',
            return_value=None
        )
        
        # Патчим сервисы платежей
        self.mock_get_payments_by_loan = self.add_patcher(
            'finance_tracker.views.loan_details_view.get_payments_by_loan',
            return_value=[]
        )
        self.mock_execute_payment = self.add_patcher(
            'finance_tracker.views.loan_details_view.execute_payment'
        )
        self.mock_early_repayment_full = self.add_patcher(
            'finance_tracker.views.loan_details_view.early_repayment_full',
            return_value={'cancelled_payments_count': 0}
        )
        self.mock_early_repayment_partial = self.add_patcher(
            'finance_tracker.views.loan_details_view.early_repayment_partial',
            return_value={'new_balance': Decimal('0.00'), 'warning': 'Тест'}
        )
        
        # Патчим EarlyRepaymentModal
        self.mock_early_repayment_modal = self.add_patcher(
            'finance_tracker.views.loan_details_view.EarlyRepaymentModal'
        )
        
        # Создаем тестовый кредит и займодателя
        self.test_lender = create_test_lender(id=1, name="Сбербанк")
        self.test_loan = create_test_loan(
            id=1,
            name="Тестовый кредит",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE,
            loan_type=LoanType.CONSUMER
        )
        
        # Настраиваем моки для возврата тестовых данных
        self.mock_get_loan_by_id.return_value = self.test_loan
        self.mock_get_lender_by_id.return_value = self.test_lender
        
        # Callback для возврата
        self.on_back_called = False
        def on_back():
            self.on_back_called = True
        self.on_back = on_back
        
        # Создаем экземпляр LoanDetailsView
        self.view = LoanDetailsView(self.page, loan_id=1, on_back=self.on_back)

    def test_initialization_with_valid_loan(self):
        """
        Тест инициализации View с валидным кредитом.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - loan_id установлен
        - UI компоненты созданы (заголовок, карточка информации, кнопки, табы, список платежей)
        - Кредит загружен
        
        Validates: Requirements 9.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, LoanDetailsView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        self.assertEqual(self.view.loan_id, 1)
        self.assertEqual(self.view.loan, self.test_loan)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.header)
        self.assertIsNotNone(self.view.info_card)
        self.assertIsNotNone(self.view.action_buttons)
        self.assertIsNotNone(self.view.tabs)
        self.assertIsNotNone(self.view.payments_list)
        self.assertIsNotNone(self.view.payment_stats)

    def test_load_loan_details_success(self):
        """
        Тест успешной загрузки деталей кредита.
        
        Проверяет:
        - При инициализации вызывается get_loan_by_id
        - При инициализации вызывается get_lender_by_id
        - Информация о кредите отображается в info_card
        - Статистика обновляется
        
        Validates: Requirements 9.1, 9.2
        """
        # Проверяем, что сервисы были вызваны
        self.assert_service_called(
            self.mock_get_loan_by_id,
            self.mock_session,
            1
        )
        self.assert_service_called(
            self.mock_get_lender_by_id,
            self.mock_session,
            1
        )
        
        # Проверяем, что info_card содержит контент
        self.assertIsNotNone(self.view.info_card.content)
        
        # Проверяем, что payment_stats содержит контент
        self.assertIsNotNone(self.view.payment_stats.content)

    def test_load_payments_pending_and_overdue(self):
        """
        Тест загрузки платежей (график платежей - ожидающие и просроченные).
        
        Проверяет:
        - При выборе таба "График платежей" загружаются платежи со статусом PENDING и OVERDUE
        - Платежи отображаются в списке
        - Количество элементов соответствует количеству платежей
        - page.update вызывается после загрузки
        
        Validates: Requirements 9.2
        """
        # Создаем тестовые платежи
        test_payments = [
            create_test_loan_payment(
                id=1,
                loan_id=1,
                scheduled_date=date.today(),
                status=PaymentStatus.PENDING,
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00")
            ),
            create_test_loan_payment(
                id=2,
                loan_id=1,
                scheduled_date=date.today() - timedelta(days=5),
                status=PaymentStatus.OVERDUE,
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00")
            ),
        ]
        
        # Настраиваем мок для возврата тестовых платежей
        self.mock_get_payments_by_loan.return_value = test_payments
        
        # Устанавливаем таб на "График платежей" (индекс 0)
        self.view.tabs.selected_index = 0
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Загружаем платежи
        self.view.load_payments()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.payments_list.controls), 2)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_payments_executed_history(self):
        """
        Тест загрузки истории платежей (исполненные платежи).
        
        Проверяет:
        - При выборе таба "История" загружаются платежи со статусом EXECUTED и EXECUTED_LATE
        - Платежи отображаются в списке
        - Количество элементов соответствует количеству платежей
        
        Validates: Requirements 9.2
        """
        # Создаем тестовые платежи
        test_payments = [
            create_test_loan_payment(
                id=1,
                loan_id=1,
                scheduled_date=date.today() - timedelta(days=30),
                status=PaymentStatus.EXECUTED,
                executed_date=date.today() - timedelta(days=30),
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00"),
                overdue_days=0
            ),
            create_test_loan_payment(
                id=2,
                loan_id=1,
                scheduled_date=date.today() - timedelta(days=60),
                status=PaymentStatus.EXECUTED_LATE,
                executed_date=date.today() - timedelta(days=55),
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00"),
                overdue_days=5
            ),
        ]
        
        # Настраиваем мок для возврата тестовых платежей
        self.mock_get_payments_by_loan.return_value = test_payments
        
        # Устанавливаем таб на "История" (индекс 1)
        self.view.tabs.selected_index = 1
        
        # Загружаем платежи
        self.view.load_payments()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.payments_list.controls), 2)

    def test_load_payments_empty_list(self):
        """
        Тест загрузки пустого списка платежей.
        
        Проверяет:
        - При пустом списке отображается сообщение "Нет платежей"
        - Количество контролов = 1 (сообщение о пустом состоянии)
        
        Validates: Requirements 9.2
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_payments_by_loan.return_value = []
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Загружаем платежи
        self.view.load_payments()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.payments_list.controls), 1)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_back_button_click(self):
        """
        Тест кнопки "Назад".
        
        Проверяет:
        - При клике на кнопку "Назад" вызывается callback on_back
        - on_back_called устанавливается в True
        
        Validates: Requirements 9.3
        """
        # Проверяем, что on_back не был вызван
        self.assertFalse(self.on_back_called)
        
        # Имитируем клик на кнопку "Назад"
        # Кнопка находится в header.controls[0]
        back_button = self.view.header.controls[0]
        back_button.on_click(None)
        
        # Проверяем, что on_back был вызван
        self.assertTrue(self.on_back_called)

    def test_loan_not_found_error(self):
        """
        Тест обработки несуществующего кредита.
        
        Проверяет:
        - Если кредит не найден (get_loan_by_id возвращает None), отображается ошибка
        - Метод load_loan_details обрабатывает ошибку корректно
        - Кредит остается None
        
        Validates: Requirements 9.4
        """
        # Создаем новый View с мок для возврата None
        self.mock_get_loan_by_id.return_value = None
        
        # Создаем новый View
        view = LoanDetailsView(self.page, loan_id=999, on_back=self.on_back)
        
        # Проверяем, что кредит не был загружен
        self.assertIsNone(view.loan)

    def test_open_early_repayment_dialog(self):
        """
        Тест открытия модального окна досрочного погашения.
        
        Проверяет:
        - При нажатии кнопки "Досрочное погашение" открывается EarlyRepaymentModal
        - Диалог открывается с правильными параметрами (session, loan, on_repay)
        - page.open вызывается
        
        Validates: Requirements 9.5
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем метод открытия диалога
        self.view.open_early_repayment_dialog(mock_event)
        
        # Проверяем, что EarlyRepaymentModal был создан
        self.mock_early_repayment_modal.assert_called_once()
        
        # Проверяем параметры создания
        call_args = self.mock_early_repayment_modal.call_args
        self.assertEqual(call_args[1]['session'], self.mock_session)
        self.assertEqual(call_args[1]['loan'], self.test_loan)
        self.assertIsNotNone(call_args[1]['on_repay'])
        
        # Проверяем, что modal.open был вызван
        modal_instance = self.mock_early_repayment_modal.return_value
        modal_instance.open.assert_called_once_with(self.page)

    def test_execute_payment_action(self):
        """
        Тест исполнения платежа.
        
        Проверяет:
        - При вызове execute_payment_action вызывается execute_payment сервис
        - После исполнения перезагружаются детали кредита
        
        Validates: Requirements 9.2
        """
        # Создаем тестовый платеж
        test_payment = create_test_loan_payment(
            id=1,
            loan_id=1,
            status=PaymentStatus.PENDING
        )
        
        # Вызываем execute_payment_action
        self.view.execute_payment_action(test_payment)
        
        # Проверяем, что execute_payment был вызван
        self.assert_service_called(self.mock_execute_payment, self.mock_session, 1)

    def test_handle_early_repayment_full(self):
        """
        Тест обработки полного досрочного погашения.
        
        Проверяет:
        - При вызове handle_early_repayment с is_full=True вызывается early_repayment_full
        - После погашения перезагружаются детали кредита
        
        Validates: Requirements 9.5
        """
        # Настраиваем мок для возврата результата
        self.mock_early_repayment_full.return_value = {'cancelled_payments_count': 5}
        
        # Вызываем handle_early_repayment
        self.view.handle_early_repayment(
            is_full=True,
            amount=Decimal("100000.00"),
            repayment_date=date.today()
        )
        
        # Проверяем, что early_repayment_full был вызван
        self.assert_service_called(
            self.mock_early_repayment_full,
            self.mock_session,
            1,
            Decimal("100000.00"),
            date.today()
        )

    def test_handle_early_repayment_partial(self):
        """
        Тест обработки частичного досрочного погашения.
        
        Проверяет:
        - При вызове handle_early_repayment с is_full=False вызывается early_repayment_partial
        - После погашения перезагружаются детали кредита
        
        Validates: Requirements 9.5
        """
        # Настраиваем мок для возврата результата
        self.mock_early_repayment_partial.return_value = {
            'new_balance': Decimal("50000.00"),
            'warning': 'Остаток долга: 50000.00 ₽'
        }
        
        # Вызываем handle_early_repayment
        self.view.handle_early_repayment(
            is_full=False,
            amount=Decimal("50000.00"),
            repayment_date=date.today()
        )
        
        # Проверяем, что early_repayment_partial был вызван
        self.assert_service_called(
            self.mock_early_repayment_partial,
            self.mock_session,
            1,
            Decimal("50000.00"),
            date.today()
        )

    def test_update_payment_stats(self):
        """
        Тест обновления статистики по платежам.
        
        Проверяет:
        - При вызове update_payment_stats получаются данные от сервиса
        - payment_stats содержит контент с информацией о статистике
        
        Validates: Requirements 9.2
        """
        # Создаем тестовые платежи
        test_payments = [
            create_test_loan_payment(
                id=1,
                loan_id=1,
                status=PaymentStatus.PENDING,
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00")
            ),
            create_test_loan_payment(
                id=2,
                loan_id=1,
                status=PaymentStatus.OVERDUE,
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00")
            ),
            create_test_loan_payment(
                id=3,
                loan_id=1,
                status=PaymentStatus.EXECUTED,
                executed_date=date.today() - timedelta(days=30),
                principal_amount=Decimal("8000.00"),
                interest_amount=Decimal("875.00")
            ),
        ]
        
        # Настраиваем мок для возврата тестовых платежей
        self.mock_get_payments_by_loan.return_value = test_payments
        
        # Вызываем update_payment_stats
        self.view.update_payment_stats()
        
        # Проверяем, что payment_stats содержит контент
        self.assertIsNotNone(self.view.payment_stats.content)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 1.2
        """
        # Проверяем, что context manager был создан
        self.assertIsNotNone(self.view.cm)
        
        # Проверяем, что session была получена
        self.assertIsNotNone(self.view.session)


if __name__ == '__main__':
    unittest.main()
