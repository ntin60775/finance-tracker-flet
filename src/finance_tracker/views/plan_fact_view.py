import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

import flet as ft
from finance_tracker.services.plan_fact_service import get_plan_fact_analysis
from finance_tracker.services.category_service import get_all_categories
from finance_tracker.database import get_db
from finance_tracker.utils.logger import get_logger
from finance_tracker.components.occurrence_details_modal import OccurrenceDetailsModal
from finance_tracker.views.transaction_history_view import (
    _build_category_filter_metadata,
    _resolve_selected_category_ids,
)

logger = get_logger(__name__)


def _apply_category_aggregate_filter(
    analysis: Dict[str, Any],
    selected_category_ids: Optional[Set[str]],
) -> Dict[str, Any]:
    if not selected_category_ids:
        return analysis

    filtered_occurrences = [
        occurrence
        for occurrence in analysis.get("occurrences", [])
        if str(occurrence.get("category_id")) in selected_category_ids
    ]

    return _recalculate_analysis_summary(filtered_occurrences)


def _recalculate_analysis_summary(occurrences: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_occurrences = len(occurrences)
    executed_count = 0
    skipped_count = 0
    pending_count = 0
    executed_with_deviation_count = 0
    on_time_count = 0
    total_amount_deviation = Decimal("0.0")
    total_date_deviation_days = 0.0

    for occurrence in occurrences:
        status = occurrence.get("status")

        if status == "executed":
            executed_count += 1
            amount_deviation = occurrence.get("amount_deviation")
            if amount_deviation is not None:
                total_amount_deviation += Decimal(str(amount_deviation))
                executed_with_deviation_count += 1

            date_deviation = occurrence.get("date_deviation")
            if date_deviation is not None:
                date_deviation_value = float(date_deviation)
                total_date_deviation_days += date_deviation_value
                if date_deviation_value == 0:
                    on_time_count += 1
        elif status == "skipped":
            skipped_count += 1
        elif status == "pending":
            pending_count += 1

    avg_amount_deviation = (
        total_amount_deviation / executed_with_deviation_count
        if executed_with_deviation_count > 0
        else Decimal("0.0")
    )

    avg_date_deviation_days = (
        total_date_deviation_days / executed_count if executed_count > 0 else 0.0
    )

    on_time_percentage = (on_time_count / executed_count * 100) if executed_count > 0 else 0.0
    skipped_percentage = (skipped_count / total_occurrences * 100) if total_occurrences > 0 else 0.0

    return {
        "total_occurrences": total_occurrences,
        "executed_count": executed_count,
        "skipped_count": skipped_count,
        "pending_count": pending_count,
        "avg_amount_deviation": avg_amount_deviation,
        "avg_date_deviation_days": avg_date_deviation_days,
        "on_time_percentage": on_time_percentage,
        "skipped_percentage": skipped_percentage,
        "occurrences": occurrences,
    }


class PlanFactView(ft.Container):
    """
    Экран план-факт анализа.

    Позволяет просматривать статистику исполнения плановых транзакций,
    анализировать отклонения по суммам и датам.
    """

    def __init__(self):
        super().__init__()
        self.alignment = ft.Alignment.TOP_LEFT
        self.start_date = datetime.date.today().replace(day=1)
        self.end_date = self._get_last_day_of_month(datetime.date.today())
        self.selected_category_id: Optional[str] = None
        self.selected_category_ids: Optional[Set[str]] = None
        self.comparison_enabled = False
        self.comparison_start_date: Optional[datetime.date] = None
        self.comparison_end_date: Optional[datetime.date] = None
        self._saved_filters_state = {}
        self._category_filter_ids_by_option: Dict[str, Set[str]] = {}

        # Components
        self.details_modal = OccurrenceDetailsModal()

        # UI Components
        self.date_range_button = ft.Button(
            content=f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=self._open_date_picker,
        )
        self.category_dropdown = ft.Dropdown(
            label="Категория", width=200, options=[], on_select=self._on_category_change, dense=True
        )
        self.comparison_checkbox = ft.Checkbox(
            label="Сравнить с предыдущим периодом",
            value=self.comparison_enabled,
            on_change=self._on_comparison_toggle,
        )

        # Statistics Cards
        self.stat_total = self._build_stat_card(
            "Всего вхождений", "0", ft.Icons.LIST, ft.Colors.BLUE
        )
        self.stat_executed = self._build_stat_card(
            "Исполнено", "0", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN
        )
        self.stat_skipped = self._build_stat_card("Пропущено", "0", ft.Icons.CANCEL, ft.Colors.GREY)
        self.stat_deviation = self._build_stat_card(
            "Среднее отклонение", "0.00 ₽", ft.Icons.TRENDING_UP, ft.Colors.ORANGE
        )

        # Data Table
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Дата плана")),
                ft.DataColumn(ft.Text("Категория")),
                ft.DataColumn(ft.Text("Описание")),
                ft.DataColumn(ft.Text("План")),
                ft.DataColumn(ft.Text("Факт")),
                ft.DataColumn(ft.Text("Отклонение")),
                ft.DataColumn(ft.Text("Статус")),
            ],
            rows=[],
        )

        self.content = ft.Column(
            controls=[
                ft.Text("План-факт анализ", size=24, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        self.date_range_button,
                        self.category_dropdown,
                        self.comparison_checkbox,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH, on_click=self._refresh_data, tooltip="Обновить"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    controls=[
                        self.stat_total,
                        self.stat_executed,
                        self.stat_skipped,
                        self.stat_deviation,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                ft.Container(
                    content=ft.Column(controls=[self.data_table], scroll=ft.ScrollMode.AUTO),
                    border=ft.Border.all(1, "outlineVariant"),
                    border_radius=10,
                    padding=10,
                    expand=True,
                ),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,  # Page scroll
            expand=True,
            alignment=ft.MainAxisAlignment.START,
        )
        self._save_filters_state()

    def did_mount(self):
        """Вызывается после монтирования."""
        self._restore_filters_state()
        self._apply_comparison_state()
        self._update_date_range_button_text()
        self._load_categories()
        self._load_data()

    def _get_last_day_of_month(self, date_obj: datetime.date) -> datetime.date:
        """Возвращает последний день месяца для переданной даты."""
        next_month = date_obj.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def _open_date_picker(self, e):
        if not self.page:
            return

        start_field = ft.TextField(
            label="Дата начала (YYYY-MM-DD)",
            value=self.start_date.isoformat(),
            width=260,
        )
        end_field = ft.TextField(
            label="Дата конца (YYYY-MM-DD)",
            value=self.end_date.isoformat(),
            width=260,
        )
        error_text = ft.Text(value="", color=ft.Colors.ERROR, visible=False)

        def apply_preset(preset_key: str):
            preset_start, preset_end = self._get_preset_range(preset_key)
            start_field.value = preset_start.isoformat()
            end_field.value = preset_end.isoformat()
            self.update()

        def on_save(_):
            try:
                parsed_start = datetime.date.fromisoformat(start_field.value.strip())
                parsed_end = datetime.date.fromisoformat(end_field.value.strip())
            except (TypeError, ValueError):
                error_text.value = "Введите даты в формате YYYY-MM-DD"
                error_text.visible = True
                self.update()
                return

            if parsed_start > parsed_end:
                error_text.value = "Дата начала не может быть позже даты окончания"
                error_text.visible = True
                self.update()
                return

            self.start_date = parsed_start
            self.end_date = parsed_end
            self._apply_comparison_state()
            self._save_filters_state()
            self._update_date_range_button_text()
            self.page.close(dialog)
            self._load_data()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Период анализа"),
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                "Текущий месяц", on_click=lambda _: apply_preset("current_month")
                            ),
                            ft.TextButton(
                                "Прошлый месяц", on_click=lambda _: apply_preset("previous_month")
                            ),
                            ft.TextButton(
                                "Последние 30 дней", on_click=lambda _: apply_preset("last_30_days")
                            ),
                        ],
                        spacing=8,
                    ),
                    start_field,
                    end_field,
                    error_text,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dialog)),
                ft.FilledButton("Применить", on_click=on_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(dialog)

    def _get_preset_range(self, preset_key: str) -> tuple[datetime.date, datetime.date]:
        today = datetime.date.today()

        if preset_key == "current_month":
            start = today.replace(day=1)
            end = self._get_last_day_of_month(today)
            return start, end

        if preset_key == "previous_month":
            current_month_start = today.replace(day=1)
            previous_month_end = current_month_start - datetime.timedelta(days=1)
            previous_month_start = previous_month_end.replace(day=1)
            return previous_month_start, previous_month_end

        if preset_key == "last_30_days":
            return today - datetime.timedelta(days=29), today

        return self.start_date, self.end_date

    def _on_comparison_toggle(self, e):
        self.comparison_enabled = bool(self.comparison_checkbox.value)
        self._apply_comparison_state()
        self._save_filters_state()
        self._update_date_range_button_text()
        self._load_data()

    def _apply_comparison_state(self):
        if not self.comparison_enabled:
            self.comparison_start_date = None
            self.comparison_end_date = None
            self.comparison_checkbox.value = False
            return

        self.comparison_checkbox.value = True
        self.comparison_start_date, self.comparison_end_date = self._calculate_previous_period(
            self.start_date,
            self.end_date,
        )

    def _calculate_previous_period(
        self,
        current_start: datetime.date,
        current_end: datetime.date,
    ) -> tuple[datetime.date, datetime.date]:
        period_days = (current_end - current_start).days + 1
        previous_end = current_start - datetime.timedelta(days=1)
        previous_start = previous_end - datetime.timedelta(days=period_days - 1)
        return previous_start, previous_end

    def _update_date_range_button_text(self):
        date_text = f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}"
        if self.comparison_enabled and self.comparison_start_date and self.comparison_end_date:
            comparison_text = (
                f"Сравнение: {self.comparison_start_date.strftime('%d.%m.%Y')} - "
                f"{self.comparison_end_date.strftime('%d.%m.%Y')}"
            )
            self.date_range_button.content = f"{date_text} | {comparison_text}"
            return

        self.date_range_button.content = date_text

    def _save_filters_state(self):
        self._saved_filters_state = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "selected_category_id": self.selected_category_id,
            "comparison_enabled": self.comparison_enabled,
            "comparison_start_date": self.comparison_start_date,
            "comparison_end_date": self.comparison_end_date,
        }

    def _restore_filters_state(self):
        if not self._saved_filters_state:
            return

        self.start_date = self._saved_filters_state.get("start_date", self.start_date)
        self.end_date = self._saved_filters_state.get("end_date", self.end_date)
        self.selected_category_id = self._saved_filters_state.get("selected_category_id")
        if self.selected_category_id is not None:
            self.selected_category_id = str(self.selected_category_id)
        self.selected_category_ids = None
        self.comparison_enabled = self._saved_filters_state.get("comparison_enabled", False)
        self.comparison_start_date = self._saved_filters_state.get("comparison_start_date")
        self.comparison_end_date = self._saved_filters_state.get("comparison_end_date")

    def _load_categories(self):
        """Загружает список категорий для фильтра."""
        try:
            with get_db() as session:
                categories = get_all_categories(session)
                labels_by_id, self._category_filter_ids_by_option = _build_category_filter_metadata(
                    categories
                )
                options = [ft.dropdown.Option("all", "Все категории")]
                for category in categories:
                    category_id = str(category.id)
                    category_label = labels_by_id.get(category_id)
                    if category_label is None:
                        category_label = str(category.name)
                    options.append(ft.dropdown.Option(category_id, str(category_label)))

                self.category_dropdown.options = options

                selected_value = "all"
                if self.selected_category_id is not None:
                    selected_candidate = str(self.selected_category_id)
                    option_keys = {option.key for option in options}
                    if selected_candidate in option_keys:
                        selected_value = selected_candidate
                    else:
                        self.selected_category_id = None

                self.category_dropdown.value = selected_value
                self.selected_category_ids = _resolve_selected_category_ids(
                    self.selected_category_id,
                    self._category_filter_ids_by_option,
                )
                self._save_filters_state()
                self.update()
        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")

    def _on_category_change(self, e):
        """Обработчик изменения категории."""
        val = self.category_dropdown.value
        self.selected_category_id = val if val and val != "all" else None
        self.selected_category_ids = _resolve_selected_category_ids(
            self.selected_category_id,
            self._category_filter_ids_by_option,
        )
        self._save_filters_state()
        self._load_data()

    def _refresh_data(self, e):
        self._load_data()

    def _load_data(self):
        """Загружает данные анализа."""
        try:
            with get_db() as session:
                use_aggregate_filter = (
                    bool(self.selected_category_ids) and len(self.selected_category_ids) > 1
                )
                category_id_for_service = (
                    None if use_aggregate_filter else self.selected_category_id
                )

                analysis = get_plan_fact_analysis(
                    session,
                    self.start_date,
                    self.end_date,
                    category_id_for_service,
                )
                if use_aggregate_filter:
                    analysis = _apply_category_aggregate_filter(
                        analysis, self.selected_category_ids
                    )
                self._update_ui(analysis)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных анализа: {e}")
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {e}"), bgcolor=ft.Colors.ERROR)
                )

    def _update_ui(self, analysis: dict):
        """Обновляет UI на основе полученных данных."""
        if not self.page:
            return

        # Update Stats
        self._update_stat_card(self.stat_total, str(analysis["total_occurrences"]))
        self._update_stat_card(
            self.stat_executed,
            f"{analysis['executed_count']} ({analysis['on_time_percentage']:.0f}%)",
        )
        self._update_stat_card(
            self.stat_skipped,
            f"{analysis['skipped_count']} ({analysis['skipped_percentage']:.0f}%)",
        )

        avg_dev = analysis["avg_amount_deviation"]

        self._update_stat_card(self.stat_deviation, f"{avg_dev:+.2f} ₽")

        # Update Table
        self.data_table.rows.clear()

        for occ in analysis["occurrences"]:
            status_colors = {
                "pending": ft.Colors.ORANGE,
                "executed": ft.Colors.GREEN,
                "skipped": ft.Colors.GREY,
            }
            status_color = status_colors.get(occ["status"], ft.Colors.BLACK)

            planned_amt = occ["planned_amount"]
            actual_amt = occ["actual_amount"] if occ["actual_amount"] is not None else 0
            deviation = occ["amount_deviation"] if occ["amount_deviation"] is not None else 0

            dev_text_color = ft.Colors.BLACK
            if deviation > 0:
                dev_text_color = ft.Colors.RED  # Перерасход (грубо)
            elif deviation < 0:
                dev_text_color = ft.Colors.GREEN  # Экономия

            self.data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(occ["scheduled_date"])),
                        ft.DataCell(ft.Text(occ["category_name"])),
                        ft.DataCell(ft.Text(occ["description"] or "")),
                        ft.DataCell(ft.Text(f"{planned_amt:,.2f}")),
                        ft.DataCell(
                            ft.Text(f"{actual_amt:,.2f}" if occ["status"] == "executed" else "-")
                        ),
                        ft.DataCell(
                            ft.Text(
                                f"{deviation:+.2f}" if occ["status"] == "executed" else "-",
                                color=dev_text_color,
                            )
                        ),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(occ["status"]),
                                bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                padding=5,
                                border_radius=5,
                            )
                        ),
                    ],
                    on_select_change=lambda _, x=occ: self._show_details(x),
                )
            )

        self.update()

    def _build_stat_card(self, title: str, value: str, icon: str, color: str):
        """Создает карточку статистики."""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=color, size=30),
                    ft.Column(
                        controls=[
                            ft.Text(title, size=12, color="outline"),
                            ft.Text(value, size=20, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=2,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=15,
            ),
            padding=15,
            width=220,
            bgcolor="surfaceVariant",
            border_radius=10,
        )

    def _update_stat_card(self, card: ft.Container, value: str):
        """Обновляет значение в карточке статистики."""
        try:
            text_control = card.content.controls[1].controls[1]
            text_control.value = value
        except Exception:
            pass

    def _show_details(self, occurrence: dict):
        """Показывает детали в модальном окне."""
        self.details_modal.show(self.page, occurrence)
