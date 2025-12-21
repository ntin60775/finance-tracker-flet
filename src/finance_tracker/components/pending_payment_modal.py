"""
Модальное окно для создания и редактирования отложенного платежа.
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import PendingPaymentCreate, PendingPaymentUpdate, PendingPaymentDB
from finance_tracker.models.enums import PendingPaymentPriority, TransactionType
from finance_tracker.services.category_service import get_all_categories


class PendingPaymentModal:
    """
    Модальное окно для создания и редактирования отложенного платежа.

    Позволяет пользователю:
    - Ввести сумму и описание
    - Выбрать категорию (только EXPENSE)
    - Выбрать приоритет
    - Опционально установить плановую дату
    """

    def __init__(
        self,
        session: Session,
        on_save: Callable[[PendingPaymentCreate], None],
        on_update: Optional[Callable[[str, PendingPaymentUpdate], None]] = None,
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для загрузки категорий.
            on_save: Callback при создании нового платежа.
            on_update: Callback при обновлении существующего платежа.
        """
        self.session = session
        self.on_save = on_save
        self.on_update = on_update
        self.page: Optional[ft.Page] = None
        self.edit_payment_id: Optional[str] = None
        self.planned_date: Optional[datetime.date] = None

        # UI Controls
        self.amount_field = ft.TextField(
            label="Сумма",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._clear_error
        )

        self.category_dropdown = ft.Dropdown(
            label="Категория (расход)",
            options=[],
            on_change=self._clear_error
        )

        self.description_field = ft.TextField(
            label="Описание",
            multiline=True,
            max_lines=3,
            on_change=self._clear_error
        )

        self.priority_dropdown = ft.Dropdown(
            label="Приоритет",
            value=PendingPaymentPriority.MEDIUM.value,
            options=[
                ft.dropdown.Option(
                    key=PendingPaymentPriority.LOW.value,
                    text="Низкий"
                ),
                ft.dropdown.Option(
                    key=PendingPaymentPriority.MEDIUM.value,
                    text="Средний"
                ),
                ft.dropdown.Option(
                    key=PendingPaymentPriority.HIGH.value,
                    text="Высокий"
                ),
                ft.dropdown.Option(
                    key=PendingPaymentPriority.CRITICAL.value,
                    text="Критический"
                ),
            ],
        )

        self.has_date_checkbox = ft.Checkbox(
            label="Установить плановую дату",
            value=False,
            on_change=self._on_has_date_change
        )

        self.date_button = ft.ElevatedButton(
            text="Выбрать дату",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_date_picker,
            visible=False
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Picker
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date.today(),
            last_date=datetime.date(2030, 12, 31),
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый отложенный платёж"),
            content=ft.Column(
                controls=[
                    self.amount_field,
                    self.category_dropdown,
                    self.description_field,
                    self.priority_dropdown,
                    ft.Divider(height=1),
                    self.has_date_checkbox,
                    self.date_button,
                    self.error_text,
                ],
                width=400,
                tight=True,
                spacing=15
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
        payment: Optional[PendingPaymentDB] = None
    ):
        """
        Открытие модального окна.

        Args:
            page: Ссылка на страницу Flet.
            payment: Платёж для редактирования (если None - создание нового).
        """
        self.page = page

        # Setup Date Picker if not added
        if self.date_picker not in self.page.overlay:
            self.page.overlay.append(self.date_picker)

        # Load categories
        self._load_categories()

        if payment:
            # Режим редактирования
            self.edit_payment_id = payment.id
            self.dialog.title = ft.Text("Редактировать отложенный платёж")

            self.amount_field.value = str(payment.amount)
            self.category_dropdown.value = str(payment.category_id)
            self.description_field.value = payment.description
            self.priority_dropdown.value = payment.priority.value

            if payment.planned_date:
                self.has_date_checkbox.value = True
                self.planned_date = payment.planned_date
                self.date_button.visible = True
                self.date_button.text = payment.planned_date.strftime("%d.%m.%Y")
                self.date_picker.value = payment.planned_date
            else:
                self.has_date_checkbox.value = False
                self.planned_date = None
                self.date_button.visible = False
        else:
            # Режим создания
            self.edit_payment_id = None
            self.dialog.title = ft.Text("Новый отложенный платёж")

            self.amount_field.value = ""
            self.category_dropdown.value = None
            self.description_field.value = ""
            self.priority_dropdown.value = PendingPaymentPriority.MEDIUM.value
            self.has_date_checkbox.value = False
            self.planned_date = None
            self.date_button.visible = False

        self.amount_field.error_text = None
        self.error_text.value = ""

        self.page.open(self.dialog)

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.page:
            self.page.close(self.dialog)

    def _load_categories(self):
        """Загружает категории расходов."""
        try:
            categories = get_all_categories(self.session, transaction_type=TransactionType.EXPENSE)
            self.category_dropdown.options = [
                ft.dropdown.Option(key=str(cat.id), text=cat.name)
                for cat in categories
            ]

            # Если только одна категория - выбираем её автоматически
            if len(categories) == 1 and not self.category_dropdown.value:
                self.category_dropdown.value = str(categories[0].id)

        except Exception as e:
            self.error_text.value = f"Ошибка загрузки категорий: {str(e)}"
            if self.page:
                self.page.update()

    def _on_has_date_change(self, e):
        """Обработка изменения чекбокса 'Установить плановую дату'."""
        self.date_button.visible = self.has_date_checkbox.value
        if not self.has_date_checkbox.value:
            self.planned_date = None
            self.date_button.text = "Выбрать дату"
        if self.page:
            self.page.update()

    def _open_date_picker(self, e):
        """Открытие выбора даты."""
        if self.planned_date:
            self.date_picker.value = self.planned_date
        else:
            self.date_picker.value = datetime.date.today()
        self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработка изменения даты."""
        if self.date_picker.value:
            self.planned_date = self.date_picker.value
            self.date_button.text = self.planned_date.strftime("%d.%m.%Y")
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

        # Валидация категории
        if not self.category_dropdown.value:
            self.error_text.value = "Выберите категорию"
            is_valid = False

        # Валидация описания
        if not self.description_field.value or not self.description_field.value.strip():
            self.error_text.value = "Введите описание"
            is_valid = False

        if self.page:
            self.page.update()

        return is_valid

    def _save(self, e):
        """Сохранение отложенного платежа."""
        if not self._validate():
            return

        try:
            amount = Decimal(self.amount_field.value)
            category_id = self.category_dropdown.value
            description = self.description_field.value.strip()
            priority = PendingPaymentPriority(self.priority_dropdown.value)
            planned_date = self.planned_date if self.has_date_checkbox.value else None

            if self.edit_payment_id:
                # Обновление существующего платежа
                if self.on_update:
                    update_data = PendingPaymentUpdate(
                        amount=amount,
                        category_id=category_id,
                        description=description,
                        priority=priority,
                        planned_date=planned_date
                    )
                    self.on_update(self.edit_payment_id, update_data)
            else:
                # Создание нового платежа
                payment_data = PendingPaymentCreate(
                    amount=amount,
                    category_id=category_id,
                    description=description,
                    priority=priority,
                    planned_date=planned_date
                )
                self.on_save(payment_data)

            self.close()

        except ValueError as ve:
            self.error_text.value = str(ve)
            if self.page:
                self.page.update()
        except Exception as ex:
            self.error_text.value = f"Ошибка сохранения: {str(ex)}"
            if self.page:
                self.page.update()