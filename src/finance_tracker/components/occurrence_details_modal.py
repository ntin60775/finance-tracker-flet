
import flet as ft
from finance_tracker.models.enums import OccurrenceStatus

class OccurrenceDetailsModal(ft.AlertDialog):
    """
    Модальное окно для просмотра деталей планового вхождения.
    Отображает плановые данные, фактические данные и отклонения.
    """

    def __init__(self):
        super().__init__()
        self.title = ft.Text("Детали операции")
        self.scrollable = True
        
        # UI Components
        self.content_column = ft.Column(spacing=20, width=400, scroll=ft.ScrollMode.AUTO)
        self.content = self.content_column
        self.actions = [
            ft.TextButton("Закрыть", on_click=self.close)
        ]

    def show(self, page: ft.Page, details: dict):
        """
        Показывает модальное окно с данными.
        
        Args:
            page: Текущая страница Flet.
            details: Словарь с деталями вхождения (из get_occurrence_details или get_plan_fact_analysis).
        """
        self.page = page
        self._build_content(details)
        page.dialog = self
        self.open = True
        page.update()

    def close(self, e=None):
        """Закрывает модальное окно."""
        self.open = False
        if self.page:
            self.page.update()

    def _build_content(self, details: dict):
        """Строит содержимое окна на основе данных."""
        self.content_column.controls.clear()
        
        # --- Status Header ---
        status_value = details.get('status', 'unknown')
        status_colors = {
            OccurrenceStatus.PENDING: ft.Colors.ORANGE,
            OccurrenceStatus.EXECUTED: ft.Colors.GREEN,
            OccurrenceStatus.SKIPPED: ft.Colors.GREY
        }
        status_color = status_colors.get(status_value, ft.Colors.BLACK)
        
        status_names = {
            OccurrenceStatus.PENDING: "Ожидает",
            OccurrenceStatus.EXECUTED: "Исполнено",
            OccurrenceStatus.SKIPPED: "Пропущено"
        }
        status_text = status_names.get(status_value, status_value)

        self.content_column.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.WHITE),
                        ft.Text(status_text.upper(), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                bgcolor=status_color,
                padding=10,
                border_radius=5
            )
        )

        # --- Planned Data Section ---
        planned_date = details.get('scheduled_date', '')
        planned_amount = details.get('planned_amount', 0)
        category = details.get('category_name', 'Без категории')
        description = details.get('description') or "-"

        self.content_column.controls.append(
            self._build_section(
                "Плановые данные",
                [
                    ("Дата:", planned_date),
                    ("Сумма:", f"{planned_amount:,.2f} ₽"),
                    ("Категория:", category),
                    ("Описание:", description),
                ]
            )
        )

        # --- Actual Data Section (if executed) ---
        if status_value == OccurrenceStatus.EXECUTED:
            executed_date = details.get('executed_date', '')
            actual_amount = details.get('actual_amount', 0)
            amt_dev = details.get('amount_deviation', 0)
            date_dev = details.get('date_deviation', 0)
            
            dev_color = ft.Colors.RED if amt_dev > 0 else ft.Colors.GREEN # Условно
            
            self.content_column.controls.append(ft.Divider())
            self.content_column.controls.append(
                self._build_section(
                    "Фактические данные",
                    [
                        ("Дата исполнения:", executed_date),
                        ("Фактическая сумма:", f"{actual_amount:,.2f} ₽"),
                    ]
                )
            )
            
            self.content_column.controls.append(ft.Divider())
            self.content_column.controls.append(
                self._build_section(
                    "Отклонения",
                    [
                        ("По сумме:", ft.Text(f"{amt_dev:+.2f} ₽", color=dev_color, weight=ft.FontWeight.BOLD)),
                        ("По дате:", f"{date_dev:+} дн."),
                    ]
                )
            )
            
        elif status_value == OccurrenceStatus.SKIPPED:
            skip_reason = details.get('skip_reason') or "Не указана"
            self.content_column.controls.append(ft.Divider())
            self.content_column.controls.append(
                self._build_section(
                    "Информация о пропуске",
                    [
                        ("Причина:", skip_reason),
                    ]
                )
            )

    def _build_section(self, title: str, rows: list):
        """Строит секцию с данными."""
        controls = [
            ft.Text(title, weight=ft.FontWeight.BOLD, size=16),
            ft.Container(height=5)
        ]
        
        for label, value in rows:
            val_control = value if isinstance(value, ft.Control) else ft.Text(str(value), weight=ft.FontWeight.W_500)
            
            controls.append(
                ft.Row(
                    controls=[
                        ft.Text(label, color="outline", width=120),
                        val_control
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START
                )
            )
            
        return ft.Column(controls=controls, spacing=5)
