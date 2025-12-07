"""
Модальное окно для создания и редактирования плановых транзакций.

Компонент предоставляет UI для:
- Создания плановых транзакций (однократных и периодических)
- Настройки правил повторения
- Настройки условий окончания
- Валидации всех полей согласно требованиям
"""

import datetime
from typing import Optional, Callable
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models import (
    TransactionType,
    PlannedTransactionCreate,
    RecurrenceRuleCreate,
    RecurrenceType,
    EndConditionType
)
from finance_tracker.services.category_service import get_all_categories


class PlannedTransactionModal:
    """
    Модальное окно для создания и редактирования плановых транзакций.

    Позволяет пользователю:
    - Выбрать тип транзакции (Доход/Расход)
    - Выбрать категорию
    - Ввести сумму и описание
    - Выбрать дату начала
    - Настроить правило повторения (тип, условие окончания)

    Согласно Requirements 5.1 и 5.2:
    - Поддерживает все типы повторения
    - Поддерживает все условия окончания
    - Автоматически генерирует вхождения
    """

    def __init__(
        self,
        session: Session,
        on_save: Callable[[PlannedTransactionCreate], None],
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для загрузки категорий.
            on_save: Callback, вызываемый при успешном сохранении.
                     Принимает объект PlannedTransactionCreate.
        """
        self.session = session
        self.on_save = on_save
        self.page: Optional[ft.Page] = None
        self.current_start_date = datetime.date.today()
        self.current_end_date: Optional[datetime.date] = None

        # UI Controls - Basic fields
        self.type_segment = ft.SegmentedButton(
            segments=[
                ft.Segment(
                    value=TransactionType.EXPENSE.value,
                    label=ft.Text("Расход"),
                    icon=ft.Icons.ARROW_CIRCLE_DOWN,
                ),
                ft.Segment(
                    value=TransactionType.INCOME.value,
                    label=ft.Text("Доход"),
                    icon=ft.Icons.ARROW_CIRCLE_UP,
                ),
            ],
            selected={TransactionType.EXPENSE.value},
            on_change=self._on_type_change,
        )

        self.start_date_button = ft.ElevatedButton(
            text=self.current_start_date.strftime("%d.%m.%Y"),
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_start_date_picker
        )

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
            label="Категория",
            options=[],
            on_change=self._clear_error
        )

        self.description_field = ft.TextField(
            label="Описание (необязательно)",
            multiline=True,
            max_lines=3
        )

        # Recurrence settings
        self.recurrence_type_dropdown = ft.Dropdown(
            label="Тип повторения",
            options=[
                ft.dropdown.Option(key=RecurrenceType.NONE.value, text="Однократная"),
                ft.dropdown.Option(key=RecurrenceType.DAILY.value, text="Ежедневная"),
                ft.dropdown.Option(key=RecurrenceType.WEEKLY.value, text="Еженедельная"),
                ft.dropdown.Option(key=RecurrenceType.MONTHLY.value, text="Ежемесячная"),
                ft.dropdown.Option(key=RecurrenceType.YEARLY.value, text="Ежегодная"),
                ft.dropdown.Option(key=RecurrenceType.CUSTOM.value, text="Кастомная"),
            ],
            value=RecurrenceType.NONE.value,
            on_change=self._on_recurrence_type_change
        )

        # Custom interval fields (for CUSTOM type)
        self.interval_field = ft.TextField(
            label="Интервал",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
            visible=False,
            on_change=self._clear_error
        )

        self.interval_unit_dropdown = ft.Dropdown(
            label="Единица",
            options=[
                ft.dropdown.Option(key="days", text="Дни"),
                ft.dropdown.Option(key="weeks", text="Недели"),
                ft.dropdown.Option(key="months", text="Месяцы"),
                ft.dropdown.Option(key="years", text="Годы"),
            ],
            value="days",
            width=150,
            visible=False
        )

        # End condition settings
        self.end_condition_dropdown = ft.Dropdown(
            label="Условие окончания",
            options=[
                ft.dropdown.Option(key=EndConditionType.NEVER.value, text="Бессрочно"),
                ft.dropdown.Option(key=EndConditionType.UNTIL_DATE.value, text="До даты"),
                ft.dropdown.Option(key=EndConditionType.AFTER_COUNT.value, text="После N повторений"),
            ],
            value=EndConditionType.NEVER.value,
            on_change=self._on_end_condition_change,
            visible=False  # Initially hidden until recurrence is set
        )

        self.end_date_button = ft.ElevatedButton(
            text="Выбрать дату",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_end_date_picker,
            visible=False
        )

        self.occurrences_count_field = ft.TextField(
            label="Количество повторений",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
            visible=False,
            on_change=self._clear_error
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Pickers
        self.start_date_picker = ft.DatePicker(
            on_change=self._on_start_date_change,
            first_date=datetime.date(2020, 1, 1),
            last_date=datetime.date(2030, 12, 31),
        )

        self.end_date_picker = ft.DatePicker(
            on_change=self._on_end_date_change,
            first_date=datetime.date(2020, 1, 1),
            last_date=datetime.date(2030, 12, 31),
        )

        # Recurrence section container
        self.recurrence_section = ft.Column(
            controls=[
                ft.Text("Правило повторения", weight=ft.FontWeight.BOLD, size=14),
                self.recurrence_type_dropdown,
                ft.Row([self.interval_field, self.interval_unit_dropdown], spacing=10),
                self.end_condition_dropdown,
                self.end_date_button,
                self.occurrences_count_field,
            ],
            spacing=10,
            visible=True
        )

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новая плановая транзакция"),
            content=ft.Column(
                controls=[
                    ft.Row([self.type_segment], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=10),
                    self.start_date_button,
                    self.amount_field,
                    self.category_dropdown,
                    self.description_field,
                    ft.Divider(),
                    self.recurrence_section,
                    self.error_text,
                ],
                width=500,
                tight=True,
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self.close),
                ft.ElevatedButton("Сохранить", on_click=self._save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(self, page: ft.Page, date: Optional[datetime.date] = None):
        """
        Открытие модального окна.

        Args:
            page: Ссылка на страницу Flet.
            date: Предустановленная дата начала (по умолчанию сегодня).
        """
        self.page = page
        self.page.dialog = self.dialog

        # Setup Date Pickers if not added
        if self.start_date_picker not in self.page.overlay:
            self.page.overlay.append(self.start_date_picker)
        if self.end_date_picker not in self.page.overlay:
            self.page.overlay.append(self.end_date_picker)

        # Reset fields
        self.current_start_date = date or datetime.date.today()
        self.current_end_date = None
        self.start_date_button.text = self.current_start_date.strftime("%d.%m.%Y")
        self.start_date_picker.value = self.current_start_date

        self.amount_field.value = ""
        self.amount_field.error_text = None
        self.description_field.value = ""
        self.error_text.value = ""

        # Default to Expense
        self.type_segment.selected = {TransactionType.EXPENSE.value}

        # Reset recurrence fields
        self.recurrence_type_dropdown.value = RecurrenceType.NONE.value
        self.end_condition_dropdown.value = EndConditionType.NEVER.value
        self.interval_field.value = ""
        self.interval_unit_dropdown.value = "days"
        self.occurrences_count_field.value = ""

        # Hide conditional fields
        self._update_recurrence_ui()

        # Load categories
        self._load_categories(TransactionType.EXPENSE)

        self.dialog.open = True
        self.page.update()

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog:
            self.dialog.open = False
            self.page.update()

    def _open_start_date_picker(self, e):
        """Открытие выбора даты начала."""
        self.start_date_picker.pick_date()

    def _on_start_date_change(self, e):
        """Обработка выбора даты начала."""
        if self.start_date_picker.value:
            self.current_start_date = self.start_date_picker.value.date()
            self.start_date_button.text = self.current_start_date.strftime("%d.%m.%Y")
            self.start_date_button.update()

    def _open_end_date_picker(self, e):
        """Открытие выбора даты окончания."""
        self.end_date_picker.pick_date()

    def _on_end_date_change(self, e):
        """Обработка выбора даты окончания."""
        if self.end_date_picker.value:
            self.current_end_date = self.end_date_picker.value.date()
            self.end_date_button.text = self.current_end_date.strftime("%d.%m.%Y")
            self.end_date_button.update()

    def _on_type_change(self, e):
        """Обработка смены типа транзакции."""
        if not self.type_segment.selected:
            # Prevent deselecting all
            return

        selected_type = list(self.type_segment.selected)[0]
        self._load_categories(TransactionType(selected_type))
        self.page.update()

    def _load_categories(self, t_type: TransactionType):
        """Загрузка категорий выбранного типа."""
        try:
            categories = get_all_categories(self.session, t_type)
            self.category_dropdown.options = [
                ft.dropdown.Option(key=str(c.id), text=c.name) for c in categories
            ]
            self.category_dropdown.value = None
            self.category_dropdown.error_text = None
        except Exception as e:
            self.error_text.value = f"Ошибка загрузки категорий: {e}"

    def _on_recurrence_type_change(self, e):
        """Обработка изменения типа повторения."""
        self._update_recurrence_ui()
        self.page.update()

    def _on_end_condition_change(self, e):
        """Обработка изменения условия окончания."""
        self._update_end_condition_ui()
        self.page.update()

    def _update_recurrence_ui(self):
        """Обновление видимости полей в зависимости от типа повторения."""
        rec_type = self.recurrence_type_dropdown.value

        # Show/hide custom interval fields
        is_custom = rec_type == RecurrenceType.CUSTOM.value
        self.interval_field.visible = is_custom
        self.interval_unit_dropdown.visible = is_custom

        # Show/hide end condition (only for periodic transactions)
        is_periodic = rec_type != RecurrenceType.NONE.value
        self.end_condition_dropdown.visible = is_periodic

        if is_periodic:
            self._update_end_condition_ui()
        else:
            # Hide all end condition fields for non-periodic
            self.end_date_button.visible = False
            self.occurrences_count_field.visible = False

    def _update_end_condition_ui(self):
        """Обновление видимости полей в зависимости от условия окончания."""
        end_cond = self.end_condition_dropdown.value

        self.end_date_button.visible = (end_cond == EndConditionType.UNTIL_DATE.value)
        self.occurrences_count_field.visible = (end_cond == EndConditionType.AFTER_COUNT.value)

    def _clear_error(self, e):
        """Сброс ошибок при вводе."""
        if isinstance(e.control, ft.TextField):
            e.control.error_text = None
        elif isinstance(e.control, ft.Dropdown):
            e.control.error_text = None
        self.page.update()

    def _validate_fields(self) -> bool:
        """
        Валидация всех полей формы.

        Returns:
            True если все поля валидны, False иначе.
        """
        errors = False

        # Validate Amount
        try:
            amount = float(self.amount_field.value)
            if amount <= 0:
                self.amount_field.error_text = "Сумма должна быть больше 0"
                errors = True
        except (ValueError, TypeError):
            self.amount_field.error_text = "Введите корректное число"
            errors = True

        # Validate Category
        if not self.category_dropdown.value:
            self.category_dropdown.error_text = "Выберите категорию"
            errors = True

        # Validate custom interval (if CUSTOM type selected)
        if self.recurrence_type_dropdown.value == RecurrenceType.CUSTOM.value:
            try:
                interval = int(self.interval_field.value)
                if interval <= 0:
                    self.interval_field.error_text = "Интервал должен быть больше 0"
                    errors = True
            except (ValueError, TypeError):
                self.interval_field.error_text = "Введите корректное число"
                errors = True

        # Validate occurrences count (if AFTER_COUNT selected)
        if self.end_condition_dropdown.value == EndConditionType.AFTER_COUNT.value:
            try:
                count = int(self.occurrences_count_field.value)
                if count <= 0:
                    self.occurrences_count_field.error_text = "Количество должно быть больше 0"
                    errors = True
            except (ValueError, TypeError):
                self.occurrences_count_field.error_text = "Введите корректное число"
                errors = True

        # Validate end_date (if UNTIL_DATE selected)
        if self.end_condition_dropdown.value == EndConditionType.UNTIL_DATE.value:
            if self.current_end_date is None:
                self.error_text.value = "Выберите дату окончания"
                errors = True
            elif self.current_end_date <= self.current_start_date:
                self.error_text.value = "Дата окончания должна быть после даты начала"
                errors = True

        return not errors

    def _build_recurrence_rule(self) -> Optional[RecurrenceRuleCreate]:
        """
        Построение объекта правила повторения из UI полей.

        Returns:
            RecurrenceRuleCreate или None, если транзакция однократная.
        """
        rec_type = RecurrenceType(self.recurrence_type_dropdown.value)

        # If NONE, no recurrence rule needed
        if rec_type == RecurrenceType.NONE:
            return None

        # Build base recurrence rule
        rule_data = {
            "recurrence_type": rec_type,
        }

        # Custom interval
        if rec_type == RecurrenceType.CUSTOM:
            rule_data["interval"] = int(self.interval_field.value)
            rule_data["interval_unit"] = self.interval_unit_dropdown.value

        # End condition
        end_cond = EndConditionType(self.end_condition_dropdown.value)
        rule_data["end_condition_type"] = end_cond

        if end_cond == EndConditionType.UNTIL_DATE:
            rule_data["end_date"] = self.current_end_date
        elif end_cond == EndConditionType.AFTER_COUNT:
            rule_data["occurrences_count"] = int(self.occurrences_count_field.value)

        return RecurrenceRuleCreate(**rule_data)

    def _save(self, e):
        """
        Валидация и сохранение плановой транзакции.

        Validates: Requirements 5.1, 5.2 - создание плановых транзакций с правилами повторения
        """
        if not self._validate_fields():
            self.page.update()
            return

        try:
            selected_type = list(self.type_segment.selected)[0]
            amount = float(self.amount_field.value)

            # Build recurrence rule (if periodic)
            recurrence_rule = self._build_recurrence_rule()

            # Calculate end_date for planned transaction
            # If periodic with UNTIL_DATE, use that; otherwise None
            end_date = None
            if recurrence_rule and recurrence_rule.end_condition_type == EndConditionType.UNTIL_DATE:
                end_date = self.current_end_date

            planned_tx_data = PlannedTransactionCreate(
                amount=amount,
                type=TransactionType(selected_type),
                category_id=int(self.category_dropdown.value),
                description=self.description_field.value or None,
                start_date=self.current_start_date,
                end_date=end_date,
                recurrence_rule=recurrence_rule,
                is_active=True
            )

            self.on_save(planned_tx_data)
            self.close()

        except Exception as ex:
            self.error_text.value = f"Ошибка сохранения: {ex}"
            self.page.update()
