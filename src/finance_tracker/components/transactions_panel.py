import datetime
from typing import List, Callable, Optional

import flet as ft

from finance_tracker.models.models import TransactionDB, PlannedOccurrence, PendingPaymentDB, LoanPaymentDB
from finance_tracker.models.enums import TransactionType, OccurrenceStatus, PendingPaymentPriority, PaymentStatus
from finance_tracker.services.balance_forecast_service import calculate_forecast_balance
from finance_tracker.services.pending_payment_service import get_pending_payments_by_date
from finance_tracker.services.loan_payment_service import get_payments_by_date
from finance_tracker.database import get_db
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class TransactionsPanel(ft.Container):
    """
    Панель для отображения списка транзакций за выбранный день.
    
    Включает:
    - Список фактических транзакций
    - Список плановых вхождений на этот день
    - Сводку за день (доходы, расходы, баланс)
    - Прогноз баланса на конец дня
    - Кнопку добавления новой транзакции
    """

    def __init__(
        self,
        date_obj: datetime.date,
        transactions: List[TransactionDB],
        on_add_transaction: Callable[[], None],
        planned_occurrences: Optional[List[PlannedOccurrence]] = None,
        on_execute_occurrence: Optional[Callable[[PlannedOccurrence], None]] = None,
        on_skip_occurrence: Optional[Callable[[PlannedOccurrence], None]] = None,
        on_execute_pending_payment: Optional[Callable[[PendingPaymentDB], None]] = None,
        on_execute_loan_payment: Optional[Callable[[LoanPaymentDB], None]] = None,
    ):
        """
        Инициализация панели транзакций.

        Args:
            date_obj: Выбранная дата.
            transactions: Список транзакций за эту дату.
            on_add_transaction: Callback для открытия модального окна создания транзакции.
            planned_occurrences: Список плановых вхождений на эту дату.
            on_execute_occurrence: Callback для исполнения планового вхождения.
            on_skip_occurrence: Callback для пропуска планового вхождения.
            on_execute_pending_payment: Callback для исполнения отложенного платежа.
            on_execute_loan_payment: Callback для исполнения платежа по кредиту.
        """
        super().__init__()
        self.date = date_obj
        self.transactions = transactions
        self.planned_occurrences = planned_occurrences or []
        self.pending_payments: List[PendingPaymentDB] = []
        self.loan_payments: List[LoanPaymentDB] = []
        self.on_add_transaction = on_add_transaction
        self.on_execute_occurrence = on_execute_occurrence
        self.on_skip_occurrence = on_skip_occurrence
        self.on_execute_pending_payment = on_execute_pending_payment
        self.on_execute_loan_payment = on_execute_loan_payment
        self.forecast_balance: Optional[float] = None
        
        # UI Components to be updated
        self.transactions_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.planned_occurrences_list = ft.ListView(spacing=10, padding=10) # Без expand, чтобы не занимало все место
        self.pending_payments_list = ft.ListView(spacing=10, padding=10) # Список отложенных платежей
        self.loan_payments_list = ft.ListView(spacing=10, padding=10) # Список платежей по кредитам
        self.summary_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND)
        self.forecast_container = ft.Container() # Контейнер для прогноза
        self.header_text = ft.Text(value="", size=18, weight=ft.FontWeight.BOLD)
        
        # Layout
        self.padding = 15
        self.border = ft.border.all(1, "outlineVariant")
        self.border_radius = 10
        self.bgcolor = "surface"
        self.expand = True
        
        self.content = ft.Column(
            controls=[
                self._build_header(),
                ft.Divider(),
                self.forecast_container, # Добавляем блок прогноза
                self._build_summary(),
                ft.Divider(),
                ft.Text("Плановые операции", weight=ft.FontWeight.BOLD, visible=False, key="planned_title"),
                self.planned_occurrences_list,
                ft.Text("Отложенные платежи", weight=ft.FontWeight.BOLD, visible=False, key="pending_title"),
                self.pending_payments_list,
                ft.Text("Платежи по кредитам", weight=ft.FontWeight.BOLD, visible=False, key="loan_payments_title"),
                self.loan_payments_list,
                ft.Text("Транзакции", weight=ft.FontWeight.BOLD),
                self.transactions_list,
            ],
            spacing=5,
            scroll=ft.ScrollMode.AUTO
        )

    def did_mount(self):
        """Вызывается после монтирования."""
        self._load_pending_payments()
        self._load_loan_payments()
        self._update_forecast()
        self._update_view()

    def set_data(
        self,
        date_obj: datetime.date,
        transactions: List[TransactionDB],
        planned_occurrences: Optional[List[PlannedOccurrence]] = None
    ):
        """
        Обновление данных панели.
        
        Args:
            date_obj: Новая дата.
            transactions: Новый список транзакций.
            planned_occurrences: Новый список плановых вхождений.
        """
        self.date = date_obj
        self.transactions = transactions
        self.planned_occurrences = planned_occurrences or []
        self._load_pending_payments()
        self._load_loan_payments()
        self._update_forecast()
        self._update_view()

    def _load_pending_payments(self):
        """Загружает отложенные платежи для выбранной даты."""
        try:
            with get_db() as session:
                self.pending_payments = get_pending_payments_by_date(session, self.date)
        except Exception as e:
            logger.error(f"Ошибка при загрузке отложенных платежей: {e}")
            self.pending_payments = []

    def _load_loan_payments(self):
        """Загружает платежи по кредитам для выбранной даты."""
        try:
            with get_db() as session:
                self.loan_payments = get_payments_by_date(session, self.date)
        except Exception as e:
            logger.error(f"Ошибка при загрузке платежей по кредитам: {e}")
            self.loan_payments = []

    def _update_forecast(self):
        """Обновляет прогнозируемый баланс на выбранную дату."""
        try:
            with get_db() as session:
                # Рассчитываем прогноз на выбранную дату
                self.forecast_balance = calculate_forecast_balance(session, self.date)
        except Exception as e:
            logger.error(f"Ошибка при расчёте прогноза: {e}")
            self.forecast_balance = None

    def _build_header(self):
        """Создание заголовка с датой и кнопкой добавления."""
        return ft.Row(
            controls=[
                self.header_text,
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    on_click=self._safe_add_transaction,
                    tooltip="Добавить транзакцию",
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.ON_PRIMARY,
                    disabled=self.on_add_transaction is None,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _build_summary(self):
        """Создание строки с итогами дня."""
        return self.summary_row

    def _safe_add_transaction(self, e):
        """
        Безопасный вызов callback для добавления транзакции.
        
        Args:
            e: Event от Flet (не используется).
        """
        try:
            if self.on_add_transaction is not None:
                logger.debug("Вызов callback для добавления транзакции")
                self.on_add_transaction()
            else:
                logger.warning("Callback для добавления транзакции не установлен")
                # Показываем пользователю информацию о том, что функция недоступна
                if hasattr(self, 'page') and self.page:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Функция добавления транзакции недоступна"),
                        bgcolor=ft.Colors.ORANGE
                    ))
        except Exception as ex:
            logger.error(f"Ошибка при вызове callback добавления транзакции: {ex}", exc_info=True)
            # Показываем пользователю сообщение об ошибке, если есть доступ к page
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Ошибка при открытии формы добавления транзакции"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar с ошибкой: {snack_error}")

    def _update_view(self):
        """Обновление содержимого виджета."""
        if not self.page:
            return
            
        # 1. Обновляем заголовок
        self.header_text.value = self.date.strftime("%d.%m.%Y")

        # 2. Обновляем блок прогноза
        if self.forecast_balance is not None:
            is_cash_gap = self.forecast_balance < 0
            
            content_controls = [
                ft.Text("Прогноз баланса:", size=12, color="outline"),
                ft.Text(
                    f"{self.forecast_balance:,.2f} ₽",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.RED if is_cash_gap else ft.Colors.ON_SURFACE
                )
            ]
            
            if is_cash_gap:
                content_controls.append(
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED, size=16),
                            ft.Text("Внимание: Кассовый разрыв!", color=ft.Colors.RED, size=12, weight=ft.FontWeight.BOLD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=5
                    )
                )
            
            self.forecast_container.content = ft.Container(
                content=ft.Column(
                    controls=content_controls,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2
                ),
                padding=10,
                bgcolor=ft.Colors.RED_50 if is_cash_gap else None,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.RED) if is_cash_gap else None,
                alignment=ft.alignment.center
            )
            self.forecast_container.visible = True
        else:
            self.forecast_container.visible = False

        # 3. Считаем итоги дня (только фактические транзакции влияют на баланс дня)
        total_income = sum(t.amount for t in self.transactions if t.type == TransactionType.INCOME)
        total_expense = sum(t.amount for t in self.transactions if t.type == TransactionType.EXPENSE)
        balance = total_income - total_expense

        # 4. Обновляем UI итогов
        self.summary_row.controls = [
            self._build_summary_item("Доход", total_income, ft.Colors.GREEN),
            self._build_summary_item("Расход", total_expense, ft.Colors.RED),
            self._build_summary_item("Баланс", balance, ft.Colors.BLUE if balance >= 0 else ft.Colors.RED),
        ]
        
        # 5. Обновляем список плановых вхождений
        self.planned_occurrences_list.controls.clear()
        planned_title = next((c for c in self.content.controls if isinstance(c, ft.Text) and c.key == "planned_title"), None)
        
        if not self.planned_occurrences:
            self.planned_occurrences_list.visible = False
            if planned_title:
                planned_title.visible = False
        else:
            self.planned_occurrences_list.visible = True
            if planned_title:
                planned_title.visible = True
            
            for occ in self.planned_occurrences:
                 self.planned_occurrences_list.controls.append(self._build_occurrence_tile(occ))

        # 5.1. Обновляем список отложенных платежей
        self.pending_payments_list.controls.clear()
        pending_title = next((c for c in self.content.controls if isinstance(c, ft.Text) and c.key == "pending_title"), None)
        
        if not self.pending_payments:
            self.pending_payments_list.visible = False
            if pending_title:
                pending_title.visible = False
        else:
            self.pending_payments_list.visible = True
            if pending_title:
                pending_title.visible = True
            
            for payment in self.pending_payments:
                self.pending_payments_list.controls.append(self._build_pending_payment_tile(payment))

        # 5.2. Обновляем список платежей по кредитам
        self.loan_payments_list.controls.clear()
        loan_payments_title = next((c for c in self.content.controls if isinstance(c, ft.Text) and c.key == "loan_payments_title"), None)
        
        if not self.loan_payments:
            self.loan_payments_list.visible = False
            if loan_payments_title:
                loan_payments_title.visible = False
        else:
            self.loan_payments_list.visible = True
            if loan_payments_title:
                loan_payments_title.visible = True
            
            for payment in self.loan_payments:
                self.loan_payments_list.controls.append(self._build_loan_payment_tile(payment))

        # 6. Обновляем список транзакций
        self.transactions_list.controls.clear()
        
        if not self.transactions:
            self.transactions_list.controls.append(
                ft.Container(
                    content=ft.Text("Нет транзакций", color="outline"),
                    alignment=ft.alignment.center,
                    padding=20
                )
            )
        else:
            for t in self.transactions:
                # Пытаемся безопасно получить имя категории
                category_name = "Без категории"
                try:
                    if t.category:
                        category_name = t.category.name
                except Exception:
                     pass

                amount_color = ft.Colors.GREEN if t.type == TransactionType.INCOME else ft.Colors.RED
                amount_sign = "+" if t.type == TransactionType.INCOME else "-"
                
                self.transactions_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(
                            ft.Icons.ARROW_CIRCLE_UP if t.type == TransactionType.INCOME else ft.Icons.ARROW_CIRCLE_DOWN,
                            color=amount_color
                        ),
                        title=ft.Text(category_name, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(t.description) if t.description else None,
                        trailing=ft.Text(
                            f"{amount_sign}{t.amount:,.2f}",
                            color=amount_color,
                            weight=ft.FontWeight.BOLD,
                            size=16
                        ),
                        bgcolor="surfaceVariant",
                    )
                )
        
        self.update()

    def _build_occurrence_tile(self, occurrence: PlannedOccurrence) -> ft.ListTile:
        """Создание элемента списка для планового вхождения."""
        planned_tx = occurrence.planned_transaction
        try:
            category_name = planned_tx.category.name if planned_tx.category else "Без категории"
        except Exception as e:
            logger.warning(f"Could not resolve planned transaction details for occurrence {occurrence.id}: {e}")
            category_name = "Unknown"

        icon = ft.Icons.SCHEDULE
        
        trailing = None
        if occurrence.status == OccurrenceStatus.PENDING:
            trailing = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHECK,
                        icon_color=ft.Colors.GREEN,
                        tooltip="Исполнить",
                        on_click=lambda _, o=occurrence: self.on_execute_occurrence(o) if self.on_execute_occurrence else None
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=ft.Colors.RED,
                        tooltip="Пропустить",
                        on_click=lambda _, o=occurrence: self.on_skip_occurrence(o) if self.on_skip_occurrence else None
                    )
                ],
                spacing=0,
                main_axis_alignment=ft.MainAxisAlignment.END,
                width=100
            )
        else:
             status_text = "Исполнено" if occurrence.status == OccurrenceStatus.EXECUTED else "Пропущено"
             trailing = ft.Text(status_text, italic=True, size=12)

        return ft.ListTile(
            leading=ft.Icon(icon, color=ft.Colors.ORANGE),
            title=ft.Text(f"{category_name} (План)", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(f"{occurrence.amount:,.2f} ₽"),
            trailing=trailing,
            bgcolor=ft.Colors.ORANGE_50,
        )

    def _build_pending_payment_tile(self, payment: PendingPaymentDB) -> ft.ListTile:
        """Создание элемента списка для отложенного платежа."""
        try:
            category_name = payment.category.name if payment.category else "Без категории"
        except Exception as e:
            logger.warning(f"Не удалось получить категорию для платежа {payment.id}: {e}")
            category_name = "Без категории"

        # Определяем цвет и иконку по приоритету
        priority_colors = {
            PendingPaymentPriority.CRITICAL: ft.Colors.RED,
            PendingPaymentPriority.HIGH: ft.Colors.ORANGE,
            PendingPaymentPriority.MEDIUM: ft.Colors.BLUE,
            PendingPaymentPriority.LOW: ft.Colors.GREY,
        }
        
        priority_icons = {
            PendingPaymentPriority.CRITICAL: ft.Icons.PRIORITY_HIGH,
            PendingPaymentPriority.HIGH: ft.Icons.ARROW_UPWARD,
            PendingPaymentPriority.MEDIUM: ft.Icons.REMOVE,
            PendingPaymentPriority.LOW: ft.Icons.ARROW_DOWNWARD,
        }

        icon_color = priority_colors.get(payment.priority, ft.Colors.BLUE)
        icon = priority_icons.get(payment.priority, ft.Icons.PAYMENT)

        # Кнопка быстрого исполнения
        trailing = ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE,
            icon_color=ft.Colors.GREEN,
            tooltip="Исполнить платёж",
            on_click=lambda _, p=payment: self.on_execute_pending_payment(p) if self.on_execute_pending_payment else None
        )

        return ft.ListTile(
            leading=ft.Icon(icon, color=icon_color),
            title=ft.Text(f"{category_name} (Отложенный)", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(f"{payment.description} • {payment.amount:,.2f} ₽ • {payment.priority.value}"),
            trailing=trailing,
            bgcolor=ft.Colors.BLUE_50,
        )

    def _build_loan_payment_tile(self, payment: LoanPaymentDB) -> ft.ListTile:
        """Создание элемента списка для платежа по кредиту."""
        try:
            loan_name = payment.loan.name if payment.loan else "Неизвестный кредит"
        except Exception as e:
            logger.warning(f"Не удалось получить название кредита для платежа {payment.id}: {e}")
            loan_name = "Неизвестный кредит"

        # Определяем цвет и иконку по статусу
        status_colors = {
            PaymentStatus.PENDING: ft.Colors.BLUE,
            PaymentStatus.EXECUTED: ft.Colors.GREEN,
            PaymentStatus.EXECUTED_WITH_DELAY: ft.Colors.ORANGE,
            PaymentStatus.OVERDUE: ft.Colors.RED,
            PaymentStatus.CANCELLED: ft.Colors.GREY,
        }
        
        status_icons = {
            PaymentStatus.PENDING: ft.Icons.SCHEDULE,
            PaymentStatus.EXECUTED: ft.Icons.CHECK_CIRCLE,
            PaymentStatus.EXECUTED_WITH_DELAY: ft.Icons.WARNING,
            PaymentStatus.OVERDUE: ft.Icons.ERROR,
            PaymentStatus.CANCELLED: ft.Icons.CANCEL,
        }

        status_labels = {
            PaymentStatus.PENDING: "Ожидается",
            PaymentStatus.EXECUTED: "Выполнен",
            PaymentStatus.EXECUTED_WITH_DELAY: "Выполнен с просрочкой",
            PaymentStatus.OVERDUE: "Просрочен",
            PaymentStatus.CANCELLED: "Отменён",
        }

        icon_color = status_colors.get(payment.status, ft.Colors.BLUE)
        icon = status_icons.get(payment.status, ft.Icons.PAYMENT)
        status_label = status_labels.get(payment.status, payment.status.value)

        # Формируем подзаголовок с информацией о платеже
        subtitle_parts = [
            f"{payment.total_amount:,.2f} ₽",
            status_label
        ]
        
        # Добавляем информацию о просрочке, если есть
        if payment.overdue_days and payment.overdue_days > 0:
            subtitle_parts.append(f"Просрочка: {payment.overdue_days} дн.")

        subtitle = " • ".join(subtitle_parts)

        # Кнопка быстрого исполнения (только для PENDING и OVERDUE)
        trailing = None
        if payment.status in (PaymentStatus.PENDING, PaymentStatus.OVERDUE):
            trailing = ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE,
                icon_color=ft.Colors.GREEN,
                tooltip="Исполнить платёж",
                on_click=lambda _, p=payment: self.on_execute_loan_payment(p) if self.on_execute_loan_payment else None
            )
        else:
            # Для исполненных/отменённых платежей показываем только статус
            trailing = ft.Text(status_label, italic=True, size=12, color=icon_color)

        # Определяем цвет фона в зависимости от статуса
        bgcolor = None
        if payment.status == PaymentStatus.OVERDUE:
            bgcolor = ft.Colors.RED_50
        elif payment.status == PaymentStatus.PENDING:
            bgcolor = ft.Colors.BLUE_50
        elif payment.status == PaymentStatus.EXECUTED:
            bgcolor = ft.Colors.GREEN_50

        return ft.ListTile(
            leading=ft.Icon(icon, color=icon_color),
            title=ft.Text(f"{loan_name} (Кредит)", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitle),
            trailing=trailing,
            bgcolor=bgcolor,
        )

    def _build_summary_item(self, label: str, value: float, color: str):
        """Helper для создания элемента сводки."""
        return ft.Column(
            controls=[
                ft.Text(label, size=12, color="outline"),
                ft.Text(f"{value:,.2f}", size=16, weight=ft.FontWeight.BOLD, color=color),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
