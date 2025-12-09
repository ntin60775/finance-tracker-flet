import flet as ft
import logging
from finance_tracker.config import settings
from finance_tracker.utils.error_handler import safe_handler

logger = logging.getLogger(__name__)

class SettingsView(ft.Column):
    """
    Представление настроек приложения.
    Позволяет изменять тему оформления, путь к базе данных и форматы отображения.
    """

    def __init__(self, page: ft.Page):
        super().__init__(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            alignment=ft.MainAxisAlignment.START
        )
        self.page = page
        
        self._init_controls()
        self._update_controls_values()

    def _init_controls(self):
        """Инициализация элементов управления."""
        
        # Заголовок
        self.header = ft.Text("Настройки", size=28, weight=ft.FontWeight.BOLD)
        
        # Секция "Внешний вид"
        self.theme_dropdown = ft.Dropdown(
            label="Тема оформления",
            options=[
                ft.dropdown.Option("light", "Светлая"),
                ft.dropdown.Option("dark", "Тёмная"),
                # ft.dropdown.Option("system", "Системная"), # Flet может не поддерживать system корректно везде
            ],
            width=300,
            on_change=self._on_theme_changed
        )
        
        appearance_section = ft.Column(
            controls=[
                ft.Text("Внешний вид", size=20, weight=ft.FontWeight.W_500),
                self.theme_dropdown,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START
        )
        
        # Секция "База данных"
        self.db_path_field = ft.TextField(
            label="Путь к базе данных",
            read_only=True,
            width=500,
            expand=True
        )
        
        # FilePicker для выбора БД (пока не реализован полностью, так как это сложнее)
        # self.file_picker = ft.FilePicker(on_result=self._on_db_file_picked)
        # self.page.overlay.append(self.file_picker)
        
        database_section = ft.Column(
            controls=[
                ft.Text("База данных", size=20, weight=ft.FontWeight.W_500),
                ft.Row(
                    controls=[
                        self.db_path_field,
                        # ft.IconButton(icon=ft.icons.FOLDER_OPEN, on_click=lambda _: self.file_picker.pick_files(allowed_extensions=["db"]))
                    ]
                ),
                ft.Text("Текущий путь к файлу базы данных (изменение пока недоступно в UI)", size=12, color=ft.Colors.GREY_700),
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START
        )
        
        # Секция "Форматы"
        self.date_format_dropdown = ft.Dropdown(
            label="Формат даты",
            options=[
                ft.dropdown.Option("%d.%m.%Y", "DD.MM.YYYY (31.12.2023)"),
                ft.dropdown.Option("%Y-%m-%d", "YYYY-MM-DD (2023-12-31)"),
                ft.dropdown.Option("%m/%d/%Y", "MM/DD/YYYY (12/31/2023)"),
            ],
            width=300,
            on_change=self._on_date_format_changed
        )
        
        formats_section = ft.Column(
            controls=[
                ft.Text("Форматы", size=20, weight=ft.FontWeight.W_500),
                self.date_format_dropdown,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.START
        )
        
        # Кнопка сохранения (хотя изменения применяются сразу, кнопка для явного подтверждения сохранения в файл)
        self.save_button = ft.ElevatedButton(
            text="Сохранить настройки",
            icon=ft.Icons.SAVE,
            on_click=self._save_settings
        )

        # Сборка всех элементов
        self.controls = [
            self.header,
            ft.Divider(),
            appearance_section,
            ft.Divider(),
            database_section,
            ft.Divider(),
            formats_section,
            ft.Divider(),
            ft.Row([self.save_button], alignment=ft.MainAxisAlignment.END)
        ]

    def _update_controls_values(self):
        """Установка значений элементов управления из настроек."""
        self.theme_dropdown.value = settings.theme_mode
        self.db_path_field.value = settings.db_path
        self.date_format_dropdown.value = settings.date_format

    def _on_theme_changed(self, e):
        """Обработчик изменения темы."""
        settings.theme_mode = self.theme_dropdown.value
        self.page.theme_mode = ft.ThemeMode.LIGHT if settings.theme_mode == "light" else ft.ThemeMode.DARK
        self.page.update()
        logger.info(f"Тема изменена на: {settings.theme_mode}")

    def _on_date_format_changed(self, e):
        """Обработчик изменения формата даты."""
        settings.date_format = self.date_format_dropdown.value
        logger.info(f"Формат даты изменен на: {settings.date_format}")

    @safe_handler()
    def _save_settings(self, e):
        """Сохранение настроек в файл."""
        settings.save()
        
        # Показываем уведомление об успехе
        snack_bar = ft.SnackBar(
            content=ft.Text("Настройки успешно сохранены"),
            bgcolor=ft.Colors.GREEN
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()
