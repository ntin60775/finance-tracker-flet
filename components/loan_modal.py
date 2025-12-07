"""
Модальное окно для создания и редактирования кредита.
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
import flet as ft
from sqlalchemy.orm import Session

from models.models import LoanDB
from models.enums import LoanType
from services.lender_service import get_all_lenders


class LoanModal:
    """
    Модальное окно для создания и редактирования кредита.

    Позволяет пользователю:
    - Выбрать займодателя из списка
    - Ввести название кредита (обязательное)
    - Выбрать тип кредита
    - Ввести сумму кредита (обязательное)
    - Указать процентную ставку
    - Указать даты выдачи и окончания (обязательные)
    - Добавить номер договора и описание
    """

    def __init__(
        self,
        session: Session,
        on_save: Callable[[int, str, LoanType, Decimal, datetime.date, Optional[Decimal], Optional[datetime.date], Optional[str], Optional[str]], None],
        on_update: Optional[Callable[[int, Optional[str], Optional[LoanType], Optional[Decimal], Optional[datetime.date], Optional[Decimal], Optional[datetime.date], Optional[str], Optional[str]], None]] = None,
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для загрузки займодателей
            on_save: Callback при создании нового кредита
                     Параметры: lender_id, name, loan_type, amount, issue_date,
                               interest_rate, end_date, contract_number, description
            on_update: Callback при обновлении существующего кредита
                       Параметры: loan_id, name, loan_type, amount, issue_date,
                                 interest_rate, end_date, contract_number, description
        """
        self.session = session
        self.on_save = on_save
        self.on_update = on_update
        self.page: Optional[ft.Page] = None
        self.edit_loan_id: Optional[int] = None
        self.issue_date: Optional[datetime.date] = None
        self.end_date: Optional[datetime.date] = None

        # UI Controls
        self.lender_dropdown = ft.Dropdown(
            label="Займодатель *",
            options=[],
            on_change=self._clear_error
        )

        self.name_field = ft.TextField(
            label="Название кредита *",
            hint_text="Например: Ипотека на квартиру",
            autofocus=True,
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._clear_error
        )

        self.type_dropdown = ft.Dropdown(
            label="Тип кредита *",
            value=LoanType.CONSUMER.value,
            options=[
                ft.dropdown.Option(key=LoanType.MICROLOAN.value, text="Микрокредит"),
                ft.dropdown.Option(key=LoanType.CONSUMER.value, text="Потребительский"),
                ft.dropdown.Option(key=LoanType.MORTGAGE.value, text="Ипотека"),
                ft.dropdown.Option(key=LoanType.PERSONAL.value, text="Личный займ"),
                ft.dropdown.Option(key=LoanType.OTHER.value, text="Другое"),
            ],
            on_change=self._clear_error
        )

        self.amount_field = ft.TextField(
            label="Сумма кредита *",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._clear_error
        )

        self.interest_rate_field = ft.TextField(
            label="Процентная ставка",
            hint_text="Например: 12.5",
            suffix_text="%",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._clear_error
        )

        self.issue_date_button = ft.ElevatedButton(
            text="Выбрать дату выдачи *",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_issue_date_picker
        )

        self.end_date_button = ft.ElevatedButton(
            text="Выбрать дату окончания",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_end_date_picker
        )

        self.contract_number_field = ft.TextField(
            label="Номер договора",
            hint_text="Опционально",
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._clear_error
        )

        self.description_field = ft.TextField(
            label="Описание",
            hint_text="Дополнительная информация о кредите",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_change=self._clear_error
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Pickers
        self.issue_date_picker = ft.DatePicker(
            on_change=self._on_issue_date_change,
            first_date=datetime.date(2000, 1, 1),
            last_date=datetime.date.today(),
        )

        self.end_date_picker = ft.DatePicker(
            on_change=self._on_end_date_change,
            first_date=datetime.date.today(),
            last_date=datetime.date(2050, 12, 31),
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый кредит"),
            content=ft.Column(
                controls=[
                    self.lender_dropdown,
                    self.name_field,
                    self.type_dropdown,
                    self.amount_field,
                    self.interest_rate_field,
                    ft.Divider(height=1),
                    self.issue_date_button,
                    self.end_date_button,
                    ft.Divider(height=1),
                    self.contract_number_field,
                    self.description_field,
                    self.error_text,
                ],
                width=500,
                tight=True,
                spacing=15,
                scroll=ft.ScrollMode.AUTO
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self.close),
                ft.ElevatedButton("Сохранить", on_click=self._save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(
        self,
        page: ft.Page,
        loan: Optional[LoanDB] = None
    ):
        """
        Открытие модального окна.

        Args:
            page: Страница Flet для отображения диалога
            loan: Кредит для редактирования (None = создание нового)
        """
        self.page = page

        # Загружаем список займодателей
        self._load_lenders()

        # Режим редактирования или создания
        if loan:
            self.edit_loan_id = loan.id
            self.dialog.title = ft.Text(f"Редактировать: {loan.name}")
            self.lender_dropdown.value = str(loan.lender_id)
            self.name_field.value = loan.name
            self.type_dropdown.value = loan.loan_type.value
            self.amount_field.value = str(loan.amount)
            self.interest_rate_field.value = str(loan.interest_rate) if loan.interest_rate else ""
            self.issue_date = loan.issue_date
            self.issue_date_button.text = f"Дата выдачи: {loan.issue_date.strftime('%d.%m.%Y')}"
            self.end_date = loan.end_date
            if loan.end_date:
                self.end_date_button.text = f"Дата окончания: {loan.end_date.strftime('%d.%m.%Y')}"
            else:
                self.end_date_button.text = "Выбрать дату окончания"
            self.contract_number_field.value = loan.contract_number or ""
            self.description_field.value = loan.description or ""
        else:
            self.edit_loan_id = None
            self.dialog.title = ft.Text("Новый кредит")
            self.lender_dropdown.value = None
            self.name_field.value = ""
            self.type_dropdown.value = LoanType.CONSUMER.value
            self.amount_field.value = ""
            self.interest_rate_field.value = ""
            self.issue_date = None
            self.issue_date_button.text = "Выбрать дату выдачи *"
            self.end_date = None
            self.end_date_button.text = "Выбрать дату окончания"
            self.contract_number_field.value = ""
            self.description_field.value = ""

        # Очищаем ошибку
        self.error_text.value = ""

        # Добавляем date pickers в overlay
        page.overlay.extend([self.issue_date_picker, self.end_date_picker])

        # Открываем диалог
        page.overlay.append(self.dialog)
        self.dialog.open = True
        page.update()

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self.page:
            self.dialog.open = False
            self.page.update()

    def _load_lenders(self):
        """Загружает список займодателей в dropdown."""
        try:
            lenders = get_all_lenders(self.session)
            self.lender_dropdown.options = [
                ft.dropdown.Option(key=str(lender.id), text=lender.name)
                for lender in lenders
            ]

            if not lenders:
                self.lender_dropdown.options.append(
                    ft.dropdown.Option(key="0", text="Нет займодателей")
                )
                self.lender_dropdown.disabled = True

        except Exception as e:
            self.error_text.value = f"Ошибка загрузки займодателей: {str(e)}"
            if self.page:
                self.page.update()

    def _clear_error(self, e=None):
        """Очищает сообщение об ошибке при изменении поля."""
        if self.error_text.value:
            self.error_text.value = ""
            if self.page:
                self.page.update()

    def _open_issue_date_picker(self, e):
        """Открывает date picker для даты выдачи."""
        self.issue_date_picker.pick_date()

    def _open_end_date_picker(self, e):
        """Открывает date picker для даты окончания."""
        self.end_date_picker.pick_date()

    def _on_issue_date_change(self, e):
        """Обработчик выбора даты выдачи."""
        if e.control.value:
            self.issue_date = e.control.value
            self.issue_date_button.text = f"Дата выдачи: {self.issue_date.strftime('%d.%m.%Y')}"
            self._clear_error()
            if self.page:
                self.page.update()

    def _on_end_date_change(self, e):
        """Обработчик выбора даты окончания."""
        if e.control.value:
            self.end_date = e.control.value
            self.end_date_button.text = f"Дата окончания: {self.end_date.strftime('%d.%m.%Y')}"
            self._clear_error()
            if self.page:
                self.page.update()

    def _validate_and_get_data(self) -> Optional[dict]:
        """
        Валидация полей формы и возврат очищенных данных.

        Returns:
            Словарь с данными или None, если валидация не прошла
        """
        # Проверка обязательных полей
        if not self.lender_dropdown.value or self.lender_dropdown.value == "0":
            self.error_text.value = "Выберите займодателя"
            return None

        if not self.name_field.value or not self.name_field.value.strip():
            self.error_text.value = "Название кредита не может быть пустым"
            return None

        if not self.amount_field.value:
            self.error_text.value = "Укажите сумму кредита"
            return None

        try:
            amount = Decimal(self.amount_field.value)
            if amount <= Decimal('0'):
                self.error_text.value = "Сумма кредита должна быть больше нуля"
                return None
        except (InvalidOperation, ValueError):
            self.error_text.value = "Некорректная сумма кредита"
            return None

        if not self.issue_date:
            self.error_text.value = "Укажите дату выдачи кредита"
            return None

        # Валидация процентной ставки (если указана)
        interest_rate = None
        if self.interest_rate_field.value:
            try:
                rate = Decimal(self.interest_rate_field.value)
                if rate < Decimal('0'):
                    self.error_text.value = "Процентная ставка не может быть отрицательной"
                    return None
                interest_rate = rate
            except (InvalidOperation, ValueError):
                self.error_text.value = "Некорректная процентная ставка"
                return None

        # Валидация дат
        if self.end_date and self.issue_date:
            if self.end_date <= self.issue_date:
                self.error_text.value = "Дата окончания должна быть позже даты выдачи"
                return None

        # Собираем данные
        return {
            "lender_id": int(self.lender_dropdown.value),
            "name": self.name_field.value.strip(),
            "loan_type": LoanType(self.type_dropdown.value),
            "amount": amount,
            "issue_date": self.issue_date,
            "interest_rate": interest_rate,
            "end_date": self.end_date,
            "contract_number": self.contract_number_field.value.strip() if self.contract_number_field.value else None,
            "description": self.description_field.value.strip() if self.description_field.value else None,
        }

    def _save(self, e):
        """Сохранение данных кредита."""
        validated_data = self._validate_and_get_data()
        
        if not validated_data:
            if self.page:
                self.page.update()
            return

        try:
            # Вызываем соответствующий callback
            if self.edit_loan_id is not None:
                # Режим редактирования
                if self.on_update:
                    self.on_update(
                        self.edit_loan_id,
                        validated_data["name"],
                        validated_data["loan_type"],
                        validated_data["amount"],
                        validated_data["issue_date"],
                        validated_data["interest_rate"],
                        validated_data["end_date"],
                        validated_data["contract_number"],
                        validated_data["description"]
                    )
            else:
                # Режим создания
                if self.on_save:
                    self.on_save(
                        validated_data["lender_id"],
                        validated_data["name"],
                        validated_data["loan_type"],
                        validated_data["amount"],
                        validated_data["issue_date"],
                        validated_data["interest_rate"],
                        validated_data["end_date"],
                        validated_data["contract_number"],
                        validated_data["description"]
                    )

            # Закрываем диалог
            self.close()

        except ValueError as ve:
            self.error_text.value = str(ve)
            if self.page:
                self.page.update()
        except Exception as ex:
            self.error_text.value = f"Ошибка: {str(ex)}"
            if self.page:
                self.page.update()
