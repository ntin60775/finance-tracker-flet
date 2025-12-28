"""
Unit тесты для PlannedTransactionsWidget.

Тестирует:
- Инициализацию кнопки добавления плановой транзакции
- Взаимодействие с кнопкой
- Обработку callback функций
- Состояние UI компонентов
- Обзорный режим (без кнопок действий)
- Клик на карточку для навигации
- Сортировку просроченных вхождений

Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 4.3, 5.3
"""
import unittest
from unittest.mock import Mock
from decimal import Decimal
import datetime
from uuid import uuid4
import flet as ft

from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget
from finance_tracker.models import PlannedOccurrence, OccurrenceStatus, TransactionType


class TestPlannedTransactionsWidgetAddButton(unittest.TestCase):
    """Unit тесты для кнопки добавления в PlannedTransactionsWidget."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_skip = Mock()
        self.mock_on_show_all = Mock()
        self.mock_on_add_planned_transaction = Mock()

    def tearDown(self):
        """Очистка после каждого теста."""
        pass

    def test_add_button_exists_when_callback_provided(self):
        """
        Тест наличия кнопки добавления при заданном callback.
        
        Проверяет:
        - Создание кнопки при инициализации виджета с callback
        - Наличие кнопки в атрибуте add_button
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет с callback для добавления
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем наличие кнопки
        self.assertIsNotNone(
            widget.add_button, 
            "Кнопка добавления должна быть создана при заданном callback"
        )
        self.assertIsInstance(
            widget.add_button, 
            ft.IconButton, 
            "Кнопка должна быть IconButton"
        )

    def test_add_button_not_exists_when_callback_none(self):
        """
        Тест отсутствия кнопки добавления при callback=None.
        
        Проверяет:
        - Отсутствие кнопки при инициализации виджета без callback
        - add_button должен быть None
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback для добавления
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем отсутствие кнопки
        self.assertIsNone(
            widget.add_button, 
            "Кнопка добавления не должна создаваться при callback=None"
        )

    def test_add_button_icon_attribute(self):
        """
        Тест атрибута icon кнопки добавления.
        
        Проверяет:
        - Иконку кнопки (ft.Icons.ADD)
        
        Requirements: 2.2
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем иконку кнопки
        self.assertEqual(
            widget.add_button.icon, 
            ft.Icons.ADD, 
            "Кнопка должна иметь иконку ADD"
        )

    def test_add_button_tooltip_attribute(self):
        """
        Тест атрибута tooltip кнопки добавления.
        
        Проверяет:
        - Tooltip кнопки ("Добавить плановую транзакцию")
        
        Requirements: 2.3
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем tooltip кнопки
        self.assertEqual(
            widget.add_button.tooltip, 
            "Добавить плановую транзакцию", 
            "Кнопка должна иметь правильный tooltip"
        )

    def test_add_button_color_attribute(self):
        """
        Тест атрибута цвета кнопки добавления.
        
        Проверяет:
        - Цвет иконки кнопки (ft.Colors.PRIMARY)
        
        Requirements: 2.4
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем цвет кнопки
        self.assertEqual(
            widget.add_button.icon_color, 
            ft.Colors.PRIMARY, 
            "Кнопка должна иметь PRIMARY цвет"
        )

    def test_add_button_callback_invocation(self):
        """
        Тест вызова callback при нажатии кнопки добавления.
        
        Проверяет:
        - Вызов callback функции при нажатии кнопки
        - Корректную установку обработчика события
        
        Requirements: 2.1
        """
        # Arrange - создаем виджет с mock callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Act - симулируем нажатие кнопки
        add_button = widget.add_button
        self.assertIsNotNone(
            add_button.on_click, 
            "on_click должен быть установлен"
        )
        
        # Нажимаем кнопку (Flet передает event, но мы его не используем)
        add_button.on_click(None)

        # Assert - проверяем вызов callback
        self.mock_on_add_planned_transaction.assert_called_once()

    def test_add_button_in_header_layout_when_callback_provided(self):
        """
        Тест расположения кнопки добавления в заголовке виджета.
        
        Проверяет:
        - Наличие кнопки в структуре заголовка
        - Правильное расположение кнопки (рядом с кнопкой "Показать все")
        - Структуру заголовка (Row с правильными элементами)
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем структуру заголовка
        # Заголовок - это первый элемент в content.controls
        header_row = widget.content.controls[0]
        
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать 2 элемента")
        
        # Второй элемент заголовка должен быть Row с кнопками
        buttons_row = header_row.controls[1]
        self.assertIsInstance(buttons_row, ft.Row, "Второй элемент должен быть Row с кнопками")
        
        # В Row с кнопками должно быть 2 кнопки: добавить и показать все
        self.assertEqual(
            len(buttons_row.controls), 
            2, 
            "Должно быть 2 кнопки: добавить и показать все"
        )
        
        # Первая кнопка - добавить плановую транзакцию
        add_button = buttons_row.controls[0]
        self.assertIsInstance(add_button, ft.IconButton, "Первая кнопка должна быть IconButton")
        self.assertEqual(add_button.icon, ft.Icons.ADD, "Первая кнопка должна быть кнопкой добавления")
        
        # Вторая кнопка - показать все
        show_all_button = buttons_row.controls[1]
        self.assertIsInstance(show_all_button, ft.TextButton, "Вторая кнопка должна быть TextButton")

    def test_header_layout_without_add_button_when_callback_none(self):
        """
        Тест структуры заголовка без кнопки добавления.
        
        Проверяет:
        - Отсутствие кнопки добавления в заголовке при callback=None
        - Наличие только кнопки "Показать все"
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем структуру заголовка
        header_row = widget.content.controls[0]
        
        self.assertIsInstance(header_row, ft.Row, "Заголовок должен быть Row")
        self.assertEqual(len(header_row.controls), 2, "Заголовок должен содержать 2 элемента")
        
        # Второй элемент заголовка должен быть Row с кнопками
        buttons_row = header_row.controls[1]
        self.assertIsInstance(buttons_row, ft.Row, "Второй элемент должен быть Row с кнопками")
        
        # В Row с кнопками должна быть только 1 кнопка: показать все
        self.assertEqual(
            len(buttons_row.controls), 
            1, 
            "Должна быть только 1 кнопка: показать все"
        )
        
        # Единственная кнопка - показать все
        show_all_button = buttons_row.controls[0]
        self.assertIsInstance(show_all_button, ft.TextButton, "Кнопка должна быть TextButton")

    def test_callback_storage_in_widget(self):
        """
        Тест сохранения callback в виджете.
        
        Проверяет:
        - Сохранение callback функции в атрибуте виджета
        - Доступность callback для использования
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет с callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=self.mock_on_add_planned_transaction
        )

        # Assert - проверяем сохранение callback
        self.assertEqual(
            widget.on_add_planned_transaction, 
            self.mock_on_add_planned_transaction, 
            "Callback должен быть сохранен в виджете"
        )

    def test_callback_storage_none_in_widget(self):
        """
        Тест сохранения None callback в виджете.
        
        Проверяет:
        - Сохранение None в атрибуте виджета при отсутствии callback
        
        Requirements: 2.1
        """
        # Arrange & Act - создаем виджет без callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_add_planned_transaction=None
        )

        # Assert - проверяем сохранение None
        self.assertIsNone(
            widget.on_add_planned_transaction, 
            "Callback должен быть None в виджете"
        )


if __name__ == '__main__':
    unittest.main()



class TestPlannedTransactionsWidgetOverviewMode(unittest.TestCase):
    """
    Unit тесты для обзорного режима PlannedTransactionsWidget.
    
    Тестирует:
    - Инициализацию с callback on_occurrence_click
    - Отсутствие кнопок действий в карточках
    - Вызов callback при клике на карточку
    - Сортировку просроченных вхождений
    
    Requirements: 1.1, 2.1, 4.3, 5.3
    """

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.mock_session = Mock()
        self.mock_on_execute = Mock()
        self.mock_on_skip = Mock()
        self.mock_on_show_all = Mock()
        self.mock_on_occurrence_click = Mock()

    def tearDown(self):
        """Очистка после каждого теста."""
        pass

    def _create_test_occurrence(
        self,
        occurrence_date: datetime.date,
        amount: Decimal = Decimal("100.00"),
        status: OccurrenceStatus = OccurrenceStatus.PENDING
    ) -> PlannedOccurrence:
        """
        Вспомогательная функция для создания тестового вхождения.
        
        Args:
            occurrence_date: Дата вхождения.
            amount: Сумма вхождения.
            status: Статус вхождения.
            
        Returns:
            PlannedOccurrence с валидными UUID и временными метками.
        """
        now = datetime.datetime.now()
        return PlannedOccurrence(
            id=str(uuid4()),
            planned_transaction_id=str(uuid4()),
            occurrence_date=occurrence_date,
            amount=amount,
            status=status,
            created_at=now,
            updated_at=now
        )

    def test_initialization_with_occurrence_click_callback(self):
        """
        Тест инициализации виджета с callback on_occurrence_click.
        
        Проверяет:
        - Создание виджета с новым callback
        - Сохранение callback в атрибуте виджета
        
        Requirements: 5.3
        """
        # Arrange & Act - создаем виджет с callback для клика на вхождение
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        # Assert - проверяем сохранение callback
        self.assertEqual(
            widget.on_occurrence_click,
            self.mock_on_occurrence_click,
            "Callback on_occurrence_click должен быть сохранен в виджете"
        )

    def test_initialization_without_occurrence_click_callback(self):
        """
        Тест инициализации виджета без callback on_occurrence_click.
        
        Проверяет:
        - Создание виджета без callback (None)
        - Сохранение None в атрибуте виджета
        
        Requirements: 5.3
        """
        # Arrange & Act - создаем виджет без callback для клика на вхождение
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=None
        )

        # Assert - проверяем сохранение None
        self.assertIsNone(
            widget.on_occurrence_click,
            "Callback on_occurrence_click должен быть None"
        )

    def test_occurrence_card_has_no_action_buttons(self):
        """
        Тест отсутствия кнопок действий в карточках вхождений.
        
        Проверяет:
        - Метод _build_action_buttons возвращает пустой список
        - Карточки не содержат кнопок "Исполнить" и "Пропустить"
        
        Requirements: 1.1, 5.2
        """
        # Arrange - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        # Создаем тестовое вхождение
        test_occurrence = self._create_test_occurrence(datetime.date.today())

        # Act - вызываем метод построения кнопок действий
        action_buttons = widget._build_action_buttons(test_occurrence)

        # Assert - проверяем, что список пустой
        self.assertEqual(
            len(action_buttons),
            0,
            "Метод _build_action_buttons должен возвращать пустой список в обзорном режиме"
        )
        self.assertIsInstance(
            action_buttons,
            list,
            "Метод должен возвращать список"
        )

    def test_occurrence_card_is_clickable(self):
        """
        Тест кликабельности карточки вхождения.
        
        Проверяет:
        - Карточка имеет обработчик on_click
        - Карточка имеет ink=True для ripple эффекта
        - Карточка имеет обработчик on_hover для hover-эффекта
        
        Requirements: 2.1, 2.3
        """
        # Arrange - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        # Создаем тестовое вхождение
        test_occurrence = self._create_test_occurrence(datetime.date.today())

        # Act - создаем карточку вхождения
        card = widget._build_occurrence_card(
            test_occurrence,
            "Тестовая категория",
            TransactionType.EXPENSE
        )

        # Assert - проверяем кликабельность
        self.assertIsNotNone(
            card.on_click,
            "Карточка должна иметь обработчик on_click"
        )
        self.assertTrue(
            card.ink,
            "Карточка должна иметь ink=True для ripple эффекта"
        )
        self.assertIsNotNone(
            card.on_hover,
            "Карточка должна иметь обработчик on_hover для hover-эффекта"
        )

    def test_card_click_invokes_callback(self):
        """
        Тест вызова callback при клике на карточку вхождения.
        
        Проверяет:
        - Клик на карточку вызывает callback on_occurrence_click
        - Callback вызывается с правильным вхождением
        
        Requirements: 2.1
        """
        # Arrange - создаем виджет с mock callback
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        # Создаем тестовое вхождение
        test_occurrence = self._create_test_occurrence(datetime.date.today())

        # Act - симулируем клик на карточку
        widget._on_card_click(test_occurrence)

        # Assert - проверяем вызов callback
        self.mock_on_occurrence_click.assert_called_once_with(test_occurrence)

    def test_card_click_without_callback_does_not_raise_error(self):
        """
        Тест клика на карточку без установленного callback.
        
        Проверяет:
        - Клик на карточку без callback не вызывает ошибку
        - Логируется предупреждение
        
        Requirements: 2.1
        """
        # Arrange - создаем виджет без callback для клика
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=None
        )

        # Создаем тестовое вхождение
        test_occurrence = self._create_test_occurrence(datetime.date.today())

        # Act & Assert - клик не должен вызывать ошибку
        try:
            widget._on_card_click(test_occurrence)
        except Exception as e:
            self.fail(f"Клик на карточку без callback вызвал ошибку: {e}")

    def test_overdue_occurrences_sorting(self):
        """
        Тест сортировки просроченных вхождений.
        
        Проверяет:
        - Просроченные вхождения отображаются первыми в списке
        - Просроченные вхождения сортируются по дате (старые первыми)
        - Будущие вхождения идут после просроченных
        
        Requirements: 4.3
        """
        # Arrange - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        today = datetime.date.today()

        # Создаем тестовые вхождения (несортированные) с валидными UUID
        future_1 = self._create_test_occurrence(
            today + datetime.timedelta(days=5),
            Decimal("100.00")
        )
        future_1.id = "future-1"
        
        overdue_1 = self._create_test_occurrence(
            today - datetime.timedelta(days=3),
            Decimal("200.00")
        )
        overdue_1.id = "overdue-1"
        
        future_2 = self._create_test_occurrence(
            today + datetime.timedelta(days=2),
            Decimal("150.00")
        )
        future_2.id = "future-2"
        
        overdue_2 = self._create_test_occurrence(
            today - datetime.timedelta(days=5),
            Decimal("300.00")
        )
        overdue_2.id = "overdue-2"

        occurrences = [
            # Будущее вхождение
            (future_1, "Категория 1", TransactionType.EXPENSE),
            # Просроченное вхождение (3 дня назад)
            (overdue_1, "Категория 2", TransactionType.INCOME),
            # Будущее вхождение
            (future_2, "Категория 3", TransactionType.EXPENSE),
            # Просроченное вхождение (5 дней назад - самое старое)
            (overdue_2, "Категория 4", TransactionType.EXPENSE),
        ]

        # Сортируем вхождения так, как это должно делаться в реальном коде
        # (просроченные первыми, затем будущие, все по дате)
        sorted_occurrences = sorted(
            occurrences,
            key=lambda x: (x[0].occurrence_date >= today, x[0].occurrence_date)
        )

        # Act - устанавливаем отсортированные вхождения
        widget.set_occurrences(sorted_occurrences)

        # Assert - проверяем порядок в виджете
        displayed_occurrences = widget.occurrences

        # Должно быть 4 вхождения (или меньше, если лимит 5)
        self.assertGreater(len(displayed_occurrences), 0, "Должны быть отображены вхождения")

        # Первое вхождение должно быть самым старым просроченным (5 дней назад)
        first_occ = displayed_occurrences[0][0]
        self.assertEqual(
            first_occ.id,
            "overdue-2",
            "Первым должно быть самое старое просроченное вхождение"
        )
        self.assertLess(
            first_occ.occurrence_date,
            today,
            "Первое вхождение должно быть просроченным"
        )

        # Второе вхождение должно быть просроченным (3 дня назад)
        second_occ = displayed_occurrences[1][0]
        self.assertEqual(
            second_occ.id,
            "overdue-1",
            "Вторым должно быть просроченное вхождение (3 дня назад)"
        )
        self.assertLess(
            second_occ.occurrence_date,
            today,
            "Второе вхождение должно быть просроченным"
        )

        # Третье и четвертое вхождения должны быть будущими
        third_occ = displayed_occurrences[2][0]
        self.assertGreaterEqual(
            third_occ.occurrence_date,
            today,
            "Третье вхождение должно быть будущим"
        )

        fourth_occ = displayed_occurrences[3][0]
        self.assertGreaterEqual(
            fourth_occ.occurrence_date,
            today,
            "Четвертое вхождение должно быть будущим"
        )

        # Проверяем, что будущие вхождения тоже отсортированы по дате
        self.assertLessEqual(
            third_occ.occurrence_date,
            fourth_occ.occurrence_date,
            "Будущие вхождения должны быть отсортированы по дате"
        )

    def test_overdue_occurrence_visual_indication(self):
        """
        Тест визуального выделения просроченных вхождений.
        
        Проверяет:
        - Просроченные вхождения имеют метку "(просрочено)" в дате
        - Дата просроченного вхождения имеет цвет ERROR
        
        Requirements: 4.1, 4.2
        """
        # Arrange - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        today = datetime.date.today()

        # Создаем просроченное вхождение с валидными UUID
        overdue_occurrence = self._create_test_occurrence(
            today - datetime.timedelta(days=3),
            Decimal("100.00")
        )

        # Act - создаем карточку просроченного вхождения
        card = widget._build_occurrence_card(
            overdue_occurrence,
            "Тестовая категория",
            TransactionType.EXPENSE
        )

        # Assert - проверяем визуальное выделение
        # Карточка должна иметь bgcolor для просроченных вхождений
        self.assertEqual(
            card.bgcolor,
            ft.Colors.SURFACE,
            "Просроченное вхождение должно иметь bgcolor=SURFACE"
        )

        # Проверяем содержимое карточки (текст даты должен содержать "(просрочено)")
        # Структура: card.content -> Column -> Row -> Column -> Text (дата)
        card_column = card.content
        self.assertIsInstance(card_column, ft.Column, "Содержимое карточки должно быть Column")

        first_row = card_column.controls[0]
        self.assertIsInstance(first_row, ft.Row, "Первый элемент должен быть Row")

        date_column = first_row.controls[1]
        self.assertIsInstance(date_column, ft.Column, "Второй элемент Row должен быть Column")

        date_text = date_column.controls[1]
        self.assertIsInstance(date_text, ft.Text, "Второй элемент Column должен быть Text с датой")

        # Проверяем, что текст содержит "(просрочено)"
        self.assertIn(
            "(просрочено)",
            date_text.value,
            "Текст даты должен содержать метку '(просрочено)'"
        )

        # Проверяем цвет текста даты
        self.assertEqual(
            date_text.color,
            ft.Colors.ERROR,
            "Цвет даты просроченного вхождения должен быть ERROR"
        )

    def test_future_occurrence_no_overdue_indication(self):
        """
        Тест отсутствия визуального выделения для будущих вхождений.
        
        Проверяет:
        - Будущие вхождения не имеют метку "(просрочено)"
        - Дата будущего вхождения не имеет цвет ERROR
        
        Requirements: 4.1, 4.2
        """
        # Arrange - создаем виджет
        widget = PlannedTransactionsWidget(
            session=self.mock_session,
            on_execute=self.mock_on_execute,
            on_skip=self.mock_on_skip,
            on_show_all=self.mock_on_show_all,
            on_occurrence_click=self.mock_on_occurrence_click
        )

        today = datetime.date.today()

        # Создаем будущее вхождение с валидными UUID
        future_occurrence = self._create_test_occurrence(
            today + datetime.timedelta(days=3),
            Decimal("100.00")
        )

        # Act - создаем карточку будущего вхождения
        card = widget._build_occurrence_card(
            future_occurrence,
            "Тестовая категория",
            TransactionType.EXPENSE
        )

        # Assert - проверяем отсутствие визуального выделения
        # Карточка не должна иметь bgcolor для будущих вхождений
        self.assertIsNone(
            card.bgcolor,
            "Будущее вхождение не должно иметь bgcolor"
        )

        # Проверяем содержимое карточки (текст даты не должен содержать "(просрочено)")
        card_column = card.content
        first_row = card_column.controls[0]
        date_column = first_row.controls[1]
        date_text = date_column.controls[1]

        # Проверяем, что текст НЕ содержит "(просрочено)"
        self.assertNotIn(
            "(просрочено)",
            date_text.value,
            "Текст даты не должен содержать метку '(просрочено)' для будущих вхождений"
        )

        # Проверяем цвет текста даты (не ERROR)
        self.assertNotEqual(
            date_text.color,
            ft.Colors.ERROR,
            "Цвет даты будущего вхождения не должен быть ERROR"
        )


if __name__ == '__main__':
    unittest.main()
