"""
Виджет для отображения ближайших плановых вхождений на главном экране.

Компонент предоставляет:
- Список ближайших 5 вхождений с информацией о статусе
- Быстрое исполнение/пропуск вхождений
- Кнопку "Показать все" для перехода в полный раздел
- Автоматическое обновление при изменениях
"""

import datetime
from typing import Callable, List, Optional, Tuple
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models import PlannedOccurrence, OccurrenceStatus, TransactionType
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class PlannedTransactionsWidget(ft.Container):
    """
    Виджет для отображения ближайших плановых вхождений.

    Отображает:
    - Топ-5 ближайших вхождений со статусом PENDING
    - Информацию о каждом вхождении (дата, сумма, категория, тип)
    - Кнопки быстрого исполнения и пропуска

    Согласно Requirement 5.6:
    - Отображает список плановых транзакций
    - Позволяет быстро исполнять вхождения
    """

    def __init__(
        self,
        session: Session,
        on_execute: Callable[[PlannedOccurrence], None],
        on_skip: Callable[[PlannedOccurrence], None],
        on_show_all: Callable[[], None],
        on_add_planned_transaction: Optional[Callable[[], None]] = None,
    ):
        """
        Инициализация виджета плановых транзакций.

        Args:
            session: Сессия БД для загрузки данных.
            on_execute: Callback для исполнения вхождения.
            on_skip: Callback для пропуска вхождения.
            on_show_all: Callback для перехода в полный раздел плановых транзакций.
            on_add_planned_transaction: Callback для добавления новой плановой транзакции.
                                        Если None, кнопка добавления не отображается.
        """
        super().__init__()
        self.session = session
        self.on_execute = on_execute
        self.on_skip = on_skip
        self.on_show_all = on_show_all
        self.on_add_planned_transaction = on_add_planned_transaction
        self.occurrences: List[Tuple[PlannedOccurrence, str, TransactionType]] = []

        # UI Components
        self.title_text = ft.Text(
            "Плановые транзакции",
            size=18,
            weight=ft.FontWeight.BOLD
        )

        self.occurrences_list = ft.Column(spacing=5)

        self.empty_text = ft.Text(
            "Нет ближайших плановых транзакций",
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            italic=True
        )

        self.show_all_button = ft.TextButton(
            "Показать все",
            icon=ft.Icons.ARROW_FORWARD,
            on_click=lambda _: self.on_show_all()
        )

        # Кнопка добавления плановой транзакции (отображается только если callback задан)
        self.add_button: Optional[ft.IconButton] = None
        if self.on_add_planned_transaction:
            self.add_button = ft.IconButton(
                icon=ft.Icons.ADD,
                icon_color=ft.Colors.PRIMARY,
                tooltip="Добавить плановую транзакцию",
                on_click=lambda _: self.on_add_planned_transaction()
            )

        # Init Layout
        self.padding = 15
        self.border = ft.border.all(1, "outlineVariant")
        self.border_radius = 10
        self.bgcolor = "surface"

        self.content = ft.Column(
            controls=[
                self._build_header(),
                ft.Divider(),
                self.occurrences_list,
            ],
            spacing=10,
        )

    def _build_header(self) -> ft.Row:
        """
        Построение заголовка виджета.

        Структура: [Title] ... [+Add] [Show All]
        - Title слева
        - Кнопки справа, сгруппированы вместе
        - Кнопка добавления отображается только если callback задан

        Returns:
            Row с заголовком и кнопками действий.
        """
        # Группа кнопок справа
        right_buttons = []

        # Кнопка добавления (если callback задан)
        if self.add_button:
            right_buttons.append(self.add_button)

        right_buttons.append(self.show_all_button)

        return ft.Row(
            controls=[
                self.title_text,
                ft.Row(
                    controls=right_buttons,
                    spacing=5,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def set_occurrences(
        self,
        occurrences: List[Tuple[PlannedOccurrence, str, TransactionType]]
    ):
        """
        Обновление списка вхождений для отображения.

        Args:
            occurrences: Список кортежей (вхождение, название_категории, тип_транзакции).
                        Ожидается отсортированный по дате список.
        """
        self.occurrences = occurrences[:5]  # Берём только первые 5
        self._update_occurrences_list()

    def _update_occurrences_list(self):
        """Обновление списка вхождений в UI."""
        self.occurrences_list.controls.clear()

        if not self.occurrences:
            self.occurrences_list.controls.append(self.empty_text)
        else:
            for occ, cat_name, tx_type in self.occurrences:
                self.occurrences_list.controls.append(
                    self._build_occurrence_card(occ, cat_name, tx_type)
                )

        if self.page:
            self.update()

    def _build_occurrence_card(
        self,
        occurrence: PlannedOccurrence,
        category_name: str,
        tx_type: TransactionType
    ) -> ft.Container:
        """
        Создание карточки вхождения.

        Args:
            occurrence: Плановое вхождение.
            category_name: Название категории.
            tx_type: Тип транзакции.

        Returns:
            Container с информацией о вхождении и кнопками действий.
        """
        # Определение цвета и иконки по типу
        if tx_type == TransactionType.INCOME:
            color = ft.Colors.GREEN_700
            icon = ft.Icons.ARROW_UPWARD
        else:
            color = ft.Colors.RED_700
            icon = ft.Icons.ARROW_DOWNWARD

        # Форматирование даты
        occ_date = occurrence.occurrence_date
        today = datetime.date.today()

        if occ_date == today:
            date_str = "Сегодня"
        elif occ_date == today + datetime.timedelta(days=1):
            date_str = "Завтра"
        else:
            date_str = occ_date.strftime("%d.%m.%Y")

        # Определение просроченности
        is_overdue = occ_date < today
        if is_overdue:
            date_str += " (просрочено)"
            date_color = ft.Colors.ERROR
        else:
            date_color = ft.Colors.ON_SURFACE_VARIANT

        # Статус
        status_map = {
            OccurrenceStatus.PENDING: ("Ожидается", ft.Colors.ORANGE_700),
            OccurrenceStatus.EXECUTED: ("Исполнено", ft.Colors.GREEN_700),
            OccurrenceStatus.SKIPPED: ("Пропущено", ft.Colors.GREY_700),
        }
        status_text, status_color = status_map.get(
            occurrence.status,
            ("Неизвестно", ft.Colors.GREY_700)
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, color=color, size=20),
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        f"{category_name}",
                                        size=14,
                                        weight=ft.FontWeight.BOLD
                                    ),
                                    ft.Text(
                                        f"{date_str}",
                                        size=12,
                                        color=date_color
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Text(
                                f"{occurrence.amount:.2f} ₽",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=color
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(
                                    status_text,
                                    size=11,
                                    color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.BOLD
                                ),
                                bgcolor=status_color,
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                border_radius=5,
                            ),
                            ft.Container(expand=True),
                            # Показываем кнопки только для PENDING статуса
                            *self._build_action_buttons(occurrence)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=8,
            ),
            padding=10,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE if is_overdue else None,
        )

    def _build_action_buttons(self, occurrence: PlannedOccurrence) -> List[ft.Control]:
        """
        Создание кнопок действий для вхождения.

        Args:
            occurrence: Плановое вхождение.

        Returns:
            Список кнопок (исполнить, пропустить) только для PENDING статуса.
        """
        if occurrence.status != OccurrenceStatus.PENDING:
            return []

        return [
            ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                icon_color=ft.Colors.GREEN_700,
                tooltip="Исполнить",
                on_click=lambda _, occ=occurrence: self.on_execute(occ),
                icon_size=20,
            ),
            ft.IconButton(
                icon=ft.Icons.SKIP_NEXT,
                icon_color=ft.Colors.ORANGE_700,
                tooltip="Пропустить",
                on_click=lambda _, occ=occurrence: self.on_skip(occ),
                icon_size=20,
            ),
        ]
