"""
Экран управления отложенными платежами.

Предоставляет UI для:
- Отображения списка всех активных отложенных платежей
- Создания и редактирования отложенных платежей
- Фильтрации по статусу, наличию даты, приоритету
- Исполнения, отмены и удаления платежей
- Просмотра статистики
"""

import flet as ft
from typing import Optional, List
from datetime import date

from models.models import (
    PendingPaymentDB,
    PendingPaymentCreate,
    PendingPaymentUpdate,
    PendingPaymentExecute,
    PendingPaymentCancel,
    CategoryDB
)
from models.enums import PendingPaymentPriority, PendingPaymentStatus
from database import get_db_session
from services.pending_payment_service import (
    get_all_pending_payments,
    create_pending_payment,
    update_pending_payment,
    execute_pending_payment,
    cancel_pending_payment,
    delete_pending_payment,
    get_pending_payments_statistics
)
from components.pending_payment_modal import PendingPaymentModal
from components.execute_pending_payment_modal import ExecutePendingPaymentModal
from utils.logger import get_logger

logger = get_logger(__name__)


class PendingPaymentsView(ft.Column):
    """
    Экран управления отложенными платежами.

    Позволяет пользователю:
    - Просматривать список всех отложенных платежей
    - Фильтровать по статусу, наличию даты, приоритету
    - Создавать новые отложенные платежи
    - Редактировать, исполнять, отменять и удалять платежи
    - Просматривать статистику

    Согласно Requirements 8.6 и 8.7:
    - Отображает список активных платежей
    - Сортировка по приоритету и дате
    - Фильтрация: все, с датой, без даты
    - Статистика
    """

    def __init__(self, page: ft.Page):
        """
        Инициализация экрана отложенных платежей.

        Args:
            page: Страница Flet для отображения UI
        """
        super().__init__(expand=True)
        self.page = page
        self.has_date_filter: Optional[bool] = None  # None=все, True=с датой, False=без даты
        self.priority_filter: Optional[PendingPaymentPriority] = None
        self.selected_payment: Optional[PendingPaymentDB] = None

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # Modals
        self.payment_modal = PendingPaymentModal(
            session=self.session,
            on_save=self.on_create_payment,
            on_update=self.on_update_payment
        )

        self.execute_modal = ExecutePendingPaymentModal(
            session=self.session,
            on_execute=self.on_execute_payment
        )

        # UI Components
        self._build_ui()

    def _build_ui(self):
        """Построение UI компонентов."""
        # Заголовок и кнопка создания
        self.header = ft.Row(
            controls=[
                ft.Text("Отложенные платежи", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.ON_PRIMARY,
                    tooltip="Добавить отложенный платёж",
                    on_click=self.open_create_dialog
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Статистика
        self.stats_card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("Загрузка статистики...", size=14)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            bgcolor=ft.Colors.SURFACE,
            padding=15,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

        # Фильтры по наличию даты
        self.date_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Все"),
                ft.Tab(text="С датой", icon=ft.Icons.CALENDAR_TODAY),
                ft.Tab(text="Без даты", icon=ft.Icons.EVENT_BUSY),
            ],
            on_change=self.on_date_filter_change
        )

        # Фильтр по приоритету
        self.priority_dropdown = ft.Dropdown(
            label="Приоритет",
            width=200,
            options=[
                ft.dropdown.Option(key="all", text="Все"),
                ft.dropdown.Option(key=PendingPaymentPriority.LOW.value, text="Низкий"),
                ft.dropdown.Option(key=PendingPaymentPriority.MEDIUM.value, text="Средний"),
                ft.dropdown.Option(key=PendingPaymentPriority.HIGH.value, text="Высокий"),
                ft.dropdown.Option(key=PendingPaymentPriority.CRITICAL.value, text="Критический"),
            ],
            value="all",
            on_change=self.on_priority_filter_change
        )

        # Список отложенных платежей
        self.payments_list = ft.ListView(expand=True, spacing=5, padding=10)

        # Layout
        self.main_content = ft.Column(
            controls=[
                self.stats_card,
                ft.Row(
                    controls=[
                        self.date_tabs,
                        self.priority_dropdown,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Divider(height=1),
                self.payments_list
            ],
            spacing=10,
            expand=True,
        )

        self.controls = [
            self.header,
            ft.Divider(height=1),
            self.main_content,
        ]

    def did_mount(self):
        """Вызывается после монтирования контрола на страницу."""
        self.refresh_data()

    def will_unmount(self):
        """Очистка ресурсов при размонтировании."""
        if self.cm:
            self.cm.__exit__(None, None, None)

    def on_date_filter_change(self, e):
        """Обработка смены фильтра по наличию даты."""
        index = self.date_tabs.selected_index
        if index == 0:
            self.has_date_filter = None  # Все
        elif index == 1:
            self.has_date_filter = True  # С датой
        elif index == 2:
            self.has_date_filter = False  # Без даты

        self.refresh_data()

    def on_priority_filter_change(self, e):
        """Обработка смены фильтра по приоритету."""
        value = self.priority_dropdown.value
        if value == "all":
            self.priority_filter = None
        else:
            self.priority_filter = PendingPaymentPriority(value)

        self.refresh_data()

    def refresh_data(self):
        """Загрузка и отображение списка отложенных платежей."""
        try:
            # Получаем список с учётом фильтров
            payments = get_all_pending_payments(
                self.session,
                status=PendingPaymentStatus.ACTIVE,
                has_planned_date=self.has_date_filter,
                priority=self.priority_filter
            )

            # Получаем статистику
            statistics = get_pending_payments_statistics(self.session)

            # Обновляем статистику
            self._update_statistics(statistics)

            # Обновляем список
            self._update_payments_list(payments)

            logger.info(f"Загружено {len(payments)} отложенных платежей")

        except Exception as e:
            logger.error(f"Ошибка загрузки отложенных платежей: {e}")
            self.show_error(f"Ошибка загрузки данных: {str(e)}")

    def _update_statistics(self, statistics: dict):
        """Обновление статистики."""
        total_active = statistics.get("total_active", 0)
        total_amount = statistics.get("total_amount", 0)
        with_date = statistics.get("with_planned_date", 0)
        without_date = statistics.get("without_planned_date", 0)

        self.stats_card.content = ft.Column(
            controls=[
                ft.Text(
                    f"Всего активных платежей: {total_active}",
                    size=16,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    f"Общая сумма: {total_amount:.2f} ₽",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT
                ),
                ft.Row(
                    controls=[
                        ft.Text(f"С датой: {with_date}", size=12),
                        ft.Text(f"Без даты: {without_date}", size=12),
                    ],
                    spacing=20,
                ),
            ],
            spacing=5,
        )

        if self.page:
            self.stats_card.update()

    def _update_payments_list(self, payments: List[PendingPaymentDB]):
        """Обновление списка платежей."""
        self.payments_list.controls.clear()

        if not payments:
            self.payments_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Нет отложенных платежей",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True
                    ),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for payment in payments:
                self.payments_list.controls.append(
                    self._build_payment_card(payment)
                )

        if self.page:
            self.payments_list.update()

    def _build_payment_card(self, payment: PendingPaymentDB) -> ft.Container:
        """
        Создание карточки платежа.

        Args:
            payment: Отложенный платёж

        Returns:
            Container с информацией о платеже и кнопками действий
        """
        # Цвет и иконка по приоритету
        priority_colors = {
            PendingPaymentPriority.LOW: ft.Colors.GREY_600,
            PendingPaymentPriority.MEDIUM: ft.Colors.BLUE_600,
            PendingPaymentPriority.HIGH: ft.Colors.ORANGE_600,
            PendingPaymentPriority.CRITICAL: ft.Colors.RED_600,
        }
        color = priority_colors.get(payment.priority, ft.Colors.GREY_600)

        priority_icons = {
            PendingPaymentPriority.LOW: ft.Icons.ARROW_DOWNWARD,
            PendingPaymentPriority.MEDIUM: ft.Icons.REMOVE,
            PendingPaymentPriority.HIGH: ft.Icons.ARROW_UPWARD,
            PendingPaymentPriority.CRITICAL: ft.Icons.PRIORITY_HIGH,
        }
        icon = priority_icons.get(payment.priority, ft.Icons.REMOVE)

        priority_names = {
            PendingPaymentPriority.LOW: "Низкий",
            PendingPaymentPriority.MEDIUM: "Средний",
            PendingPaymentPriority.HIGH: "Высокий",
            PendingPaymentPriority.CRITICAL: "Критический",
        }
        priority_name = priority_names.get(payment.priority, "Средний")

        # Категория
        category = self.session.query(CategoryDB).filter(
            CategoryDB.id == payment.category_id
        ).first()
        category_name = category.name if category else "Неизвестно"

        # Дата
        date_info = ""
        if payment.planned_date:
            date_str = payment.planned_date.strftime("%d.%m.%Y")
            days_until = (payment.planned_date - date.today()).days
            if days_until == 0:
                date_info = f"📅 Сегодня ({date_str})"
            elif days_until == 1:
                date_info = f"📅 Завтра ({date_str})"
            elif days_until < 0:
                date_info = f"⚠️ Просрочено ({date_str})"
            else:
                date_info = f"📅 {date_str} (через {days_until} дн.)"
        else:
            date_info = "Без даты"

        # Кнопки действий
        execute_btn = ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE,
            tooltip="Исполнить",
            icon_color=ft.Colors.GREEN,
            on_click=lambda _, p=payment: self.open_execute_dialog(p)
        )

        edit_btn = ft.IconButton(
            icon=ft.Icons.EDIT,
            tooltip="Редактировать",
            on_click=lambda _, p=payment: self.open_edit_dialog(p)
        )

        cancel_btn = ft.IconButton(
            icon=ft.Icons.CANCEL,
            tooltip="Отменить",
            icon_color=ft.Colors.ORANGE,
            on_click=lambda _, p=payment: self.confirm_cancel_payment(p)
        )

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE,
            tooltip="Удалить",
            icon_color=ft.Colors.RED,
            on_click=lambda _, p=payment: self.confirm_delete_payment(p)
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(name=icon, color=color, size=20),
                            ft.Text(
                                priority_name,
                                size=14,
                                color=color,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                f"{payment.amount:.2f} ₽",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    ft.Text(
                        payment.description,
                        size=14,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"Категория: {category_name}",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                            ft.Text(
                                date_info,
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1),
                    ft.Row(
                        controls=[
                            execute_btn,
                            edit_btn,
                            cancel_btn,
                            delete_btn,
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=8,
            ),
            padding=15,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        )

    def open_create_dialog(self, e):
        """Открытие диалога создания платежа."""
        self.payment_modal.open(self.page)

    def open_edit_dialog(self, payment: PendingPaymentDB):
        """Открытие диалога редактирования платежа."""
        self.payment_modal.open(self.page, payment=payment)

    def open_execute_dialog(self, payment: PendingPaymentDB):
        """Открытие диалога исполнения платежа."""
        self.execute_modal.open(self.page, payment=payment)

    def on_create_payment(self, payment_data: PendingPaymentCreate):
        """Callback создания платежа."""
        try:
            create_pending_payment(self.session, payment_data)
            self.show_success("Отложенный платёж создан")
            self.refresh_data()
        except ValueError as ve:
            self.show_error(str(ve))
        except Exception as e:
            logger.error(f"Ошибка создания отложенного платежа: {e}")
            self.show_error(f"Ошибка создания: {str(e)}")

    def on_update_payment(self, payment_id: int, payment_data: PendingPaymentUpdate):
        """Callback обновления платежа."""
        try:
            update_pending_payment(self.session, payment_id, payment_data)
            self.show_success("Отложенный платёж обновлён")
            self.refresh_data()
        except ValueError as ve:
            self.show_error(str(ve))
        except Exception as e:
            logger.error(f"Ошибка обновления отложенного платежа: {e}")
            self.show_error(f"Ошибка обновления: {str(e)}")

    def on_execute_payment(self, payment_id: int, executed_amount: float, executed_date: date):
        """Callback исполнения платежа."""
        try:
            execute_data = PendingPaymentExecute(
                executed_date=executed_date,
                executed_amount=executed_amount
            )
            execute_pending_payment(self.session, payment_id, execute_data)
            self.show_success("Отложенный платёж исполнен")
            self.refresh_data()
        except ValueError as ve:
            self.show_error(str(ve))
        except Exception as e:
            logger.error(f"Ошибка исполнения отложенного платежа: {e}")
            self.show_error(f"Ошибка исполнения: {str(e)}")

    def confirm_cancel_payment(self, payment: PendingPaymentDB):
        """Подтверждение отмены платежа."""
        def on_confirm(e):
            try:
                reason = reason_field.value or None
                cancel_data = PendingPaymentCancel(cancel_reason=reason)
                cancel_pending_payment(self.session, payment.id, cancel_data)
                dialog.open = False
                self.page.update()
                self.show_success("Отложенный платёж отменён")
                self.refresh_data()
            except Exception as ex:
                logger.error(f"Ошибка отмены платежа: {ex}")
                self.show_error(f"Ошибка отмены: {str(ex)}")

        reason_field = ft.TextField(
            label="Причина отмены (опционально)",
            multiline=True,
            max_lines=3
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Отменить платёж?"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Платёж: {payment.description}"),
                    ft.Text(f"Сумма: {payment.amount:.2f} ₽"),
                    ft.Divider(),
                    reason_field,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: setattr(dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Отменить платёж", on_click=on_confirm),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def confirm_delete_payment(self, payment: PendingPaymentDB):
        """Подтверждение удаления платежа."""
        def on_confirm(e):
            try:
                delete_pending_payment(self.session, payment.id)
                dialog.open = False
                self.page.update()
                self.show_success("Отложенный платёж удалён")
                self.refresh_data()
            except ValueError as ve:
                self.show_error(str(ve))
            except Exception as ex:
                logger.error(f"Ошибка удаления платежа: {ex}")
                self.show_error(f"Ошибка удаления: {str(ex)}")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удалить платёж?"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Платёж: {payment.description}"),
                    ft.Text(f"Сумма: {payment.amount:.2f} ₽"),
                    ft.Text("Это действие нельзя отменить!", color=ft.Colors.ERROR),
                ],
                tight=True,
                spacing=5,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: setattr(dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Удалить", on_click=on_confirm, bgcolor=ft.Colors.ERROR),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_success(self, message: str):
        """Отображение сообщения об успехе."""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.GREEN,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def show_error(self, message: str):
        """Отображение сообщения об ошибке."""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()
