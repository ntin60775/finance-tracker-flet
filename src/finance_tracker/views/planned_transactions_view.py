"""
Экран управления плановыми транзакциями.

Предоставляет UI для:
- Отображения списка всех плановых транзакций с фильтрацией
- Создания и редактирования плановых транзакций
- Просмотра деталей плановой транзакции с историей вхождений
- Деактивации и удаления плановых транзакций
"""

import flet as ft
from datetime import date
from typing import Optional

from finance_tracker.models import (
    TransactionType,
    PlannedTransactionDB,
    PlannedOccurrenceDB,
    OccurrenceStatus,
    CategoryDB,
    RecurrenceType,
)
from finance_tracker.database import get_db_session
from finance_tracker.services.planned_transaction_service import (
    get_all_planned_transactions,
    deactivate_planned_transaction,
    delete_planned_transaction,
    create_planned_transaction,
)
from finance_tracker.services.obligations_service import (
    create_obligation,
    get_obligations_metrics_for_month,
    link_transaction_to_obligation,
    update_obligation_target,
)
from finance_tracker.components.planned_transaction_modal import PlannedTransactionModal
from finance_tracker.utils.logger import get_logger
from finance_tracker.utils.exceptions import BusinessLogicError, ValidationError

logger = get_logger(__name__)


class PlannedTransactionsView(ft.Column):
    """
    Экран управления плановыми транзакциями.

    Позволяет пользователю:
    - Просматривать список всех плановых транзакций
    - Фильтровать по статусу (активные/неактивные) и типу (доходы/расходы)
    - Создавать новые плановые транзакции
    - Просматривать детали и историю вхождений
    - Редактировать, деактивировать и удалять плановые транзакции

    Согласно Requirement 5.6:
    - Отображает список плановых транзакций с возможностью редактирования и удаления
    """

    def __init__(self, page: ft.Page):
        """
        Инициализация экрана плановых транзакций.

        Args:
            page: Страница Flet для отображения UI
        """
        super().__init__(expand=True, alignment=ft.MainAxisAlignment.START)
        self._page = page
        self.status_filter: Optional[bool] = True  # True = активные, None = все
        self.type_filter: Optional[TransactionType] = None
        self.selected_planned_tx: Optional[PlannedTransactionDB] = None
        self.obligations_month: date = date.today().replace(day=1)

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # UI Components
        self._build_ui()

    def _build_ui(self):
        """Построение UI компонентов."""
        # Заголовок и кнопка создания
        self.header = ft.Row(
            controls=[
                ft.Text("Плановые транзакции", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.ON_PRIMARY,
                    tooltip="Добавить плановую транзакцию",
                    on_click=self.open_create_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.obligations_list = ft.Column(spacing=8)

        self.obligations_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Обязательства", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        self.obligations_month.strftime("%m.%Y"),
                                        size=12,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ADD,
                                        tooltip="Добавить обязательство",
                                        on_click=self.open_create_obligation_dialog,
                                    ),
                                ],
                                spacing=5,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.obligations_list,
                ],
                spacing=10,
            ),
            bgcolor="surfaceVariant",
            padding=10,
            border_radius=10,
        )

        # Фильтры по статусу
        self.status_tabs = ft.Tabs(
            content=ft.TabBar(
                tabs=[
                    ft.Tab(label="Активные"),
                    ft.Tab(label="Неактивные"),
                    ft.Tab(label="Все"),
                ]
            ),
            length=3,
            selected_index=0,
            animation_duration=300,
            on_change=self.on_status_filter_change,
        )

        # Фильтры по типу
        self.type_tabs = ft.Tabs(
            content=ft.TabBar(
                tabs=[
                    ft.Tab(label="Все"),
                    ft.Tab(label="Расходы", icon=ft.Icon(ft.Icons.ARROW_CIRCLE_DOWN)),
                    ft.Tab(label="Доходы", icon=ft.Icon(ft.Icons.ARROW_CIRCLE_UP)),
                ]
            ),
            length=3,
            selected_index=0,
            animation_duration=300,
            on_change=self.on_type_filter_change,
        )

        # Список плановых транзакций
        self.transactions_list = ft.ListView(expand=True, spacing=5, padding=10)

        # Панель деталей (изначально скрыта)
        self.details_panel = ft.Container(
            visible=False,
            expand=True,
            bgcolor=ft.Colors.SURFACE,
            padding=15,
            border_radius=10,
        )

        # Layout с разделением на список и детали
        self.main_content = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self.status_tabs,
                            self.type_tabs,
                            ft.Divider(height=1),
                            self.transactions_list,
                        ],
                        spacing=10,
                        expand=True,
                    ),
                    expand=2,
                ),
                self.details_panel,
            ],
            expand=True,
            spacing=10,
        )

        self.controls = [
            self.header,
            self.obligations_container,
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

    def on_status_filter_change(self, e):
        """Обработка смены фильтра по статусу."""
        index = self.status_tabs.selected_index
        if index == 0:
            self.status_filter = True  # Только активные
        elif index == 1:
            self.status_filter = False  # Только неактивные
        elif index == 2:
            self.status_filter = None  # Все

        self.refresh_data()

    def on_type_filter_change(self, e):
        """Обработка смены фильтра по типу."""
        index = self.type_tabs.selected_index
        if index == 0:
            self.type_filter = None
        elif index == 1:
            self.type_filter = TransactionType.EXPENSE
        elif index == 2:
            self.type_filter = TransactionType.INCOME

        self.refresh_data()

    def refresh_data(self):
        """Загрузка и отображение списка плановых транзакций."""
        try:
            # Получаем список с учётом фильтров
            if self.status_filter is None:
                # Все транзакции
                transactions = get_all_planned_transactions(
                    self.session, active_only=False, transaction_type=self.type_filter
                )
            else:
                # Фильтруем по статусу
                all_txs = get_all_planned_transactions(
                    self.session, active_only=False, transaction_type=self.type_filter
                )
                transactions = [tx for tx in all_txs if tx.is_active == self.status_filter]

            transactions = [tx for tx in transactions if not getattr(tx, "is_obligation", False)]

            self.transactions_list.controls.clear()
            self._refresh_obligations_block()

            if not transactions:
                self.transactions_list.controls.append(
                    ft.Container(
                        content=ft.Text("Плановые транзакции не найдены", color="outline"),
                        alignment=ft.Alignment.CENTER,
                        padding=20,
                    )
                )
            else:
                for tx in transactions:
                    self.transactions_list.controls.append(self._create_transaction_tile(tx))

            self.update()

        except Exception as e:
            logger.error(f"Ошибка загрузки плановых транзакций: {e}")
            if self._page:
                snack = ft.SnackBar(content=ft.Text(f"Ошибка загрузки плановых транзакций: {e}"))
                self._page.open(snack)

    def _refresh_obligations_block(self) -> None:
        self.obligations_list.controls.clear()

        try:
            metrics_list = get_obligations_metrics_for_month(self.session, self.obligations_month)
        except Exception as ex:
            self.obligations_list.controls.append(
                ft.Text(f"Ошибка загрузки обязательств: {ex}", color=ft.Colors.ERROR)
            )
            return

        if not metrics_list:
            self.obligations_list.controls.append(
                ft.Text("Нет обязательств на этот месяц", color="outline")
            )
            return

        for metrics in metrics_list:
            obligation = (
                self.session.query(PlannedTransactionDB).filter_by(id=metrics.obligation_id).first()
            )
            if not obligation:
                continue

            category = self.session.query(CategoryDB).filter_by(id=obligation.category_id).first()
            category_name = category.name if category else "Неизвестная категория"

            progress = 0.0
            if metrics.target and metrics.target > 0:
                progress = float(metrics.paid / metrics.target)
                progress = max(0.0, min(1.0, progress))

            title = obligation.description or category_name

            self.obligations_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Изменить цель",
                                        on_click=lambda _, o=obligation, m=metrics: (
                                            self.open_edit_obligation_dialog(o, m)
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                f"цель: {metrics.target:.2f} ₽ • оплачено: {metrics.paid:.2f} ₽ • остаток: {metrics.remaining:.2f} ₽",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.ProgressBar(value=progress),
                        ],
                        spacing=6,
                    ),
                    bgcolor=ft.Colors.SURFACE,
                    padding=10,
                    border_radius=8,
                )
            )

    def open_create_obligation_dialog(self, e=None):
        modal = PlannedTransactionModal(
            session=self.session,
            on_save=self._on_planned_transaction_saved,
            on_save_obligation=self._on_obligation_saved,
        )
        modal.open(self._page, mode="obligation", target_month=self.obligations_month)

    def open_edit_obligation_dialog(self, obligation: PlannedTransactionDB, metrics):
        modal = PlannedTransactionModal(
            session=self.session,
            on_save=self._on_planned_transaction_saved,
            on_save_obligation=self._on_obligation_saved,
        )
        modal.open(
            self._page,
            mode="obligation",
            obligation_id=obligation.id,
            target_month=metrics.month,
            target_amount=metrics.target,
            category_id=obligation.category_id,
            tx_type=obligation.type,
            description=obligation.description,
        )

    def _on_obligation_saved(self, payload: dict) -> None:
        try:
            obligation_id = payload.get("obligation_id")
            if obligation_id:
                update_obligation_target(
                    self.session,
                    obligation_id=obligation_id,
                    target_amount=payload["target_amount"],
                )
                message = "Цель обязательства обновлена"
            else:
                create_obligation(
                    self.session,
                    category_id=payload["category_id"],
                    target_amount=payload["target_amount"],
                    target_month=payload["target_month"],
                    t_type=payload["type"],
                    description=payload.get("description"),
                )
                message = "Обязательство создано"

            if self._page:
                self._page.open(ft.SnackBar(content=ft.Text(message)))

            self.refresh_data()
        except (ValidationError, BusinessLogicError) as ex:
            if self._page:
                self._page.open(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                )
        except Exception as ex:
            logger.error("Ошибка сохранения обязательства: %s", ex)
            if self._page:
                self._page.open(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                )

    def _create_transaction_tile(self, tx: PlannedTransactionDB) -> ft.ListTile:
        """
        Создание элемента списка для плановой транзакции.

        Args:
            tx: Плановая транзакция из БД

        Returns:
            ListTile с информацией о плановой транзакции
        """
        # Иконка и цвет по типу
        icon = (
            ft.Icons.ARROW_CIRCLE_DOWN
            if tx.type == TransactionType.EXPENSE
            else ft.Icons.ARROW_CIRCLE_UP
        )
        color = ft.Colors.RED if tx.type == TransactionType.EXPENSE else ft.Colors.GREEN

        # Получаем название категории
        category = self.session.query(CategoryDB).filter_by(id=tx.category_id).first()
        category_name = category.name if category else "Неизвестная категория"

        # Получаем информацию о правиле повторения
        recurrence_info = "Однократная"
        if tx.recurrence_rule:
            rule = tx.recurrence_rule
            recurrence_info = self._format_recurrence_info(rule.recurrence_type, rule.interval)

        # Статус
        status_text = "Активна" if tx.is_active else "Неактивна"
        status_color = ft.Colors.GREEN_700 if tx.is_active else ft.Colors.GREY_700

        # Даты
        date_range = f"{tx.start_date.strftime('%d.%m.%Y')}"
        if tx.end_date:
            date_range += f" - {tx.end_date.strftime('%d.%m.%Y')}"

        return ft.ListTile(
            leading=ft.Icon(icon, color=color, size=32),
            title=ft.Row(
                controls=[
                    ft.Text(category_name, weight=ft.FontWeight.BOLD, size=16),
                    ft.Container(
                        content=ft.Text(
                            status_text, size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD
                        ),
                        bgcolor=status_color,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        border_radius=5,
                    ),
                ],
                spacing=10,
            ),
            subtitle=ft.Column(
                controls=[
                    ft.Text(f"{tx.amount:.2f} ₽ • {recurrence_info}", size=14),
                    ft.Text(date_range, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(tx.description or "", size=12, italic=True)
                    if tx.description
                    else ft.Container(),
                ],
                spacing=2,
            ),
            bgcolor="surfaceVariant",
            on_click=lambda _, ptx=tx: self.show_details(ptx),
        )

    def _format_recurrence_info(self, recurrence_type: RecurrenceType, interval: int) -> str:
        """
        Форматирование информации о правиле повторения.

        Args:
            recurrence_type: Тип повторения
            interval: Интервал повторения

        Returns:
            Строка с описанием правила повторения
        """
        type_names = {
            RecurrenceType.DAILY: "день",
            RecurrenceType.WEEKLY: "неделя",
            RecurrenceType.MONTHLY: "месяц",
            RecurrenceType.YEARLY: "год",
            RecurrenceType.CUSTOM: "период",
        }

        type_name = type_names.get(recurrence_type, "период")

        if interval == 1:
            if recurrence_type == RecurrenceType.DAILY:
                return "Ежедневно"
            elif recurrence_type == RecurrenceType.WEEKLY:
                return "Еженедельно"
            elif recurrence_type == RecurrenceType.MONTHLY:
                return "Ежемесячно"
            elif recurrence_type == RecurrenceType.YEARLY:
                return "Ежегодно"

        return f"Каждые {interval} {type_name}"

    def show_details(self, tx: PlannedTransactionDB):
        """
        Отображение панели с деталями плановой транзакции.

        Args:
            tx: Плановая транзакция для отображения
        """
        self.selected_planned_tx = tx

        # Получаем категорию
        category = self.session.query(CategoryDB).filter_by(id=tx.category_id).first()
        category_name = category.name if category else "Неизвестная категория"

        # Получаем вхождения
        occurrences = (
            self.session.query(PlannedOccurrenceDB)
            .filter_by(planned_transaction_id=tx.id)
            .order_by(PlannedOccurrenceDB.occurrence_date.desc())
            .all()
        )

        # Статистика по вхождениям
        total = len(occurrences)
        executed = len([o for o in occurrences if o.status == OccurrenceStatus.EXECUTED])
        skipped = len([o for o in occurrences if o.status == OccurrenceStatus.SKIPPED])
        pending = len([o for o in occurrences if o.status == OccurrenceStatus.PENDING])

        # Информация о правиле повторения
        recurrence_info = self._build_recurrence_info(tx)

        # Построение панели деталей
        self.details_panel.content = ft.Column(
            controls=[
                # Заголовок
                ft.Row(
                    controls=[
                        ft.Text("Детали", size=20, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip="Закрыть",
                            on_click=lambda _: self.hide_details(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                # Основная информация
                ft.Text(category_name, size=18, weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"{tx.amount:.2f} ₽",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED if tx.type == TransactionType.EXPENSE else ft.Colors.GREEN,
                ),
                ft.Text(tx.description or "Без описания", size=14, italic=True),
                ft.Divider(),
                # Правило повторения
                ft.Text("Правило повторения", size=14, weight=ft.FontWeight.BOLD),
                recurrence_info,
                ft.Divider(),
                # Статистика вхождений
                ft.Text("Статистика вхождений", size=14, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        self._create_stat_card("Всего", total, ft.Colors.BLUE_700),
                        self._create_stat_card("Исполнено", executed, ft.Colors.GREEN_700),
                        self._create_stat_card("Пропущено", skipped, ft.Colors.ORANGE_700),
                        self._create_stat_card("Ожидается", pending, ft.Colors.GREY_700),
                    ],
                    spacing=5,
                ),
                ft.Divider(),
                # История вхождений
                ft.Text("История вхождений", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.ListView(
                        controls=[
                            self._create_occurrence_item(occ, tx) for occ in occurrences[:10]
                        ],
                        spacing=5,
                    ),
                    height=200,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=5,
                    padding=5,
                ),
                ft.Divider(),
                # Кнопки действий
                ft.Row(
                    controls=[
                        ft.Button(
                            "Редактировать",
                            icon=ft.Icons.EDIT,
                            on_click=lambda _: self.edit_planned_transaction(tx),
                        ),
                        ft.Button(
                            "Деактивировать" if tx.is_active else "Активировать",
                            icon=ft.Icons.PAUSE_CIRCLE if tx.is_active else ft.Icons.PLAY_CIRCLE,
                            on_click=lambda _: self.toggle_active(tx),
                        ),
                        ft.Button(
                            "Удалить",
                            icon=ft.Icons.DELETE,
                            color=ft.Colors.ERROR,
                            on_click=lambda _: self.confirm_delete(tx),
                        ),
                    ],
                    spacing=10,
                    wrap=True,
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.details_panel.visible = True
        self.details_panel.expand = 1
        self.update()

    def _build_recurrence_info(self, tx: PlannedTransactionDB) -> ft.Column:
        """
        Построение информации о правиле повторения.

        Args:
            tx: Плановая транзакция

        Returns:
            Column с информацией о правиле повторения
        """
        if not tx.recurrence_rule:
            return ft.Column(
                controls=[
                    ft.Text("Однократная транзакция", size=12),
                    ft.Text(f"Дата: {tx.start_date.strftime('%d.%m.%Y')}", size=12),
                ],
                spacing=2,
            )

        rule = tx.recurrence_rule

        # Тип повторения
        recurrence_text = self._format_recurrence_info(rule.recurrence_type, rule.interval)

        # Условие окончания
        end_condition = "Бессрочно"
        if rule.end_date:
            end_condition = f"До {rule.end_date.strftime('%d.%m.%Y')}"
        elif rule.occurrences_count:
            end_condition = f"После {rule.occurrences_count} повторений"

        return ft.Column(
            controls=[
                ft.Text(f"Тип: {recurrence_text}", size=12),
                ft.Text(f"Начало: {tx.start_date.strftime('%d.%m.%Y')}", size=12),
                ft.Text(f"Окончание: {end_condition}", size=12),
                ft.Text(f"Только рабочие дни: {'Да' if rule.only_workdays else 'Нет'}", size=12)
                if rule.only_workdays
                else ft.Container(),
            ],
            spacing=2,
        )

    def _create_stat_card(self, label: str, value: int, color: str) -> ft.Container:
        """
        Создание карточки статистики.

        Args:
            label: Название статистики
            value: Значение
            color: Цвет

        Returns:
            Container с карточкой статистики
        """
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(label, size=11),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            bgcolor=ft.Colors.SURFACE,
            padding=10,
            border_radius=8,
            expand=True,
        )

    def _create_occurrence_item(
        self, occ: PlannedOccurrenceDB, tx: PlannedTransactionDB
    ) -> ft.Container:
        """
        Создание элемента истории вхождений.

        Args:
            occ: Вхождение плановой транзакции

        Returns:
            Container с информацией о вхождении
        """
        # Статус
        status_map = {
            OccurrenceStatus.PENDING: ("Ожидается", ft.Colors.GREY_700),
            OccurrenceStatus.EXECUTED: ("Исполнено", ft.Colors.GREEN_700),
            OccurrenceStatus.SKIPPED: ("Пропущено", ft.Colors.ORANGE_700),
        }
        status_text, status_color = status_map.get(occ.status, ("Неизвестно", ft.Colors.GREY_700))

        # Дата
        date_str = occ.occurrence_date.strftime("%d.%m.%Y")

        # Сумма
        amount_str = f"{occ.amount:.2f} ₽"
        if occ.status == OccurrenceStatus.EXECUTED and occ.executed_amount:
            amount_str = f"{occ.executed_amount:.2f} ₽"
            if abs(occ.executed_amount - occ.amount) > 0.01:
                deviation = occ.executed_amount - occ.amount
                amount_str += f" ({deviation:+.2f})"

        controls = [
            ft.Text(date_str, size=12, expand=True),
            ft.Text(amount_str, size=12, expand=True),
            ft.Container(
                content=ft.Text(
                    status_text,
                    size=10,
                    color=ft.Colors.WHITE,
                ),
                bgcolor=status_color,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                border_radius=4,
            ),
        ]

        if occ.status == OccurrenceStatus.EXECUTED and occ.actual_transaction_id:
            controls.append(
                ft.IconButton(
                    icon=ft.Icons.LINK,
                    tooltip="Привязать транзакцию к обязательству",
                    on_click=lambda _, tid=occ.actual_transaction_id, cid=tx.category_id, m=occ.occurrence_date: (
                        self.open_link_to_obligation_dialog(
                            transaction_id=tid,
                            category_id=cid,
                            month=m,
                        )
                    ),
                )
            )

        return ft.Container(
            content=ft.Row(controls=controls, spacing=10),
            padding=5,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=5,
        )

    def open_link_to_obligation_dialog(
        self, *, transaction_id: str, category_id: str, month: date
    ) -> None:
        normalized_month = date(month.year, month.month, 1)
        try:
            metrics_list = get_obligations_metrics_for_month(
                self.session,
                normalized_month,
                category_id=category_id,
            )
        except Exception as ex:
            if self._page:
                self._page.open(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                )
            return

        if not metrics_list:
            if self._page:
                self._page.open(
                    ft.SnackBar(content=ft.Text("Нет обязательств для выбранного месяца"))
                )
            return

        obligation_dropdown = ft.Dropdown(
            label="Обязательство",
            options=[],
        )
        for m in metrics_list:
            obligation = (
                self.session.query(PlannedTransactionDB).filter_by(id=m.obligation_id).first()
            )
            if not obligation:
                continue
            title = obligation.description or "Обязательство"
            obligation_dropdown.options.append(
                ft.dropdown.Option(
                    key=m.obligation_id,
                    text=f"{title} (остаток {m.remaining:.2f} ₽)",
                )
            )

        def link_action(e):
            if not obligation_dropdown.value:
                obligation_dropdown.error_text = "Выберите обязательство"
                self._page.update()
                return

            try:
                link_transaction_to_obligation(
                    self.session,
                    transaction_id=transaction_id,
                    obligation_id=obligation_dropdown.value,
                )
                self._page.close(dlg)
                self._page.open(
                    ft.SnackBar(content=ft.Text("Транзакция привязана к обязательству"))
                )
                self.refresh_data()
            except BusinessLogicError as ex:
                message = str(ex)
                if "превышает остаток" in message:
                    self._page.open(
                        ft.SnackBar(
                            content=ft.Text(
                                "Сумма транзакции больше остатка по обязательству — разбейте транзакцию вручную"
                            ),
                            bgcolor=ft.Colors.ERROR,
                        )
                    )
                else:
                    self._page.open(
                        ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                    )
            except ValidationError as ex:
                self._page.open(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                )
            except Exception as ex:
                logger.error("Ошибка привязки транзакции к обязательству: %s", ex)
                self._page.open(
                    ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"), bgcolor=ft.Colors.ERROR)
                )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Привязка к обязательству"),
            content=ft.Column(
                controls=[
                    ft.Text(
                        normalized_month.strftime("%m.%Y"),
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    obligation_dropdown,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self._page.close(dlg)),
                ft.Button("Привязать", on_click=link_action),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._page.open(dlg)

    def hide_details(self):
        """Скрытие панели деталей."""
        self.details_panel.visible = False
        self.details_panel.expand = 0
        self.selected_planned_tx = None
        self.update()

    def open_create_dialog(self, e):
        """Открытие диалога создания плановой транзакции."""
        logger.info("Открытие диалога создания плановой транзакции")

        modal = PlannedTransactionModal(
            session=self.session, on_save=self._on_planned_transaction_saved
        )
        modal.open(self._page)

    def _on_planned_transaction_saved(self, planned_tx_data):
        """
        Callback при сохранении плановой транзакции из модального окна.

        Args:
            planned_tx_data: Данные плановой транзакции (PlannedTransactionCreate)
        """
        try:
            create_planned_transaction(self.session, planned_tx_data)

            logger.info("Плановая транзакция успешно создана")

            if self._page:
                snack = ft.SnackBar(content=ft.Text("Плановая транзакция создана"))
                self._page.open(snack)

            self.refresh_data()

        except Exception as ex:
            logger.error(f"Ошибка создания плановой транзакции: {ex}")
            if self._page:
                snack = ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"))
                self._page.open(snack)

    def edit_planned_transaction(self, tx: PlannedTransactionDB):
        """
        Редактирование плановой транзакции.

        Args:
            tx: Плановая транзакция для редактирования
        """
        logger.info(f"Редактирование плановой транзакции ID {tx.id}")
        # TODO: Открыть PlannedTransactionModal в режиме редактирования
        if self._page:
            snack = ft.SnackBar(
                content=ft.Text("Редактирование плановых транзакций будет реализовано")
            )
            self._page.open(snack)

    def toggle_active(self, tx: PlannedTransactionDB):
        """
        Переключение статуса активности плановой транзакции.

        Args:
            tx: Плановая транзакция
        """
        try:
            if tx.is_active:
                deactivate_planned_transaction(self.session, tx.id)
                action = "деактивирована"
            else:
                # Активация (просто меняем флаг)
                tx.is_active = True
                self.session.commit()
                action = "активирована"

            logger.info(f"Плановая транзакция ID {tx.id} {action}")

            if self._page:
                snack = ft.SnackBar(content=ft.Text(f"Плановая транзакция {action}"))
                self._page.open(snack)

            self.hide_details()
            self.refresh_data()

        except Exception as e:
            logger.error(f"Ошибка изменения статуса плановой транзакции: {e}")
            if self._page:
                snack = ft.SnackBar(content=ft.Text(f"Ошибка: {e}"))
                self._page.open(snack)

    def confirm_delete(self, tx: PlannedTransactionDB):
        """
        Диалог подтверждения удаления плановой транзакции.

        Args:
            tx: Плановая транзакция для удаления
        """

        def delete_action(e):
            try:
                # Спрашиваем, удалять ли связанные транзакции
                delete_planned_transaction(self.session, tx.id, delete_actual_transactions=False)

                self._page.close(dlg)

                logger.info(f"Плановая транзакция ID {tx.id} удалена")

                if self._page:
                    snack = ft.SnackBar(content=ft.Text("Плановая транзакция удалена"))
                    self._page.open(snack)

                self.hide_details()
                self.refresh_data()

            except Exception as ex:
                logger.error(f"Ошибка удаления плановой транзакции: {ex}")
                self._page.close(dlg)

                if self._page:
                    snack = ft.SnackBar(content=ft.Text(f"Ошибка: {ex}"))
                    self._page.open(snack)

        # Получаем категорию для отображения
        category = self.session.query(CategoryDB).filter_by(id=tx.category_id).first()
        category_name = category.name if category else "транзакцию"

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение удаления"),
            content=ft.Text(
                f"Вы уверены, что хотите удалить плановую транзакцию '{category_name}'?\n\n"
                "Фактические транзакции, созданные из вхождений, НЕ будут удалены."
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._page.close(dlg)),
                ft.Button("Удалить", color=ft.Colors.ERROR, on_click=delete_action),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._page.open(dlg)
