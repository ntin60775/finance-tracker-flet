"""
Интеграционные тесты для CalendarLegend с HomeView.

Проверяет интеграцию CalendarLegend с HomeView, передачу ширины календаря,
консистентность индикаторов между календарём и легендой.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
from decimal import Decimal
from hypothesis import given, strategies as st, settings

import flet as ft

from finance_tracker.views.home_view import HomeView
from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.models.models import TransactionDB, CategoryDB
from finance_tracker.models.enums import TransactionType
from finance_tracker.services.transaction_service import create_transaction
from finance_tracker.models import TransactionCreate


class TestCalendarLegendIntegration(unittest.TestCase):
    """Интеграционные тесты для CalendarLegend с HomeView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_page = MagicMock()
        self.mock_session = Mock()
        
        # Настраиваем mock page
        self.mock_page.overlay = []
        self.mock_page.width = 1200
        self.mock_page.height = 800
        self.mock_page.update = Mock()
        self.mock_page.open = Mock()
        self.mock_page.close = Mock()

    def test_calendar_legend_integration_with_home_view(self):
        """
        Тест интеграции CalendarLegend с HomeView.
        
        Проверяет:
        - CalendarLegend создается в составе HomeView
        - CalendarLegend получает доступ к календарю
        - Компоненты корректно взаимодействуют
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Act - создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Assert - проверяем интеграцию
            
            # 1. Проверяем, что CalendarLegend создан
            self.assertIsNotNone(home_view.legend)
            self.assertIsInstance(home_view.legend, CalendarLegend)
            
            # 2. Проверяем, что CalendarWidget создан
            self.assertIsNotNone(home_view.calendar_widget)
            self.assertIsInstance(home_view.calendar_widget, CalendarWidget)
            
            # 3. Проверяем, что легенда находится в правильной колонке (центральная)
            main_row = home_view.controls[0]  # Основной Row
            center_column = main_row.controls[2]  # Центральная колонка (индекс 2)
            
            # Проверяем, что легенда находится в центральной колонке
            legend_found = False
            for control in center_column.controls:
                if isinstance(control, CalendarLegend):
                    legend_found = True
                    break
            
            self.assertTrue(legend_found, "CalendarLegend должен находиться в центральной колонке")
            
            # 4. Проверяем порядок компонентов в центральной колонке
            center_controls = center_column.controls
            self.assertGreaterEqual(len(center_controls), 3, 
                                  "В центральной колонке должно быть минимум 3 компонента")
            
            # Ожидаемый порядок: CalendarWidget, CalendarLegend, PlannedTransactionsWidget
            self.assertIsInstance(center_controls[0], CalendarWidget, 
                                "Первый компонент должен быть CalendarWidget")
            self.assertIsInstance(center_controls[1], CalendarLegend, 
                                "Второй компонент должен быть CalendarLegend")

    def test_calendar_width_transmission(self):
        """
        Тест передачи ширины календаря в CalendarLegend.
        
        Проверяет:
        - CalendarLegend получает информацию о ширине календаря
        - Ширина корректно используется для адаптивности
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Act - создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            
            # Assert - проверяем передачу ширины
            
            # 1. Проверяем, что CalendarWidget имеет определенные размеры
            calendar_widget = home_view.calendar_widget
            self.assertIsNotNone(calendar_widget)
            
            # 2. Проверяем, что CalendarLegend может получить ширину календаря
            legend = home_view.legend
            self.assertIsNotNone(legend)
            
            # 3. Тестируем обновление ширины календаря в легенде
            test_width = 800
            legend.update_calendar_width(test_width)
            
            self.assertEqual(legend.calendar_width, test_width,
                           f"Ширина календаря должна быть {test_width}")
            
            # 4. Проверяем, что легенда адаптируется к ширине
            # При узкой ширине должен быть компактный режим
            narrow_width = 300
            legend.update_calendar_width(narrow_width)
            
            self.assertEqual(legend.calendar_width, narrow_width)
            self.assertFalse(legend._should_show_full_legend(),
                           "При узкой ширине должен быть компактный режим")
            
            # При широкой ширине должен быть полный режим
            wide_width = 1200
            legend.update_calendar_width(wide_width)
            
            self.assertEqual(legend.calendar_width, wide_width)
            self.assertTrue(legend._should_show_full_legend(),
                          "При широкой ширине должен быть полный режим")

    def test_indicator_consistency_between_calendar_and_legend(self):
        """
        Тест консистентности индикаторов между календарём и легендой.
        
        Проверяет:
        - Индикаторы в календаре соответствуют индикаторам в легенде
        - Цвета и символы консистентны
        - Все типы индикаторов представлены
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            calendar_widget = home_view.calendar_widget
            legend = home_view.legend
            
            # Act & Assert - проверяем консистентность индикаторов
            
            # 1. Проверяем, что легенда содержит все типы индикаторов
            legend_indicators = legend.all_indicators
            self.assertGreaterEqual(len(legend_indicators), 7,
                                  "Легенда должна содержать минимум 7 типов индикаторов")
            
            # 2. Проверяем наличие основных индикаторов
            indicator_types = [indicator.type for indicator in legend_indicators]
            
            from finance_tracker.components.calendar_legend_types import IndicatorType
            
            expected_types = [
                IndicatorType.INCOME_DOT,      # Зелёная точка - доходы
                IndicatorType.EXPENSE_DOT,     # Красная точка - расходы
                IndicatorType.PLANNED_SYMBOL,  # ◆ символ - плановые
                IndicatorType.PENDING_SYMBOL,  # 📋 символ - отложенные
                IndicatorType.LOAN_SYMBOL,     # 💳 символ - кредиты
                IndicatorType.CASH_GAP_BG,     # Жёлтый фон - разрывы
                IndicatorType.OVERDUE_BG       # Красный фон - просрочки
            ]
            
            for expected_type in expected_types:
                self.assertIn(expected_type, indicator_types,
                            f"Индикатор {expected_type} должен присутствовать в легенде")
            
            # 3. Проверяем консистентность цветов для точечных индикаторов
            income_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.INCOME_DOT), 
                None
            )
            expense_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.EXPENSE_DOT), 
                None
            )
            
            self.assertIsNotNone(income_indicator, "Индикатор доходов должен существовать")
            self.assertIsNotNone(expense_indicator, "Индикатор расходов должен существовать")
            
            # Проверяем цвета (должны соответствовать календарю)
            self.assertEqual(income_indicator.visual_element.bgcolor, ft.Colors.GREEN,
                           "Цвет индикатора доходов должен быть зелёным")
            self.assertEqual(expense_indicator.visual_element.bgcolor, ft.Colors.RED,
                           "Цвет индикатора расходов должен быть красным")
            
            # 4. Проверяем консистентность символов
            planned_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.PLANNED_SYMBOL), 
                None
            )
            pending_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.PENDING_SYMBOL), 
                None
            )
            loan_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.LOAN_SYMBOL), 
                None
            )
            
            self.assertIsNotNone(planned_indicator, "Индикатор плановых транзакций должен существовать")
            self.assertIsNotNone(pending_indicator, "Индикатор отложенных платежей должен существовать")
            self.assertIsNotNone(loan_indicator, "Индикатор кредитных платежей должен существовать")
            
            # Проверяем символы (должны соответствовать календарю)
            self.assertEqual(planned_indicator.visual_element.value, "◆",
                           "Символ плановых транзакций должен быть ◆")
            self.assertEqual(pending_indicator.visual_element.value, "📋",
                           "Символ отложенных платежей должен быть 📋")
            self.assertEqual(loan_indicator.visual_element.value, "💳",
                           "Символ кредитных платежей должен быть 💳")
            
            # 5. Проверяем консистентность фоновых индикаторов
            cash_gap_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.CASH_GAP_BG), 
                None
            )
            overdue_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.OVERDUE_BG), 
                None
            )
            
            self.assertIsNotNone(cash_gap_indicator, "Индикатор кассовых разрывов должен существовать")
            self.assertIsNotNone(overdue_indicator, "Индикатор просроченных платежей должен существовать")
            
            # Проверяем цвета фона (должны соответствовать календарю)
            self.assertEqual(cash_gap_indicator.visual_element.bgcolor, ft.Colors.AMBER_100,
                           "Цвет индикатора кассовых разрывов должен быть жёлтым")
            self.assertEqual(overdue_indicator.visual_element.bgcolor, ft.Colors.RED_100,
                           "Цвет индикатора просроченных платежей должен быть красным")

    def test_legend_updates_with_calendar_data(self):
        """
        Тест обновления легенды при изменении данных календаря.
        
        Проверяет:
        - Легенда остается актуальной при изменении данных
        - Индикаторы корректно отображаются при наличии данных
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            calendar_widget = home_view.calendar_widget
            legend = home_view.legend
            
            # Создаем тестовые данные
            test_date = date(2024, 12, 11)
            
            # Мокируем транзакции
            mock_transactions = [
                Mock(date=test_date, type=TransactionType.INCOME, amount=Decimal('100')),
                Mock(date=test_date, type=TransactionType.EXPENSE, amount=Decimal('50'))
            ]
            
            # Мокируем плановые вхождения
            mock_occurrences = [
                Mock(occurrence_date=test_date, description="Плановая транзакция")
            ]
            
            # Act - обновляем данные календаря
            calendar_widget.set_transactions(mock_transactions, mock_occurrences)
            
            # Assert - проверяем, что легенда остается корректной
            
            # 1. Проверяем, что легенда все еще содержит все индикаторы
            self.assertGreaterEqual(len(legend.all_indicators), 7,
                                  "Легенда должна содержать все индикаторы после обновления данных")
            
            # 2. Проверяем, что легенда может корректно отображаться
            if legend._should_show_full_legend():
                full_content = legend._build_full_legend()
                self.assertIsInstance(full_content, ft.Row,
                                    "Полная легенда должна возвращать Row")
                self.assertGreater(len(full_content.controls), 0,
                                 "Полная легенда должна содержать элементы")
            else:
                compact_content = legend._build_compact_legend()
                self.assertIsInstance(compact_content, ft.Row,
                                    "Компактная легенда должна возвращать Row")
                self.assertGreater(len(compact_content.controls), 0,
                                 "Компактная легенда должна содержать элементы")
            
            # 3. Проверяем стабильность при множественных обновлениях
            for i in range(5):
                # Изменяем данные
                updated_transactions = [
                    Mock(date=test_date, type=TransactionType.INCOME, amount=Decimal(f'{100 + i * 10}'))
                ]
                calendar_widget.set_transactions(updated_transactions, [])
                
                # Проверяем, что легенда остается стабильной
                self.assertIsNotNone(legend.all_indicators,
                                   f"Индикаторы легенды должны оставаться доступными после обновления {i}")
                self.assertGreaterEqual(len(legend.all_indicators), 7,
                                      f"Количество индикаторов не должно уменьшаться после обновления {i}")

    @given(st.integers(min_value=200, max_value=1500))
    @settings(max_examples=50, deadline=None)
    def test_property_13_responsive_stability(self, calendar_width):
        """
        **Feature: calendar-legend-improvement, Property 13: Responsive stability**
        **Validates: Requirements 5.5**
        
        Property: При любом изменении размера окна легенда должна пересчитывать 
        свой layout и режим отображения без ошибок или визуальных артефактов.
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Act - изменяем ширину календаря
            old_width = legend.calendar_width
            legend.update_calendar_width(calendar_width)
            
            # Assert - проверяем стабильность
            
            # 1. Легенда должна принять новую ширину
            assert legend.calendar_width == calendar_width, \
                f"Ширина легенды должна быть {calendar_width}, получено {legend.calendar_width}"
            
            # 2. Легенда должна корректно определить режим отображения
            required_width = legend._calculate_required_width()
            expected_full_mode = calendar_width >= required_width
            actual_full_mode = legend._should_show_full_legend()
            
            assert actual_full_mode == expected_full_mode, \
                f"Режим отображения должен быть {'полный' if expected_full_mode else 'компактный'} " \
                f"для ширины {calendar_width} (требуется {required_width})"
            
            # 3. Легенда должна корректно строить UI без ошибок
            try:
                if actual_full_mode:
                    content = legend._build_full_legend()
                else:
                    content = legend._build_compact_legend()
                
                assert isinstance(content, ft.Row), \
                    f"Контент легенды должен быть Row, получено {type(content)}"
                assert len(content.controls) > 0, \
                    "Контент легенды должен содержать элементы"
                
            except Exception as e:
                assert False, f"Построение UI легенды не должно вызывать ошибок: {e}"
            
            # 4. Все индикаторы должны оставаться доступными
            assert legend.all_indicators is not None, \
                "Индикаторы легенды должны оставаться доступными"
            assert len(legend.all_indicators) >= 7, \
                f"Должно быть минимум 7 индикаторов, найдено {len(legend.all_indicators)}"
            
            # 5. При компактном режиме должна быть кнопка "Подробнее"
            if not actual_full_mode:
                compact_content = legend._build_compact_legend()
                button_found = False
                
                for control in compact_content.controls:
                    if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                        button_found = True
                        break
                
                assert button_found, \
                    "В компактном режиме должна быть кнопка 'Подробнее'"
            
            # 6. Модальное окно должно оставаться функциональным
            assert legend.modal_manager is not None, \
                "ModalManager должен оставаться доступным"
            
            try:
                modal = legend.modal_manager.create_modal(legend.all_indicators)
                assert modal is not None, \
                    "Модальное окно должно создаваться без ошибок"
            except Exception as e:
                assert False, f"Создание модального окна не должно вызывать ошибок: {e}"

    def test_integration_error_handling(self):
        """
        Тест обработки ошибок в интеграции CalendarLegend с HomeView.
        
        Проверяет:
        - Устойчивость к ошибкам инициализации
        - Корректную обработку отсутствующих компонентов
        - Fallback поведение при ошибках
        """
        # Arrange & Act & Assert
        
        # 1. Тест с некорректной сессией
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = None  # Некорректная сессия
            mock_get_db.return_value.__exit__.return_value = None
            
            try:
                home_view = HomeView(self.mock_page, None)
                
                # Проверяем, что компоненты все равно создались
                self.assertIsNotNone(home_view.legend,
                                   "CalendarLegend должен создаваться даже при проблемах с сессией")
                self.assertIsNotNone(home_view.calendar_widget,
                                   "CalendarWidget должен создаваться даже при проблемах с сессией")
                
            except Exception as e:
                self.fail(f"HomeView должен обрабатывать ошибки инициализации корректно: {e}")
        
        # 2. Тест с некорректным page объектом
        broken_page = Mock()
        broken_page.overlay = None  # Некорректный overlay
        
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            try:
                home_view = HomeView(broken_page, self.mock_session)
                
                # Проверяем, что легенда может работать с некорректным page
                legend = home_view.legend
                self.assertIsNotNone(legend)
                
                # Тестируем безопасное открытие модального окна
                mock_event = Mock()
                mock_event.control = None
                
                # Не должно вызывать исключений
                legend._open_modal_safe(mock_event)
                
            except Exception as e:
                self.fail(f"Интеграция должна быть устойчива к некорректным page объектам: {e}")
        
        # 3. Тест восстановления после ошибок
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Симулируем ошибку в легенде
            original_method = legend._build_full_legend
            
            def failing_method():
                raise Exception("Тестовая ошибка")
            
            legend._build_full_legend = failing_method
            
            # Проверяем, что система может восстановиться
            try:
                legend._initialize_ui()
                
                # Восстанавливаем оригинальный метод
                legend._build_full_legend = original_method
                
                # Проверяем, что система снова работает
                legend._initialize_ui()
                self.assertIsNotNone(legend.content,
                                   "Легенда должна восстанавливаться после ошибок")
                
            except Exception as e:
                # Восстанавливаем метод в любом случае
                legend._build_full_legend = original_method
                self.fail(f"Система должна восстанавливаться после ошибок: {e}")
            
            # 3. Все индикаторы должны оставаться доступными
            self.assertGreaterEqual(len(legend.all_indicators), 7,
                                  "Все индикаторы должны оставаться доступными")
            
            # 4. Модальное окно должно создаваться без проблем
            try:
                modal = legend.modal_manager.create_modal(legend.all_indicators)
                self.assertIsNotNone(modal, "Модальное окно должно создаваться с большими данными")
            except Exception as e:
                self.fail(f"Создание модального окна не должно падать с большими данными: {e}")


if __name__ == '__main__':
    unittest.main()