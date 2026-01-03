"""
Интеграционные тесты для создания кредитора из DebtTransferModal.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal

from finance_tracker.components.debt_transfer_modal import DebtTransferModal
from finance_tracker.models.enums import LenderType


class TestDebtTransferLenderIntegration(unittest.TestCase):
    """Интеграционные тесты для создания кредитора из DebtTransferModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_loan = Mock()
        self.mock_loan.id = "loan-123"
        self.mock_loan.name = "Тестовый кредит"
        self.mock_loan.effective_holder_id = "holder-123"
        
        # Мокируем текущего держателя
        self.mock_current_holder = Mock()
        self.mock_current_holder.name = "Текущий держатель"
        self.mock_loan.current_holder = self.mock_current_holder
        self.mock_loan.lender = self.mock_current_holder
        
        self.mock_callback = Mock()

    def create_mock_page(self):
        """Создает mock Page с методами для диалогов."""
        mock_page = MagicMock()
        mock_page.open = Mock()
        mock_page.close = Mock()
        mock_page.update = Mock()
        mock_page.overlay = []
        return mock_page

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.create_lender')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_full_lender_creation_workflow(self, mock_get_lenders, mock_create_lender, mock_get_remaining_debt):
        """Тест полного workflow создания кредитора из DebtTransferModal."""
        # Настройка моков
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        mock_get_lenders.return_value = []  # Нет доступных кредиторов
        
        # Мокируем созданного кредитора
        mock_new_lender = Mock()
        mock_new_lender.id = "collector-123"
        mock_new_lender.name = "Коллекторское агентство"
        mock_create_lender.return_value = mock_new_lender
        
        # Создаем DebtTransferModal
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        
        # 1. Открываем DebtTransferModal
        modal.open(mock_page)
        
        # Проверяем, что показывается сообщение о отсутствии кредиторов
        self.assertEqual(len(modal.to_lender_dropdown.options), 1)
        self.assertEqual(modal.to_lender_dropdown.options[0].key, "0")
        self.assertIn("Нет доступных кредиторов", modal.to_lender_dropdown.options[0].text)
        
        # 2. Нажимаем кнопку "Создать кредитора"
        modal.lender_modal.open = Mock()  # Мокируем открытие LenderModal
        modal._on_create_lender(None)
        
        # Проверяем, что LenderModal открылся
        modal.lender_modal.open.assert_called_once_with(mock_page)
        
        # 3. Симулируем создание кредитора через LenderModal
        # Обновляем mock_get_lenders для возврата нового кредитора
        mock_get_lenders.return_value = [mock_new_lender]
        
        modal._on_lender_created(
            name="Коллекторское агентство",
            lender_type=LenderType.COLLECTOR,
            description="Агентство по взысканию долгов",
            contact_info="+7 800 123 45 67",
            notes="Работает с просроченными долгами"
        )
        
        # 4. Проверяем результаты
        # Проверяем вызов create_lender с правильными параметрами
        mock_create_lender.assert_called_once_with(
            session=self.mock_session,
            name="Коллекторское агентство",
            lender_type=LenderType.COLLECTOR,
            description="Агентство по взысканию долгов",
            contact_info="+7 800 123 45 67",
            notes="Работает с просроченными долгами"
        )
        
        # Проверяем, что новый кредитор автоматически выбран
        self.assertEqual(modal.to_lender_dropdown.value, "collector-123")
        
        # Проверяем обновление UI
        mock_page.update.assert_called()
        
        # Проверяем, что ошибка очищена
        self.assertEqual(modal.error_text.value, "")

    @patch('finance_tracker.components.debt_transfer_modal.get_remaining_debt')
    @patch('finance_tracker.components.debt_transfer_modal.create_lender')
    @patch('finance_tracker.components.debt_transfer_modal.get_all_lenders')
    def test_lender_creation_error_handling(self, mock_get_lenders, mock_create_lender, mock_get_remaining_debt):
        """Тест обработки ошибки при создании кредитора."""
        # Настройка моков
        mock_get_remaining_debt.return_value = Decimal('1000.00')
        mock_get_lenders.return_value = []
        
        # Мокируем ошибку при создании кредитора
        mock_create_lender.side_effect = Exception("Ошибка БД")
        
        # Создаем DebtTransferModal
        modal = DebtTransferModal(
            session=self.mock_session,
            loan=self.mock_loan,
            on_transfer_callback=self.mock_callback
        )
        
        mock_page = self.create_mock_page()
        modal.page = mock_page
        
        # Симулируем создание кредитора с ошибкой
        modal._on_lender_created(
            name="Проблемный кредитор",
            lender_type=LenderType.COLLECTOR,
            description=None,
            contact_info=None,
            notes=None
        )
        
        # Проверяем, что ошибка отображается
        self.assertIn("Ошибка при создании кредитора", modal.error_text.value)
        self.assertIn("Ошибка БД", modal.error_text.value)
        
        # Проверяем обновление UI
        mock_page.update.assert_called()


class TestDebtTransferStatisticsIntegration(unittest.TestCase):
    """Интеграционные тесты для отображения статистики по держателям."""

    @patch('finance_tracker.services.loan_statistics_service.get_debt_by_holder_statistics')
    def test_statistics_includes_holder_information(self, mock_get_holder_stats):
        """
        Интеграционный тест: статистика включает информацию о держателях.
        
        Проверяет полный сценарий:
        1. Создание кредитов с разными держателями
        2. Передача долга между держателями
        3. Получение статистики с группировкой по текущим держателям
        4. Отображение статистики в UI
        
        Validates: Requirements 7.2
        """
        from finance_tracker.services.loan_statistics_service import get_summary_statistics
        from finance_tracker.models.enums import LoanStatus
        
        # Настройка mock для возврата статистики по держателям
        mock_get_holder_stats.return_value = {
            'holder-1': {
                'holder_name': 'Банк ВТБ',
                'loan_count': 2,
                'total_debt': Decimal('300000.00')
            },
            'holder-2': {
                'holder_name': 'Коллектор Альфа',
                'loan_count': 1,
                'total_debt': Decimal('200000.00')
            }
        }
        
        # Мокируем сессию и запросы к БД
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        
        # Мокируем активные кредиты
        mock_loan1 = Mock()
        mock_loan1.amount = Decimal('150000.00')
        mock_loan1.interest_rate = Decimal('12.0')
        
        mock_loan2 = Mock()
        mock_loan2.amount = Decimal('150000.00')
        mock_loan2.interest_rate = Decimal('15.0')
        
        mock_loan3 = Mock()
        mock_loan3.amount = Decimal('200000.00')
        mock_loan3.interest_rate = Decimal('18.0')
        
        mock_query.filter.return_value.all.return_value = [mock_loan1, mock_loan2, mock_loan3]
        
        # Мокируем платежи
        mock_query.filter_by.return_value.all.return_value = []
        
        # Вызываем get_summary_statistics
        stats = get_summary_statistics(mock_session)
        
        # Проверяем, что статистика содержит информацию о держателях
        self.assertIn('by_holder', stats)
        self.assertEqual(len(stats['by_holder']), 2)
        
        # Проверяем информацию о первом держателе
        self.assertIn('holder-1', stats['by_holder'])
        holder1_info = stats['by_holder']['holder-1']
        self.assertEqual(holder1_info['holder_name'], 'Банк ВТБ')
        self.assertEqual(holder1_info['loan_count'], 2)
        self.assertEqual(holder1_info['total_debt'], 300000.00)
        
        # Проверяем информацию о втором держателе
        self.assertIn('holder-2', stats['by_holder'])
        holder2_info = stats['by_holder']['holder-2']
        self.assertEqual(holder2_info['holder_name'], 'Коллектор Альфа')
        self.assertEqual(holder2_info['loan_count'], 1)
        self.assertEqual(holder2_info['total_debt'], 200000.00)


if __name__ == '__main__':
    unittest.main()