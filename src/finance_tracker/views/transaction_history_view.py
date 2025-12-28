"""
История операций - основной экран для просмотра всех транзакций.

Отображает все фактические транзакции с:
- Фильтрацией по дате, категории, типу
- Поиском по описанию
- Группировкой и сортировкой
- Статистикой доходов/расходов
- Графиком по категориям
"""

import datetime
from typing import List, Optional, Dict
from decimal import Decimal
from collections import defaultdict

import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.database import get_db
from finance_tracker.models import TransactionDB, TransactionType
from finance_tracker.services.transaction_service import get_by_date_range
from finance_tracker.services.category_service import get_all_categories
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class TransactionHistoryView(ft.Container):
    """
    Экран истории операций.

    Показывает все фактические транзакции с расширенными возможностями:
    - Фильтрация по периоду, категории, типу операции
    - Поиск по описанию
    - Группировка по датам/категориям/месяцам
    - Сортировка по дате, сумме, категории
    - Статистика: доходы, расходы, баланс
    - График распределения по категориям
    """

    def __init__(self):
        super().__init__()
        self.alignment = ft.alignment.top_left
        self.expand = True

        # Начальные параметры фильтрации
        self.start_date = datetime.date.today().replace(day=1)  # Первый день текущего месяца
        self.end_date = self._get_last_day_of_month(datetime.date.today())
        self.selected_category_id: Optional[str] = None
        self.selected_type: Optional[TransactionType] = None
        self.search_query: str = ""
        self.group_by: str = "date"  # date, category, month
        self.sort_by: str = "date_desc"  # date_asc, date_desc, amount_asc, amount_desc

        # Данные
        self.transactions: List[TransactionDB] = []
        self.filtered_transactions: List[TransactionDB] = []

        # UI Components - фильтры
        self.date_range_text = ft.Text(
            f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}",
            size=14
        )

        self.category_dropdown = ft.Dropdown(
            label="Категория",
            width=200,
            options=[],
            on_change=self._on_filter_change,
            dense=True
        )

        self.type_dropdown = ft.Dropdown(
            label="Тип операции",
            width=180,
            options=[
                ft.dropdown.Option("all", "Все"),
                ft.dropdown.Option("income", "Доходы"),
                ft.dropdown.Option("expense", "Расходы")
            ],
            value="all",
            on_change=self._on_filter_change,
            dense=True
        )

        self.search_field = ft.TextField(
            label="Поиск по описанию",
            width=250,
            on_change=self._on_search_change,
            dense=True,
            prefix_icon=ft.Icons.SEARCH
        )

        self.group_dropdown = ft.Dropdown(
            label="Группировка",
            width=150,
            options=[
                ft.dropdown.Option("date", "По дате"),
                ft.dropdown.Option("category", "По категории"),
                ft.dropdown.Option("month", "По месяцам")
            ],
            value="date",
            on_change=self._on_group_change,
            dense=True
        )

        self.sort_dropdown = ft.Dropdown(
            label="Сортировка",
            width=180,
            options=[
                ft.dropdown.Option("date_desc", "Дата ↓"),
                ft.dropdown.Option("date_asc", "Дата ↑"),
                ft.dropdown.Option("amount_desc", "Сумма ↓"),
                ft.dropdown.Option("amount_asc", "Сумма ↑")
            ],
            value="date_desc",
            on_change=self._on_sort_change,
            dense=True
        )

        # UI Components - статистика
        self.stat_income = self._build_stat_card("Доходы", "0.00 ₽", ft.Icons.ARROW_UPWARD, ft.Colors.GREEN)
        self.stat_expense = self._build_stat_card("Расходы", "0.00 ₽", ft.Icons.ARROW_DOWNWARD, ft.Colors.RED)
        self.stat_balance = self._build_stat_card("Баланс", "0.00 ₽", ft.Icons.ACCOUNT_BALANCE_WALLET, ft.Colors.BLUE)
        self.stat_count = self._build_stat_card("Операций", "0", ft.Icons.RECEIPT_LONG, ft.Colors.ORANGE)

        # UI Components - данные
        self.transactions_container = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
            expand=True
        )

        # График по категориям
        self.chart_container = ft.Container(
            content=ft.Text("График загружается..."),
            visible=False,
            border=ft.border.all(1, "outlineVariant"),
            border_radius=10,
            padding=20,
            height=300
        )

        # Кнопки действий
        self.show_chart_button = ft.ElevatedButton(
            "Показать график",
            icon=ft.Icons.PIE_CHART,
            on_click=self._toggle_chart
        )

        # Layout
        self.content = ft.Column(
            controls=[
                # Заголовок
                ft.Row(
                    controls=[
                        ft.Text("История операций", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        self.show_chart_button
                    ]
                ),

                # Фильтры - верхняя строка
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Выбрать период",
                            icon=ft.Icons.DATE_RANGE,
                            on_click=self._open_date_picker
                        ),
                        self.date_range_text,
                        self.category_dropdown,
                        self.type_dropdown,
                        self.search_field,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=10,
                    wrap=True
                ),

                # Фильтры - нижняя строка
                ft.Row(
                    controls=[
                        self.group_dropdown,
                        self.sort_dropdown,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            on_click=self._refresh_data,
                            tooltip="Обновить"
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLEAR,
                            on_click=self._reset_filters,
                            tooltip="Сбросить фильтры"
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=10
                ),

                # Статистика
                ft.Row(
                    controls=[
                        self.stat_income,
                        self.stat_expense,
                        self.stat_balance,
                        self.stat_count
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15
                ),

                # График (скрыт по умолчанию)
                self.chart_container,

                # Список транзакций
                ft.Container(
                    content=self.transactions_container,
                    border=ft.border.all(1, "outlineVariant"),
                    border_radius=10,
                    padding=15,
                    expand=True
                )
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            alignment=ft.MainAxisAlignment.START
        )

    def did_mount(self):
        """Вызывается после монтирования на страницу."""
        self._load_categories()
        self._load_data()

    def _get_last_day_of_month(self, date_obj: datetime.date) -> datetime.date:
        """Возвращает последний день месяца для переданной даты."""
        next_month = date_obj.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

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
                if self.page:
                    self.update()
        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")

    def _load_data(self):
        """Загружает транзакции за выбранный период."""
        try:
            with get_db() as session:
                self.transactions = get_by_date_range(session, self.start_date, self.end_date)
                self._apply_filters()
                self._update_ui()
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            if self.page:
                self.page.open(ft.SnackBar(
                    content=ft.Text(f"Ошибка загрузки данных: {e}"),
                    bgcolor=ft.Colors.ERROR
                ))

    def _apply_filters(self):
        """Применяет фильтры к транзакциям."""
        self.filtered_transactions = self.transactions.copy()

        # Фильтр по категории
        if self.selected_category_id:
            self.filtered_transactions = [
                t for t in self.filtered_transactions
                if t.category_id == self.selected_category_id
            ]

        # Фильтр по типу
        if self.selected_type:
            self.filtered_transactions = [
                t for t in self.filtered_transactions
                if t.type == self.selected_type
            ]

        # Поиск по описанию
        if self.search_query:
            query_lower = self.search_query.lower()
            self.filtered_transactions = [
                t for t in self.filtered_transactions
                if t.description and query_lower in t.description.lower()
            ]

        # Сортировка
        self._apply_sorting()

    def _apply_sorting(self):
        """Применяет сортировку к отфильтрованным транзакциям."""
        reverse = self.sort_by.endswith("_desc")

        if self.sort_by.startswith("date"):
            self.filtered_transactions.sort(
                key=lambda t: t.transaction_date,
                reverse=reverse
            )
        elif self.sort_by.startswith("amount"):
            self.filtered_transactions.sort(
                key=lambda t: t.amount,
                reverse=reverse
            )

    def _update_ui(self):
        """Обновляет UI на основе отфильтрованных данных."""
        if not self.page:
            return

        # Обновляем статистику
        self._update_statistics()

        # Обновляем список транзакций
        self._update_transactions_list()

        # Обновляем график если он видим
        if self.chart_container.visible:
            self._update_chart()

        self.update()

    def _update_statistics(self):
        """Обновляет карточки статистики."""
        total_income = sum(
            (t.amount for t in self.filtered_transactions if t.type == TransactionType.INCOME),
            Decimal('0.0')
        )
        total_expense = sum(
            (t.amount for t in self.filtered_transactions if t.type == TransactionType.EXPENSE),
            Decimal('0.0')
        )
        balance = total_income - total_expense
        count = len(self.filtered_transactions)

        self._update_stat_card(self.stat_income, f"{total_income:,.2f} ₽".replace(",", " "))
        self._update_stat_card(self.stat_expense, f"{total_expense:,.2f} ₽".replace(",", " "))

        # Баланс с цветовой индикацией
        balance_text = f"{balance:+,.2f} ₽".replace(",", " ")
        self._update_stat_card(self.stat_balance, balance_text)
        # Меняем цвет иконки в зависимости от баланса
        try:
            icon = self.stat_balance.content.controls[0]
            if balance > 0:
                icon.color = ft.Colors.GREEN
            elif balance < 0:
                icon.color = ft.Colors.RED
            else:
                icon.color = ft.Colors.BLUE
        except Exception:
            pass

        self._update_stat_card(self.stat_count, str(count))

    def _update_transactions_list(self):
        """Обновляет список транзакций с группировкой."""
        self.transactions_container.controls.clear()

        if not self.filtered_transactions:
            self.transactions_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Нет транзакций за выбранный период",
                        size=16,
                        color="outline"
                    ),
                    alignment=ft.alignment.center,
                    padding=40
                )
            )
            return

        # Группировка
        if self.group_by == "date":
            self._render_by_date()
        elif self.group_by == "category":
            self._render_by_category()
        elif self.group_by == "month":
            self._render_by_month()

    def _render_by_date(self):
        """Отображение транзакций с группировкой по дате."""
        # Группируем по датам
        by_date: Dict[datetime.date, List[TransactionDB]] = defaultdict(list)
        for transaction in self.filtered_transactions:
            by_date[transaction.transaction_date].append(transaction)

        # Сортируем даты
        sorted_dates = sorted(by_date.keys(), reverse=self.sort_by.startswith("date_desc"))

        for date_obj in sorted_dates:
            transactions = by_date[date_obj]
            day_income = sum((t.amount for t in transactions if t.type == TransactionType.INCOME), Decimal('0.0'))
            day_expense = sum((t.amount for t in transactions if t.type == TransactionType.EXPENSE), Decimal('0.0'))
            day_balance = day_income - day_expense

            # Заголовок дня
            self.transactions_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                date_obj.strftime("%d.%m.%Y (%A)"),
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Container(expand=True),
                            ft.Text(f"Доходы: {day_income:,.2f} ₽".replace(",", " "), color=ft.Colors.GREEN, size=12),
                            ft.Text(f"Расходы: {day_expense:,.2f} ₽".replace(",", " "), color=ft.Colors.RED, size=12),
                            ft.Text(f"Баланс: {day_balance:+,.2f} ₽".replace(",", " "), size=12, weight=ft.FontWeight.BOLD)
                        ]
                    ),
                    bgcolor=ft.Colors.SURFACE_VARIANT,
                    padding=10,
                    border_radius=5
                )
            )

            # Транзакции дня
            for transaction in transactions:
                self.transactions_container.controls.append(
                    self._build_transaction_card(transaction)
                )

    def _render_by_category(self):
        """Отображение транзакций с группировкой по категории."""
        # Группируем по категориям
        by_category: Dict[str, List[TransactionDB]] = defaultdict(list)
        for transaction in self.filtered_transactions:
            category_name = transaction.category.name if transaction.category else "Без категории"
            by_category[category_name].append(transaction)

        # Сортируем категории
        sorted_categories = sorted(by_category.keys())

        for category_name in sorted_categories:
            transactions = by_category[category_name]
            cat_total = sum((t.amount for t in transactions), Decimal('0.0'))

            # Заголовок категории
            self.transactions_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(category_name, size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.Text(f"Всего: {cat_total:,.2f} ₽".replace(",", " "), size=12),
                            ft.Text(f"Операций: {len(transactions)}", size=12)
                        ]
                    ),
                    bgcolor=ft.Colors.SURFACE_VARIANT,
                    padding=10,
                    border_radius=5
                )
            )

            # Транзакции категории
            for transaction in transactions:
                self.transactions_container.controls.append(
                    self._build_transaction_card(transaction)
                )

    def _render_by_month(self):
        """Отображение транзакций с группировкой по месяцам."""
        # Группируем по месяцам
        by_month: Dict[tuple, List[TransactionDB]] = defaultdict(list)
        for transaction in self.filtered_transactions:
            month_key = (transaction.transaction_date.year, transaction.transaction_date.month)
            by_month[month_key].append(transaction)

        # Сортируем месяцы
        sorted_months = sorted(by_month.keys(), reverse=True)

        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }

        for year, month in sorted_months:
            transactions = by_month[(year, month)]
            month_income = sum((t.amount for t in transactions if t.type == TransactionType.INCOME), Decimal('0.0'))
            month_expense = sum((t.amount for t in transactions if t.type == TransactionType.EXPENSE), Decimal('0.0'))
            month_balance = month_income - month_expense

            # Заголовок месяца
            self.transactions_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"{month_names[month]} {year}",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Container(expand=True),
                            ft.Text(f"Доходы: {month_income:,.2f} ₽".replace(",", " "), color=ft.Colors.GREEN, size=12),
                            ft.Text(f"Расходы: {month_expense:,.2f} ₽".replace(",", " "), color=ft.Colors.RED, size=12),
                            ft.Text(f"Баланс: {month_balance:+,.2f} ₽".replace(",", " "), size=12, weight=ft.FontWeight.BOLD)
                        ]
                    ),
                    bgcolor=ft.Colors.SURFACE_VARIANT,
                    padding=10,
                    border_radius=5
                )
            )

            # Транзакции месяца
            for transaction in transactions:
                self.transactions_container.controls.append(
                    self._build_transaction_card(transaction)
                )

    def _build_transaction_card(self, transaction: TransactionDB) -> ft.Container:
        """Создаёт карточку транзакции."""
        category_name = transaction.category.name if transaction.category else "Без категории"

        # Цвет в зависимости от типа
        amount_color = ft.Colors.GREEN if transaction.type == TransactionType.INCOME else ft.Colors.RED
        amount_prefix = "+" if transaction.type == TransactionType.INCOME else "-"

        return ft.Container(
            content=ft.Row(
                controls=[
                    # Дата
                    ft.Container(
                        content=ft.Text(
                            transaction.transaction_date.strftime("%d.%m.%Y"),
                            size=12
                        ),
                        width=80
                    ),
                    # Категория
                    ft.Container(
                        content=ft.Text(category_name, size=12),
                        width=150
                    ),
                    # Описание
                    ft.Container(
                        content=ft.Text(
                            transaction.description or "",
                            size=12,
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        expand=True
                    ),
                    # Сумма
                    ft.Text(
                        f"{amount_prefix}{transaction.amount:,.2f} ₽".replace(",", " "),
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=amount_color
                    ),
                    # Кнопка деталей
                    ft.IconButton(
                        icon=ft.Icons.INFO_OUTLINE,
                        icon_size=16,
                        tooltip="Детали",
                        on_click=lambda _, t=transaction: self._show_transaction_details(t)
                    )
                ],
                alignment=ft.MainAxisAlignment.START
            ),
            padding=10,
            border=ft.border.only(bottom=ft.BorderSide(1, "outlineVariant")),
            on_hover=lambda e: self._on_card_hover(e)
        )

    def _on_card_hover(self, e):
        """Подсветка карточки при наведении."""
        e.control.bgcolor = ft.Colors.SURFACE_VARIANT if e.data == "true" else None
        e.control.update()

    def _show_transaction_details(self, transaction: TransactionDB):
        """Показывает детали транзакции в диалоге."""
        category_name = transaction.category.name if transaction.category else "Без категории"
        type_text = "Доход" if transaction.type == TransactionType.INCOME else "Расход"

        dialog = ft.AlertDialog(
            title=ft.Text("Детали транзакции"),
            content=ft.Column(
                controls=[
                    ft.Row([ft.Text("Дата:", weight=ft.FontWeight.BOLD), ft.Text(transaction.transaction_date.strftime("%d.%m.%Y"))]),
                    ft.Row([ft.Text("Тип:", weight=ft.FontWeight.BOLD), ft.Text(type_text)]),
                    ft.Row([ft.Text("Категория:", weight=ft.FontWeight.BOLD), ft.Text(category_name)]),
                    ft.Row([ft.Text("Сумма:", weight=ft.FontWeight.BOLD), ft.Text(f"{transaction.amount:,.2f} ₽".replace(",", " "))]),
                    ft.Divider(),
                    ft.Text("Описание:", weight=ft.FontWeight.BOLD),
                    ft.Text(transaction.description or "Нет описания", size=12),
                    ft.Divider(),
                    ft.Text(f"ID: {transaction.id}", size=10, color="outline"),
                    ft.Text(f"Создано: {transaction.created_at.strftime('%d.%m.%Y %H:%M')}", size=10, color="outline")
                ],
                tight=True,
                spacing=10
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda _: self.page.close(dialog))
            ]
        )

        self.page.open(dialog)

    def _update_chart(self):
        """Обновляет график распределения по категориям."""
        # Группируем по категориям
        by_category: Dict[str, Decimal] = defaultdict(lambda: Decimal('0.0'))
        for transaction in self.filtered_transactions:
            category_name = transaction.category.name if transaction.category else "Без категории"
            by_category[category_name] += transaction.amount

        if not by_category:
            self.chart_container.content = ft.Text("Нет данных для графика")
            return

        # Создаём простую визуализацию (гистограмму)
        total = sum(by_category.values())
        bars = []

        for category, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            percentage = (amount / total * 100) if total > 0 else 0
            bars.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(category, size=12, width=120, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Container(
                                        content=ft.Container(
                                            bgcolor=ft.Colors.PRIMARY,
                                            height=20,
                                            border_radius=3
                                        ),
                                        width=int(percentage * 3),  # Масштаб
                                        height=20
                                    ),
                                    ft.Text(f"{amount:,.2f} ₽ ({percentage:.1f}%)".replace(",", " "), size=12)
                                ],
                                alignment=ft.MainAxisAlignment.START,
                                spacing=10
                            )
                        ]
                    ),
                    padding=5
                )
            )

        self.chart_container.content = ft.Column(
            controls=[
                ft.Text("Распределение по категориям", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Column(controls=bars, scroll=ft.ScrollMode.AUTO, spacing=5)
            ],
            spacing=10
        )

    def _build_stat_card(self, title: str, value: str, icon: str, color: str) -> ft.Container:
        """Создаёт карточку статистики."""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, color=color, size=30),
                    ft.Column(
                        controls=[
                            ft.Text(title, size=12, color="outline"),
                            ft.Text(value, size=18, weight=ft.FontWeight.BOLD)
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

    # Event Handlers

    def _on_filter_change(self, e):
        """Обработчик изменения фильтров."""
        # Обновляем выбранную категорию
        cat_val = self.category_dropdown.value
        self.selected_category_id = cat_val if cat_val and cat_val != "all" else None

        # Обновляем выбранный тип
        type_val = self.type_dropdown.value
        if type_val == "income":
            self.selected_type = TransactionType.INCOME
        elif type_val == "expense":
            self.selected_type = TransactionType.EXPENSE
        else:
            self.selected_type = None

        self._apply_filters()
        self._update_ui()

    def _on_search_change(self, e):
        """Обработчик изменения поискового запроса."""
        self.search_query = self.search_field.value or ""
        self._apply_filters()
        self._update_ui()

    def _on_group_change(self, e):
        """Обработчик изменения группировки."""
        self.group_by = self.group_dropdown.value
        self._update_ui()

    def _on_sort_change(self, e):
        """Обработчик изменения сортировки."""
        self.sort_by = self.sort_dropdown.value
        self._apply_filters()
        self._update_ui()

    def _refresh_data(self, e):
        """Обновление данных."""
        self._load_data()

    def _reset_filters(self, e):
        """Сброс всех фильтров."""
        self.start_date = datetime.date.today().replace(day=1)
        self.end_date = self._get_last_day_of_month(datetime.date.today())
        self.selected_category_id = None
        self.selected_type = None
        self.search_query = ""
        self.group_by = "date"
        self.sort_by = "date_desc"

        # Обновляем UI контролы
        self.date_range_text.value = f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}"
        self.category_dropdown.value = "all"
        self.type_dropdown.value = "all"
        self.search_field.value = ""
        self.group_dropdown.value = "date"
        self.sort_dropdown.value = "date_desc"

        self._load_data()

    def _open_date_picker(self, e):
        """Открывает диалог выбора периода."""
        # Поля для ввода дат
        start_field = ft.TextField(
            label="Дата начала",
            value=self.start_date.strftime("%Y-%m-%d"),
            hint_text="YYYY-MM-DD",
            width=150
        )

        end_field = ft.TextField(
            label="Дата окончания",
            value=self.end_date.strftime("%Y-%m-%d"),
            hint_text="YYYY-MM-DD",
            width=150
        )

        def apply_dates(_):
            try:
                new_start = datetime.datetime.strptime(start_field.value, "%Y-%m-%d").date()
                new_end = datetime.datetime.strptime(end_field.value, "%Y-%m-%d").date()

                if new_start > new_end:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Дата начала не может быть позже даты окончания"),
                        bgcolor=ft.Colors.ERROR
                    ))
                    return

                self.start_date = new_start
                self.end_date = new_end
                self.date_range_text.value = f"{self.start_date.strftime('%d.%m.%Y')} - {self.end_date.strftime('%d.%m.%Y')}"
                self.page.close(dialog)
                self._load_data()

            except ValueError:
                self.page.open(ft.SnackBar(
                    content=ft.Text("Некорректный формат даты (ожидается YYYY-MM-DD)"),
                    bgcolor=ft.Colors.ERROR
                ))

        def cancel(_):
            self.page.close(dialog)

        # Быстрые пресеты
        def set_current_month(_):
            today = datetime.date.today()
            start_field.value = today.replace(day=1).strftime("%Y-%m-%d")
            end_field.value = self._get_last_day_of_month(today).strftime("%Y-%m-%d")
            start_field.update()
            end_field.update()

        def set_last_month(_):
            today = datetime.date.today()
            first_of_month = today.replace(day=1)
            last_month = first_of_month - datetime.timedelta(days=1)
            start_field.value = last_month.replace(day=1).strftime("%Y-%m-%d")
            end_field.value = last_month.strftime("%Y-%m-%d")
            start_field.update()
            end_field.update()

        def set_current_year(_):
            today = datetime.date.today()
            start_field.value = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_field.value = today.replace(month=12, day=31).strftime("%Y-%m-%d")
            start_field.update()
            end_field.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Выбор периода"),
            content=ft.Column(
                controls=[
                    ft.Row([start_field, end_field]),
                    ft.Divider(),
                    ft.Text("Быстрый выбор:", size=12, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton("Текущий месяц", on_click=set_current_month, compact=True),
                        ft.ElevatedButton("Прошлый месяц", on_click=set_last_month, compact=True),
                        ft.ElevatedButton("Текущий год", on_click=set_current_year, compact=True)
                    ], wrap=True)
                ],
                tight=True,
                spacing=10,
                width=400
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel),
                ft.ElevatedButton("Применить", on_click=apply_dates)
            ]
        )

        self.page.open(dialog)

    def _toggle_chart(self, e):
        """Переключает видимость графика."""
        self.chart_container.visible = not self.chart_container.visible
        self.show_chart_button.text = "Скрыть график" if self.chart_container.visible else "Показать график"

        if self.chart_container.visible:
            self._update_chart()

        self.update()
