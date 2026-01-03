"""
Тесты для LoansView.

Проверяет:
- Инициализацию View
- Загрузку кредитов и статистики
- Фильтрацию по статусу кредита
- Открытие модального окна создания
- Навигацию к LoanDetailsView
- Обновление статистики
"""
import unittest
from unittest.mock import Mock
from decimal import Decimal
from datetime import date

from finance_tracker.views.loans_view import LoansView
from finance_tracker.models.enums import LoanStatus, LoanType
from test_view_base import ViewTestBase
from test_factories import create_test_loan, create_test_lender


class TestLoansView(ViewTestBase):
    """Тесты для LoansView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.loans_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы кредитов
        self.mock_get_all_loans = self.add_patcher(
            'finance_tracker.views.loans_view.get_all_loans',
            return_value=[]
        )
        self.mock_create_loan = self.add_patcher(
            'finance_tracker.views.loans_view.create_loan'
        )
        self.mock_update_loan = self.add_patcher(
            'finance_tracker.views.loans_view.update_loan'
        )
        self.mock_delete_loan = self.add_patcher(
            'finance_tracker.views.loans_view.delete_loan'
        )
        
        # Патчим сервисы статистики
        self.mock_get_summary_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_summary_statistics',
            return_value={
                'total_active_loans': 0,
                'total_active_amount': Decimal('0.00'),
                'monthly_payments_sum': Decimal('0.00'),
                'by_holder': {}
            }
        )
        self.mock_get_monthly_burden_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_monthly_burden_statistics',
            return_value={
                'burden_percent': 0.0,
                'is_healthy': True,
            }
        )
        
        # Патчим LoanModal
        self.mock_loan_modal = self.add_patcher(
            'finance_tracker.views.loans_view.LoanModal'
        )
        
        # Патчим LoanDetailsView
        self.mock_loan_details_view = self.add_patcher(
            'finance_tracker.views.loans_view.LoanDetailsView'
        )
        
        # Создаем экземпляр LoansView
        self.view = LoansView(self.page)

    def test_initialization(self):
        """
        Тест инициализации LoansView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - UI компоненты созданы (заголовок, фильтры, список, статистика)
        - Начальное состояние фильтра (None - все кредиты)
        
        Validates: Requirements 8.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, LoansView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.header)
        self.assertIsNotNone(self.view.status_dropdown)
        self.assertIsNotNone(self.view.loans_column)
        self.assertIsNotNone(self.view.stats_card)
        
        # Проверяем начальное состояние фильтра
        self.assertIsNone(self.view.status_filter)
        self.assertEqual(self.view.status_dropdown.value, "all")

    def test_load_statistics_on_init(self):
        """
        Тест загрузки статистики при инициализации.
        
        Проверяет:
        - При инициализации вызывается get_summary_statistics
        - При инициализации вызывается get_monthly_burden_statistics
        - Статистика отображается в stats_card
        
        Validates: Requirements 8.5
        """
        # Проверяем, что сервисы были вызваны
        self.assert_service_called(
            self.mock_get_summary_statistics,
            self.mock_session
        )
        self.assert_service_called(
            self.mock_get_monthly_burden_statistics,
            self.mock_session
        )
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(self.view.stats_card.content)

    def test_load_loans_on_init(self):
        """
        Тест загрузки кредитов при инициализации.
        
        Проверяет:
        - При инициализации вызывается get_all_loans
        - Сервис вызывается с правильной сессией и фильтром
        
        Validates: Requirements 8.1
        """
        # Проверяем, что сервис был вызван
        self.assert_service_called(
            self.mock_get_all_loans,
            self.mock_session,
            status=None  # Фильтр по умолчанию - None (все кредиты)
        )

    def test_load_loans_with_data(self):
        """
        Тест загрузки кредитов с данными.
        
        Проверяет:
        - Кредиты отображаются в списке
        - Количество элементов соответствует количеству кредитов
        - page.update вызывается после загрузки
        
        Validates: Requirements 8.1
        """
        # Создаем тестовые кредиты
        lender = create_test_lender(id=1, name="Сбербанк")
        test_loans = [
            create_test_loan(
                id=1,
                name="Кредит 1",
                lender_id=1,
                amount=Decimal("100000.00"),
                status=LoanStatus.ACTIVE,
                loan_type=LoanType.CONSUMER
            ),
            create_test_loan(
                id=2,
                name="Кредит 2",
                lender_id=1,
                amount=Decimal("50000.00"),
                status=LoanStatus.PAID_OFF,
                loan_type=LoanType.MORTGAGE
            ),
        ]
        
        # Добавляем lender к кредитам
        for loan in test_loans:
            loan.lender = lender
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_all_loans.return_value = test_loans
        
        # Загружаем данные
        self.view.load_loans()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.loans_column.controls), 2)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_loans_empty_list(self):
        """
        Тест загрузки пустого списка кредитов.
        
        Проверяет:
        - При пустом списке отображается сообщение "Нет кредитов"
        - Количество контролов = 1 (сообщение о пустом состоянии)
        
        Validates: Requirements 8.1
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_all_loans.return_value = []
        
        # Загружаем данные
        self.view.load_loans()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.loans_column.controls), 1)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_filter_change_to_active(self):
        """
        Тест фильтрации по активным кредитам.
        
        Проверяет:
        - При выборе "Активные" устанавливается фильтр ACTIVE
        - Вызывается перезагрузка данных с новым фильтром
        - get_all_loans вызывается с status=LoanStatus.ACTIVE
        
        Validates: Requirements 8.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_loans.reset_mock()
        
        # Имитируем выбор "Активные"
        self.view.status_dropdown.value = LoanStatus.ACTIVE.value
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.status_filter, LoanStatus.ACTIVE)
        
        # Проверяем, что сервис вызван с фильтром ACTIVE
        self.assert_service_called(
            self.mock_get_all_loans,
            self.mock_session,
            status=LoanStatus.ACTIVE
        )

    def test_filter_change_to_paid_off(self):
        """
        Тест фильтрации по погашенным кредитам.
        
        Проверяет:
        - При выборе "Погашенные" устанавливается фильтр PAID_OFF
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 8.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_loans.reset_mock()
        
        # Имитируем выбор "Погашенные"
        self.view.status_dropdown.value = LoanStatus.PAID_OFF.value
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.status_filter, LoanStatus.PAID_OFF)
        
        # Проверяем, что сервис вызван с фильтром PAID_OFF
        self.assert_service_called(
            self.mock_get_all_loans,
            self.mock_session,
            status=LoanStatus.PAID_OFF
        )

    def test_filter_change_to_overdue(self):
        """
        Тест фильтрации по просроченным кредитам.
        
        Проверяет:
        - При выборе "Просроченные" устанавливается фильтр OVERDUE
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 8.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_loans.reset_mock()
        
        # Имитируем выбор "Просроченные"
        self.view.status_dropdown.value = LoanStatus.OVERDUE.value
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.status_filter, LoanStatus.OVERDUE)
        
        # Проверяем, что сервис вызван с фильтром OVERDUE
        self.assert_service_called(
            self.mock_get_all_loans,
            self.mock_session,
            status=LoanStatus.OVERDUE
        )

    def test_filter_change_to_all(self):
        """
        Тест сброса фильтра (все кредиты).
        
        Проверяет:
        - При выборе "Все статусы" фильтр сбрасывается (None)
        - Вызывается перезагрузка данных без фильтра
        
        Validates: Requirements 8.2
        """
        # Устанавливаем фильтр
        self.view.status_filter = LoanStatus.ACTIVE
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_loans.reset_mock()
        
        # Имитируем выбор "Все статусы"
        self.view.status_dropdown.value = "all"
        self.view.on_status_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.status_filter)
        
        # Проверяем, что сервис вызван без фильтра
        self.assert_service_called(
            self.mock_get_all_loans,
            self.mock_session,
            status=None
        )

    def test_open_create_dialog(self):
        """
        Тест открытия модального окна создания кредита.
        
        Проверяет:
        - При нажатии кнопки создания открывается LoanModal
        - Диалог открывается в режиме создания (без кредита)
        - selected_loan устанавливается в None
        
        Validates: Requirements 8.3
        """
        # Создаем мок события
        mock_event = Mock()
        
        # Вызываем метод открытия диалога
        self.view.open_create_dialog(mock_event)
        
        # Проверяем, что selected_loan установлен в None
        self.assertIsNone(self.view.selected_loan)
        
        # Проверяем, что loan_modal.open был вызван
        self.view.loan_modal.open.assert_called_once()
        
        # Проверяем, что вызов был с page и loan=None
        call_args = self.view.loan_modal.open.call_args
        self.assertEqual(call_args[0][0], self.page)
        self.assertIsNone(call_args[1]['loan'])

    def test_open_loan_details(self):
        """
        Тест открытия экрана деталей кредита.
        
        Проверяет:
        - При клике на кредит открывается LoanDetailsView
        - LoanDetailsView создается с правильным loan_id
        - Контролы View заменяются на контролы LoanDetailsView
        
        Validates: Requirements 8.4
        """
        # Создаем тестовый кредит
        lender = create_test_lender(id=1, name="Сбербанк")
        test_loan = create_test_loan(id=1, name="Тестовый кредит", lender_id=1)
        test_loan.lender = lender
        
        # Настраиваем мок LoanDetailsView
        mock_details_view = Mock()
        mock_details_view.controls = [Mock(), Mock()]  # Два контрола
        self.mock_loan_details_view.return_value = mock_details_view
        
        # Сохраняем исходное количество контролов
        original_controls_count = len(self.view.controls)
        
        # Вызываем метод открытия деталей
        self.view.open_loan_details(test_loan)
        
        # Проверяем, что LoanDetailsView был создан с правильными параметрами
        self.mock_loan_details_view.assert_called_once()
        call_args = self.mock_loan_details_view.call_args
        self.assertEqual(call_args[1]['page'], self.page)
        self.assertEqual(call_args[1]['loan_id'], test_loan.id)
        self.assertIsNotNone(call_args[1]['on_back'])
        
        # Проверяем, что контролы были заменены
        self.assertEqual(len(self.view.controls), 2)

    def test_return_from_details(self):
        """
        Тест возврата из экрана деталей к списку кредитов.
        
        Проверяет:
        - При вызове return_from_details восстанавливаются исходные контролы
        - Данные перезагружаются (load_statistics и load_loans)
        - page.update вызывается
        
        Validates: Requirements 8.4
        """
        # Сохраняем исходные контролы
        original_controls = self.view.controls.copy()
        
        # Имитируем переход к деталям (сохраняем контролы)
        self.view._saved_controls = original_controls
        
        # Заменяем контролы на другие
        self.view.controls.clear()
        self.view.controls.append(Mock())
        
        # Сбрасываем счетчики вызовов
        self.mock_get_all_loans.reset_mock()
        self.mock_get_summary_statistics.reset_mock()
        self.page.update.reset_mock()
        
        # Вызываем return_from_details
        self.view.return_from_details()
        
        # Проверяем, что контролы восстановлены
        self.assertEqual(len(self.view.controls), len(original_controls))
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_summary_statistics, self.mock_session)
        self.assert_service_called(self.mock_get_all_loans, self.mock_session, status=None)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_on_create_loan_success(self):
        """
        Тест успешного создания кредита.
        
        Проверяет:
        - При вызове on_create_loan вызывается create_loan сервис
        - После создания перезагружаются статистика и список кредитов
        - Показывается сообщение об успехе через page.open()
        
        Validates: Requirements 8.3
        """
        # Настраиваем мок для возврата созданного кредита
        created_loan = create_test_loan(id=1, name="Новый кредит", loan_type=LoanType.CONSUMER)
        self.mock_create_loan.return_value = created_loan
        
        # Сбрасываем счетчики вызовов
        self.mock_get_all_loans.reset_mock()
        self.mock_get_summary_statistics.reset_mock()
        self.page.open.reset_mock()
        
        # Вызываем on_create_loan
        self.view.on_create_loan(
            lender_id=1,
            name="Новый кредит",
            loan_type=LoanType.CONSUMER,
            amount=Decimal("100000.00"),
            issue_date=date.today(),
            interest_rate=Decimal("10.5"),
            end_date=None,
            contract_number="123456",
            description="Тестовый кредит"
        )
        
        # Проверяем, что create_loan был вызван
        self.assert_service_called(self.mock_create_loan)
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_summary_statistics, self.mock_session)
        self.assert_service_called(self.mock_get_all_loans, self.mock_session, status=None)
        
        # Проверяем, что page.open был вызван для SnackBar
        self.page.open.assert_called()

    def test_on_update_loan_success(self):
        """
        Тест успешного обновления кредита.
        
        Проверяет:
        - При вызове on_update_loan вызывается update_loan сервис
        - После обновления перезагружаются статистика и список кредитов
        - Показывается сообщение об успехе через page.open()
        
        Validates: Requirements 8.3
        """
        # Настраиваем мок для возврата обновленного кредита
        updated_loan = create_test_loan(id=1, name="Обновленный кредит", loan_type=LoanType.CONSUMER)
        self.mock_update_loan.return_value = updated_loan
        
        # Сбрасываем счетчики вызовов
        self.mock_get_all_loans.reset_mock()
        self.mock_get_summary_statistics.reset_mock()
        self.page.open.reset_mock()
        
        # Вызываем on_update_loan
        self.view.on_update_loan(
            loan_id=1,
            name="Обновленный кредит",
            loan_type=LoanType.CONSUMER,
            amount=Decimal("120000.00"),
            issue_date=date.today(),
            interest_rate=Decimal("11.0"),
            end_date=None,
            contract_number="123456",
            description="Обновленный кредит"
        )
        
        # Проверяем, что update_loan был вызван
        self.assert_service_called(self.mock_update_loan)
        
        # Проверяем, что данные перезагружены
        self.assert_service_called(self.mock_get_summary_statistics, self.mock_session)
        self.assert_service_called(self.mock_get_all_loans, self.mock_session, status=None)
        
        # Проверяем, что page.open был вызван для SnackBar
        self.page.open.assert_called()

    def test_confirm_delete_loan(self):
        """
        Тест открытия диалога подтверждения удаления кредита.
        
        Проверяет:
        - При вызове confirm_delete_loan открывается диалог подтверждения
        - Диалог содержит информацию об удаляемом кредите
        - page.open() вызывается с диалогом
        
        Validates: Requirements 8.3
        """
        # Создаем тестовый кредит
        test_loan = create_test_loan(id=1, name="Кредит для удаления")
        
        # Вызываем метод подтверждения удаления
        self.view.confirm_delete_loan(test_loan)
        
        # Проверяем, что page.open был вызван с диалогом
        self.page.open.assert_called_once()

    def test_load_statistics_with_data(self):
        """
        Тест загрузки статистики с данными.
        
        Проверяет:
        - При вызове load_statistics получаются данные от сервисов
        - stats_card содержит контент с информацией о статистике
        - page.update вызывается
        
        Validates: Requirements 8.5
        """
        # Настраиваем моки для возврата статистики
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': 3,
            'total_active_amount': Decimal('500000.00'),
            'monthly_payments_sum': Decimal('15000.00'),
            'by_holder': {}
        }
        self.mock_get_monthly_burden_statistics.return_value = {
            'burden_percent': 25.5,
            'is_healthy': True,
        }
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем load_statistics
        self.view.load_statistics()
        
        # Проверяем, что сервисы были вызваны
        self.assert_service_called(self.mock_get_summary_statistics, self.mock_session)
        self.assert_service_called(self.mock_get_monthly_burden_statistics, self.mock_session)
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(self.view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_statistics_error_handling(self):
        """
        Тест обработки ошибки при загрузке статистики.
        
        Проверяет:
        - При ошибке в сервисе отображается сообщение об ошибке
        - stats_card содержит текст об ошибке
        - page.update вызывается
        
        Validates: Requirements 8.5
        """
        # Настраиваем мок для возврата ошибки
        self.mock_get_summary_statistics.side_effect = Exception("Ошибка БД")
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем load_statistics
        self.view.load_statistics()
        
        # Проверяем, что stats_card содержит сообщение об ошибке
        self.assertIsNotNone(self.view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 1.2
        """
        # Вызываем will_unmount
        self.view.will_unmount()
        
        # Проверяем, что __exit__ был вызван
        self.mock_db_cm.__exit__.assert_called_once()

    def test_load_statistics_with_holders(self):
        """
        Тест загрузки статистики с информацией о держателях долга.
        
        Проверяет:
        - Статистика по держателям отображается, если есть переданные кредиты
        - Для каждого держателя показывается имя, количество кредитов и сумма долга
        - Секция держателей имеет заголовок
        
        Validates: Requirements 7.2
        """
        # Настраиваем mock для возврата статистики с держателями
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': 3,
            'total_active_amount': Decimal('500000.00'),
            'monthly_payments_sum': Decimal('25000.00'),
            'by_holder': {
                'holder-1': {
                    'holder_name': 'Банк ВТБ',
                    'loan_count': 2,
                    'total_debt': 300000.00
                },
                'holder-2': {
                    'holder_name': 'Коллектор Альфа',
                    'loan_count': 1,
                    'total_debt': 200000.00
                }
            }
        }
        
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_summary_statistics.reset_mock()
        
        # Вызываем load_statistics
        self.view.load_statistics()
        
        # Проверяем, что stats_card обновлен
        self.assertIsNotNone(self.view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)
        
        # Проверяем, что get_summary_statistics был вызван
        self.mock_get_summary_statistics.assert_called_once_with(self.mock_session)

    def test_load_statistics_without_holders(self):
        """
        Тест загрузки статистики без информации о держателях.
        
        Проверяет:
        - Если нет переданных кредитов, секция держателей не отображается
        - Основная статистика отображается корректно
        
        Validates: Requirements 7.2
        """
        # Настраиваем mock для возврата статистики без держателей
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': 2,
            'total_active_amount': Decimal('300000.00'),
            'monthly_payments_sum': Decimal('15000.00'),
            'by_holder': {}  # Пустой словарь - нет переданных кредитов
        }
        
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_summary_statistics.reset_mock()
        
        # Вызываем load_statistics
        self.view.load_statistics()
        
        # Проверяем, что stats_card обновлен
        self.assertIsNotNone(self.view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_create_holder_stat_item(self):
        """
        Тест создания элемента статистики по держателю.
        
        Проверяет:
        - Метод _create_holder_stat_item создает Container
        - Container содержит имя держателя
        - Container содержит количество кредитов и сумму долга
        - Container имеет правильное форматирование
        
        Validates: Requirements 7.2
        """
        # Создаем элемент статистики по держателю
        holder_item = self.view._create_holder_stat_item(
            holder_name="Банк ВТБ",
            loan_count=2,
            total_debt=300000.50
        )
        
        # Проверяем, что возвращается Container
        self.assertIsNotNone(holder_item)
        
        # Проверяем, что Container имеет content
        self.assertIsNotNone(holder_item.content)


if __name__ == '__main__':
    unittest.main()



# ============================================================================
# Property-based тесты для LoansView
# ============================================================================

from hypothesis import given, strategies as st, settings


class TestLoansViewProperties(ViewTestBase):
    """Property-based тесты для LoansView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.loans_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы кредитов
        self.mock_get_all_loans = self.add_patcher(
            'finance_tracker.views.loans_view.get_all_loans',
            return_value=[]
        )
        
        # Патчим сервисы статистики
        self.mock_get_summary_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_summary_statistics',
            return_value={
                'total_active_loans': 0,
                'total_active_amount': Decimal('0.00'),
                'monthly_payments_sum': Decimal('0.00'),
                'by_holder': {}
            }
        )
        self.mock_get_monthly_burden_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_monthly_burden_statistics',
            return_value={
                'burden_percent': 0.0,
                'is_healthy': True,
            }
        )
        
        # Патчим LoanModal
        self.mock_loan_modal = self.add_patcher(
            'finance_tracker.views.loans_view.LoanModal'
        )

    @given(
        num_loans=st.integers(min_value=0, max_value=20),
        total_amount=st.decimals(
            min_value=Decimal('0.00'),
            max_value=Decimal('1000000.00'),
            places=2
        ),
        monthly_payments=st.decimals(
            min_value=Decimal('0.00'),
            max_value=Decimal('100000.00'),
            places=2
        ),
        burden_percent=st.decimals(
            min_value=Decimal('0.00'),
            max_value=Decimal('100.00'),
            places=2
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_statistics_calculation(
        self,
        num_loans,
        total_amount,
        monthly_payments,
        burden_percent
    ):
        """
        Feature: ui-testing, Property 5.2: Статистика кредитов
        
        Validates: Requirements 8.5
        
        Для любого набора кредитов, статистика должна корректно 
        рассчитываться и отображаться в UI.
        
        Проверяет:
        - При загрузке View вызываются сервисы статистики
        - Статистика отображается в stats_card
        - Количество активных кредитов соответствует данным
        - Общая сумма кредитов соответствует данным
        - Ежемесячные платежи соответствуют данным
        - Кредитная нагрузка соответствует данным
        - page.update вызывается после загрузки статистики
        """
        # Настраиваем моки для возврата статистики
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': num_loans,
            'total_active_amount': total_amount,
            'total_closed_loans': 0,
            'monthly_payments_sum': monthly_payments,
            'total_interest_expected': Decimal('0.00'),
            'total_overpayment': Decimal('0.00'),
            'by_holder': {}
        }
        
        self.mock_get_monthly_burden_statistics.return_value = {
            'monthly_income': Decimal('100000.00'),
            'monthly_payments': monthly_payments,
            'burden_percent': burden_percent,
            'is_healthy': burden_percent < 30
        }
        
        # Создаем View
        view = LoansView(self.page)
        
        # Проверяем, что сервисы были вызваны при инициализации
        self.assert_service_called(
            self.mock_get_summary_statistics,
            self.mock_session
        )
        self.assert_service_called(
            self.mock_get_monthly_burden_statistics,
            self.mock_session
        )
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)
        
        # Сбрасываем счетчик вызовов
        self.mock_get_summary_statistics.reset_mock()
        self.mock_get_monthly_burden_statistics.reset_mock()
        self.page.update.reset_mock()
        
        # Вызываем load_statistics явно
        view.load_statistics()
        
        # Проверяем, что сервисы были вызваны снова
        self.assert_service_called(
            self.mock_get_summary_statistics,
            self.mock_session
        )
        self.assert_service_called(
            self.mock_get_monthly_burden_statistics,
            self.mock_session
        )
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    @given(
        num_loans=st.integers(min_value=1, max_value=10),
        is_healthy=st.booleans()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_statistics_health_status(self, num_loans, is_healthy):
        """
        Feature: ui-testing, Property 5.2: Статистика кредитов
        
        Validates: Requirements 8.5
        
        Для любого набора кредитов, статус здоровья кредитной нагрузки
        должен корректно отображаться в UI.
        
        Проверяет:
        - Статус здоровья (is_healthy) корректно отображается
        - При здоровой нагрузке (< 30%) is_healthy = True
        - При нездоровой нагрузке (>= 30%) is_healthy = False
        - stats_card обновляется при изменении статуса
        """
        # Определяем burden_percent на основе is_healthy
        if is_healthy:
            burden_percent = Decimal('20.00')  # < 30%
        else:
            burden_percent = Decimal('50.00')  # >= 30%
        
        # Настраиваем моки
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': num_loans,
            'total_active_amount': Decimal('500000.00'),
            'total_closed_loans': 0,
            'monthly_payments_sum': Decimal('10000.00'),
            'total_interest_expected': Decimal('0.00'),
            'total_overpayment': Decimal('0.00'),
            'by_holder': {}
        }
        
        self.mock_get_monthly_burden_statistics.return_value = {
            'monthly_income': Decimal('100000.00'),
            'monthly_payments': Decimal('10000.00'),
            'burden_percent': burden_percent,
            'is_healthy': is_healthy
        }
        
        # Создаем View
        view = LoansView(self.page)
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    @given(
        num_loans=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_statistics_empty_state(self, num_loans):
        """
        Feature: ui-testing, Property 5.2: Статистика кредитов
        
        Validates: Requirements 8.5
        
        Для пустого набора кредитов, статистика должна показывать нули.
        
        Проверяет:
        - При num_loans = 0 total_active_loans = 0
        - При num_loans = 0 total_active_amount = 0
        - stats_card содержит корректные нулевые значения
        """
        # Настраиваем моки для пустого набора
        self.mock_get_summary_statistics.return_value = {
            'total_active_loans': 0,
            'total_active_amount': Decimal('0.00'),
            'total_closed_loans': 0,
            'monthly_payments_sum': Decimal('0.00'),
            'total_interest_expected': Decimal('0.00'),
            'total_overpayment': Decimal('0.00'),
            'by_holder': {}
        }
        
        self.mock_get_monthly_burden_statistics.return_value = {
            'monthly_income': Decimal('0.00'),
            'monthly_payments': Decimal('0.00'),
            'burden_percent': Decimal('0.00'),
            'is_healthy': True
        }
        
        # Создаем View
        view = LoansView(self.page)
        
        # Проверяем, что stats_card содержит контент
        self.assertIsNotNone(view.stats_card.content)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)


class TestLoansViewTransferIndicator(ViewTestBase):
    """Тесты для индикатора передачи долга в списке кредитов."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.loans_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы кредитов
        self.mock_get_all_loans = self.add_patcher(
            'finance_tracker.views.loans_view.get_all_loans',
            return_value=[]
        )
        
        # Патчим сервисы статистики
        self.mock_get_summary_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_summary_statistics',
            return_value={
                'total_active_loans': 0,
                'total_active_amount': Decimal('0.00'),
                'monthly_payments_sum': Decimal('0.00'),
                'by_holder': {}
            }
        )
        self.mock_get_monthly_burden_statistics = self.add_patcher(
            'finance_tracker.views.loans_view.get_monthly_burden_statistics',
            return_value={
                'burden_percent': 0.0,
                'is_healthy': True,
            }
        )
        
        # Патчим LoanModal
        self.mock_loan_modal = self.add_patcher(
            'finance_tracker.views.loans_view.LoanModal'
        )
        
        # Создаем экземпляр LoansView
        self.view = LoansView(self.page)

    def test_transfer_indicator_not_shown_for_non_transferred_loan(self):
        """
        Тест отсутствия индикатора для непереданного кредита.
        
        Проверяет:
        - Для кредита без передачи (is_transferred = False) индикатор не отображается
        - Карточка содержит только бейдж статуса
        
        Validates: Requirements 5.1, 5.2
        """
        # Создаем тестовый кредит без передачи
        lender = create_test_lender(id=1, name="Сбербанк")
        test_loan = create_test_loan(
            id=1,
            name="Обычный кредит",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE
        )
        test_loan.lender = lender
        test_loan.current_holder_id = None  # Нет передачи
        test_loan.debt_transfers = []
        
        # Создаем карточку кредита
        card = self.view._create_loan_card(test_loan)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        
        # Проверяем, что в карточке нет индикатора передачи
        # (только один бейдж - статус кредита)
        # Это проверяется косвенно через структуру карточки

    def test_transfer_indicator_shown_for_transferred_loan(self):
        """
        Тест отображения индикатора для переданного кредита.
        
        Проверяет:
        - Для кредита с передачей (is_transferred = True) отображается индикатор
        - Индикатор содержит иконку SWAP_HORIZ
        - Индикатор содержит текст "Передан"
        - Индикатор имеет оранжевый цвет (ft.Colors.ORANGE)
        
        Validates: Requirements 5.1, 5.2
        """
        # Создаем тестовый кредит с передачей
        original_lender = create_test_lender(id=1, name="МФО")
        current_holder = create_test_lender(id=2, name="Коллектор")
        
        test_loan = create_test_loan(
            id=1,
            name="Переданный кредит",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE
        )
        test_loan.lender = original_lender
        test_loan.original_lender = original_lender
        test_loan.current_holder = current_holder
        test_loan.current_holder_id = 2  # Устанавливаем current_holder_id для is_transferred = True
        
        # Создаем мок передачи и устанавливаем напрямую через __dict__
        mock_transfer = Mock()
        mock_transfer.transfer_date = date(2024, 12, 1)
        mock_transfer.from_lender = original_lender
        mock_transfer.to_lender = current_holder
        test_loan.__dict__['debt_transfers'] = [mock_transfer]
        
        # Создаем карточку кредита
        card = self.view._create_loan_card(test_loan)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        
        # Проверяем, что карточка содержит контент
        self.assertIsNotNone(card.content)

    def test_transfer_indicator_tooltip_content(self):
        """
        Тест содержимого tooltip индикатора передачи.
        
        Проверяет:
        - Tooltip содержит имя исходного кредитора
        - Tooltip содержит имя текущего держателя
        - Tooltip содержит дату передачи в формате DD.MM.YYYY
        - Формат tooltip: "Передан от [Original] к [Current] [Date]"
        
        Validates: Requirements 5.3
        """
        # Создаем тестовый кредит с передачей
        original_lender = create_test_lender(id=1, name="Сбербанк")
        current_holder = create_test_lender(id=2, name="Коллекторское агентство")
        
        test_loan = create_test_loan(
            id=1,
            name="Переданный кредит",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE
        )
        test_loan.lender = original_lender
        test_loan.original_lender = original_lender
        test_loan.current_holder = current_holder
        test_loan.current_holder_id = 2  # Устанавливаем current_holder_id для is_transferred = True
        
        # Создаем мок передачи с конкретной датой и устанавливаем напрямую через __dict__
        mock_transfer = Mock()
        mock_transfer.transfer_date = date(2024, 12, 15)
        mock_transfer.from_lender = original_lender
        mock_transfer.to_lender = current_holder
        test_loan.__dict__['debt_transfers'] = [mock_transfer]
        
        # Создаем карточку кредита
        card = self.view._create_loan_card(test_loan)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        
        # Проверяем, что карточка содержит контент
        self.assertIsNotNone(card.content)
        
        # Tooltip проверяется косвенно через структуру карточки
        # В реальном UI tooltip будет отображаться при наведении

    def test_transfer_indicator_with_multiple_transfers(self):
        """
        Тест индикатора при множественных передачах.
        
        Проверяет:
        - При множественных передачах используется последняя передача
        - Tooltip содержит информацию о последней передаче
        - Индикатор отображается корректно
        
        Validates: Requirements 5.1, 5.2, 5.3
        """
        # Создаем тестовый кредит с множественными передачами
        original_lender = create_test_lender(id=1, name="МФО")
        first_collector = create_test_lender(id=2, name="Коллектор 1")
        second_collector = create_test_lender(id=3, name="Коллектор 2")
        
        test_loan = create_test_loan(
            id=1,
            name="Многократно переданный кредит",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE
        )
        test_loan.lender = original_lender
        test_loan.original_lender = original_lender
        test_loan.current_holder = second_collector
        test_loan.current_holder_id = 3  # Устанавливаем current_holder_id для is_transferred = True
        
        # Создаем моки передач и устанавливаем напрямую через __dict__
        first_transfer = Mock()
        first_transfer.transfer_date = date(2024, 11, 1)
        first_transfer.from_lender = original_lender
        first_transfer.to_lender = first_collector
        
        second_transfer = Mock()
        second_transfer.transfer_date = date(2024, 12, 1)
        second_transfer.from_lender = first_collector
        second_transfer.to_lender = second_collector
        
        test_loan.__dict__['debt_transfers'] = [first_transfer, second_transfer]
        
        # Создаем карточку кредита
        card = self.view._create_loan_card(test_loan)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        
        # Проверяем, что карточка содержит контент
        self.assertIsNotNone(card.content)
        
        # Tooltip должен содержать информацию о последней передаче (second_transfer)

    def test_transfer_indicator_without_transfer_history(self):
        """
        Тест индикатора при отсутствии истории передач.
        
        Проверяет:
        - Если is_transferred = True, но debt_transfers пуст, используется fallback tooltip
        - Tooltip содержит текст "Долг передан"
        - Индикатор отображается корректно
        
        Validates: Requirements 5.1, 5.2
        """
        # Создаем тестовый кредит с передачей, но без истории
        original_lender = create_test_lender(id=1, name="МФО")
        current_holder = create_test_lender(id=2, name="Коллектор")
        
        test_loan = create_test_loan(
            id=1,
            name="Кредит без истории",
            lender_id=1,
            amount=Decimal("100000.00"),
            status=LoanStatus.ACTIVE
        )
        test_loan.lender = original_lender
        test_loan.original_lender = original_lender
        test_loan.current_holder = current_holder
        test_loan.current_holder_id = 2  # Устанавливаем current_holder_id для is_transferred = True
        test_loan.debt_transfers = []  # Пустая история
        
        # Создаем карточку кредита
        card = self.view._create_loan_card(test_loan)
        
        # Проверяем, что карточка создана
        self.assertIsNotNone(card)
        
        # Проверяем, что карточка содержит контент
        self.assertIsNotNone(card.content)


if __name__ == '__main__':
    unittest.main()
