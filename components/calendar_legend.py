import flet as ft


class CalendarLegend(ft.Container):
    """
    Виджет легенды для календаря.
    
    Показывает, что означают цветовые индикаторы.
    Имеет два режима:
    - Краткий: только основные индикаторы (в строку)
    - Полный: модальное окно со всеми описаниями
    """

    def __init__(self):
        super().__init__()
        self.dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Легенда календаря"),
            content=self._build_full_legend_content(),
            actions=[
                ft.TextButton("Закрыть", on_click=self._close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.padding = 5
        self.content = ft.Row(
            controls=[
                self._build_legend_item(ft.Colors.GREEN, "Доход"),
                self._build_legend_item(ft.Colors.RED, "Расход"),
                # Будущие индикаторы
                # self._build_legend_item(ft.Colors.BLUE, "План"),
                # self._build_legend_item(ft.Colors.ORANGE, "Разрыв"),
                ft.TextButton("Подробнее...", on_click=self._open_dlg, height=30),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )

    def _build_legend_item(self, color: str, text: str, icon: str = None):
        """Helper для создания элемента легенды."""
        content_list = []
        
        if icon:
             content_list.append(ft.Icon(icon, color=color, size=16))
        else:
             content_list.append(ft.Container(width=10, height=10, border_radius=5, bgcolor=color))
             
        content_list.append(ft.Text(text, size=12))
        
        return ft.Row(
            controls=content_list,
            spacing=5,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def _build_full_legend_content(self):
        """Создание контента для полного модального окна."""
        return ft.Column(
            controls=[
                ft.Text("Индикаторы транзакций (точки):", weight=ft.FontWeight.BOLD),
                self._build_legend_item(ft.Colors.GREEN, "Доход (зеленая точка)"),
                self._build_legend_item(ft.Colors.RED, "Расход (красная точка)"),
                
                ft.Divider(),
                
                ft.Text("Фон дня:", weight=ft.FontWeight.BOLD),
                self._build_legend_item(ft.Colors.AMBER_100, "Кассовый разрыв (отрицательный прогноз)", icon=ft.Icons.WARNING),
                
                ft.Divider(),
                
                ft.Text("Символы:", weight=ft.FontWeight.BOLD),
                self._build_legend_item(ft.Colors.ON_SURFACE, "◆ Плановая транзакция", icon=ft.Icons.DIAMOND_OUTLINED),
                self._build_legend_item(ft.Colors.ON_SURFACE, "📋 Отложенный платеж", icon=ft.Icons.PASTE),
                self._build_legend_item(ft.Colors.ON_SURFACE, "💳 Кредитный платеж", icon=ft.Icons.CREDIT_CARD),
            ],
            height=300,
            width=400,
            scroll=ft.ScrollMode.AUTO,
        )

    def _open_dlg(self, e):
        """Открытие модального окна."""
        # Получаем page из event control (кнопка, которая была нажата)
        page = e.control.page if e.control else self.page
        if not page:
            return
        page.dialog = self.dlg_modal
        self.dlg_modal.open = True
        page.update()

    def _close_dlg(self, e):
        """Закрытие модального окна."""
        # Получаем page из event control (кнопка "Закрыть")
        page = e.control.page if e.control else self.page
        if not page:
            return
        self.dlg_modal.open = False
        page.update()