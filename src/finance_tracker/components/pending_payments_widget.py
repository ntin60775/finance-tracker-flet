"""
Виджет для отображения активных отложенных платежей на главном экране.

Компонент предоставляет:
- Список топ-5 активных платежей по приоритету
- Статистику (общая сумма, количество)
- Фильтры: все, с датой, без даты
- Кнопку "Показать все" для перехода в полный раздел
- Быстрые действия: исполнить, отменить, удалить
"""

import datetime
from typing import Callable, List, Dict, Any
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import PendingPaymentDB
from finance_tracker.models.enums import PendingPaymentPriority
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class PendingPaymentsWidget(ft.Container):
    """
    Виджет для отображения активных отложенных платежей.

    Отображает:
    - Топ-5 активных платежей по приоритету
    - Статистику (общая сумма, количество)
    - Быстрые действия для каждого платежа

    Согласно Requirement 8.6 и 8.7:
    - Отображает список отложенных платежей с фильтрацией
    - Позволяет быстро исполнять/отменять платежи
    - Показывает статистику
    """

    def __init__(
        self,
        session: Session,
        on_execute: Callable[[PendingPaymentDB], None],
        on_cancel: Callable[[PendingPaymentDB], None],
        on_delete: Callable[[int], None],
        on_show_all: Callable[[], None],
    ):
        """
        Инициализация виджета отложенных платежей.

        Args:
            session: Сессия БД для загрузки данных.
            on_execute: Callback для исполнения платежа.
            on_cancel: Callback для отмены платежа.
            on_delete: Callback для удаления платежа.
            on_show_all: Callback для перехода в полный раздел отложенных платежей.
        """
        super().__init__()
        self.session = session
        self.on_execute = on_execute
        self.on_cancel = on_cancel
        self.on_delete = on_delete
        self.on_show_all = on_show_all
        self.payments: List[PendingPaymentDB] = []
        self.statistics: Dict[str, Any] = {}
        self.current_filter = "all"  # all, with_date, without_date

        # UI Components
        self.title_text = ft.Text(
            "Отложенные платежи",
            size=18,
            weight=ft.FontWeight.BOLD
        )

        self.stats_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT
        )

        # Filter buttons
        self.filter_all_btn = ft.TextButton(
            "Все",
            on_click=lambda _: self._change_filter("all"),
            style=ft.ButtonStyle(
                color=ft.Colors.PRIMARY,
            )
        )

        self.filter_with_date_btn = ft.TextButton(
            "С датой",
            on_click=lambda _: self._change_filter("with_date")
        )

        self.filter_without_date_btn = ft.TextButton(
            "Без даты",
            on_click=lambda _: self._change_filter("without_date")
        )

        self.payments_list = ft.Column(spacing=5)

        self.empty_text = ft.Text(
            "Нет активных отложенных платежей",
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            italic=True
        )

        self.show_all_button = ft.TextButton(
            "Показать все",
            icon=ft.Icons.ARROW_FORWARD,
            on_click=lambda _: self.on_show_all()
        )

        # Init Layout
        self.padding = 15
        self.border = ft.border.all(1, "outlineVariant")
        self.border_radius = 10
        self.bgcolor = "surface"

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                self.title_text,
                                self.stats_text,
                            ],
                            spacing=2,
                        ),
                        self.show_all_button,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        self.filter_all_btn,
                        self.filter_with_date_btn,
                        self.filter_without_date_btn,
                    ],
                    spacing=5,
                ),
                ft.Divider(),
                self.payments_list,
            ],
            spacing=10,
        )

    def set_payments(
        self,
        payments: List[PendingPaymentDB],
        statistics: Dict[str, Any]
    ):
        """
        Обновление списка платежей и статистики для отображения.

        Args:
            payments: Список отложенных платежей (уже отсортирован).
            statistics: Статистика платежей.
        """
        self.payments = payments[:5]  # Берём только первые 5
        self.statistics = statistics
        self._update_statistics()
        self._update_payments_list()

    def _change_filter(self, filter_type: str):
        """Изменение текущего фильтра."""
        self.current_filter = filter_type

        # Update button styles
        self.filter_all_btn.style = ft.ButtonStyle(
            color=ft.Colors.PRIMARY if filter_type == "all" else None
        )
        self.filter_with_date_btn.style = ft.ButtonStyle(
            color=ft.Colors.PRIMARY if filter_type == "with_date" else None
        )
        self.filter_without_date_btn.style = ft.ButtonStyle(
            color=ft.Colors.PRIMARY if filter_type == "without_date" else None
        )

        # TODO: Trigger data reload with new filter
        # This requires callback to parent component

        if self.page:
            self.update()

    def _update_statistics(self):
        """Обновление статистики."""
        total_active = self.statistics.get("total_active", 0)
        total_amount = self.statistics.get("total_amount", 0)

        self.stats_text.value = f"{total_active} платежей · {total_amount:.2f} ₽"

    def _update_payments_list(self):
        """Обновление списка платежей в UI."""
        self.payments_list.controls.clear()

        if not self.payments:
            self.payments_list.controls.append(self.empty_text)
        else:
            for payment in self.payments:
                self.payments_list.controls.append(
                    self._build_payment_card(payment)
                )

        if self.page:
            self.update()

    def _build_payment_card(
        self,
        payment: PendingPaymentDB
    ) -> ft.Container:
        """
        Создание карточки платежа.

        Args:
            payment: Отложенный платёж.

        Returns:
            Container с информацией о платеже и кнопками действий.
        """
        # Определение цвета по приоритету
        priority_colors = {
            PendingPaymentPriority.LOW: ft.Colors.GREY_600,
            PendingPaymentPriority.MEDIUM: ft.Colors.BLUE_600,
            PendingPaymentPriority.HIGH: ft.Colors.ORANGE_600,
            PendingPaymentPriority.CRITICAL: ft.Colors.RED_600,
        }
        color = priority_colors.get(payment.priority, ft.Colors.GREY_600)

        # Иконки приоритета
        priority_icons = {
            PendingPaymentPriority.LOW: ft.Icons.ARROW_DOWNWARD,
            PendingPaymentPriority.MEDIUM: ft.Icons.REMOVE,
            PendingPaymentPriority.HIGH: ft.Icons.ARROW_UPWARD,
            PendingPaymentPriority.CRITICAL: ft.Icons.PRIORITY_HIGH,
        }
        icon = priority_icons.get(payment.priority, ft.Icons.REMOVE)

        # Текст приоритета
        priority_names = {
            PendingPaymentPriority.LOW: "Низкий",
            PendingPaymentPriority.MEDIUM: "Средний",
            PendingPaymentPriority.HIGH: "Высокий",
            PendingPaymentPriority.CRITICAL: "Критический",
        }
        priority_name = priority_names.get(payment.priority, "Средний")

        # Дата
        date_text = ""
        if payment.planned_date:
            date_str = payment.planned_date.strftime("%d.%m.%Y")
            days_until = (payment.planned_date - datetime.date.today()).days
            if days_until == 0:
                date_text = f"📅 Сегодня ({date_str})"
            elif days_until == 1:
                date_text = f"📅 Завтра ({date_str})"
            elif days_until < 0:
                date_text = f"📅 Просрочено ({date_str})"
            else:
                date_text = f"📅 {date_str} (через {days_until} дн.)"

        # Кнопки действий
        execute_button = ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            tooltip="Исполнить",
            icon_size=20,
            on_click=lambda _, p=payment: self.on_execute(p)
        )

        cancel_button = ft.IconButton(
            icon=ft.Icons.CANCEL_OUTLINED,
            tooltip="Отменить",
            icon_size=20,
            on_click=lambda _, p=payment: self.on_cancel(p)
        )

        delete_button = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            tooltip="Удалить",
            icon_size=20,
            on_click=lambda _, p_id=payment.id: self.on_delete(p_id)
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(name=icon, color=color, size=16),
                            ft.Text(
                                priority_name,
                                size=12,
                                color=color,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                f"{payment.amount:.2f} ₽",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE
                            ),
                        ],
                        spacing=5,
                    ),
                    ft.Text(
                        payment.description,
                        size=13,
                        color=ft.Colors.ON_SURFACE,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    ft.Text(
                        date_text if date_text else "Без даты",
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=not date_text
                    ),
                    ft.Row(
                        controls=[
                            execute_button,
                            cancel_button,
                            delete_button,
                        ],
                        spacing=5,
                    ),
                ],
                spacing=5,
                tight=True,
            ),
            padding=10,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        )
