"""
Модальное окно для создания и редактирования плановых транзакций.

Компонент предоставляет UI для:
- Создания плановых транзакций (однократных и периодических)
- Настройки правил повторения
- Настройки условий окончания
- Валидации всех полей согласно требованиям
"""

import datetime
from typing import Optional, Callable, Literal
from decimal import Decimal
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models import (
    TransactionType,
    PlannedTransactionCreate,
    RecurrenceRuleCreate,
    RecurrenceType,
    EndConditionType,
)
from finance_tracker.services.category_service import get_selectable_leaf_categories


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
        on_save_obligation: Optional[Callable[[dict], None]] = None,
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
        self.on_save_obligation = on_save_obligation
        self._page: Optional[ft.Page] = None

        self._mode: Literal["planned", "obligation"] = "planned"
        self._editing_obligation_id: Optional[str] = None

        self.current_start_date = datetime.date.today()
        self.current_end_date: Optional[datetime.date] = None
        self.current_target_month: datetime.date = datetime.date.today().replace(day=1)

        # UI Controls - Basic fields
        self.type_segment = ft.SegmentedButton(
            segments=[
                ft.Segment(
                    value=TransactionType.EXPENSE.value,
                    label=ft.Text("Расход"),
                    icon=ft.Icon(ft.Icons.ARROW_CIRCLE_DOWN),
                ),
                ft.Segment(
                    value=TransactionType.INCOME.value,
                    label=ft.Text("Доход"),
                    icon=ft.Icon(ft.Icons.ARROW_CIRCLE_UP),
                ),
            ],
            selected=[TransactionType.EXPENSE.value],
            on_change=self._on_type_change,
        )

        self.start_date_button = ft.Button(
            content=self.current_start_date.strftime("%d.%m.%Y"),
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_start_date_picker,
        )

        self.target_month_button = ft.Button(
            content=self.current_target_month.strftime("%m.%Y"),
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_target_month_picker,
            visible=False,
        )

        self.amount_field = ft.TextField(
            label="Сумма",
            suffix="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True, regex_string=r"^\d*\.?\d{0,2}$", replacement_string=""
            ),
            on_change=self._clear_error,
        )

        self.category_dropdown = ft.Dropdown(
            label="Категория", options=[], on_select=self._clear_error
        )

        self.description_field = ft.TextField(
            label="Описание (необязательно)", multiline=True, max_lines=3
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
            on_select=self._on_recurrence_type_change,
        )

        # Custom interval fields (for CUSTOM type)
        self.interval_field = ft.TextField(
            label="Интервал",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=100,
            visible=False,
            on_change=self._clear_error,
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
            visible=False,
        )

        # End condition settings
        self.end_condition_dropdown = ft.Dropdown(
            label="Условие окончания",
            options=[
                ft.dropdown.Option(key=EndConditionType.NEVER.value, text="Бессрочно"),
                ft.dropdown.Option(key=EndConditionType.UNTIL_DATE.value, text="До даты"),
                ft.dropdown.Option(
                    key=EndConditionType.AFTER_COUNT.value, text="После N повторений"
                ),
            ],
            value=EndConditionType.NEVER.value,
            on_select=self._on_end_condition_change,
            visible=False,  # Initially hidden until recurrence is set
        )

        self.end_date_button = ft.Button(
            content="Выбрать дату",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_end_date_picker,
            visible=False,
        )

        self.occurrences_count_field = ft.TextField(
            label="Количество повторений",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
            visible=False,
            on_change=self._clear_error,
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

        self.target_month_picker = ft.DatePicker(
            on_change=self._on_target_month_change,
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
            visible=True,
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
                    self.target_month_button,
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
                ft.Button("Сохранить", on_click=self._save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(
        self,
        page: ft.Page,
        date: Optional[datetime.date] = None,
        *,
        mode: Literal["planned", "obligation"] = "planned",
        obligation_id: Optional[str] = None,
        target_month: Optional[datetime.date] = None,
        target_amount: Optional[Decimal] = None,
        category_id: Optional[str] = None,
        tx_type: Optional[TransactionType] = None,
        description: Optional[str] = None,
    ):
        self._page = page
        self._mode = mode
        self._editing_obligation_id = obligation_id if mode == "obligation" else None

        # Setup Date Pickers if not added
        if self.start_date_picker not in self._page.overlay:
            self._page.overlay.append(self.start_date_picker)
        if self.end_date_picker not in self._page.overlay:
            self._page.overlay.append(self.end_date_picker)
        if self.target_month_picker not in self._page.overlay:
            self._page.overlay.append(self.target_month_picker)

        self._reset_common_fields()

        if mode == "planned":
            self._prepare_planned_mode(date=date)
        else:
            self._prepare_obligation_mode(
                target_month=target_month,
                target_amount=target_amount,
                category_id=category_id,
                tx_type=tx_type,
                description=description,
            )

        self._page.open(self.dialog)

    def _reset_common_fields(self) -> None:
        self.amount_field.error_text = None
        self.category_dropdown.error_text = None
        self.error_text.value = ""

    def _prepare_planned_mode(self, *, date: Optional[datetime.date]) -> None:
        self.dialog.title.value = "Новая плановая транзакция"
        self.start_date_button.visible = True
        self.target_month_button.visible = False
        self.recurrence_section.visible = True
        self.amount_field.label = "Сумма"

        self.target_month_button.disabled = False
        self.category_dropdown.disabled = False
        self.type_segment.disabled = False

        # Reset fields
        self.current_start_date = date or datetime.date.today()
        self.current_end_date = None
        self.start_date_button.text = self.current_start_date.strftime("%d.%m.%Y")
        self.start_date_picker.value = self.current_start_date

        self.amount_field.value = ""
        self.description_field.value = ""

        # Default to Expense
        self.type_segment.selected = [TransactionType.EXPENSE.value]

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

    def _prepare_obligation_mode(
        self,
        *,
        target_month: Optional[datetime.date],
        target_amount: Optional[Decimal],
        category_id: Optional[str],
        tx_type: Optional[TransactionType],
        description: Optional[str],
    ) -> None:
        is_edit = self._editing_obligation_id is not None
        self.dialog.title.value = "Цель обязательства" if is_edit else "Новое обязательство"

        self.start_date_button.visible = False
        self.target_month_button.visible = True
        self.recurrence_section.visible = False
        self.amount_field.label = "Цель"

        self.target_month_button.disabled = is_edit
        self.category_dropdown.disabled = is_edit
        self.type_segment.disabled = is_edit

        resolved_type = tx_type or TransactionType.EXPENSE
        self.type_segment.selected = [resolved_type.value]
        self._load_categories(resolved_type)

        self.current_target_month = (target_month or datetime.date.today()).replace(day=1)
        self.target_month_picker.value = self.current_target_month
        self.target_month_button.text = self.current_target_month.strftime("%m.%Y")

        self.amount_field.value = f"{target_amount}" if target_amount is not None else ""
        self.category_dropdown.value = category_id
        self.description_field.value = description or ""

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self._page:
            self._page.close(self.dialog)

    def _open_start_date_picker(self, e):
        """Открытие выбора даты начала."""
        self._page.open(self.start_date_picker)

    def _open_target_month_picker(self, e):
        """Открытие выбора месяца обязательства."""
        self._page.open(self.target_month_picker)

    def _on_start_date_change(self, e):
        """Обработка выбора даты начала."""
        if self.start_date_picker.value:
            # DatePicker.value уже datetime.date в современном Flet
            if isinstance(self.start_date_picker.value, datetime.datetime):
                self.current_start_date = self.start_date_picker.value.date()
            else:
                self.current_start_date = self.start_date_picker.value
            self.start_date_button.text = self.current_start_date.strftime("%d.%m.%Y")
            self._page.update()

    def _on_target_month_change(self, e):
        """Обработка выбора месяца обязательства."""
        if self.target_month_picker.value:
            raw_value = self.target_month_picker.value
            if isinstance(raw_value, datetime.datetime):
                raw_value = raw_value.date()
            self.current_target_month = raw_value.replace(day=1)
            self.target_month_button.text = self.current_target_month.strftime("%m.%Y")
            self._page.update()

    def _open_end_date_picker(self, e):
        """Открытие выбора даты окончания."""
        self._page.open(self.end_date_picker)

    def _on_end_date_change(self, e):
        """Обработка выбора даты окончания."""
        if self.end_date_picker.value:
            # DatePicker.value уже datetime.date в современном Flet
            if isinstance(self.end_date_picker.value, datetime.datetime):
                self.current_end_date = self.end_date_picker.value.date()
            else:
                self.current_end_date = self.end_date_picker.value
            self.end_date_button.text = self.current_end_date.strftime("%d.%m.%Y")
            self._page.update()

    def _on_type_change(self, e):
        """Обработка смены типа транзакции."""
        if not self.type_segment.selected:
            # Prevent deselecting all
            return

        selected_type = list(self.type_segment.selected)[0]
        self._load_categories(TransactionType(selected_type))
        self._page.update()

    def _load_categories(self, t_type: TransactionType):
        """Загрузка категорий выбранного типа."""
        try:
            categories = get_selectable_leaf_categories(self.session, t_type)
            self.category_dropdown.options = [
                ft.dropdown.Option(
                    key=str(c.id),
                    text=self._format_category_label(c),
                )
                for c in categories
            ]
            self.category_dropdown.value = None
            self.category_dropdown.error_text = None
        except Exception as e:
            self.error_text.value = f"Ошибка загрузки категорий: {e}"

    def _format_category_label(self, category) -> str:
        category_name = getattr(category, "name", "")
        parent = getattr(category, "parent", None)
        parent_name = getattr(parent, "name", None) if parent is not None else None

        if parent_name:
            return f"{parent_name} / {category_name}"

        return category_name

    def _on_recurrence_type_change(self, e):
        """Обработка изменения типа повторения."""
        self._update_recurrence_ui()
        self._page.update()

    def _on_end_condition_change(self, e):
        """Обработка изменения условия окончания."""
        self._update_end_condition_ui()
        self._page.update()

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

        self.end_date_button.visible = end_cond == EndConditionType.UNTIL_DATE.value
        self.occurrences_count_field.visible = end_cond == EndConditionType.AFTER_COUNT.value

    def _clear_error(self, e):
        """Сброс ошибок при вводе."""
        if isinstance(e.control, ft.TextField):
            e.control.error_text = None
        elif isinstance(e.control, ft.Dropdown):
            e.control.error_text = None
        self._page.update()

    def _validate_fields(self) -> bool:
        """
        Валидация всех полей формы.

        Returns:
            True если все поля валидны, False иначе.
        """
        errors = False

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

        if self._mode != "planned":
            return not errors

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
            "interval": 1,  # По умолчанию интервал = 1
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
            self._page.update()
            return

        try:
            selected_type = list(self.type_segment.selected)[0]
            amount = Decimal(self.amount_field.value)

            if self._mode == "obligation":
                if not self.on_save_obligation:
                    raise RuntimeError("on_save_obligation не задан")

                payload = {
                    "obligation_id": self._editing_obligation_id,
                    "target_amount": amount,
                    "target_month": self.current_target_month,
                    "category_id": self.category_dropdown.value,
                    "type": TransactionType(selected_type),
                    "description": self.description_field.value or None,
                }
                self.on_save_obligation(payload)
                self.close()
                return

            # Build recurrence rule (if periodic)
            recurrence_rule = self._build_recurrence_rule()

            # Calculate end_date for planned transaction
            # If periodic with UNTIL_DATE, use that; otherwise None
            end_date = None
            if (
                recurrence_rule
                and recurrence_rule.end_condition_type == EndConditionType.UNTIL_DATE
            ):
                end_date = self.current_end_date

            planned_tx_data = PlannedTransactionCreate(
                amount=amount,
                type=TransactionType(selected_type),
                category_id=self.category_dropdown.value,
                description=self.description_field.value or None,
                start_date=self.current_start_date,
                end_date=end_date,
                recurrence_rule=recurrence_rule,
                is_active=True,
            )

            self.on_save(planned_tx_data)
            self.close()

        except Exception as ex:
            self.error_text.value = f"Ошибка сохранения: {ex}"
            self._page.update()
