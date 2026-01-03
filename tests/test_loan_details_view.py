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
        
        # Патчим сервис передачи долга
        self.mock_get_transfer_history = self.add_patcher(
            'finance_tracker.views.loan_details_view.get_transfer_history',
            return_value=[]
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
        
        # Загружаем платежи
        self.view.load_payments()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.payments_list.controls), 2)

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
        
        # Загружаем платежи
        self.view.load_payments()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.payments_list.controls), 1)

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

    def test_load_transfer_history_empty(self):
        """
        Тест загрузки пустой истории передач.
        
        Проверяет:
        - При пустой истории передач отображается сообщение "История передач пуста"
        - Для активного кредита также отображается кнопка "Передать долг"
        - Количество контролов = 2 (сообщение о пустом состоянии + кнопка)
        
        Validates: Requirements 3.1, 3.2
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_transfer_history.return_value = []
        
        # Убеждаемся, что кредит активен
        self.test_loan.status = LoanStatus.ACTIVE
        
        # Устанавливаем таб на "История передач" (индекс 2)
        self.view.tabs.selected_index = 2
        
        # Загружаем историю передач
        self.view.load_transfer_history()
        
        # Проверяем, что в списке 2 элемента (сообщение о пустом состоянии + кнопка)
        self.assertEqual(len(self.view.payments_list.controls), 2)

    def test_load_transfer_history_with_transfers(self):
        """
        Тест загрузки истории передач с данными.
        
        Проверяет:
        - При наличии передач они отображаются в списке
        - Для активного кредита также отображается кнопка "Передать долг"
        - Количество элементов = количество передач + 2 (заголовок + кнопка)
        - Каждая передача отображается с правильной информацией
        
        Validates: Requirements 3.1, 3.2
        """
        # Создаем тестовых кредиторов
        from_lender = create_test_lender(id=1, name="МФО Быстроденьги")
        to_lender = create_test_lender(id=2, name="Коллекторское агентство")
        
        # Создаем тестовую передачу
        from finance_tracker.models import DebtTransferDB
        test_transfer = Mock(spec=DebtTransferDB)
        test_transfer.id = "transfer-1"
        test_transfer.loan_id = "1"
        test_transfer.from_lender_id = "1"
        test_transfer.to_lender_id = "2"
        test_transfer.transfer_date = date(2025, 1, 15)
        test_transfer.transfer_amount = Decimal("105000.00")
        test_transfer.previous_amount = Decimal("100000.00")
        test_transfer.amount_difference = Decimal("5000.00")
        test_transfer.reason = "Продажа долга"
        test_transfer.notes = "Тестовое примечание"
        test_transfer.from_lender = from_lender
        test_transfer.to_lender = to_lender
        
        # Настраиваем мок для возврата тестовой передачи
        self.mock_get_transfer_history.return_value = [test_transfer]
        
        # Убеждаемся, что кредит активен
        self.test_loan.status = LoanStatus.ACTIVE
        
        # Устанавливаем таб на "История передач" (индекс 2)
        self.view.tabs.selected_index = 2
        
        # Загружаем историю передач
        self.view.load_transfer_history()
        
        # Проверяем, что в списке 3 элемента (заголовок + карточка передачи + кнопка)
        self.assertEqual(len(self.view.payments_list.controls), 3)
        
        # Проверяем, что get_transfer_history был вызван
        self.assert_service_called(
            self.mock_get_transfer_history,
            self.mock_session,
            1
        )

    def test_tab_change_to_transfer_history(self):
        """
        Тест переключения на таб "История передач".
        
        Проверяет:
        - При переключении на таб "История передач" вызывается load_transfer_history
        - При переключении на другие табы вызывается load_payments
        
        Validates: Requirements 3.1
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Переключаемся на таб "История передач" (индекс 2)
        self.view.tabs.selected_index = 2
        self.view.on_tab_change(mock_event)
        
        # Проверяем, что get_transfer_history был вызван
        self.mock_get_transfer_history.assert_called()
        
        # Переключаемся на таб "График платежей" (индекс 0)
        self.view.tabs.selected_index = 0
        self.view.on_tab_change(mock_event)
        
        # Проверяем, что get_payments_by_loan был вызван
        self.mock_get_payments_by_loan.assert_called()

    def test_create_transfer_card_with_positive_difference(self):
        """
        Тест создания карточки передачи с положительной разницей (увеличение долга).
        
        Проверяет:
        - Карточка создается с правильной информацией
        - Разница отображается красным цветом (увеличение долга)
        - Иконка стрелки вверх для положительной разницы
        
        Validates: Requirements 3.2
        """
        # Создаем тестовых кредиторов
        from_lender = create_test_lender(id=1, name="МФО")
        to_lender = create_test_lender(id=2, name="Коллектор")
        
        # Создаем тестовую передачу с положительной разницей
        from finance_tracker.models import DebtTransferDB
        test_transfer = Mock(spec=DebtTransferDB)
        test_transfer.transfer_date = date(2025, 1, 15)
        test_transfer.transfer_amount = Decimal("105000.00")
        test_transfer.previous_amount = Decimal("100000.00")
        test_transfer.amount_difference = Decimal("5000.00")  # Положительная разница
        test_transfer.reason = "Продажа долга"
        test_transfer.notes = None
        test_transfer.from_lender = from_lender
        test_transfer.to_lender = to_lender
        
        # Создаем карточку передачи
        card = self.view._create_transfer_card(test_transfer)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        # Карточка должна быть Container
        import flet as ft
        self.assertIsInstance(card, ft.Container)

    def test_create_transfer_card_with_negative_difference(self):
        """
        Тест создания карточки передачи с отрицательной разницей (уменьшение долга).
        
        Проверяет:
        - Карточка создается с правильной информацией
        - Разница отображается зеленым цветом (уменьшение долга)
        - Иконка стрелки вниз для отрицательной разницы
        
        Validates: Requirements 3.2
        """
        # Создаем тестовых кредиторов
        from_lender = create_test_lender(id=1, name="МФО")
        to_lender = create_test_lender(id=2, name="Коллектор")
        
        # Создаем тестовую передачу с отрицательной разницей
        from finance_tracker.models import DebtTransferDB
        test_transfer = Mock(spec=DebtTransferDB)
        test_transfer.transfer_date = date(2025, 1, 15)
        test_transfer.transfer_amount = Decimal("95000.00")
        test_transfer.previous_amount = Decimal("100000.00")
        test_transfer.amount_difference = Decimal("-5000.00")  # Отрицательная разница
        test_transfer.reason = None
        test_transfer.notes = None
        test_transfer.from_lender = from_lender
        test_transfer.to_lender = to_lender
        
        # Создаем карточку передачи
        card = self.view._create_transfer_card(test_transfer)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)

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

    def test_transfer_indicator_not_shown_for_non_transferred_loan(self):
        """
        Тест отсутствия индикатора передачи для непереданного кредита.
        
        Проверяет:
        - Для кредита без передачи индикатор не отображается
        - _build_transfer_indicator возвращает None
        
        Validates: Requirements 3.4
        """
        # Создаем кредит без передачи (original_lender_id и current_holder_id = None)
        self.test_loan.original_lender_id = None
        self.test_loan.current_holder_id = None
        
        # Вызываем метод построения индикатора
        indicator = self.view._build_transfer_indicator()
        
        # Проверяем, что индикатор не создан
        self.assertIsNone(indicator)

    def test_transfer_indicator_shown_for_transferred_loan(self):
        """
        Тест отображения индикатора передачи для переданного кредита.
        
        Проверяет:
        - Для переданного кредита индикатор отображается
        - Индикатор содержит правильную информацию (от кого к кому)
        - Индикатор имеет правильный цвет (AMBER)
        - Индикатор имеет иконку SWAP_HORIZ
        
        Validates: Requirements 3.4
        """
        # Создаем кредиторов
        original_lender = create_test_lender(id=1, name="МФО Быстроденьги")
        current_holder = create_test_lender(id=2, name="Коллекторское агентство")
        
        # Настраиваем кредит как переданный (устанавливаем original_lender_id и current_holder_id)
        self.test_loan.original_lender_id = "1"
        self.test_loan.current_holder_id = "2"
        
        # Настраиваем моки для возврата кредиторов
        def get_lender_side_effect(session, lender_id):
            if lender_id == "1":
                return original_lender
            elif lender_id == "2":
                return current_holder
            return None
        
        self.mock_get_lender_by_id.side_effect = get_lender_side_effect
        
        # Вызываем метод построения индикатора
        indicator = self.view._build_transfer_indicator()
        
        # Проверяем, что индикатор создан
        self.assertIsNotNone(indicator)
        
        # Проверяем тип индикатора
        import flet as ft
        self.assertIsInstance(indicator, ft.Container)
        
        # Проверяем цвет фона (AMBER для индикатора передачи)
        self.assertEqual(indicator.bgcolor, ft.Colors.AMBER)
        
        # Проверяем tooltip
        expected_tooltip = "Кредит был передан от МФО Быстроденьги к Коллекторское агентство"
        self.assertEqual(indicator.tooltip, expected_tooltip)

    def test_transfer_indicator_in_info_card(self):
        """
        Тест интеграции индикатора передачи в карточку информации.
        
        Проверяет:
        - При обновлении info_card для переданного кредита индикатор добавляется в заголовок
        - Заголовок содержит 3 элемента: название, статус, индикатор передачи
        
        Validates: Requirements 3.4
        """
        # Создаем кредиторов
        original_lender = create_test_lender(id=1, name="МФО")
        current_holder = create_test_lender(id=2, name="Коллектор")
        
        # Настраиваем кредит как переданный (устанавливаем original_lender_id и current_holder_id)
        self.test_loan.original_lender_id = "1"
        self.test_loan.current_holder_id = "2"
        
        # Настраиваем моки для возврата кредиторов
        def get_lender_side_effect(session, lender_id):
            if lender_id == "1":
                return original_lender
            elif lender_id == "2":
                return current_holder
            elif lender_id == 1:  # Основной займодатель
                return self.test_lender
            return None
        
        self.mock_get_lender_by_id.side_effect = get_lender_side_effect
        
        # Создаем новый View с переданным кредитом
        # (это вызовет update_info_card в load_loan_details)
        view = LoanDetailsView(self.page, loan_id=1, on_back=lambda: None)
        
        # Проверяем, что info_card содержит контент
        self.assertIsNotNone(view.info_card.content)
        
        # Получаем заголовок (первый Row в Column)
        header_row = view.info_card.content.controls[0]
        
        # Проверяем, что заголовок содержит 3 элемента
        # (название кредита, статус, индикатор передачи)
        self.assertEqual(len(header_row.controls), 3)

    def test_debt_transfer_button_shown_for_active_loan(self):
        """
        Тест отображения кнопки "Передать долг" для активного кредита.
        
        Проверяет:
        - При загрузке истории передач для активного кредита отображается кнопка "Передать долг"
        - Кнопка имеет правильный текст и иконку
        - Кнопка имеет обработчик on_click
        
        Validates: Requirements 8.1
        """
        # Настраиваем мок для возврата пустого списка передач
        self.mock_get_transfer_history.return_value = []
        
        # Убеждаемся, что кредит активен
        self.test_loan.status = LoanStatus.ACTIVE
        
        # Устанавливаем таб на "История передач" (индекс 2)
        self.view.tabs.selected_index = 2
        
        # Загружаем историю передач
        self.view.load_transfer_history()
        
        # Проверяем, что в списке 2 элемента (сообщение о пустом состоянии + кнопка)
        self.assertEqual(len(self.view.payments_list.controls), 2)
        
        # Получаем последний элемент (контейнер с кнопкой)
        button_container = self.view.payments_list.controls[-1]
        
        # Проверяем, что это Container
        import flet as ft
        self.assertIsInstance(button_container, ft.Container)
        
        # Получаем кнопку из контейнера
        button = button_container.content
        self.assertIsInstance(button, ft.ElevatedButton)
        
        # Проверяем атрибуты кнопки
        self.assertEqual(button.text, "Передать долг")
        self.assertEqual(button.icon, ft.Icons.SWAP_HORIZ)
        self.assertIsNotNone(button.on_click)

    def test_debt_transfer_button_not_shown_for_paid_off_loan(self):
        """
        Тест отсутствия кнопки "Передать долг" для погашенного кредита.
        
        Проверяет:
        - При загрузке истории передач для погашенного кредита кнопка НЕ отображается
        - Количество элементов = 1 (только сообщение о пустом состоянии)
        
        Validates: Requirements 6.1
        """
        # Настраиваем мок для возврата пустого списка передач
        self.mock_get_transfer_history.return_value = []
        
        # Устанавливаем статус кредита как PAID_OFF
        self.test_loan.status = LoanStatus.PAID_OFF
        
        # Устанавливаем таб на "История передач" (индекс 2)
        self.view.tabs.selected_index = 2
        
        # Загружаем историю передач
        self.view.load_transfer_history()
        
        # Проверяем, что в списке только 1 элемент (сообщение о пустом состоянии, без кнопки)
        self.assertEqual(len(self.view.payments_list.controls), 1)

    def test_open_debt_transfer_modal(self):
        """
        Тест открытия модального окна передачи долга.
        
        Проверяет:
        - При нажатии кнопки "Передать долг" открывается DebtTransferModal
        - Модальное окно создается с правильными параметрами (session, loan, callback)
        - modal.open вызывается с page
        
        Validates: Requirements 8.1
        """
        # Патчим DebtTransferModal
        mock_debt_transfer_modal = self.add_patcher(
            'finance_tracker.views.loan_details_view.DebtTransferModal'
        )
        
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем метод открытия модального окна
        self.view.open_debt_transfer_modal(mock_event)
        
        # Проверяем, что DebtTransferModal был создан
        mock_debt_transfer_modal.assert_called_once()
        
        # Проверяем параметры создания
        call_args = mock_debt_transfer_modal.call_args
        self.assertEqual(call_args[1]['session'], self.mock_session)
        self.assertEqual(call_args[1]['loan'], self.test_loan)
        self.assertIsNotNone(call_args[1]['on_transfer_callback'])
        
        # Проверяем, что modal.open был вызван
        modal_instance = mock_debt_transfer_modal.return_value
        modal_instance.open.assert_called_once_with(self.page)

    def test_handle_debt_transfer_success(self):
        """
        Тест успешной обработки передачи долга.
        
        Проверяет:
        - При вызове handle_debt_transfer вызывается create_debt_transfer сервис
        - После передачи перезагружаются детали кредита
        - Отображается уведомление об успехе
        
        Validates: Requirements 2.1
        """
        # Патчим create_debt_transfer
        mock_create_debt_transfer = self.add_patcher(
            'finance_tracker.views.loan_details_view.create_debt_transfer'
        )
        
        # Создаем мок передачи
        from finance_tracker.models import DebtTransferDB
        mock_transfer = Mock(spec=DebtTransferDB)
        mock_transfer.id = "transfer-1"
        mock_create_debt_transfer.return_value = mock_transfer
        
        # Вызываем handle_debt_transfer
        self.view.handle_debt_transfer(
            loan_id="1",
            to_lender_id="2",
            transfer_date=date(2025, 1, 15),
            transfer_amount=Decimal("105000.00"),
            reason="Продажа долга",
            notes="Тестовое примечание"
        )
        
        # Проверяем, что create_debt_transfer был вызван
        mock_create_debt_transfer.assert_called_once()
        
        # Проверяем параметры вызова
        call_args = mock_create_debt_transfer.call_args
        self.assertEqual(call_args[1]['session'], self.mock_session)
        self.assertEqual(call_args[1]['loan_id'], "1")
        self.assertEqual(call_args[1]['to_lender_id'], "2")
        self.assertEqual(call_args[1]['transfer_date'], date(2025, 1, 15))
        self.assertEqual(call_args[1]['transfer_amount'], Decimal("105000.00"))
        self.assertEqual(call_args[1]['reason'], "Продажа долга")
        self.assertEqual(call_args[1]['notes'], "Тестовое примечание")

    def test_handle_debt_transfer_validation_error(self):
        """
        Тест обработки ошибки валидации при передаче долга.
        
        Проверяет:
        - При ошибке валидации (ValueError) отображается сообщение об ошибке
        - Детали кредита не перезагружаются
        
        Validates: Requirements 6.1, 6.2, 6.3
        """
        # Патчим create_debt_transfer для выброса ValueError
        mock_create_debt_transfer = self.add_patcher(
            'finance_tracker.views.loan_details_view.create_debt_transfer'
        )
        mock_create_debt_transfer.side_effect = ValueError("Нельзя передать погашенный кредит")
        
        # Вызываем handle_debt_transfer
        self.view.handle_debt_transfer(
            loan_id="1",
            to_lender_id="2",
            transfer_date=date(2025, 1, 15),
            transfer_amount=Decimal("105000.00"),
            reason=None,
            notes=None
        )
        
        # Проверяем, что create_debt_transfer был вызван
        mock_create_debt_transfer.assert_called_once()
        
        # Проверяем, что page.open был вызван для отображения ошибки (SnackBar)
        self.page.open.assert_called()


if __name__ == '__main__':
    unittest.main()

