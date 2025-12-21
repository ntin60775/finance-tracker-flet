"""
Модальное окно для досрочного погашения кредита.

Предоставляет UI для:
- Выбора типа досрочного погашения (полное/частичное)
- Ввода суммы погашения
- Выбора даты погашения
- Подтверждения операции
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import LoanDB
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class EarlyRepaymentModal:
    """
    Модальное окно для досрочного погашения кредита.

    Позволяет пользователю:
    - Выбрать тип погашения (полное/частичное)
    - Ввести сумму погашения
    - Выбрать дату погашения
    - Подтвердить операцию

    Согласно Requirements 10.7:
    - Поддерживает полное и частичное досрочное погашение
    """

    def __init__(
        self,
        session: Session,
        loan: LoanDB,
        on_repay: Callable[[bool, Decimal, datetime.date], None],
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД
            loan: Объект кредита для погашения
            on_repay: Callback при подтверждении погашения
                     Параметры: is_full (bool), amount (Decimal), repayment_date (date)
        """
        self.session = session
        self.loan = loan
        self.on_repay = on_repay
        self.page: Optional[ft.Page] = None
        self.repayment_date: Optional[datetime.date] = datetime.date.today()

        # UI Controls
        self.repayment_type_radio = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(
                    value="full",
                    label="Полное погашение (закрыть кредит полностью)"
                ),
                ft.Radio(
                    value="partial",
                    label="Частичное погашение (внести дополнительный платёж)"
                ),
            ]),
            value="full",
            on_change=self._on_type_change
        )

        self.amount_field = ft.TextField(
            label="Сумма погашения *",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._clear_error
        )

        self.repayment_date_button = ft.ElevatedButton(
            text=f"Дата погашения: {self.repayment_date.strftime('%d.%m.%Y')}",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_date_picker
        )

        self.warning_text = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.AMBER, size=20),
                    ft.Text(
                        "При полном погашении все будущие платежи будут отменены, "
                        "а статус кредита изменится на 'Погашен'.",
                        size=12,
                        color=ft.Colors.AMBER,
                        expand=True
                    )
                ],
                spacing=10
            ),
            padding=10,
            bgcolor=ft.Colors.AMBER_100,
            border_radius=5,
            visible=True
        )

        self.partial_warning_text = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE, size=20),
                    ft.Text(
                        "При частичном погашении график платежей останется без изменений. "
                        "Рекомендуется обновить график после погашения.",
                        size=12,
                        color=ft.Colors.BLUE,
                        expand=True
                    )
                ],
                spacing=10
            ),
            padding=10,
            bgcolor=ft.Colors.BLUE_100,
            border_radius=5,
            visible=False
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Picker
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date(2000, 1, 1),
            last_date=datetime.date.today() + datetime.timedelta(days=365),
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Досрочное погашение: {loan.name}"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Тип погашения:", weight=ft.FontWeight.BOLD),
                        self.repayment_type_radio,
                        ft.Divider(height=1),
                        self.amount_field,
                        self.repayment_date_button,
                        ft.Divider(height=1),
                        self.warning_text,
                        self.partial_warning_text,
                        self.error_text,
                    ],
                    spacing=10,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO
                ),
                width=500,
                height=450
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self._close_dialog),
                ft.ElevatedButton(
                    "Погасить",
                    icon=ft.Icons.PAYMENTS,
                    on_click=self._handle_repay,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(self, page: ft.Page):
        """
        Открывает модальное окно.

        Args:
            page: Страница Flet для отображения диалога
        """
        self.page = page
        page.overlay.append(self.date_picker)
        page.open(self.dialog)

        logger.debug(f"Открыто модальное окно досрочного погашения для кредита ID {self.loan.id}")

    def _close_dialog(self, e=None):
        """Закрывает модальное окно."""
        if self.page:
            self.page.close(self.dialog)
            logger.debug("Модальное окно досрочного погашения закрыто")

    def _on_type_change(self, e):
        """Обработчик изменения типа погашения."""
        is_full = self.repayment_type_radio.value == "full"
        self.warning_text.visible = is_full
        self.partial_warning_text.visible = not is_full
        self._clear_error()
        if self.page:
            self.page.update()

    def _open_date_picker(self, e):
        """Открывает выбор даты погашения."""
        if self.page:
            self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработчик изменения даты погашения."""
        if e.control.value:
            self.repayment_date = e.control.value
            self.repayment_date_button.text = f"Дата погашения: {self.repayment_date.strftime('%d.%m.%Y')}"
            self._clear_error()
            if self.page:
                self.page.update()

    def _clear_error(self, e=None):
        """Очищает сообщение об ошибке."""
        self.error_text.value = ""
        if self.page:
            self.page.update()

    def _show_error(self, message: str):
        """
        Показывает сообщение об ошибке.

        Args:
            message: Текст ошибки
        """
        self.error_text.value = message
        if self.page:
            self.page.update()

    def _validate_inputs(self) -> bool:
        """
        Валидирует введённые данные.

        Returns:
            True, если все данные корректны, иначе False
        """
        # Проверяем сумму
        if not self.amount_field.value or not self.amount_field.value.strip():
            self._show_error("Введите сумму погашения")
            return False

        try:
            amount = Decimal(self.amount_field.value.strip())
            if amount <= Decimal('0'):
                self._show_error("Сумма погашения должна быть больше 0")
                return False
        except (InvalidOperation, ValueError):
            self._show_error("Некорректная сумма погашения")
            return False

        # Проверяем дату
        if not self.repayment_date:
            self._show_error("Выберите дату погашения")
            return False

        return True

    def _handle_repay(self, e):
        """Обработчик подтверждения погашения."""
        if not self._validate_inputs():
            return

        try:
            # Получаем данные
            is_full = self.repayment_type_radio.value == "full"
            amount = Decimal(self.amount_field.value.strip())

            logger.info(
                f"Досрочное погашение кредита ID {self.loan.id}: "
                f"тип={'полное' if is_full else 'частичное'}, сумма={amount}, дата={self.repayment_date}"
            )

            # Закрываем диалог
            self._close_dialog()

            # Вызываем callback
            self.on_repay(is_full, amount, self.repayment_date)

        except Exception as ex:
            logger.error(f"Ошибка при обработке досрочного погашения: {ex}")
            self._show_error(f"Ошибка: {str(ex)}")
