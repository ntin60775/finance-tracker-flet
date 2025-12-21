"""
Модальное окно для исполнения отложенного платежа.

Компонент предоставляет UI для:
- Исполнения отложенного платежа с созданием фактической транзакции
- Редактирования суммы и даты при исполнении
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import PendingPaymentDB


class ExecutePendingPaymentModal:
    """
    Модальное окно для исполнения отложенного платежа.

    Позволяет пользователю:
    - Исполнить платёж с возможностью изменения суммы и даты
    - Просмотреть информацию об отложенном платеже

    Согласно Requirements 8.4:
    - При исполнении создаётся фактическая транзакция EXPENSE
    - Можно указать фактическую сумму (отличную от запланированной)
    - Можно указать фактическую дату
    """

    def __init__(
        self,
        session: Session,
        on_execute: Callable[[str, Decimal, datetime.date], None],
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для работы с данными.
            on_execute: Callback для исполнения платежа.
                        Принимает (payment_id, executed_amount, executed_date).
        """
        self.session = session
        self.on_execute = on_execute
        self.page: Optional[ft.Page] = None
        self.payment: Optional[PendingPaymentDB] = None
        self.current_date = datetime.date.today()

        # UI Controls
        self.date_button = ft.ElevatedButton(
            text=self.current_date.strftime("%d.%m.%Y"),
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_date_picker
        )

        self.amount_field = ft.TextField(
            label="Сумма исполнения",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._clear_error
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Info display
        self.info_text = ft.Text(size=14, color=ft.Colors.ON_SURFACE_VARIANT)

        # Date Picker
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date(2020, 1, 1),
            last_date=datetime.date(2030, 12, 31),
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Исполнить отложенный платёж"),
            content=ft.Column(
                controls=[
                    self.info_text,
                    ft.Divider(height=1),
                    self.date_button,
                    self.amount_field,
                    self.error_text,
                ],
                width=400,
                tight=True,
                spacing=15
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self.close),
                ft.ElevatedButton(
                    "Исполнить",
                    icon=ft.Icons.CHECK_CIRCLE,
                    on_click=self._execute
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(self, page: ft.Page, payment: PendingPaymentDB):
        """
        Открытие модального окна для исполнения платежа.

        Args:
            page: Ссылка на страницу Flet.
            payment: Отложенный платёж для исполнения.
        """
        self.page = page
        self.payment = payment

        # Setup Date Picker if not added
        if self.date_picker not in self.page.overlay:
            self.page.overlay.append(self.date_picker)

        # Reset fields
        self.current_date = datetime.date.today()
        self.date_button.text = self.current_date.strftime("%d.%m.%Y")
        self.date_picker.value = self.current_date

        # Set amount to planned amount
        self.amount_field.value = str(payment.amount)
        self.amount_field.error_text = None

        # Set info text
        priority_map = {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "critical": "Критический"
        }
        priority_text = priority_map.get(payment.priority.value, payment.priority.value)

        self.info_text.value = (
            f"Описание: {payment.description}\n"
            f"Плановая сумма: {payment.amount:.2f} ₽\n"
            f"Приоритет: {priority_text}"
        )

        if payment.planned_date:
            self.info_text.value += f"\nПлановая дата: {payment.planned_date.strftime('%d.%m.%Y')}"

        self.error_text.value = ""

        self.page.open(self.dialog)

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.page:
            self.page.close(self.dialog)

    def _open_date_picker(self, e):
        """Открытие выбора даты."""
        self.date_picker.value = self.current_date
        self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработка изменения даты."""
        if self.date_picker.value:
            self.current_date = self.date_picker.value
            self.date_button.text = self.current_date.strftime("%d.%m.%Y")
            if self.page:
                self.page.update()

    def _clear_error(self, e=None):
        """Очистка сообщений об ошибках."""
        self.amount_field.error_text = None
        self.error_text.value = ""
        if self.page:
            self.page.update()

    def _validate(self) -> bool:
        """
        Валидация полей формы.

        Returns:
            True если все поля валидны, иначе False.
        """
        is_valid = True

        # Валидация суммы
        try:
            amount = float(self.amount_field.value or "0")
            if amount <= 0:
                self.amount_field.error_text = "Сумма должна быть больше 0"
                is_valid = False
        except ValueError:
            self.amount_field.error_text = "Некорректная сумма"
            is_valid = False

        if self.page:
            self.page.update()

        return is_valid

    def _execute(self, e):
        """Исполнение отложенного платежа."""
        if not self._validate():
            return

        if not self.payment:
            return

        try:
            executed_amount = Decimal(self.amount_field.value)
            executed_date = self.current_date

            self.on_execute(self.payment.id, executed_amount, executed_date)
            self.close()

        except ValueError as ve:
            self.error_text.value = str(ve)
            if self.page:
                self.page.update()
        except Exception as ex:
            self.error_text.value = f"Ошибка исполнения: {str(ex)}"
            if self.page:
                self.page.update()