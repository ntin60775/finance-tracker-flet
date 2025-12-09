import datetime
from typing import Optional

import flet as ft
from finance_tracker.services.plan_fact_service import get_plan_fact_analysis
from finance_tracker.services.category_service import get_all_categories
from finance_tracker.database import get_db
from finance_tracker.utils.logger import get_logger
from finance_tracker.components.occurrence_details_modal import OccurrenceDetailsModal

logger = get_logger(__name__)


class PlanFactView(ft.Container):
    """
    Экран план-факт анализа.
    
    Позволяет просматривать статистику исполнения плановых транзакций,
    анализировать отклонения по суммам и датам.
    """

    def __init__(self):
        super().__init__()
        self.alignment = ft.alignment.top_left
        self.start_date = datetime.date.today().replace(day=1)
        self.end_date = self._get_last_day_of_month(datetime.date.today())
        self.selected_category_id: Optional[int] = None
        
        # Components
        self.details_modal = OccurrenceDetailsModal()
        
        # UI Components
        self.date_range_button = ft.ElevatedButton(
            text=f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=self._open_date_picker
        )
        self.category_dropdown = ft.Dropdown(
            label="Категория",
            width=200,
            options=[],
            on_change=self._on_category_change,
            dense=True
        )
        
        # Statistics Cards
        self.stat_total = self._build_stat_card("Всего вхождений", "0", ft.Icons.LIST, ft.Colors.BLUE)
        self.stat_executed = self._build_stat_card("Исполнено", "0", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN)
        self.stat_skipped = self._build_stat_card("Пропущено", "0", ft.Icons.CANCEL, ft.Colors.GREY)
        self.stat_deviation = self._build_stat_card("Среднее отклонение", "0.00 ₽", ft.Icons.TRENDING_UP, ft.Colors.ORANGE)
        
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
            rows=[]
        )
        
        self.content = ft.Column(
            controls=[
                ft.Text("План-факт анализ", size=24, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        self.date_range_button,
                        self.category_dropdown,
                        ft.IconButton(icon=ft.Icons.REFRESH, on_click=self._refresh_data, tooltip="Обновить")
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Row(
                    controls=[
                        self.stat_total,
                        self.stat_executed,
                        self.stat_skipped,
                        self.stat_deviation
                    ],
                    scroll=ft.ScrollMode.AUTO
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[self.data_table],
                        scroll=ft.ScrollMode.AUTO
                    ),
                    border=ft.border.all(1, "outlineVariant"),
                    border_radius=10,
                    padding=10,
                    expand=True
                )
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO, # Page scroll
            expand=True,
            alignment=ft.MainAxisAlignment.START
        )

    def did_mount(self):
        """Вызывается после монтирования."""
        self._load_categories()
        self._load_data()

    def _get_last_day_of_month(self, date_obj: datetime.date) -> datetime.date:
        """Возвращает последний день месяца для переданной даты."""
        next_month = date_obj.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def _open_date_picker(self, e):
        """Открывает диалог выбора дат (упрощенно - пока выбор месяца)."""
        # TODO: Реализовать полноценный DateRangePicker. 
        # Пока просто переключаем на текущий месяц.
        # В реальном приложении здесь нужен модальный диалог.
        pass

    def _load_categories(self):
        """Загружает список категорий для фильтра."""
        try:
            with get_db() as session:
                categories = get_all_categories(session)
                self.category_dropdown.options = [
                    ft.dropdown.Option("all", "Все категории")
                ] + [
                    ft.dropdown.Option(str(c.id), c.name) for c in categories
                ]
                self.category_dropdown.value = "all"
                self.update()
        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")

    def _on_category_change(self, e):
        """Обработчик изменения категории."""
        val = self.category_dropdown.value
        self.selected_category_id = int(val) if val and val != "all" else None
        self._load_data()

    def _refresh_data(self, e):
        self._load_data()

    def _load_data(self):
        """Загружает данные анализа."""
        try:
            with get_db() as session:
                analysis = get_plan_fact_analysis(
                    session,
                    self.start_date,
                    self.end_date,
                    self.selected_category_id
                )
                self._update_ui(analysis)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных анализа: {e}")
            if self.page:
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text(f"Ошибка: {e}"), bgcolor=ft.Colors.ERROR))

    def _update_ui(self, analysis: dict):
        """Обновляет UI на основе полученных данных."""
        if not self.page:
            return

        # Update Stats
        self._update_stat_card(self.stat_total, str(analysis['total_occurrences']))
        self._update_stat_card(self.stat_executed, f"{analysis['executed_count']} ({analysis['on_time_percentage']:.0f}%)")
        self._update_stat_card(self.stat_skipped, f"{analysis['skipped_count']} ({analysis['skipped_percentage']:.0f}%)")
        
        avg_dev = analysis['avg_amount_deviation']
        
        self._update_stat_card(self.stat_deviation, f"{avg_dev:+.2f} ₽")

        # Update Table
        self.data_table.rows.clear()
        
        for occ in analysis['occurrences']:
            status_colors = {
                "pending": ft.Colors.ORANGE,
                "executed": ft.Colors.GREEN,
                "skipped": ft.Colors.GREY
            }
            status_color = status_colors.get(occ['status'], ft.Colors.BLACK)
            
            planned_amt = occ['planned_amount']
            actual_amt = occ['actual_amount'] if occ['actual_amount'] is not None else 0
            deviation = occ['amount_deviation'] if occ['amount_deviation'] is not None else 0
            
            dev_text_color = ft.Colors.BLACK
            if deviation > 0:
                dev_text_color = ft.Colors.RED # Перерасход (грубо)
            elif deviation < 0:
                dev_text_color = ft.Colors.GREEN # Экономия
            
            self.data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(occ['scheduled_date'])),
                        ft.DataCell(ft.Text(occ['category_name'])),
                        ft.DataCell(ft.Text(occ['description'] or "")),
                        ft.DataCell(ft.Text(f"{planned_amt:,.2f}")),
                        ft.DataCell(ft.Text(f"{actual_amt:,.2f}" if occ['status'] == 'executed' else "-")),
                        ft.DataCell(ft.Text(f"{deviation:+.2f}" if occ['status'] == 'executed' else "-", color=dev_text_color)),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(occ['status']),
                                bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                padding=5,
                                border_radius=5
                            )
                        ),
                    ],
                    on_select_changed=lambda _, x=occ: self._show_details(x)
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
                            ft.Text(value, size=20, weight=ft.FontWeight.BOLD)
                        ],
                        spacing=2
                    )
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=15
            ),
            padding=15,
            width=220,
            bgcolor="surfaceVariant",
            border_radius=10
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