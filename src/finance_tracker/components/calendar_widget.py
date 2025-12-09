import calendar
import datetime
from typing import Callable, List, Optional

import flet as ft

from finance_tracker.models.enums import TransactionType, PaymentStatus
from finance_tracker.models.models import Transaction, PlannedOccurrence, PendingPaymentDB, LoanPaymentDB
from finance_tracker.utils.logger import get_logger
from finance_tracker.services.balance_forecast_service import detect_cash_gaps
from finance_tracker.services.pending_payment_service import get_all_pending_payments
from finance_tracker.database import get_db

logger = get_logger(__name__)


class CalendarWidget(ft.Container):
    """
    Виджет календаря для отображения дней месяца и индикаторов транзакций.
    """

    def __init__(
        self,
        on_date_selected: Callable[[datetime.date], None],
        initial_date: Optional[datetime.date] = None,
    ):
        """
        Инициализация виджета календаря.

        Args:
            on_date_selected: Callback функция, вызываемая при выборе даты.
            initial_date: Начальная дата (по умолчанию сегодня).
        """
        super().__init__()
        self.on_date_selected = on_date_selected
        self.current_date = initial_date or datetime.date.today()
        # Устанавливаем selected_date на current_date, чтобы при старте что-то было выбрано
        self.selected_date = self.current_date
        self.calendar = calendar.Calendar(firstweekday=0)  # Понедельник - первый день
        self.transactions: List[Transaction] = []
        self.planned_occurrences: List[PlannedOccurrence] = []
        self.pending_payments: List[PendingPaymentDB] = []
        self.loan_payments: List[LoanPaymentDB] = []
        self.cash_gaps: List[datetime.date] = []
        
        # UI Components
        self.header_text = ft.Text(
            value="", 
            size=20, 
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER
        )
        self.days_grid = ft.Column(spacing=2)

        # Init Layout
        self.padding = 10
        self.border = ft.border.all(1, "outlineVariant")
        self.border_radius = 10
        self.bgcolor = "surface"
        
        self.content = ft.Column(
            controls=[
                self._build_header(),
                self._build_weekdays_header(),
                self.days_grid,
            ],
            spacing=10,
        )

    def did_mount(self):
        """Вызывается после монтирования контрола на страницу."""
        self._update_calendar()

    def set_transactions(
        self, 
        transactions: List[Transaction], 
        planned_occurrences: Optional[List[PlannedOccurrence]] = None
    ):
        """
        Обновление данных для отображения индикаторов.
        
        Args:
            transactions: Список транзакций за отображаемый месяц.
            planned_occurrences: Список плановых вхождений за отображаемый месяц.
        """
        self.transactions = transactions
        self.planned_occurrences = planned_occurrences or []
        
        # Обновляем кассовые разрывы для текущего месяца
        self._update_cash_gaps()
        
        # Обновляем отложенные платежи для текущего месяца
        self._update_pending_payments()
        
        # Обновляем платежи по кредитам для текущего месяца
        self._update_loan_payments()
        
        self._update_calendar()

    def _update_cash_gaps(self):
        """Обновляет список кассовых разрывов для отображаемого месяца."""
        try:
            # Определяем диапазон дат для текущего месяца
            # Находим первый и последний день месяца
            _, days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)
            start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
            end_date = datetime.date(self.current_date.year, self.current_date.month, days_in_month)
            
            # Используем сервис для обнаружения кассовых разрывов
            with get_db() as session:
                self.cash_gaps = detect_cash_gaps(session, start_date, end_date)
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении кассовых разрывов: {e}")
            self.cash_gaps = []

    def _update_pending_payments(self):
        """Обновляет список отложенных платежей с плановой датой для отображаемого месяца."""
        try:
            # Загружаем все активные отложенные платежи с плановой датой
            with get_db() as session:
                all_payments = get_all_pending_payments(session, has_planned_date=True)
                
                # Фильтруем только платежи текущего месяца
                _, days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)
                start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
                end_date = datetime.date(self.current_date.year, self.current_date.month, days_in_month)
                
                self.pending_payments = [
                    p for p in all_payments 
                    if p.planned_date and start_date <= p.planned_date <= end_date
                ]
                
                logger.info(
                    f"Загружено {len(self.pending_payments)} отложенных платежей "
                    f"для месяца {self.current_date.month}/{self.current_date.year}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении отложенных платежей: {e}")
            self.pending_payments = []

    def _update_loan_payments(self):
        """Обновляет список платежей по кредитам для отображаемого месяца."""
        try:
            # Определяем диапазон дат для текущего месяца
            _, days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)
            start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
            end_date = datetime.date(self.current_date.year, self.current_date.month, days_in_month)
            
            # Загружаем все платежи по кредитам для текущего месяца
            with get_db() as session:
                self.loan_payments = session.query(LoanPaymentDB).filter(
                    LoanPaymentDB.scheduled_date >= start_date,
                    LoanPaymentDB.scheduled_date <= end_date
                ).all()
                
                logger.info(
                    f"Загружено {len(self.loan_payments)} платежей по кредитам "
                    f"для месяца {self.current_date.month}/{self.current_date.year}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении платежей по кредитам: {e}")
            self.loan_payments = []

    def _build_header(self):
        """Создание заголовка с навигацией."""
        return ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    on_click=self._prev_month,
                    tooltip="Предыдущий месяц"
                ),
                ft.Container(
                    content=self.header_text,
                    expand=True,
                    alignment=ft.alignment.center
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    on_click=self._next_month,
                    tooltip="Следующий месяц"
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _build_weekdays_header(self):
        """Создание заголовка дней недели."""
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(day, weight=ft.FontWeight.BOLD, color="secondary"),
                    expand=True,
                    alignment=ft.alignment.center,
                )
                for day in weekdays
            ],
        )

    def _prev_month(self, _):
        """Переход к предыдущему месяцу."""
        # Вычисляем первый день предыдущего месяца
        first_day = self.current_date.replace(day=1)
        prev_month = first_day - datetime.timedelta(days=1)
        self.current_date = prev_month.replace(day=1)
        
        # Обновляем кассовые разрывы, отложенные платежи и платежи по кредитам при смене месяца
        self._update_cash_gaps()
        self._update_pending_payments()
        self._update_loan_payments()
        self._update_calendar()

    def _next_month(self, _):
        """Переход к следующему месяцу."""
        # Вычисляем первый день следующего месяца
        days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
        next_month = self.current_date.replace(day=1) + datetime.timedelta(days=days_in_month)
        self.current_date = next_month
        
        # Обновляем кассовые разрывы, отложенные платежи и платежи по кредитам при смене месяца
        self._update_cash_gaps()
        self._update_pending_payments()
        self._update_loan_payments()
        self._update_calendar()

    def _on_day_click(self, date_obj: datetime.date):
        """Обработка клика по дню."""
        self.selected_date = date_obj
        self._update_calendar()  # Перерисовываем для обновления выделения
        if self.on_date_selected:
            self.on_date_selected(date_obj)

    def _update_calendar(self):
        """Перерисовка сетки календаря."""
        if not self.page:
            return

        # Обновляем заголовок
        months = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        self.header_text.value = f"{months[self.current_date.month - 1]} {self.current_date.year}"

        # Очищаем сетку
        self.days_grid.controls.clear()

        # Генерируем сетку дней
        month_matrix = self.calendar.monthdayscalendar(self.current_date.year, self.current_date.month)
        
        for week in month_matrix:
            week_row = ft.Row(spacing=2)
            for day in week:
                if day == 0:
                    # Пустая ячейка - квадратная
                    week_row.controls.append(
                        ft.Container(
                            expand=True,
                            aspect_ratio=1.0
                        )
                    )
                else:
                    current_day_date = datetime.date(self.current_date.year, self.current_date.month, day)
                    is_selected = self.selected_date == current_day_date
                    is_today = current_day_date == datetime.date.today()
                    is_cash_gap = current_day_date in self.cash_gaps
                    
                    # Проверяем наличие просроченных платежей по кредитам
                    has_overdue_payment = self._has_overdue_payment(current_day_date)
                    
                    # Собираем индикаторы для дня
                    indicators = self._get_indicators_for_date(current_day_date)
                    
                    # Стилизация
                    if has_overdue_payment:
                        # Просроченный платеж - красный фон (requirements 11.7)
                        bg_color = ft.Colors.RED_100
                        text_color = ft.Colors.BLACK
                    elif is_cash_gap:
                         # Если кассовый разрыв - желтый/оранжевый фон (requirements 6.3)
                        bg_color = ft.Colors.AMBER_100
                        text_color = ft.Colors.BLACK # На желтом фоне лучше черный
                    else:
                        bg_color = "primaryContainer" if is_selected else "surfaceVariant"
                        if is_selected:
                            text_color = "onPrimaryContainer"
                        elif is_today:
                            text_color = "primary"
                        else:
                            text_color = "onSurface"
                    
                    # Рамка для текущего дня или просроченного платежа
                    if has_overdue_payment:
                        border = ft.border.all(2, ft.Colors.RED_700)  # Красная рамка для просроченных
                    elif is_today:
                        border = ft.border.all(2, "primary")
                    else:
                        border = None

                    # Формируем tooltip
                    tooltip_text = None
                    if has_overdue_payment:
                        tooltip_text = "Просроченный платёж по кредиту!"
                    elif is_cash_gap:
                        tooltip_text = "Кассовый разрыв!"
                    
                    day_container = ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    str(day),
                                    weight=ft.FontWeight.BOLD if is_today or is_selected else ft.FontWeight.NORMAL,
                                    color=text_color,
                                    size=14
                                ),
                                ft.Row(
                                    controls=indicators,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=2,
                                    height=6
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2
                        ),
                        expand=True,
                        aspect_ratio=1.0,
                        bgcolor=bg_color,
                        border_radius=8,
                        border=border,
                        on_click=lambda _, d=current_day_date: self._on_day_click(d),
                        ink=True,
                        tooltip=tooltip_text
                    )
                    week_row.controls.append(day_container)
            
            self.days_grid.controls.append(week_row)
        
        self.update()

    def _has_overdue_payment(self, date_obj: datetime.date) -> bool:
        """
        Проверяет наличие просроченных платежей по кредитам для конкретной даты.
        
        Args:
            date_obj: Дата для проверки
            
        Returns:
            True, если есть просроченные платежи на эту дату
        """
        for payment in self.loan_payments:
            if payment.scheduled_date == date_obj and payment.status == PaymentStatus.OVERDUE:
                return True
        return False

    def _get_indicators_for_date(self, date_obj: datetime.date) -> List[ft.Control]:
        """Генерация индикаторов для конкретной даты."""
        indicators = []
        
        has_income = False
        has_expense = False
        
        # Фильтруем транзакции для этой даты
        for t in self.transactions:
            if t.date == date_obj:
                if t.type == TransactionType.INCOME:
                    has_income = True
                elif t.type == TransactionType.EXPENSE:
                    has_expense = True
        
        # Проверяем плановые вхождения
        has_planned = False
        for occ in self.planned_occurrences:
            if occ.occurrence_date == date_obj:
                has_planned = True
                break
        
        # Проверяем отложенные платежи с плановой датой
        has_pending_payment = False
        for payment in self.pending_payments:
            if payment.planned_date == date_obj:
                has_pending_payment = True
                break
        
        # Проверяем платежи по кредитам (requirements 11.6)
        has_loan_payment = False
        for payment in self.loan_payments:
            if payment.scheduled_date == date_obj:
                has_loan_payment = True
                break

        if has_income:
            indicators.append(
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ft.Colors.GREEN)
            )
        if has_expense:
            indicators.append(
                ft.Container(width=6, height=6, border_radius=3, bgcolor=ft.Colors.RED)
            )
        if has_planned:
            indicators.append(
                ft.Text("◆", size=8, color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD)
            )
        if has_pending_payment:
            indicators.append(
                ft.Text("📋", size=8, weight=ft.FontWeight.BOLD)
            )
        if has_loan_payment:
            indicators.append(
                ft.Text("💳", size=8, weight=ft.FontWeight.BOLD)
            )
            
        return indicators
