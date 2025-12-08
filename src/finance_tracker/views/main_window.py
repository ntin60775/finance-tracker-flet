import flet as ft
from finance_tracker.utils.logger import get_logger
from finance_tracker.config import settings
from finance_tracker.database import get_db_session
from finance_tracker.services.transaction_service import get_total_balance

from finance_tracker.views.home_view import HomeView
from finance_tracker.views.categories_view import CategoriesView
from finance_tracker.views.plan_fact_view import PlanFactView
from finance_tracker.views.pending_payments_view import PendingPaymentsView
from finance_tracker.views.planned_transactions_view import PlannedTransactionsView
from finance_tracker.views.lenders_view import LendersView
from finance_tracker.views.loans_view import LoansView
from finance_tracker.views.settings_view import SettingsView

logger = get_logger(__name__)

class MainWindow(ft.Row):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.expand = True
        self.setup_page()
        self.init_ui()

        logger.info("Инициализация главного окна")

    def setup_page(self):
        """Настройка основных параметров страницы"""
        self.page.title = "Finance Tracker"
        self.page.theme_mode = ft.ThemeMode.LIGHT if settings.theme_mode == "light" else ft.ThemeMode.DARK
        self.page.padding = 0
        
        # Настройка иконки окна
        try:
            import os
            import sys
            # Определяем путь к иконке (работает и в dev, и в собранном .exe)
            if getattr(sys, 'frozen', False):
                # Если приложение собрано PyInstaller
                base_path = sys._MEIPASS
            else:
                # Если запускается из исходников
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            icon_path = os.path.join(base_path, 'assets', 'icon.ico')
            if os.path.exists(icon_path):
                self.page.window.icon = icon_path
                logger.info(f"Иконка окна установлена: {icon_path}")
            else:
                logger.warning(f"Иконка не найдена по пути: {icon_path}")
        except Exception as e:
            logger.error(f"Ошибка при установке иконки окна: {e}")
        
        # Разворачиваем окно на весь экран
        self.page.window.maximized = True
        
        # Восстановление размера и положения окна (для случая, если пользователь выйдет из полноэкранного режима)
        self.page.window.width = settings.window_width
        self.page.window.height = settings.window_height
        if settings.window_top is not None:
            self.page.window.top = settings.window_top
        if settings.window_left is not None:
            self.page.window.left = settings.window_left

    # Removed did_mount as it is not automatically called for Row subclass

    def update_balance(self):
        """Обновляет отображение текущего баланса"""
        try:
            with get_db_session() as session:
                balance = get_total_balance(session)
                if hasattr(self, 'balance_text') and self.balance_text:
                    self.balance_text.value = f"Баланс: {balance:,.2f} ₽".replace(",", " ")
                    # Обновляем только если элемент уже добавлен на страницу
                    if self.page and hasattr(self.balance_text, 'page') and self.balance_text.page:
                        self.balance_text.update()
        except Exception as e:
            logger.error(f"Ошибка при обновлении баланса: {e}")

    def init_ui(self):
        # Боковая панель навигации
        self.rail = ft.NavigationRail(
            selected_index=settings.last_selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.CALENDAR_MONTH_OUTLINED,
                    selected_icon=ft.Icons.CALENDAR_MONTH,
                    label="Календарь",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.EVENT_REPEAT_OUTLINED,
                    selected_icon=ft.Icons.EVENT_REPEAT,
                    label="Плановые",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CREDIT_CARD_OUTLINED,
                    selected_icon=ft.Icons.CREDIT_CARD,
                    label="Кредиты",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PENDING_ACTIONS_OUTLINED,
                    selected_icon=ft.Icons.PENDING_ACTIONS,
                    label="Отложенные",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SCHEDULE_OUTLINED,
                    selected_icon=ft.Icons.SCHEDULE,
                    label="План",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_BALANCE,
                    label="Займодатели",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CATEGORY_OUTLINED,
                    selected_icon=ft.Icons.CATEGORY,
                    label="Категории",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Настройки",
                ),
            ],
            on_change=lambda e: self.navigate(e.control.selected_index),
        )

        # Текст баланса (будет обновляться в 4.4)
        self.balance_text = ft.Text(
            "Баланс: 0.00 ₽", 
            size=20, 
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_SURFACE_VARIANT
        )
        
        # AppBar
        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET),
            leading_width=40,
            title=ft.Text("Finance Tracker"),
            center_title=False,
            bgcolor=ft.Colors.BLUE_GREY_100,
            actions=[
                ft.Container(
                    content=self.balance_text,
                    padding=ft.padding.only(right=20)
                )
            ]
        )

        # Область контента
        self.content_area = ft.Container(
            content=self.get_view(settings.last_selected_index),
            expand=True,
            alignment=ft.alignment.center,
            padding=20
        )

        # Компоновка: Навигация слева, контент справа
        self.controls = [
            self.rail,
            ft.VerticalDivider(width=1),
            self.content_area,
        ]

    def save_state(self):
        """Сохраняет текущее состояние приложения"""
        settings.last_selected_index = self.rail.selected_index
        settings.window_width = self.page.window.width
        settings.window_height = self.page.window.height
        settings.window_top = self.page.window.top
        settings.window_left = self.page.window.left
        settings.save()

    def navigate(self, index: int):
        """Переключение между разделами"""
        self.rail.selected_index = index
        self.content_area.content = self.get_view(index)
        self.content_area.update()
        self.save_state()
        # При навигации также обновляем баланс
        self.update_balance()
        logger.info(f"Переход в раздел с индексом: {index}")

    def get_view(self, index: int) -> ft.Control:
        """Возвращает содержимое для выбранного раздела"""
        if index == 0:
            return HomeView(self.page)
        if index == 1:
            return PlannedTransactionsView(self.page)
        if index == 2:
            return LoansView(self.page)
        if index == 3:
            return PendingPaymentsView(self.page)
        if index == 4:
            return PlanFactView()
        if index == 5:
            return LendersView(self.page)
        if index == 6:
            return CategoriesView(self.page)
        if index == 7:
            return SettingsView(self.page)

        return ft.Text("Раздел не найден")