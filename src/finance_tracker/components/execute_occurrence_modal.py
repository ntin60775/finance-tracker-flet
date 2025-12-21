"""
Модальное окно для исполнения и пропуска плановых вхождений.

Компонент предоставляет UI для:
- Исполнения планового вхождения с созданием фактической транзакции
- Пропуска планового вхождения с указанием причины
- Редактирования суммы и даты при исполнении
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models import PlannedOccurrence


class ExecuteOccurrenceModal:
    """
    Модальное окно для исполнения или пропуска планового вхождения.

    Позволяет пользователю:
    - Исполнить вхождение с возможностью изменения суммы и даты
    - Пропустить вхождение с указанием причины
    - Просмотреть информацию о плановом вхождении

    Согласно Requirements 5.4 и 5.5:
    - При исполнении создаётся фактическая транзакция
    - При пропуске обновляется статус на SKIPPED с причиной
    """

    def __init__(
        self,
        session: Session,
        on_execute: Callable[[str, Decimal, datetime.date], None],
        on_skip: Callable[[str, Optional[str]], None],
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для работы с данными.
            on_execute: Callback для исполнения вхождения.
                        Принимает (occurrence_id, actual_amount, actual_date).
            on_skip: Callback для пропуска вхождения.
                     Принимает (occurrence_id, skip_reason).
        """
        self.session = session
        self.on_execute = on_execute
        self.on_skip = on_skip
        self.page: Optional[ft.Page] = None
        self.occurrence: Optional[PlannedOccurrence] = None
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

        self.skip_reason_field = ft.TextField(
            label="Причина пропуска",
            multiline=True,
            max_lines=3,
            visible=False
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Info display
        self.info_text = ft.Text(size=14, color=ft.Colors.ON_SURFACE_VARIANT)

        # Date Picker (будет добавлен в overlay страницы)
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date(2020, 1, 1),
            last_date=datetime.date(2030, 12, 31),
        )

        # Action buttons
        self.execute_button = ft.ElevatedButton(
            "Исполнить",
            icon=ft.Icons.CHECK_CIRCLE,
            on_click=self._execute
        )

        self.skip_button = ft.TextButton(
            "Пропустить",
            icon=ft.Icons.SKIP_NEXT,
            on_click=self._show_skip_form
        )

        self.confirm_skip_button = ft.ElevatedButton(
            "Подтвердить пропуск",
            icon=ft.Icons.CHECK,
            on_click=self._confirm_skip,
            visible=False
        )

        self.cancel_skip_button = ft.TextButton(
            "Отмена",
            on_click=self._hide_skip_form,
            visible=False
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Исполнение планового вхождения"),
            content=ft.Column(
                controls=[
                    self.info_text,
                    ft.Divider(),
                    ft.Text("Фактические данные:", weight=ft.FontWeight.BOLD, size=14),
                    self.date_button,
                    self.amount_field,
                    self.skip_reason_field,
                    self.error_text,
                ],
                width=400,
                tight=True,
                spacing=15
            ),
            actions=[
                self.skip_button,
                self.cancel_skip_button,
                self.execute_button,
                self.confirm_skip_button,
                ft.TextButton("Закрыть", on_click=self.close),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def open(
        self,
        page: ft.Page,
        occurrence: PlannedOccurrence,
        default_date: Optional[datetime.date] = None
    ):
        """
        Открытие модального окна для конкретного вхождения.

        Args:
            page: Ссылка на страницу Flet.
            occurrence: Плановое вхождение для исполнения/пропуска.
            default_date: Предустановленная дата исполнения (по умолчанию сегодня).
        """
        self.page = page
        self.occurrence = occurrence

        # Setup Date Picker if not added
        if self.date_picker not in self.page.overlay:
            self.page.overlay.append(self.date_picker)

        # Reset fields
        self.current_date = default_date or datetime.date.today()
        self.date_button.text = self.current_date.strftime("%d.%m.%Y")
        self.date_picker.value = self.current_date

        # Предустановка плановой суммы
        self.amount_field.value = str(occurrence.amount)
        self.amount_field.error_text = None

        self.skip_reason_field.value = ""
        self.skip_reason_field.visible = False
        self.error_text.value = ""

        # Show execute form by default
        self._show_execute_form()

        # Display occurrence info
        occurrence_date_str = occurrence.occurrence_date.strftime("%d.%m.%Y")
        self.info_text.value = (
            f"Плановая дата: {occurrence_date_str}\n"
            f"Плановая сумма: {occurrence.amount:.2f} ₽"
        )

        self.page.open(self.dialog)

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self.page:
            self.page.close(self.dialog)

    def _open_date_picker(self, e):
        """Открытие выбора даты."""
        self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработка выбора даты."""
        if self.date_picker.value:
            self.current_date = self.date_picker.value.date()
            self.date_button.text = self.current_date.strftime("%d.%m.%Y")
            self.date_button.update()

    def _clear_error(self, e):
        """Сброс ошибок при вводе."""
        if isinstance(e.control, ft.TextField):
            e.control.error_text = None
        self.page.update()

    def _show_execute_form(self):
        """Показать форму исполнения."""
        self.date_button.visible = True
        self.amount_field.visible = True
        self.skip_reason_field.visible = False

        self.execute_button.visible = True
        self.skip_button.visible = True
        self.confirm_skip_button.visible = False
        self.cancel_skip_button.visible = False

        self.page.update()

    def _show_skip_form(self, e=None):
        """Показать форму пропуска."""
        self.date_button.visible = False
        self.amount_field.visible = False
        self.skip_reason_field.visible = True

        self.execute_button.visible = False
        self.skip_button.visible = False
        self.confirm_skip_button.visible = True
        self.cancel_skip_button.visible = True

        self.page.update()

    def _hide_skip_form(self, e=None):
        """Вернуться к форме исполнения."""
        self._show_execute_form()

    def _execute(self, e):
        """
        Валидация и исполнение вхождения.

        Validates: Requirement 5.4 - исполнение вхождения создаёт фактическую транзакцию
        """
        errors = False

        # Validate Amount
        try:
            amount = Decimal(self.amount_field.value)
            if amount <= Decimal('0'):
                self.amount_field.error_text = "Сумма должна быть больше 0"
                errors = True
        except (ValueError, TypeError, InvalidOperation):
            self.amount_field.error_text = "Введите корректное число"
            errors = True

        if errors:
            self.page.update()
            return

        try:
            # Call execute callback
            self.on_execute(self.occurrence.id, amount, self.current_date)
            self.close()

        except Exception as ex:
            self.error_text.value = f"Ошибка исполнения: {ex}"
            self.page.update()

    def _confirm_skip(self, e):
        """
        Подтверждение пропуска вхождения.

        Validates: Requirement 5.5 - пропуск вхождения сохраняет причину пропуска
        """
        try:
            skip_reason = self.skip_reason_field.value.strip() or None

            # Call skip callback
            self.on_skip(self.occurrence.id, skip_reason)
            self.close()

        except Exception as ex:
            self.error_text.value = f"Ошибка пропуска: {ex}"
            self.page.update()