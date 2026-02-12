import datetime
from typing import List, Any, Tuple, Dict, Optional, Callable

import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.enums import OccurrenceStatus, PaymentStatus, TransactionType
from finance_tracker.models.models import (
    TransactionCreate,
    TransactionUpdate,
    TransactionDB,
    PlannedOccurrence,
    PendingPaymentCreate,
    PlannedTransactionCreate,
)
from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget
from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.components.execute_occurrence_modal import ExecuteOccurrenceModal
from finance_tracker.components.execute_pending_payment_modal import ExecutePendingPaymentModal
from finance_tracker.components.pending_payment_modal import PendingPaymentModal
from finance_tracker.components.planned_transaction_modal import PlannedTransactionModal
from finance_tracker.services import (
    loan_payment_service,
    pending_payment_service,
    planned_transaction_service,
)
from finance_tracker.services.balance_forecast_service import (
    calculate_actual_balance,
    detect_cash_gaps,
)
from finance_tracker.utils.logger import get_logger
from finance_tracker.models.models import PendingPaymentUpdate, PendingPaymentDB, LoanPaymentDB
from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.views.interfaces import IHomeViewCallbacks
from decimal import Decimal

logger = get_logger(__name__)


class HomeView(ft.Column, IHomeViewCallbacks):
    """
    Главный экран приложения (Календарь + Транзакции + Плановые операции).

    Компоновка:
    - 3 колонки: контекст (плановые + отложенные), календарь, день-инспектор
    - центрированный контейнер с max-width 1760px
    - нижняя фикс-панель "Сегодня" с компенсацией высоты в main area

    Реализует паттерн MVP: View делегирует бизнес-логику в Presenter,
    получает обновления через IHomeViewCallbacks.

    Args:
        page: Объект страницы Flet для управления UI
        session: Активная сессия БД для работы с данными
        navigate_callback: Опциональный callback для навигации между разделами приложения.
                          Принимает индекс раздела (int) для переключения.
    """

    MAX_CONTENT_WIDTH = 1760
    DEFAULT_PAGE_WIDTH = 1920
    COLUMN_GAP = 16
    CENTER_COLUMN_MIN_WIDTH = 680
    SIDE_COLUMN_MIN_WIDTH = 360
    SIDE_COLUMN_MAX_WIDTH = 420
    SIDE_COLUMN_FALLBACK_MIN_WIDTH = 300
    BOTTOM_BAR_HEIGHT = 72
    BOTTOM_BAR_SPACING = 16
    MAIN_AREA_BOTTOM_PADDING = BOTTOM_BAR_HEIGHT + BOTTOM_BAR_SPACING

    def __init__(
        self,
        page: ft.Page,
        session: Session,
        navigate_callback: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(expand=True, alignment=ft.MainAxisAlignment.START)
        self._page = page
        self.session = session
        self.selected_date = datetime.date.today()
        self.navigate_callback = navigate_callback
        self.spacing = 0
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Создаем Presenter с инжекцией зависимостей
        self.presenter = HomePresenter(session, self)

        # Получаем высоту страницы для адаптивных размеров календаря
        raw_page_height = self._page.height if hasattr(self._page, "height") else None
        page_height = self._safe_int(raw_page_height, 1080) if raw_page_height else None

        self._today_cash_gaps_7: List[datetime.date] = []
        self._today_cash_gaps_30: List[datetime.date] = []

        # UI Components
        self.calendar_widget = CalendarWidget(
            on_date_selected=self.on_date_selected,
            initial_date=self.selected_date,
            page_height=page_height,
        )

        self.transactions_panel = TransactionsPanel(
            date_obj=self.selected_date,
            transactions=[],
            on_add_transaction=self.open_add_transaction_modal,
            on_execute_occurrence=self.on_execute_occurrence,
            on_skip_occurrence=self.on_skip_occurrence,
            on_execute_pending_payment=self.on_execute_payment,
            on_execute_loan_payment=self.on_execute_loan_payment,
            on_edit_transaction=self.on_edit_transaction,
            on_delete_transaction=self.on_delete_transaction,
        )

        # Вычисляем ширину календаря для адаптивности легенды
        # Центральная колонка занимает 3/7 от общей ширины страницы
        # Вычитаем отступы и разделители для более точного расчета
        calendar_width = self._calculate_calendar_width()
        self.legend = CalendarLegend(calendar_width=calendar_width)

        self.planned_widget = PlannedTransactionsWidget(
            session=self.session,
            on_execute=self.on_execute_occurrence,
            on_skip=self.on_skip_occurrence,
            on_show_all=self.on_show_all_occurrences,
            on_add_planned_transaction=self.on_add_planned_transaction,
            on_occurrence_click=self.on_occurrence_clicked,
        )

        self.pending_payments_widget = PendingPaymentsWidget(
            session=self.session,
            on_execute=self.on_execute_payment,
            on_cancel=self.on_cancel_payment,
            on_delete=self.on_delete_payment,
            on_show_all=self.on_show_all_payments,
            on_add_payment=self.on_add_pending_payment,
            on_edit=self.on_edit_pending_payment,
        )

        # Modals
        self.transaction_modal = TransactionModal(
            session=self.session,
            on_save=self.on_transaction_saved,
            on_update=self.on_transaction_updated,
        )

        self.execute_occurrence_modal = ExecuteOccurrenceModal(
            session=self.session,
            on_execute=self.on_occurrence_executed_confirm,
            on_skip=self.on_occurrence_skipped_confirm,
            on_reschedule=self.on_occurrence_rescheduled_confirm,
        )

        self.execute_payment_modal = ExecutePendingPaymentModal(
            session=self.session, on_execute=self.on_payment_executed_confirm
        )

        self.payment_modal = PendingPaymentModal(
            session=self.session,
            on_save=self.on_pending_payment_saved,
            on_update=self.on_pending_payment_updated,
        )

        self.planned_transaction_modal = PlannedTransactionModal(
            session=self.session, on_save=self.on_planned_transaction_saved
        )

        self._layout_metrics = self._calculate_layout_metrics()

        self.left_column = ft.Column(
            controls=[self.planned_widget, self.pending_payments_widget],
            spacing=self.COLUMN_GAP,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )
        self.center_column = ft.Column(
            controls=[self.calendar_widget, self.legend],
            spacing=self.COLUMN_GAP,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )
        self.right_column = ft.Column(
            controls=[self.transactions_panel],
            spacing=self.COLUMN_GAP,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )

        self.left_column_container = ft.Container(
            width=self._layout_metrics["left_width"],
            content=self.left_column,
        )
        self.center_column_container = ft.Container(
            expand=True,
            content=self.center_column,
        )
        self.right_column_container = ft.Container(
            width=self._layout_metrics["right_width"],
            content=self.right_column,
        )

        self.main_row = ft.Row(
            controls=[
                self.left_column_container,
                self.center_column_container,
                self.right_column_container,
            ],
            width=self._layout_metrics["container_width"],
            expand=True,
            spacing=self.COLUMN_GAP,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self.main_area_container = ft.Container(
            key="home_main_area",
            expand=True,
            content=self.main_row,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(
                left=self._layout_metrics["horizontal_padding"],
                right=self._layout_metrics["horizontal_padding"],
                bottom=self.MAIN_AREA_BOTTOM_PADDING,
            ),
        )

        self.today_section: ft.Container = self._build_today_section()

        self.controls = [self.main_area_container, self.today_section]

        logger.info("HomeView инициализирован")

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(value, maximum))

    def _safe_int(self, raw_value: Any, fallback: int) -> int:
        try:
            if raw_value is None:
                return fallback
            parsed = int(raw_value)
            return parsed if parsed > 0 else fallback
        except (TypeError, ValueError):
            return fallback

    def _calculate_layout_metrics(self) -> Dict[str, int]:
        page_width = self._safe_int(getattr(self._page, "width", None), self.DEFAULT_PAGE_WIDTH)
        estimated_content_width = max(page_width - 140, 1120)
        horizontal_padding = 32 if estimated_content_width >= 2200 else 24

        container_width = min(
            max(estimated_content_width - horizontal_padding * 2, 1120),
            self.MAX_CONTENT_WIDTH,
        )

        side_candidate = int(container_width * 0.22)

        max_side_for_center = (
            container_width - self.CENTER_COLUMN_MIN_WIDTH - self.COLUMN_GAP * 2
        ) // 2

        if max_side_for_center >= self.SIDE_COLUMN_MIN_WIDTH:
            side_width = self._clamp(
                side_candidate,
                self.SIDE_COLUMN_MIN_WIDTH,
                min(self.SIDE_COLUMN_MAX_WIDTH, max_side_for_center),
            )
        else:
            safe_max = max(max_side_for_center, self.SIDE_COLUMN_FALLBACK_MIN_WIDTH)
            side_width = self._clamp(
                side_candidate,
                self.SIDE_COLUMN_FALLBACK_MIN_WIDTH,
                safe_max,
            )

        center_width = max(
            container_width - side_width * 2 - self.COLUMN_GAP * 2,
            self.CENTER_COLUMN_MIN_WIDTH,
        )

        return {
            "horizontal_padding": horizontal_padding,
            "container_width": container_width,
            "left_width": side_width,
            "right_width": side_width,
            "center_width": center_width,
        }

    def _apply_layout_metrics(self, metrics: Dict[str, int]) -> None:
        self._layout_metrics = metrics

        self.main_row.width = metrics["container_width"]
        self.left_column_container.width = metrics["left_width"]
        self.right_column_container.width = metrics["right_width"]

        self.main_area_container.padding = ft.Padding.only(
            left=metrics["horizontal_padding"],
            right=metrics["horizontal_padding"],
            bottom=self.MAIN_AREA_BOTTOM_PADDING,
        )

        if hasattr(self, "today_section"):
            self.today_section.width = metrics["container_width"]

    def _calculate_calendar_width(self) -> int:
        """
        Вычисляет ширину календаря на основе размеров страницы и layout.

        Returns:
            Приблизительная ширина календаря в пикселях
        """
        try:
            metrics = self._calculate_layout_metrics()
            calendar_width = metrics["center_width"] - 24

            logger.debug(
                f"Вычислена ширина календаря: {calendar_width}px "
                f"(центр: {metrics['center_width']}px, контейнер: {metrics['container_width']}px)"
            )

            return max(calendar_width, 300)  # Минимальная ширина 300px

        except Exception as e:
            logger.error(f"Ошибка при вычислении ширины календаря: {e}")
            return 500  # Fallback к безопасному значению

    def update_calendar_width(self):
        """
        Обновляет ширину календаря в легенде при изменении размеров окна.

        Этот метод может быть вызван при изменении размеров окна
        для обновления адаптивности легенды.
        """
        try:
            metrics = self._calculate_layout_metrics()
            self._apply_layout_metrics(metrics)

            new_width = self._calculate_calendar_width()
            if hasattr(self, "legend") and self.legend:
                self.legend.update_calendar_width(new_width)
                logger.debug(f"Ширина календаря в легенде обновлена до {new_width}px")

            if hasattr(self, "today_section"):
                self.today_section.width = metrics["container_width"]

        except Exception as e:
            logger.error(f"Ошибка при обновлении ширины календаря в легенде: {e}")

    def will_unmount(self):
        """Вызывается при удалении со страницы."""
        # Session НЕ закрывается - это ответственность создателя View
        logger.debug("HomeView размонтирован")

    def did_mount(self):
        """Вызывается после монтирования на страницу."""
        try:
            # Обновляем ширину календаря после монтирования, когда page.width доступен
            self.update_calendar_width()
            self.refresh_today_metrics()
            logger.debug("HomeView смонтирован, ширина календаря обновлена")
        except Exception as e:
            logger.error(f"Ошибка при монтировании HomeView: {e}")

    def _build_today_section(self) -> ft.Container:
        self.today_balance_value = ft.Text(
            "—", size=14, weight=ft.FontWeight.W_600, key="today_balance_value"
        )
        self.today_mandatory_value = ft.Text(
            "—", size=14, weight=ft.FontWeight.W_600, key="today_mandatory_value"
        )
        self.today_risk_7_value = ft.Text(
            "—", size=14, weight=ft.FontWeight.W_600, key="today_risk_7_value"
        )
        self.today_risk_30_value = ft.Text(
            "—", size=14, weight=ft.FontWeight.W_600, key="today_risk_30_value"
        )

        add_tx_btn = ft.Button(
            "+ Добавить транзакцию",
            icon=ft.Icons.ADD,
            key="today_action_add_tx",
            on_click=self.on_today_add_transaction,
            height=40,
        )
        mark_payment_btn = ft.OutlinedButton(
            "Отметить платёж",
            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
            key="today_action_mark_payment",
            on_click=self.on_today_mark_payment,
            height=40,
        )
        open_risk_btn = ft.TextButton(
            "Риск 7/30",
            icon=ft.Icons.WARNING_AMBER_OUTLINED,
            key="today_action_open_risk",
            on_click=self.on_today_open_risk,
        )

        metrics_row = ft.Row(
            spacing=8,
            wrap=True,
            controls=[
                ft.Text("Баланс", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                self.today_balance_value,
                ft.Text("·", color=ft.Colors.OUTLINE_VARIANT),
                ft.Text("Обязательные", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                self.today_mandatory_value,
                ft.Text("·", color=ft.Colors.OUTLINE_VARIANT),
                ft.Text("Риск", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                self.today_risk_7_value,
                ft.Text("/", color=ft.Colors.OUTLINE_VARIANT),
                self.today_risk_30_value,
            ],
        )

        return ft.Container(
            key="today_section",
            width=self._layout_metrics["container_width"],
            height=self.BOTTOM_BAR_HEIGHT,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK),
                offset=ft.Offset(0, -2),
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                "Сегодня",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                key="today_title",
                            ),
                            metrics_row,
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[add_tx_btn, mark_payment_btn, open_risk_btn],
                    ),
                ],
            ),
        )

    def refresh_today_metrics(self) -> None:
        try:
            today = datetime.date.today()

            balance = calculate_actual_balance(self.session, today)
            self.today_balance_value.value = f"{balance:,.2f} ₽".replace(",", " ")

            pending_with_date = pending_payment_service.get_all_pending_payments(
                self.session, has_planned_date=True
            )
            pending_due_today = []
            pending_overdue = []
            for payment in pending_with_date:
                planned_date = getattr(payment, "planned_date", None)
                if not isinstance(planned_date, datetime.date):
                    continue

                if planned_date == today:
                    pending_due_today.append(payment)

                if planned_date < today:
                    pending_overdue.append(payment)

            loan_payments_today = loan_payment_service.get_payments_by_date(self.session, today)
            loan_due_today = []
            for payment in loan_payments_today:
                if getattr(payment, "status", None) == PaymentStatus.PENDING:
                    loan_due_today.append(payment)
            overdue_loan_stats = loan_payment_service.get_overdue_statistics(self.session)

            planned_occurrences_today = planned_transaction_service.get_occurrences_by_date(
                self.session, today
            )
            planned_due_today = []
            for occurrence in planned_occurrences_today:
                if getattr(occurrence, "status", None) == OccurrenceStatus.PENDING:
                    planned_due_today.append(occurrence)

            due_today_count = len(pending_due_today) + len(loan_due_today) + len(planned_due_today)
            overdue_count = len(pending_overdue) + int(
                overdue_loan_stats.get("total_overdue", 0) or 0
            )

            self.today_mandatory_value.value = f"{due_today_count} / {overdue_count}"

            gaps_7 = detect_cash_gaps(self.session, today, today + datetime.timedelta(days=7))
            gaps_30 = detect_cash_gaps(self.session, today, today + datetime.timedelta(days=30))

            self._today_cash_gaps_7 = gaps_7
            self._today_cash_gaps_30 = gaps_30

            self.today_risk_7_value.value = f"{len(gaps_7)} дат"
            self.today_risk_30_value.value = f"{len(gaps_30)} дат"

            self.today_risk_7_value.color = (
                ft.Colors.ERROR if len(gaps_7) > 0 else ft.Colors.ON_SURFACE
            )
            self.today_risk_30_value.color = (
                ft.Colors.ERROR if len(gaps_30) > 0 else ft.Colors.ON_SURFACE
            )
            self.update()

        except Exception as e:
            logger.debug(f"Не удалось обновить метрики 'Сегодня': {e}")

    def on_today_add_transaction(self, e=None):
        self.open_add_transaction_modal()

    def on_today_mark_payment(self, e=None):
        if self.navigate_callback:
            try:
                self.navigate_callback(3)
            except Exception as ex:
                logger.error(f"Ошибка при навигации к отложенным платежам: {ex}")
        else:
            logger.warning("Метод навигации не доступен в HomeView")

    def on_today_open_risk(self, e=None):
        try:
            gaps = self._today_cash_gaps_30
            gaps_text = (
                "\n".join([d.strftime("%d.%m.%Y") for d in gaps[:10]])
                if gaps
                else "Кассовых разрывов не обнаружено"
            )
            if len(gaps) > 10:
                gaps_text += f"\n... (+{len(gaps) - 10})"

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Риск на 30 дней"),
                content=ft.Column(
                    tight=True,
                    spacing=8,
                    controls=[
                        ft.Text(f"Кассовые разрывы: {len(gaps)}"),
                        ft.Text(gaps_text),
                    ],
                ),
                actions=[ft.TextButton("Закрыть", on_click=lambda _: self._page.close(dlg))],
            )
            self._page.open(dlg)
        except Exception as ex:
            logger.error(f"Ошибка при открытии окна риска: {ex}")

    # ========== IHomeViewCallbacks Implementation ==========

    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        """Обновить данные календаря."""
        self.calendar_widget.set_transactions(transactions, occurrences)
        self.update()

    def update_transactions(
        self, date_obj: datetime.date, transactions: List[Any], occurrences: List[Any]
    ) -> None:
        """Обновить список транзакций для выбранной даты."""
        self.selected_date = date_obj
        self.transactions_panel.set_data(date_obj, transactions, occurrences)
        if date_obj == datetime.date.today():
            self.refresh_today_metrics()
        self.update()

    def update_planned_occurrences(
        self, occurrences: List[Tuple[PlannedOccurrence, str, TransactionType]]
    ) -> None:
        """Обновить список плановых операций."""
        self.planned_widget.set_occurrences(occurrences)
        self.update()

    def update_pending_payments(self, payments: List[Any], statistics: Dict[str, Any]) -> None:
        """Обновить список отложенных платежей."""
        self.pending_payments_widget.set_payments(payments, statistics)
        self.update()

    def show_message(self, message: str) -> None:
        """Показать информационное сообщение."""
        self._page.open(ft.SnackBar(content=ft.Text(message)))

    def show_error(self, error: str) -> None:
        """Показать сообщение об ошибке."""
        self._page.open(ft.SnackBar(content=ft.Text(error), bgcolor=ft.Colors.ERROR))

    def update_calendar_selection(self, date_obj: datetime.date) -> None:
        """
        Обновить выделение даты в календаре.

        Программно обновляет выделение даты в календаре без вызова callback.
        Используется для синхронизации календаря при выборе даты из других компонентов.

        Args:
            date_obj: Дата для выделения в календаре
        """
        try:
            logger.debug(f"update_calendar_selection вызван с датой: {date_obj}")

            # Делегируем в calendar_widget для программного обновления выделения
            self.calendar_widget.select_date(date_obj)

            logger.debug(
                f"update_calendar_selection завершён успешно, "
                f"calendar_widget.select_date() вызван для даты {date_obj}"
            )
        except Exception as e:
            logger.warning(
                f"Ошибка при обновлении выделения календаря для даты {date_obj}: {e}", exc_info=True
            )

    # ========== UI Event Handlers (делегируют в Presenter) ==========

    def on_date_selected(self, date_obj: datetime.date):
        """Обработка выбора даты в календаре - делегирует в Presenter."""
        self.presenter.on_date_selected(date_obj)

    def open_add_transaction_modal(self):
        """Открытие модального окна добавления транзакции."""
        try:
            logger.debug(
                f"Открытие модального окна добавления транзакции для даты: {self.selected_date}"
            )

            if not self._page:
                logger.error("Page не инициализирована для открытия модального окна")
                return

            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return

            self.transaction_modal.open(self._page, self.selected_date)
            logger.info("Модальное окно добавления транзакции успешно открыто")

        except Exception as e:
            logger.error(
                f"Ошибка при открытии модального окна добавления транзакции: {e}", exc_info=True
            )
            if self._page:
                try:
                    self._page.open(
                        ft.SnackBar(
                            content=ft.Text("Не удалось открыть форму добавления транзакции"),
                            bgcolor=ft.Colors.ERROR,
                        )
                    )
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def _close_bottom_sheet(self):
        """Закрытие BottomSheet."""
        try:
            if hasattr(self, "bottom_sheet"):
                self._page.close(self.bottom_sheet)
                logger.info("BottomSheet закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии BottomSheet: {e}")

    def _open_real_modal_from_sheet(self):
        """Открытие настоящего модального окна транзакции из BottomSheet."""
        try:
            # Закрываем BottomSheet
            self._close_bottom_sheet()

            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return

            self.transaction_modal.open(self._page, self.selected_date)
            logger.info("Настоящее модальное окно добавления транзакции открыто")

        except Exception as e:
            logger.error(f"Ошибка при открытии настоящего модального окна: {e}", exc_info=True)

    def on_transaction_saved(self, data: TransactionCreate):
        """Обработка сохранения новой транзакции - делегирует в Presenter."""
        self.presenter.create_transaction(data)

    def on_edit_transaction(self, transaction: TransactionDB):
        """Открытие модального окна редактирования транзакции."""
        try:
            logger.debug(
                f"Открытие модального окна редактирования для транзакции: {transaction.id}"
            )

            if not self._page:
                logger.error("Page не инициализирована для открытия модального окна редактирования")
                return

            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return

            self.transaction_modal.open_edit(self._page, transaction)
            logger.info("Модальное окно редактирования транзакции успешно открыто")

        except Exception as e:
            logger.error(
                f"Ошибка при открытии модального окна редактирования транзакции: {e}", exc_info=True
            )
            if self._page:
                try:
                    self._page.open(
                        ft.SnackBar(
                            content=ft.Text("Не удалось открыть форму редактирования транзакции"),
                            bgcolor=ft.Colors.ERROR,
                        )
                    )
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_delete_transaction(self, transaction: TransactionDB):
        """Показ диалога подтверждения удаления транзакции."""
        try:
            logger.debug(f"Запрос на удаление транзакции: {transaction.id}")

            # Получаем имя категории для отображения
            category_name = "Без категории"
            try:
                if transaction.category:
                    category_name = transaction.category.name
            except Exception:
                pass

            def confirm_delete(e):
                self._page.close(dialog)
                # Делегируем в Presenter
                self.presenter.delete_transaction(transaction.id)

            def cancel_delete(e):
                self._page.close(dialog)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Удалить транзакцию?"),
                content=ft.Column(
                    controls=[
                        ft.Text(f"Категория: {category_name}"),
                        ft.Text(f"Сумма: {transaction.amount:.2f} ₽"),
                        ft.Text(f"Описание: {transaction.description or 'Не указано'}"),
                        ft.Text(f"Дата: {transaction.transaction_date.strftime('%d.%m.%Y')}"),
                        ft.Divider(),
                        ft.Text(
                            "Это действие нельзя отменить!",
                            color=ft.Colors.ERROR,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    tight=True,
                    spacing=10,
                ),
                actions=[
                    ft.TextButton("Отмена", on_click=cancel_delete),
                    ft.Button(
                        "Удалить",
                        on_click=confirm_delete,
                        bgcolor=ft.Colors.ERROR,
                        color=ft.Colors.ON_ERROR,
                    ),
                ],
            )

            # Используем page.open() вместо page.dialog
            self._page.open(dialog)

            logger.info("Диалог подтверждения удаления транзакции показан")

        except Exception as e:
            logger.error(f"Ошибка при показе диалога удаления транзакции: {e}", exc_info=True)
            if self._page:
                try:
                    self._page.open(
                        ft.SnackBar(
                            content=ft.Text("Ошибка при открытии диалога удаления"),
                            bgcolor=ft.Colors.ERROR,
                        )
                    )
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_transaction_updated(self, transaction_id: str, data: TransactionUpdate):
        """Обработка сохранения изменений транзакции - делегирует в Presenter."""
        try:
            logger.debug(f"Обработка обновления транзакции: {transaction_id}")
            self.presenter.update_transaction(transaction_id, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления транзакции: {e}", exc_info=True)
            if self._page:
                try:
                    self._page.open(
                        ft.SnackBar(
                            content=ft.Text("Ошибка при сохранении изменений транзакции"),
                            bgcolor=ft.Colors.ERROR,
                        )
                    )
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_execute_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для исполнения планового вхождения."""
        self.execute_occurrence_modal.open(self._page, occurrence)

    def on_skip_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для пропуска планового вхождения."""
        self.execute_occurrence_modal.open(self._page, occurrence)

    def on_occurrence_executed_confirm(
        self, occurrence_id: str, amount: Decimal, execution_date: datetime.date
    ):
        """Подтверждение исполнения вхождения - делегирует в Presenter."""
        # Получаем occurrence из БД
        from finance_tracker.models import PlannedOccurrenceDB

        occurrence = self.session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
        if occurrence:
            self.presenter.execute_occurrence(occurrence, execution_date, amount)

    def on_occurrence_skipped_confirm(self, occurrence_id: str, reason: Optional[str]):
        """Подтверждение пропуска вхождения - делегирует в Presenter."""
        # Получаем occurrence из БД
        from finance_tracker.models import PlannedOccurrenceDB

        occurrence = self.session.query(PlannedOccurrenceDB).filter_by(id=occurrence_id).first()
        if occurrence:
            self.presenter.skip_occurrence(occurrence)

    def on_occurrence_rescheduled_confirm(self, occurrence_id: str, new_date: datetime.date):
        """Подтверждение переноса вхождения - делегирует в Presenter."""
        self.presenter.reschedule_occurrence(occurrence_id, new_date)

    def on_occurrence_clicked(self, occurrence: PlannedOccurrence):
        """
        Обработка клика на плановое вхождение в обзорном виджете.

        Переключает календарь на дату вхождения для отображения
        связанных транзакций в правой панели.

        Args:
            occurrence: Плановое вхождение, на которое кликнули.
        """
        try:
            logger.debug(
                f"[ДИАГНОСТИКА] on_occurrence_clicked вызван для вхождения: {occurrence.id}, "
                f"дата: {occurrence.occurrence_date}"
            )
            # Делегируем в Presenter для обновления выбранной даты
            self.presenter.on_date_selected(occurrence.occurrence_date)
            logger.info(
                f"[ДИАГНОСТИКА] Календарь переключён на дату вхождения: {occurrence.occurrence_date}"
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке клика на вхождение: {e}", exc_info=True)
            self.show_error("Не удалось переключить календарь на дату вхождения")

    def on_show_all_occurrences(self):
        """Переход к разделу всех плановых транзакций."""
        if self.navigate_callback:
            try:
                self.navigate_callback(1)
                logger.info("Переход к разделу плановых транзакций")
            except Exception as e:
                logger.error(f"Ошибка при навигации к плановым транзакциям: {e}")
        else:
            logger.warning("Метод навигации не доступен в HomeView")

    def on_execute_payment(self, payment):
        """Открытие модального окна для исполнения отложенного платежа."""
        self.execute_payment_modal.open(self._page, payment)

    def on_cancel_payment(self, payment):
        """Отмена отложенного платежа."""
        # Показываем диалог с подтверждением и полем для причины
        reason_field = ft.TextField(
            label="Причина отмены (опционально)", multiline=True, max_lines=3
        )

        def confirm_cancel(e):
            reason = reason_field.value or None
            self._page.close(dialog)
            # Делегируем в Presenter
            self.presenter.cancel_pending_payment(payment.id, reason)

        def cancel_dialog(e):
            self._page.close(dialog)

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
                ft.TextButton("Отмена", on_click=cancel_dialog),
                ft.Button("Отменить платёж", on_click=confirm_cancel),
            ],
        )

        self._page.open(dialog)

    def on_delete_payment(self, payment_id: int):
        """Удаление отложенного платежа."""

        def confirm_delete(e):
            self._page.close(dialog)
            # Делегируем в Presenter
            self.presenter.delete_pending_payment(payment_id)

        def cancel_delete(e):
            self._page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удалить платёж?"),
            content=ft.Text("Это действие нельзя отменить!"),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_delete),
                ft.Button("Удалить", on_click=confirm_delete, bgcolor=ft.Colors.ERROR),
            ],
        )

        self._page.open(dialog)

    def on_payment_executed_confirm(
        self, payment_id: str, executed_amount: Decimal, executed_date: datetime.date
    ):
        """Подтверждение исполнения отложенного платежа - делегирует в Presenter."""
        self.presenter.execute_pending_payment(payment_id, executed_amount, executed_date)

    def on_show_all_payments(self):
        """Переход к разделу всех отложенных платежей."""
        if self.navigate_callback:
            try:
                # Индекс 3 соответствует разделу "Отложенные платежи"
                self.navigate_callback(3)
                logger.info("Переход к разделу отложенных платежей")
            except Exception as e:
                logger.error(f"Ошибка при навигации к отложенным платежам: {e}")
        else:
            logger.warning("Метод навигации не доступен в HomeView")

    def on_add_pending_payment(self):
        """Открытие модального окна добавления отложенного платежа."""
        try:
            logger.debug("Открытие модального окна добавления отложенного платежа")

            if not self._page:
                logger.error("Page не инициализирована")
                return

            if not self.payment_modal:
                logger.error("PendingPaymentModal не инициализирован")
                return

            self.payment_modal.open(self._page)
            logger.info("Модальное окно добавления отложенного платежа открыто")

        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
            if self._page:
                self._page.open(
                    ft.SnackBar(
                        content=ft.Text("Не удалось открыть форму добавления платежа"),
                        bgcolor=ft.Colors.ERROR,
                    )
                )

    def on_pending_payment_saved(self, data: PendingPaymentCreate):
        """Обработка сохранения нового отложенного платежа."""
        self.presenter.create_pending_payment(data)

    def on_edit_pending_payment(self, payment: PendingPaymentDB):
        """
        Открытие модального окна редактирования отложенного платежа.

        Args:
            payment: Платёж для редактирования.
        """
        try:
            logger.debug(f"Открытие модального окна редактирования платежа: {payment.id}")

            if not self._page:
                logger.error("Page не инициализирована")
                return

            if not self.payment_modal:
                logger.error("PendingPaymentModal не инициализирован")
                return

            self.payment_modal.open(self._page, payment=payment)
            logger.info("Модальное окно редактирования отложенного платежа открыто")

        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна редактирования: {e}", exc_info=True)
            if self._page:
                self._page.open(
                    ft.SnackBar(
                        content=ft.Text("Не удалось открыть форму редактирования платежа"),
                        bgcolor=ft.Colors.ERROR,
                    )
                )

    def on_pending_payment_updated(self, payment_id: str, data: PendingPaymentUpdate):
        """
        Обработка сохранения изменений отложенного платежа.

        Args:
            payment_id: ID платежа.
            data: Данные для обновления.
        """
        self.presenter.update_pending_payment(payment_id, data)

    def on_add_planned_transaction(self):
        """
        Открытие модального окна добавления плановой транзакции.

        Вызывается при нажатии кнопки "+" в виджете плановых транзакций.
        """
        try:
            logger.debug("Открытие модального окна добавления плановой транзакции")

            if not self._page:
                logger.error("Page не инициализирована")
                return

            self.planned_transaction_modal.open(self._page, self.selected_date)
            logger.info("Модальное окно добавления плановой транзакции открыто")

        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
            self.show_error("Не удалось открыть форму добавления плановой транзакции")

    def on_planned_transaction_saved(self, data: PlannedTransactionCreate):
        """
        Обработка сохранения новой плановой транзакции.

        Args:
            data: Данные для создания плановой транзакции.
        """
        self.presenter.create_planned_transaction(data)

    def on_execute_loan_payment(self, payment: LoanPaymentDB):
        """Исполнение платежа по кредиту."""
        # Показываем диалог с подтверждением
        amount_field = ft.TextField(
            label="Сумма платежа",
            value=str(float(payment.total_amount)),
            keyboard_type=ft.KeyboardType.NUMBER,
            suffix="₽",
        )

        date_field = ft.TextField(
            label="Дата исполнения",
            value=datetime.date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-MM-DD",
        )

        def confirm_execute(e):
            # Валидация суммы
            try:
                amount = Decimal(amount_field.value)
                if amount <= 0:
                    raise ValueError("Сумма должна быть больше 0")
            except (ValueError, Exception) as ex:
                self._page.open(ft.SnackBar(content=ft.Text(f"Некорректная сумма: {ex}")))
                return

            # Валидация даты
            try:
                exec_date = datetime.datetime.strptime(date_field.value, "%Y-%m-%d").date()
            except ValueError:
                self._page.open(
                    ft.SnackBar(content=ft.Text("Некорректный формат даты (ожидается YYYY-MM-DD)"))
                )
                return

            self._page.close(dialog)
            # Делегируем в Presenter
            self.presenter.execute_loan_payment(payment, amount, exec_date)

        try:
            loan_name = payment.loan.name if payment.loan else "Неизвестный кредит"
        except Exception:
            loan_name = "Неизвестный кредит"

        def cancel_execute(e):
            self._page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Исполнить платёж по кредиту"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Кредит: {loan_name}"),
                    ft.Text(f"Плановая сумма: {payment.total_amount:.2f} ₽"),
                    ft.Divider(),
                    amount_field,
                    date_field,
                ],
                tight=True,
                spacing=10,
                width=400,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_execute),
                ft.Button("Исполнить", on_click=confirm_execute, bgcolor=ft.Colors.PRIMARY),
            ],
        )

        self._page.open(dialog)
