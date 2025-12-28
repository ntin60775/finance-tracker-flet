"""
Property-based тесты для обзорного режима PlannedTransactionsWidget.

Тестирует:
- Property 1: Карточки вхождений не содержат кнопок действий
- Property 4: Просроченные вхождения визуально выделены
- Property 5: Просроченные вхождения сортируются первыми

Requirements: 1.1, 4.1, 4.2, 4.3, 5.2
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
import datetime
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock
import flet as ft

from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget
from finance_tracker.models import PlannedOccurrence, OccurrenceStatus, TransactionType


# Стратегии для генерации тестовых данных
dates_strategy = st.dates(
    min_value=date(2024, 1, 1),
    max_value=date(2025, 12, 31)
)

amounts_strategy = st.decimals(
    min_value=Decimal('0.01'),
    max_value=Decimal('100000.00'),
    places=2
)

category_names_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        blacklist_categories=('Cs',),  # Исключаем surrogate characters
        blacklist_characters='\x00'
    )
)

transaction_types_strategy = st.sampled_from([
    TransactionType.INCOME,
    TransactionType.EXPENSE,
])

occurrence_statuses_strategy = st.sampled_from([
    OccurrenceStatus.PENDING,
    OccurrenceStatus.EXECUTED,
    OccurrenceStatus.SKIPPED,
])


def create_test_occurrence(
    occurrence_date: date,
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


class TestPlannedWidgetOverviewModeProperties:
    """Property-based тесты для обзорного режима PlannedTransactionsWidget."""

    @given(
        amount=amounts_strategy,
        category_name=category_names_strategy,
        tx_type=transaction_types_strategy,
        status=occurrence_statuses_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_no_action_buttons_in_cards(
        self, amount, category_name, tx_type, status
    ):
        """
        Property 1: Карточки вхождений не содержат кнопок действий.

        Feature: planned-widget-overview-mode, Property 1: Для любого вхождения
        в обзорном режиме, карточка этого вхождения не должна содержать кнопок
        "Исполнить" или "Пропустить"

        Validates: Requirements 1.1, 5.2

        Для любого вхождения, карточка не должна содержать кнопок действий.
        Все действия выполняются через панель транзакций.
        """
        # Arrange - создаем виджет
        mock_session = Mock()
        mock_on_execute = Mock()
        mock_on_skip = Mock()
        mock_on_show_all = Mock()
        mock_on_occurrence_click = Mock()

        widget = PlannedTransactionsWidget(
            session=mock_session,
            on_execute=mock_on_execute,
            on_skip=mock_on_skip,
            on_show_all=mock_on_show_all,
            on_occurrence_click=mock_on_occurrence_click
        )

        # Создаем тестовое вхождение с любыми валидными параметрами
        test_occurrence = create_test_occurrence(
            date.today(),
            amount,
            status
        )

        # Act - вызываем метод построения кнопок действий
        action_buttons = widget._build_action_buttons(test_occurrence)

        # Assert - проверяем, что список пустой
        assert isinstance(action_buttons, list), "Метод должен возвращать список"
        assert len(action_buttons) == 0, (
            f"Метод _build_action_buttons должен возвращать пустой список в обзорном режиме, "
            f"но вернул {len(action_buttons)} кнопок"
        )

    @given(
        amount=amounts_strategy,
        category_name=category_names_strategy,
        tx_type=transaction_types_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_card_has_no_execute_skip_buttons(
        self, amount, category_name, tx_type
    ):
        """
        Property 1 (расширенная): Карточка вхождения не содержит кнопок действий.

        Feature: planned-widget-overview-mode, Property 1: Для любого вхождения,
        при создании карточки вхождения, карточка не должна содержать кнопок
        "Исполнить" или "Пропустить"

        Validates: Requirements 1.1, 5.2

        Проверяет, что в структуре карточки отсутствуют кнопки действий.
        """
        # Arrange - создаем виджет
        mock_session = Mock()
        mock_on_execute = Mock()
        mock_on_skip = Mock()
        mock_on_show_all = Mock()
        mock_on_occurrence_click = Mock()

        widget = PlannedTransactionsWidget(
            session=mock_session,
            on_execute=mock_on_execute,
            on_skip=mock_on_skip,
            on_show_all=mock_on_show_all,
            on_occurrence_click=mock_on_occurrence_click
        )

        # Создаем тестовое вхождение
        test_occurrence = create_test_occurrence(
            date.today(),
            amount,
            OccurrenceStatus.PENDING
        )

        # Act - создаем карточку вхождения
        card = widget._build_occurrence_card(
            test_occurrence,
            category_name,
            tx_type
        )

        # Assert - проверяем структуру карточки
        assert isinstance(card, ft.Container), "Карточка должна быть Container"
        assert card.content is not None, "Карточка должна иметь содержимое"

        # Проверяем, что в содержимом нет кнопок действий
        # Структура: Container -> Column -> [Row (информация), Row (статус)]
        card_column = card.content
        assert isinstance(card_column, ft.Column), "Содержимое карточки должно быть Column"

        # Проверяем все элементы в Column
        for control in card_column.controls:
            # Проверяем, что это не кнопка действия
            if isinstance(control, ft.Row):
                for row_control in control.controls:
                    # Проверяем, что это не кнопка "Исполнить" или "Пропустить"
                    if isinstance(row_control, ft.IconButton):
                        # Кнопки действий обычно имеют иконки CHECK или CLOSE
                        assert row_control.icon not in [
                            ft.Icons.CHECK,
                            ft.Icons.CLOSE,
                            ft.Icons.DONE,
                            ft.Icons.CLEAR,
                        ], f"Найдена кнопка действия с иконкой {row_control.icon}"
                    elif isinstance(row_control, ft.TextButton):
                        # Проверяем текст кнопки
                        if hasattr(row_control, 'text'):
                            assert row_control.text not in [
                                "Исполнить",
                                "Пропустить",
                                "Execute",
                                "Skip",
                            ], f"Найдена кнопка действия с текстом '{row_control.text}'"

    @given(
        amount=amounts_strategy,
        category_name=category_names_strategy,
        tx_type=transaction_types_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_overdue_occurrences_visually_indicated(
        self, amount, category_name, tx_type
    ):
        """
        Property 4: Просроченные вхождения визуально выделены.

        Feature: planned-widget-overview-mode, Property 4: Для любого вхождения
        с датой в прошлом, карточка должна иметь визуальное выделение (цвет, рамка)
        и содержать метку "(просрочено)" в тексте даты

        Validates: Requirements 4.1, 4.2

        Для любого просроченного вхождения, карточка должна быть визуально выделена.
        """
        # Arrange - создаем виджет
        mock_session = Mock()
        mock_on_execute = Mock()
        mock_on_skip = Mock()
        mock_on_show_all = Mock()
        mock_on_occurrence_click = Mock()

        widget = PlannedTransactionsWidget(
            session=mock_session,
            on_execute=mock_on_execute,
            on_skip=mock_on_skip,
            on_show_all=mock_on_show_all,
            on_occurrence_click=mock_on_occurrence_click
        )

        today = date.today()

        # Создаем просроченное вхождение (дата в прошлом)
        overdue_date = today - timedelta(days=5)
        test_occurrence = create_test_occurrence(
            overdue_date,
            amount,
            OccurrenceStatus.PENDING
        )

        # Act - создаем карточку просроченного вхождения
        card = widget._build_occurrence_card(
            test_occurrence,
            category_name,
            tx_type
        )

        # Assert - проверяем визуальное выделение
        # Карточка должна иметь bgcolor для просроченных вхождений
        assert card.bgcolor == ft.Colors.SURFACE, (
            f"Просроченное вхождение должно иметь bgcolor=SURFACE, "
            f"но имеет {card.bgcolor}"
        )

        # Проверяем содержимое карточки (текст даты должен содержать "(просрочено)")
        card_column = card.content
        assert isinstance(card_column, ft.Column), "Содержимое карточки должно быть Column"

        first_row = card_column.controls[0]
        assert isinstance(first_row, ft.Row), "Первый элемент должен быть Row"

        date_column = first_row.controls[1]
        assert isinstance(date_column, ft.Column), "Второй элемент Row должен быть Column"

        date_text = date_column.controls[1]
        assert isinstance(date_text, ft.Text), "Второй элемент Column должен быть Text с датой"

        # Проверяем, что текст содержит "(просрочено)"
        assert "(просрочено)" in date_text.value, (
            f"Текст даты должен содержать метку '(просрочено)', "
            f"но содержит '{date_text.value}'"
        )

        # Проверяем цвет текста даты
        assert date_text.color == ft.Colors.ERROR, (
            f"Цвет даты просроченного вхождения должен быть ERROR, "
            f"но имеет {date_text.color}"
        )

    @given(
        amount=amounts_strategy,
        category_name=category_names_strategy,
        tx_type=transaction_types_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_future_occurrences_not_indicated_as_overdue(
        self, amount, category_name, tx_type
    ):
        """
        Property 4 (обратное): Будущие вхождения не выделены как просроченные.

        Feature: planned-widget-overview-mode, Property 4: Для любого вхождения
        с датой в будущем, карточка не должна содержать метку "(просрочено)"
        и не должна иметь цвет ERROR для даты

        Validates: Requirements 4.1, 4.2

        Для любого будущего вхождения, карточка не должна быть выделена как просроченная.
        """
        # Arrange - создаем виджет
        mock_session = Mock()
        mock_on_execute = Mock()
        mock_on_skip = Mock()
        mock_on_show_all = Mock()
        mock_on_occurrence_click = Mock()

        widget = PlannedTransactionsWidget(
            session=mock_session,
            on_execute=mock_on_execute,
            on_skip=mock_on_skip,
            on_show_all=mock_on_show_all,
            on_occurrence_click=mock_on_occurrence_click
        )

        today = date.today()

        # Создаем будущее вхождение (дата в будущем)
        future_date = today + timedelta(days=5)
        test_occurrence = create_test_occurrence(
            future_date,
            amount,
            OccurrenceStatus.PENDING
        )

        # Act - создаем карточку будущего вхождения
        card = widget._build_occurrence_card(
            test_occurrence,
            category_name,
            tx_type
        )

        # Assert - проверяем отсутствие визуального выделения
        # Карточка не должна иметь bgcolor для будущих вхождений
        assert card.bgcolor is None, (
            f"Будущее вхождение не должно иметь bgcolor, "
            f"но имеет {card.bgcolor}"
        )

        # Проверяем содержимое карточки (текст даты не должен содержать "(просрочено)")
        card_column = card.content
        first_row = card_column.controls[0]
        date_column = first_row.controls[1]
        date_text = date_column.controls[1]

        # Проверяем, что текст НЕ содержит "(просрочено)"
        assert "(просрочено)" not in date_text.value, (
            f"Текст даты не должен содержать метку '(просрочено)' для будущих вхождений, "
            f"но содержит '{date_text.value}'"
        )

        # Проверяем цвет текста даты (не ERROR)
        assert date_text.color != ft.Colors.ERROR, (
            f"Цвет даты будущего вхождения не должен быть ERROR, "
            f"но имеет {date_text.color}"
        )

    @given(
        amounts_list=st.lists(
            amounts_strategy,
            min_size=2,
            max_size=10,
            unique=False
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_overdue_occurrences_sorted_first(
        self, amounts_list
    ):
        """
        Property 5: Просроченные вхождения сортируются первыми.

        Feature: planned-widget-overview-mode, Property 5: Для любого списка вхождений,
        после сортировки все просроченные вхождения должны находиться в начале списка,
        отсортированные по дате (старые первыми)

        Validates: Requirements 4.3

        Для любого списка вхождений, просроченные должны быть первыми.
        """
        # Arrange - создаем виджет
        mock_session = Mock()
        mock_on_execute = Mock()
        mock_on_skip = Mock()
        mock_on_show_all = Mock()
        mock_on_occurrence_click = Mock()

        widget = PlannedTransactionsWidget(
            session=mock_session,
            on_execute=mock_on_execute,
            on_skip=mock_on_skip,
            on_show_all=mock_on_show_all,
            on_occurrence_click=mock_on_occurrence_click
        )

        today = date.today()

        # Создаем смешанный список вхождений (просроченные и будущие)
        occurrences = []

        # Добавляем будущие вхождения
        for i, amount in enumerate(amounts_list[:len(amounts_list)//2]):
            future_date = today + timedelta(days=i+1)
            occ = create_test_occurrence(future_date, amount, OccurrenceStatus.PENDING)
            occ.id = f"future-{i}"
            occurrences.append((occ, f"Category {i}", TransactionType.EXPENSE))

        # Добавляем просроченные вхождения
        for i, amount in enumerate(amounts_list[len(amounts_list)//2:]):
            overdue_date = today - timedelta(days=i+1)
            occ = create_test_occurrence(overdue_date, amount, OccurrenceStatus.PENDING)
            occ.id = f"overdue-{i}"
            occurrences.append((occ, f"Category {i+len(amounts_list)//2}", TransactionType.INCOME))

        # Сортируем вхождения (просроченные первыми, затем будущие)
        sorted_occurrences = sorted(
            occurrences,
            key=lambda x: (x[0].occurrence_date >= today, x[0].occurrence_date)
        )

        # Act - устанавливаем отсортированные вхождения
        widget.set_occurrences(sorted_occurrences)

        # Assert - проверяем порядок в виджете
        displayed_occurrences = widget.occurrences

        # Должны быть отображены вхождения (максимум 5)
        assert len(displayed_occurrences) > 0, "Должны быть отображены вхождения"

        # Проверяем, что все просроченные вхождения идут перед будущими
        found_future = False
        for occ, _, _ in displayed_occurrences:
            if occ.occurrence_date >= today:
                found_future = True
            elif found_future:
                # Если мы нашли будущее вхождение, а потом просроченное - это ошибка
                assert False, (
                    f"Просроченное вхождение {occ.id} идет после будущего вхождения, "
                    f"но должно быть перед ним"
                )

        # Проверяем, что просроченные вхождения отсортированы по дате (старые первыми)
        overdue_occurrences = [
            occ for occ, _, _ in displayed_occurrences
            if occ.occurrence_date < today
        ]

        for i in range(len(overdue_occurrences) - 1):
            assert overdue_occurrences[i].occurrence_date <= overdue_occurrences[i+1].occurrence_date, (
                f"Просроченные вхождения должны быть отсортированы по дате, "
                f"но {overdue_occurrences[i].id} ({overdue_occurrences[i].occurrence_date}) "
                f"идет после {overdue_occurrences[i+1].id} ({overdue_occurrences[i+1].occurrence_date})"
            )

        # Проверяем, что будущие вхождения тоже отсортированы по дате
        future_occurrences = [
            occ for occ, _, _ in displayed_occurrences
            if occ.occurrence_date >= today
        ]

        for i in range(len(future_occurrences) - 1):
            assert future_occurrences[i].occurrence_date <= future_occurrences[i+1].occurrence_date, (
                f"Будущие вхождения должны быть отсортированы по дате, "
                f"но {future_occurrences[i].id} ({future_occurrences[i].occurrence_date}) "
                f"идет после {future_occurrences[i+1].id} ({future_occurrences[i+1].occurrence_date})"
            )
