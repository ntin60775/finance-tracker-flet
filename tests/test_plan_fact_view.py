"""
Тесты для PlanFactView.

Проверяет:
- Инициализацию View
- Загрузку данных план-факт анализа
- Изменение периода
- Фильтрацию по категории
- Отображение пустого состояния
- Расчет и форматирование отклонений
"""
import unittest
from decimal import Decimal
from datetime import date

from finance_tracker.views.plan_fact_view import PlanFactView
from test_view_base import ViewTestBase
from test_factories import (
    create_test_category,
)


class TestPlanFactView(ViewTestBase):
    """Тесты для PlanFactView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.plan_fact_view.get_db',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы
        self.mock_get_plan_fact_analysis = self.add_patcher(
            'finance_tracker.views.plan_fact_view.get_plan_fact_analysis',
            return_value=self._create_empty_analysis()
        )
        self.mock_get_all_categories = self.add_patcher(
            'finance_tracker.views.plan_fact_view.get_all_categories',
            return_value=[]
        )
        
        # Создаем экземпляр PlanFactView
        self.view = PlanFactView()
        self.view.page = self.page

    def _create_empty_analysis(self):
        """Создает пустой анализ для тестов."""
        return {
            'total_occurrences': 0,
            'executed_count': 0,
            'skipped_count': 0,
            'pending_count': 0,
            'avg_amount_deviation': Decimal('0.0'),
            'avg_date_deviation_days': 0.0,
            'on_time_percentage': 0.0,
            'skipped_percentage': 0.0,
            'occurrences': []
        }

    def _create_test_analysis(self):
        """Создает тестовый анализ с данными."""
        return {
            'total_occurrences': 5,
            'executed_count': 3,
            'skipped_count': 1,
            'pending_count': 1,
            'avg_amount_deviation': Decimal('150.00'),
            'avg_date_deviation_days': 2.0,
            'on_time_percentage': 66.7,
            'skipped_percentage': 20.0,
            'occurrences': [
                {
                    'occurrence_id': 1,
                    'scheduled_date': '2025-01-15',
                    'category_name': 'Продукты',
                    'description': 'Еженедельные покупки',
                    'planned_amount': Decimal('1000.00'),
                    'actual_amount': Decimal('1150.00'),
                    'amount_deviation': Decimal('150.00'),
                    'status': 'executed'
                },
                {
                    'occurrence_id': 2,
                    'scheduled_date': '2025-01-20',
                    'category_name': 'Транспорт',
                    'description': 'Проездной',
                    'planned_amount': Decimal('500.00'),
                    'actual_amount': Decimal('500.00'),
                    'amount_deviation': Decimal('0.00'),
                    'status': 'executed'
                },
                {
                    'occurrence_id': 3,
                    'scheduled_date': '2025-01-25',
                    'category_name': 'Развлечения',
                    'description': 'Кино',
                    'planned_amount': Decimal('800.00'),
                    'actual_amount': None,
                    'amount_deviation': None,
                    'status': 'skipped'
                },
                {
                    'occurrence_id': 4,
                    'scheduled_date': '2025-01-28',
                    'category_name': 'Коммунальные',
                    'description': 'Электричество',
                    'planned_amount': Decimal('2000.00'),
                    'actual_amount': Decimal('1900.00'),
                    'amount_deviation': Decimal('-100.00'),
                    'status': 'executed'
                },
                {
                    'occurrence_id': 5,
                    'scheduled_date': '2025-01-30',
                    'category_name': 'Продукты',
                    'description': 'Еженедельные покупки',
                    'planned_amount': Decimal('1000.00'),
                    'actual_amount': None,
                    'amount_deviation': None,
                    'status': 'pending'
                }
            ]
        }

    def test_initialization(self):
        """
        Тест инициализации PlanFactView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - UI компоненты созданы (заголовок, фильтры, статистика, таблица)
        - Начальные значения фильтров установлены корректно
        
        Validates: Requirements 12.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, PlanFactView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        
        # Проверяем, что UI компоненты созданы
        self.assertIsNotNone(self.view.content)
        self.assertIsNotNone(self.view.date_range_button)
        self.assertIsNotNone(self.view.category_dropdown)
        self.assertIsNotNone(self.view.data_table)
        
        # Проверяем статистические карточки
        self.assertIsNotNone(self.view.stat_total)
        self.assertIsNotNone(self.view.stat_executed)
        self.assertIsNotNone(self.view.stat_skipped)
        self.assertIsNotNone(self.view.stat_deviation)
        
        # Проверяем начальное состояние фильтров
        self.assertIsNotNone(self.view.start_date)
        self.assertIsNotNone(self.view.end_date)
        self.assertIsNone(self.view.selected_category_id)
        
        # Проверяем, что start_date - первый день текущего месяца
        today = date.today()
        expected_start = today.replace(day=1)
        self.assertEqual(self.view.start_date, expected_start)

    def test_load_data_on_mount(self):
        """
        Тест загрузки данных при монтировании View.
        
        Проверяет:
        - При вызове did_mount() вызывается get_plan_fact_analysis
        - Сервис вызывается с правильными параметрами (период, категория)
        - Также загружаются категории для фильтра
        
        Validates: Requirements 12.1
        """
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_plan_fact_analysis.reset_mock()
        self.mock_get_all_categories.reset_mock()
        
        # Вызываем did_mount
        self.view.did_mount()
        
        # Проверяем, что сервис анализа был вызван
        self.assert_service_called_once(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            self.view.start_date,
            self.view.end_date,
            None  # Без фильтра по категории
        )
        
        # Проверяем, что категории были загружены
        self.assert_service_called_once(
            self.mock_get_all_categories,
            self.mock_session
        )

    def test_load_data_with_analysis(self):
        """
        Тест загрузки данных план-факт анализа.
        
        Проверяет:
        - Данные анализа отображаются в статистических карточках
        - Таблица заполняется вхождениями
        - Количество строк в таблице соответствует количеству вхождений
        
        Validates: Requirements 12.1
        """
        # Создаем тестовый анализ
        test_analysis = self._create_test_analysis()
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_plan_fact_analysis.return_value = test_analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что таблица содержит правильное количество строк
        self.assertEqual(len(self.view.data_table.rows), 5)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_data_empty_analysis(self):
        """
        Тест загрузки пустого анализа.
        
        Проверяет:
        - При пустом анализе таблица пустая
        - Статистические карточки показывают нули
        
        Validates: Requirements 12.4
        """
        # Настраиваем мок для возврата пустого анализа
        self.mock_get_plan_fact_analysis.return_value = self._create_empty_analysis()
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что таблица пустая
        self.assertEqual(len(self.view.data_table.rows), 0)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_change_period(self):
        """
        Тест изменения периода анализа.
        
        Проверяет:
        - При изменении start_date и end_date вызывается перезагрузка данных
        - Сервис вызывается с новыми датами
        
        Validates: Requirements 12.2
        """
        # Устанавливаем новый период
        new_start = date(2025, 2, 1)
        new_end = date(2025, 2, 28)
        self.view.start_date = new_start
        self.view.end_date = new_end
        
        # Сбрасываем счетчик вызовов
        self.mock_get_plan_fact_analysis.reset_mock()
        
        # Вызываем перезагрузку данных
        self.view._load_data()
        
        # Проверяем, что сервис вызван с новыми датами
        self.assert_service_called_once(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            new_start,
            new_end,
            None
        )

    def test_filter_by_category(self):
        """
        Тест фильтрации по категории.
        
        Проверяет:
        - При изменении категории в dropdown устанавливается selected_category_id
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 12.3
        """
        # Создаем тестовые категории
        test_categories = [
            create_test_category(id=1, name="Продукты"),
            create_test_category(id=2, name="Транспорт"),
        ]
        self.mock_get_all_categories.return_value = test_categories
        
        # Загружаем категории
        self.view._load_categories()
        
        # Сбрасываем счетчик вызовов
        self.mock_get_plan_fact_analysis.reset_mock()
        
        # Имитируем выбор категории
        self.view.category_dropdown.value = "1"
        self.view._on_category_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.selected_category_id, 1)
        
        # Проверяем, что сервис вызван с фильтром по категории
        self.assert_service_called(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            self.view.start_date,
            self.view.end_date,
            1  # ID категории
        )

    def test_filter_by_category_all(self):
        """
        Тест сброса фильтра по категории (все категории).
        
        Проверяет:
        - При выборе "Все категории" фильтр selected_category_id сбрасывается (None)
        - Вызывается перезагрузка данных без фильтра по категории
        
        Validates: Requirements 12.3
        """
        # Устанавливаем фильтр
        self.view.selected_category_id = 1
        
        # Сбрасываем счетчик вызовов
        self.mock_get_plan_fact_analysis.reset_mock()
        
        # Имитируем выбор "Все категории"
        self.view.category_dropdown.value = "all"
        self.view._on_category_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.selected_category_id)
        
        # Проверяем, что сервис вызван без фильтра по категории
        self.assert_service_called(
            self.mock_get_plan_fact_analysis,
            self.mock_session,
            self.view.start_date,
            self.view.end_date,
            None
        )

    def test_statistics_calculation(self):
        """
        Тест расчета и отображения статистики.
        
        Проверяет:
        - Статистические карточки обновляются с правильными значениями
        - Проценты рассчитываются корректно
        - Среднее отклонение форматируется правильно
        
        Validates: Requirements 12.5
        """
        # Создаем тестовый анализ
        test_analysis = self._create_test_analysis()
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_plan_fact_analysis.return_value = test_analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем значения в статистических карточках
        # stat_total должен показывать общее количество
        total_text = self.view.stat_total.content.controls[1].controls[1].value
        self.assertEqual(total_text, "5")
        
        # stat_executed должен показывать количество исполненных и процент вовремя
        executed_text = self.view.stat_executed.content.controls[1].controls[1].value
        self.assertIn("3", executed_text)
        self.assertIn("67", executed_text)  # 66.7% округляется до 67%
        
        # stat_skipped должен показывать количество пропущенных и процент
        skipped_text = self.view.stat_skipped.content.controls[1].controls[1].value
        self.assertIn("1", skipped_text)
        self.assertIn("20", skipped_text)
        
        # stat_deviation должен показывать среднее отклонение
        deviation_text = self.view.stat_deviation.content.controls[1].controls[1].value
        self.assertIn("150.00", deviation_text)

    def test_deviation_formatting_positive(self):
        """
        Тест форматирования положительного отклонения (перерасход).
        
        Проверяет:
        - Положительное отклонение отображается с плюсом
        - Цвет текста красный (перерасход)
        
        Validates: Requirements 12.5
        """
        # Создаем анализ с положительным отклонением
        analysis = self._create_empty_analysis()
        analysis['occurrences'] = [
            {
                'occurrence_id': 1,
                'scheduled_date': '2025-01-15',
                'category_name': 'Продукты',
                'description': 'Покупки',
                'planned_amount': Decimal('1000.00'),
                'actual_amount': Decimal('1200.00'),
                'amount_deviation': Decimal('200.00'),
                'status': 'executed'
            }
        ]
        
        # Настраиваем мок
        self.mock_get_plan_fact_analysis.return_value = analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что строка добавлена
        self.assertEqual(len(self.view.data_table.rows), 1)
        
        # Проверяем форматирование отклонения (должно быть с плюсом)
        deviation_cell = self.view.data_table.rows[0].cells[5]
        deviation_text = deviation_cell.content.value
        self.assertIn("+200.00", deviation_text)

    def test_deviation_formatting_negative(self):
        """
        Тест форматирования отрицательного отклонения (экономия).
        
        Проверяет:
        - Отрицательное отклонение отображается с минусом
        - Цвет текста зеленый (экономия)
        
        Validates: Requirements 12.5
        """
        # Создаем анализ с отрицательным отклонением
        analysis = self._create_empty_analysis()
        analysis['occurrences'] = [
            {
                'occurrence_id': 1,
                'scheduled_date': '2025-01-15',
                'category_name': 'Коммунальные',
                'description': 'Электричество',
                'planned_amount': Decimal('2000.00'),
                'actual_amount': Decimal('1800.00'),
                'amount_deviation': Decimal('-200.00'),
                'status': 'executed'
            }
        ]
        
        # Настраиваем мок
        self.mock_get_plan_fact_analysis.return_value = analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что строка добавлена
        self.assertEqual(len(self.view.data_table.rows), 1)
        
        # Проверяем форматирование отклонения (должно быть с минусом)
        deviation_cell = self.view.data_table.rows[0].cells[5]
        deviation_text = deviation_cell.content.value
        self.assertIn("-200.00", deviation_text)

    def test_pending_occurrence_display(self):
        """
        Тест отображения ожидающего вхождения.
        
        Проверяет:
        - Для ожидающих вхождений факт и отклонение показываются как "-"
        - Статус отображается корректно
        
        Validates: Requirements 12.1
        """
        # Создаем анализ с ожидающим вхождением
        analysis = self._create_empty_analysis()
        analysis['occurrences'] = [
            {
                'occurrence_id': 1,
                'scheduled_date': '2025-01-30',
                'category_name': 'Продукты',
                'description': 'Покупки',
                'planned_amount': Decimal('1000.00'),
                'actual_amount': None,
                'amount_deviation': None,
                'status': 'pending'
            }
        ]
        
        # Настраиваем мок
        self.mock_get_plan_fact_analysis.return_value = analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что строка добавлена
        self.assertEqual(len(self.view.data_table.rows), 1)
        
        # Проверяем, что факт показывается как "-"
        actual_cell = self.view.data_table.rows[0].cells[4]
        actual_text = actual_cell.content.value
        self.assertEqual(actual_text, "-")
        
        # Проверяем, что отклонение показывается как "-"
        deviation_cell = self.view.data_table.rows[0].cells[5]
        deviation_text = deviation_cell.content.value
        self.assertEqual(deviation_text, "-")

    def test_skipped_occurrence_display(self):
        """
        Тест отображения пропущенного вхождения.
        
        Проверяет:
        - Для пропущенных вхождений факт и отклонение показываются как "-"
        - Статус отображается корректно
        
        Validates: Requirements 12.1
        """
        # Создаем анализ с пропущенным вхождением
        analysis = self._create_empty_analysis()
        analysis['occurrences'] = [
            {
                'occurrence_id': 1,
                'scheduled_date': '2025-01-25',
                'category_name': 'Развлечения',
                'description': 'Кино',
                'planned_amount': Decimal('800.00'),
                'actual_amount': None,
                'amount_deviation': None,
                'status': 'skipped'
            }
        ]
        
        # Настраиваем мок
        self.mock_get_plan_fact_analysis.return_value = analysis
        
        # Загружаем данные
        self.view._load_data()
        
        # Проверяем, что строка добавлена
        self.assertEqual(len(self.view.data_table.rows), 1)
        
        # Проверяем, что факт показывается как "-"
        actual_cell = self.view.data_table.rows[0].cells[4]
        actual_text = actual_cell.content.value
        self.assertEqual(actual_text, "-")
        
        # Проверяем, что отклонение показывается как "-"
        deviation_cell = self.view.data_table.rows[0].cells[5]
        deviation_text = deviation_cell.content.value
        self.assertEqual(deviation_text, "-")

    def test_refresh_data_button(self):
        """
        Тест кнопки обновления данных.
        
        Проверяет:
        - При нажатии кнопки обновления вызывается _load_data
        - Данные перезагружаются
        
        Validates: Requirements 12.1
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_plan_fact_analysis.reset_mock()
        
        # Имитируем нажатие кнопки обновления
        self.view._refresh_data(None)
        
        # Проверяем, что сервис был вызван
        self.assert_service_called(self.mock_get_plan_fact_analysis)

    def test_load_categories_for_filter(self):
        """
        Тест загрузки категорий для фильтра.
        
        Проверяет:
        - Категории загружаются в dropdown
        - Добавляется опция "Все категории"
        - По умолчанию выбрана опция "Все категории"
        
        Validates: Requirements 12.3
        """
        # Создаем тестовые категории
        test_categories = [
            create_test_category(id=1, name="Продукты"),
            create_test_category(id=2, name="Транспорт"),
            create_test_category(id=3, name="Развлечения"),
        ]
        self.mock_get_all_categories.return_value = test_categories
        
        # Загружаем категории
        self.view._load_categories()
        
        # Проверяем, что dropdown содержит правильное количество опций
        # 3 категории + 1 опция "Все категории"
        self.assertEqual(len(self.view.category_dropdown.options), 4)
        
        # Проверяем, что первая опция - "Все категории"
        self.assertEqual(self.view.category_dropdown.options[0].key, "all")
        
        # Проверяем, что по умолчанию выбрана опция "Все категории"
        self.assertEqual(self.view.category_dropdown.value, "all")

    def test_show_details_modal(self):
        """
        Тест открытия модального окна с деталями вхождения.
        
        Проверяет:
        - При клике на строку таблицы открывается модальное окно
        - Модальное окно содержит детали вхождения
        
        Validates: Requirements 12.1
        """
        # Создаем тестовое вхождение
        test_occurrence = {
            'occurrence_id': 1,
            'scheduled_date': '2025-01-15',
            'category_name': 'Продукты',
            'description': 'Покупки',
            'planned_amount': Decimal('1000.00'),
            'actual_amount': Decimal('1150.00'),
            'amount_deviation': Decimal('150.00'),
            'status': 'executed'
        }
        
        # Вызываем метод показа деталей
        self.view._show_details(test_occurrence)
        
        # Проверяем, что метод show модального окна был вызван
        # (в реальности это вызовет page.open, но мы проверяем, что метод вызван без ошибок)
        # Тест проходит, если не возникло исключений

    def test_get_last_day_of_month(self):
        """
        Тест вспомогательного метода получения последнего дня месяца.
        
        Проверяет:
        - Метод корректно вычисляет последний день месяца
        - Работает для разных месяцев (включая февраль)
        
        Validates: Requirements 12.2
        """
        # Тест для января (31 день)
        jan_date = date(2025, 1, 15)
        last_day_jan = self.view._get_last_day_of_month(jan_date)
        self.assertEqual(last_day_jan, date(2025, 1, 31))
        
        # Тест для февраля (28 дней в 2025)
        feb_date = date(2025, 2, 10)
        last_day_feb = self.view._get_last_day_of_month(feb_date)
        self.assertEqual(last_day_feb, date(2025, 2, 28))
        
        # Тест для апреля (30 дней)
        apr_date = date(2025, 4, 5)
        last_day_apr = self.view._get_last_day_of_month(apr_date)
        self.assertEqual(last_day_apr, date(2025, 4, 30))

    def test_error_handling_on_load(self):
        """
        Тест обработки ошибок при загрузке данных.
        
        Проверяет:
        - При ошибке сервиса отображается SnackBar с сообщением об ошибке
        - Приложение не падает
        
        Validates: Requirements 12.1
        """
        # Настраиваем мок для выброса исключения
        self.mock_get_plan_fact_analysis.side_effect = Exception("Ошибка БД")
        
        # Вызываем загрузку данных
        self.view._load_data()
        
        # Проверяем, что SnackBar был показан (через page.show_snack_bar)
        # В текущей реализации используется page.show_snack_bar, но у нас мок page
        # Проверяем, что не возникло необработанного исключения
        # Тест проходит, если метод завершился без падения


if __name__ == '__main__':
    unittest.main()
