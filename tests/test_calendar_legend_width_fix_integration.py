"""
Интеграционные тесты для исправлений календарной легенды.

Проверяет интеграцию исправлений ширины календарной легенды с HomeView,
полный цикл работы легенды с исправленными ширинами, адаптивное поведение
при изменении размеров окна.
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
from finance_tracker.components.width_calculator import WidthCalculator
from finance_tracker.components.page_access_manager import PageAccessManager
from finance_tracker.components.modal_manager import ModalManager
from finance_tracker.components.calendar_legend_types import IndicatorType
from finance_tracker.models.models import TransactionDB, CategoryDB
from finance_tracker.models.enums import TransactionType


class TestCalendarLegendWidthFixIntegration(unittest.TestCase):
    """Интеграционные тесты для исправлений календарной легенды."""

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

    def test_full_cycle_with_fixed_widths(self):
        """
        Тест полного цикла работы легенды с исправленными ширинами.
        
        Проверяет:
        - Создание легенды с реалистичными оценками ширины
        - Корректное определение режима отображения
        - Работу кнопки "Подробнее" с исправленным доступом к page
        - Полный цикл: создание → отображение → клик → модальное окно
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView с исправленными компонентами
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Act & Assert - проверяем полный цикл
            
            # 1. Проверяем, что легенда создана с исправленными компонентами
            self.assertIsNotNone(legend, "CalendarLegend должен быть создан")
            # WidthCalculator используется как статический класс, проверяем его доступность
            self.assertTrue(hasattr(WidthCalculator, 'calculate_width_with_fallback'),
                          "WidthCalculator должен иметь метод calculate_width_with_fallback")
            self.assertIsInstance(legend.page_access_manager, PageAccessManager,
                                "Должен использоваться PageAccessManager")
            self.assertIsInstance(legend.modal_manager, ModalManager,
                                "Должен использоваться ModalManager")
            
            # 2. Проверяем реалистичные оценки ширины
            total_width = legend._calculate_required_width()
            
            # С исправленными оценками общая ширина должна быть около 525px
            self.assertLessEqual(total_width, 600,
                               f"Общая требуемая ширина должна быть ≤ 600px, получено {total_width}px")
            self.assertGreaterEqual(total_width, 450,
                                  f"Общая требуемая ширина должна быть ≥ 450px, получено {total_width}px")
            
            # 3. Проверяем корректное определение режима отображения
            # При ширине календаря 600px должен быть полный режим
            legend.update_calendar_width(600)
            self.assertTrue(legend._should_show_full_legend(),
                          "При ширине 600px должен быть полный режим отображения")
            
            # При ширине календаря 400px должен быть компактный режим
            legend.update_calendar_width(400)
            self.assertFalse(legend._should_show_full_legend(),
                           "При ширине 400px должен быть компактный режим отображения")
            
            # 4. Проверяем работу кнопки "Подробнее"
            # Устанавливаем компактный режим
            legend.update_calendar_width(400)
            compact_content = legend._build_compact_legend()
            
            # Находим кнопку "Подробнее"
            details_button = None
            for control in compact_content.controls:
                if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                    details_button = control
                    break
            
            self.assertIsNotNone(details_button, "Кнопка 'Подробнее' должна присутствовать в компактном режиме")
            self.assertIsNotNone(details_button.on_click, "Кнопка 'Подробнее' должна иметь обработчик клика")
            
            # 5. Проверяем открытие модального окна
            # Симулируем клик по кнопке "Подробнее"
            mock_event = Mock()
            mock_event.control = Mock()
            mock_event.control.page = self.mock_page
            
            # Кнопка должна открывать модальное окно без ошибок
            try:
                details_button.on_click(mock_event)
                
                # Проверяем, что page.open() был вызван (современный Flet API)
                self.mock_page.open.assert_called_once()
                
                # Проверяем, что был передан диалог AlertDialog
                call_args = self.mock_page.open.call_args[0]
                self.assertEqual(len(call_args), 1, "page.open() должен быть вызван с одним аргументом")
                self.assertIsInstance(call_args[0], ft.AlertDialog,
                                    "page.open() должен быть вызван с AlertDialog")
                
            except Exception as e:
                self.fail(f"Клик по кнопке 'Подробнее' не должен вызывать ошибок: {e}")

    def test_integration_with_home_view_and_calendar_widget(self):
        """
        Тест интеграции с HomeView и календарным виджетом.
        
        Проверяет:
        - Корректную передачу ширины календаря из HomeView
        - Синхронизацию между календарём и легендой
        - Обновление легенды при изменении данных календаря
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            calendar_widget = home_view.calendar_widget
            legend = home_view.legend
            
            # Act & Assert - проверяем интеграцию
            
            # 1. Проверяем передачу ширины календаря из HomeView
            initial_width = legend.calendar_width
            self.assertGreater(initial_width, 0, "Ширина календаря должна быть передана из HomeView")
            
            # 2. Проверяем метод обновления ширины календаря в HomeView
            test_width = 800
            self.mock_page.width = 1400  # Увеличиваем ширину страницы
            
            home_view.update_calendar_width()
            updated_width = legend.calendar_width
            
            # Ширина должна пересчитаться на основе новой ширины страницы
            self.assertNotEqual(initial_width, updated_width,
                              "Ширина календаря должна обновляться при изменении размеров страницы")
            
            # 3. Проверяем синхронизацию индикаторов между календарём и легендой
            test_date = date(2024, 12, 11)
            
            # Создаем тестовые транзакции
            mock_transactions = [
                Mock(date=test_date, type=TransactionType.INCOME, amount=Decimal('100')),
                Mock(date=test_date, type=TransactionType.EXPENSE, amount=Decimal('50'))
            ]
            
            # Обновляем данные календаря
            calendar_widget.set_transactions(mock_transactions, [])
            
            # Проверяем, что легенда остается корректной
            legend_indicators = legend.all_indicators
            self.assertGreaterEqual(len(legend_indicators), 7,
                                  "Легенда должна содержать все индикаторы после обновления данных календаря")
            
            # 4. Проверяем консистентность цветов между календарём и легендой
            income_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.INCOME_DOT), 
                None
            )
            expense_indicator = next(
                (ind for ind in legend_indicators if ind.type == IndicatorType.EXPENSE_DOT), 
                None
            )
            
            self.assertIsNotNone(income_indicator, "Индикатор доходов должен быть в легенде")
            self.assertIsNotNone(expense_indicator, "Индикатор расходов должен быть в легенде")
            
            # Цвета должны соответствовать календарю
            self.assertEqual(income_indicator.visual_element.bgcolor, ft.Colors.GREEN,
                           "Цвет индикатора доходов должен соответствовать календарю")
            self.assertEqual(expense_indicator.visual_element.bgcolor, ft.Colors.RED,
                           "Цвет индикатора расходов должен соответствовать календарю")

    def test_adaptive_behavior_on_window_resize(self):
        """
        Тест адаптивного поведения при изменении размеров окна.
        
        Проверяет:
        - Переключение между полным и компактным режимами
        - Стабильность при множественных изменениях размера
        - Корректное обновление UI при изменении режима
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Act & Assert - проверяем адаптивное поведение
            
            # 1. Тестируем переключение с широкого на узкое окно
            # Широкое окно - должен быть полный режим
            wide_width = 800
            legend.update_calendar_width(wide_width)
            
            self.assertTrue(legend._should_show_full_legend(),
                          "При широком окне должен быть полный режим")
            
            full_content = legend._build_full_legend()
            self.assertIsInstance(full_content, ft.Row, "Полный режим должен возвращать Row")
            
            # Проверяем, что в полном режиме нет кнопки "Подробнее"
            details_button_found = False
            for control in full_content.controls:
                if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                    details_button_found = True
                    break
            
            self.assertFalse(details_button_found,
                           "В полном режиме не должно быть кнопки 'Подробнее'")
            
            # 2. Узкое окно - должен быть компактный режим
            narrow_width = 400
            legend.update_calendar_width(narrow_width)
            
            self.assertFalse(legend._should_show_full_legend(),
                           "При узком окне должен быть компактный режим")
            
            compact_content = legend._build_compact_legend()
            self.assertIsInstance(compact_content, ft.Row, "Компактный режим должен возвращать Row")
            
            # Проверяем, что в компактном режиме есть кнопка "Подробнее"
            details_button_found = False
            for control in compact_content.controls:
                if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                    details_button_found = True
                    break
            
            self.assertTrue(details_button_found,
                          "В компактном режиме должна быть кнопка 'Подробнее'")
            
            # 3. Тестируем граничные значения
            # Ширина чуть меньше порога - компактный режим
            threshold_width = legend._calculate_required_width()
            legend.update_calendar_width(threshold_width - 1)
            
            self.assertFalse(legend._should_show_full_legend(),
                           f"При ширине {threshold_width - 1}px должен быть компактный режим")
            
            # Ширина равна порогу - полный режим
            legend.update_calendar_width(threshold_width)
            
            self.assertTrue(legend._should_show_full_legend(),
                          f"При ширине {threshold_width}px должен быть полный режим")
            
            # 4. Тестируем множественные изменения размера
            test_widths = [300, 500, 700, 400, 600, 350, 800]
            
            for width in test_widths:
                try:
                    legend.update_calendar_width(width)
                    
                    # Проверяем, что легенда остается стабильной
                    self.assertEqual(legend.calendar_width, width,
                                   f"Ширина должна быть установлена в {width}px")
                    
                    # Проверяем, что UI строится без ошибок
                    if legend._should_show_full_legend():
                        content = legend._build_full_legend()
                    else:
                        content = legend._build_compact_legend()
                    
                    self.assertIsInstance(content, ft.Row,
                                        f"UI должен строиться корректно при ширине {width}px")
                    self.assertGreater(len(content.controls), 0,
                                     f"UI должен содержать элементы при ширине {width}px")
                    
                except Exception as e:
                    self.fail(f"Изменение ширины до {width}px не должно вызывать ошибок: {e}")

    @given(st.integers(min_value=300, max_value=1200))
    @settings(max_examples=50, deadline=None)
    def test_property_responsive_integration_stability(self, calendar_width):
        """
        **Feature: calendar-legend-width-fix, Property: Responsive integration stability**
        **Validates: Requirements 4.1, 4.3**
        
        Property: При любом изменении ширины календаря интеграция между HomeView 
        и CalendarLegend должна оставаться стабильной без ошибок или потери функциональности.
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Act - изменяем ширину календаря
            legend.update_calendar_width(calendar_width)
            
            # Assert - проверяем стабильность интеграции
            
            # 1. Легенда должна принять новую ширину
            assert legend.calendar_width == calendar_width, \
                f"Ширина календаря должна быть {calendar_width}, получено {legend.calendar_width}"
            
            # 2. Все компоненты должны оставаться инициализированными
            # WidthCalculator используется как статический класс
            assert hasattr(WidthCalculator, 'calculate_width_with_fallback'), \
                "WidthCalculator должен оставаться доступным"
            assert legend.page_access_manager is not None, \
                "PageAccessManager должен оставаться доступным"
            assert legend.modal_manager is not None, \
                "ModalManager должен оставаться доступным"
            
            # 3. Вычисления ширины должны работать корректно
            try:
                required_width = legend._calculate_required_width()
                assert isinstance(required_width, int), \
                    f"Требуемая ширина должна быть целым числом, получено {type(required_width)}"
                assert required_width > 0, \
                    f"Требуемая ширина должна быть положительной, получено {required_width}"
            except Exception as e:
                assert False, f"Вычисление требуемой ширины не должно вызывать ошибок: {e}"
            
            # 4. Определение режима отображения должно работать
            try:
                should_show_full = legend._should_show_full_legend()
                assert isinstance(should_show_full, bool), \
                    f"Результат определения режима должен быть bool, получено {type(should_show_full)}"
            except Exception as e:
                assert False, f"Определение режима отображения не должно вызывать ошибок: {e}"
            
            # 5. UI должен строиться без ошибок
            try:
                if legend._should_show_full_legend():
                    content = legend._build_full_legend()
                else:
                    content = legend._build_compact_legend()
                
                assert isinstance(content, ft.Row), \
                    f"Контент должен быть Row, получено {type(content)}"
                assert len(content.controls) > 0, \
                    "Контент должен содержать элементы"
                
            except Exception as e:
                assert False, f"Построение UI не должно вызывать ошибок: {e}"
            
            # 6. Модальное окно должно создаваться
            try:
                modal = legend.modal_manager.create_modal(legend.all_indicators)
                assert modal is not None, \
                    "Модальное окно должно создаваться"
                assert isinstance(modal, ft.AlertDialog), \
                    f"Модальное окно должно быть AlertDialog, получено {type(modal)}"
            except Exception as e:
                assert False, f"Создание модального окна не должно вызывать ошибок: {e}"
            
            # 7. Кнопка "Подробнее" должна работать в компактном режиме
            if not legend._should_show_full_legend():
                try:
                    compact_content = legend._build_compact_legend()
                    details_button = None
                    
                    for control in compact_content.controls:
                        if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                            details_button = control
                            break
                    
                    assert details_button is not None, \
                        "В компактном режиме должна быть кнопка 'Подробнее'"
                    assert details_button.on_click is not None, \
                        "Кнопка 'Подробнее' должна иметь обработчик клика"
                    
                    # Тестируем клик по кнопке
                    mock_event = Mock()
                    mock_event.control = Mock()
                    mock_event.control.page = self.mock_page
                    
                    # Не должно вызывать исключений
                    details_button.on_click(mock_event)
                    
                except Exception as e:
                    assert False, f"Кнопка 'Подробнее' должна работать без ошибок: {e}"

    def test_error_recovery_in_integration(self):
        """
        Тест восстановления после ошибок в интеграции.
        
        Проверяет:
        - Устойчивость к ошибкам в компонентах
        - Fallback поведение при недоступности page
        - Восстановление функциональности после ошибок
        """
        # Arrange
        with patch('finance_tracker.database.get_db_session') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = self.mock_session
            mock_get_db.return_value.__exit__.return_value = None
            
            # Создаем HomeView
            home_view = HomeView(self.mock_page, self.mock_session)
            legend = home_view.legend
            
            # Act & Assert - тестируем восстановление после ошибок
            
            # 1. Тест с недоступным page объектом
            # Симулируем ситуацию, когда page недоступен
            broken_page = Mock()
            broken_page.open = Mock(side_effect=Exception("Page недоступен"))
            
            # Устанавливаем компактный режим для тестирования кнопки "Подробнее"
            legend.update_calendar_width(400)
            compact_content = legend._build_compact_legend()
            
            details_button = None
            for control in compact_content.controls:
                if isinstance(control, ft.TextButton) and "Подробнее" in control.text:
                    details_button = control
                    break
            
            self.assertIsNotNone(details_button, "Кнопка 'Подробнее' должна быть найдена")
            
            # Симулируем клик с недоступным page
            mock_event = Mock()
            mock_event.control = Mock()
            mock_event.control.page = broken_page
            
            # Клик не должен вызывать необработанных исключений
            try:
                details_button.on_click(mock_event)
                # Система должна обработать ошибку gracefully
            except Exception as e:
                self.fail(f"Клик по кнопке с недоступным page не должен вызывать необработанных исключений: {e}")
            
            # 2. Тест восстановления после ошибки в WidthCalculator
            # WidthCalculator используется как статический класс, тестируем через патчинг
            original_calculate = WidthCalculator.calculate_width_with_fallback
            
            def failing_calculate(indicators):
                raise Exception("Ошибка в WidthCalculator")
            
            WidthCalculator.calculate_width_with_fallback = failing_calculate
            
            # Система должна использовать fallback
            try:
                required_width = legend._calculate_required_width()
                self.assertIsInstance(required_width, int, "Должен быть возвращен fallback результат")
                self.assertGreater(required_width, 0, "Fallback результат должен быть положительным")
            except Exception as e:
                self.fail(f"Система должна использовать fallback при ошибке в WidthCalculator: {e}")
            finally:
                # Восстанавливаем оригинальный метод
                WidthCalculator.calculate_width_with_fallback = original_calculate
            
            # 3. Тест восстановления функциональности
            # После восстановления все должно работать нормально
            legend.update_calendar_width(600)
            
            try:
                # Проверяем, что все компоненты снова работают
                required_width = legend._calculate_required_width()
                should_show_full = legend._should_show_full_legend()
                content = legend._build_full_legend() if should_show_full else legend._build_compact_legend()
                modal = legend.modal_manager.create_modal(legend.all_indicators)
                
                self.assertIsInstance(required_width, int, "Вычисление ширины должно восстановиться")
                self.assertIsInstance(should_show_full, bool, "Определение режима должно восстановиться")
                self.assertIsInstance(content, ft.Row, "Построение UI должно восстановиться")
                self.assertIsInstance(modal, ft.AlertDialog, "Создание модального окна должно восстановиться")
                
            except Exception as e:
                self.fail(f"Функциональность должна восстанавливаться после ошибок: {e}")


if __name__ == '__main__':
    unittest.main()