"""
Модальное окно для создания передачи долга между кредиторами.
"""

import datetime
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import LoanDB
from finance_tracker.models.enums import LenderType
from finance_tracker.services.lender_service import get_all_lenders, create_lender
from finance_tracker.services.debt_transfer_service import get_remaining_debt
from finance_tracker.components.lender_modal import LenderModal


class DebtTransferModal:
    """
    Модальное окно для создания передачи долга.
    
    Отображает:
    - Информацию о текущем держателе
    - Текущий остаток долга
    - Выбор нового держателя (с возможностью создания)
    - Дату передачи
    - Сумму долга при передаче
    - Разницу с текущим остатком
    - Причину передачи (опционально)
    """

    def __init__(
        self,
        session: Session,
        loan: LoanDB,
        on_transfer_callback: Callable[[str, str, datetime.date, Decimal, Optional[str], Optional[str]], None],
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для загрузки кредиторов
            loan: Кредит, по которому передается долг
            on_transfer_callback: Callback при создании передачи
                                 Параметры: loan_id, to_lender_id, transfer_date, 
                                           transfer_amount, reason, notes
        """
        self.session = session
        self.loan = loan
        self.on_transfer_callback = on_transfer_callback
        self.page: Optional[ft.Page] = None
        self.transfer_date: Optional[datetime.date] = None
        self.current_remaining_debt: Optional[Decimal] = None

        # Получаем текущий остаток долга
        try:
            self.current_remaining_debt = get_remaining_debt(self.session, self.loan.id)
        except Exception:
            self.current_remaining_debt = Decimal('0')

        # Создаем LenderModal для создания новых кредиторов
        self.lender_modal = LenderModal(
            session=self.session,
            on_save=self._on_lender_created,
        )

        # UI Controls
        self._build_info_section()
        self._build_form_controls()
        self._build_dialog()

    def _build_info_section(self):
        """Строит секцию с информацией о кредите и текущем держателе."""
        # Получаем информацию о текущем держателе
        current_holder = self.loan.current_holder if self.loan.current_holder else self.loan.lender
        
        self.loan_info_text = ft.Text(
            f"Кредит: {self.loan.name}",
            size=16,
            weight=ft.FontWeight.BOLD
        )
        
        self.current_holder_text = ft.Text(
            f"Текущий держатель: {current_holder.name}",
            size=14
        )
        
        self.remaining_debt_text = ft.Text(
            f"Текущий остаток долга: {self.current_remaining_debt:,.2f} ₽",
            size=14,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY
        )

    def _build_form_controls(self):
        """Строит элементы формы."""
        # Выбор нового держателя
        self.to_lender_dropdown = ft.Dropdown(
            label="Новый держатель долга *",
            options=[],
            on_change=self._clear_error
        )

        # Кнопка создания нового кредитора
        self.create_lender_button = ft.TextButton(
            text="Создать кредитора",
            icon=ft.Icons.ADD,
            on_click=self._on_create_lender
        )

        # Дата передачи
        self.transfer_date_button = ft.ElevatedButton(
            text="Выбрать дату передачи *",
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_date_picker
        )

        # Сумма передачи
        self.amount_field = ft.TextField(
            label="Сумма долга при передаче *",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=r"^\d*\.?\d{0,2}$",
                replacement_string=""
            ),
            on_change=self._on_amount_change
        )

        # Разница с текущим остатком
        self.amount_difference_text = ft.Text(
            "",
            size=12,
            italic=True
        )

        # Причина передачи
        self.reason_field = ft.TextField(
            label="Причина передачи",
            hint_text="Например: Продажа долга коллекторскому агентству",
            multiline=True,
            min_lines=2,
            max_lines=3,
            on_change=self._clear_error
        )

        # Примечания
        self.notes_field = ft.TextField(
            label="Примечания",
            hint_text="Дополнительная информация",
            multiline=True,
            min_lines=2,
            max_lines=3,
            on_change=self._clear_error
        )

        # Сообщение об ошибке
        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Picker
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date(2000, 1, 1),
            last_date=datetime.date(2050, 12, 31),
        )

    def _build_dialog(self):
        """Строит диалоговое окно."""
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Передача долга"),
            content=ft.Column(
                controls=[
                    # Информация о кредите
                    ft.Container(
                        content=ft.Column([
                            self.loan_info_text,
                            self.current_holder_text,
                            self.remaining_debt_text,
                        ]),
                        bgcolor=ft.Colors.SURFACE,
                        padding=15,
                        border_radius=8,
                        margin=ft.margin.only(bottom=15)
                    ),
                    
                    # Выбор нового держателя
                    ft.Row([
                        ft.Container(
                            content=self.to_lender_dropdown,
                            expand=True
                        ),
                        self.create_lender_button
                    ]),
                    
                    # Дата передачи
                    self.transfer_date_button,
                    
                    # Сумма передачи
                    self.amount_field,
                    self.amount_difference_text,
                    
                    ft.Divider(height=1),
                    
                    # Дополнительные поля
                    self.reason_field,
                    self.notes_field,
                    
                    # Ошибка
                    self.error_text,
                ],
                width=500,
                tight=True,
                spacing=15,
                scroll=ft.ScrollMode.AUTO
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self.close),
                ft.ElevatedButton("Передать долг", on_click=self._on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open(self, page: ft.Page):
        """
        Открытие модального окна.

        Args:
            page: Страница Flet для отображения диалога
        """
        self.page = page

        # Загружаем список кредиторов
        self._load_lenders()

        # Предзаполняем сумму текущим остатком долга (Requirement 8.3)
        self.amount_field.value = str(self.current_remaining_debt)
        self._update_amount_difference()

        # Устанавливаем дату по умолчанию на сегодня
        self.transfer_date = datetime.date.today()
        self.transfer_date_button.text = f"Дата передачи: {self.transfer_date.strftime('%d.%m.%Y')}"

        # Очищаем ошибку
        self.error_text.value = ""

        # Добавляем date picker в overlay
        page.overlay.append(self.date_picker)

        # Открываем диалог используя современный Flet API
        page.open(self.dialog)

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self.page:
            self.page.close(self.dialog)

    def _load_lenders(self):
        """Загружает список кредиторов в dropdown."""
        try:
            lenders = get_all_lenders(self.session)
            
            # Исключаем текущего держателя из списка
            current_holder_id = self.loan.effective_holder_id
            available_lenders = [
                lender for lender in lenders 
                if str(lender.id) != current_holder_id
            ]
            
            self.to_lender_dropdown.options = [
                ft.dropdown.Option(key=str(lender.id), text=lender.name)
                for lender in available_lenders
            ]

            # Если нет доступных кредиторов, добавляем информационное сообщение
            if not available_lenders:
                self.to_lender_dropdown.options.append(
                    ft.dropdown.Option(key="0", text="Нет доступных кредиторов - создайте нового")
                )
                # НЕ отключаем dropdown, чтобы пользователь мог видеть сообщение
                self.to_lender_dropdown.disabled = False
            else:
                self.to_lender_dropdown.disabled = False

        except Exception as e:
            self.error_text.value = f"Ошибка загрузки кредиторов: {str(e)}"
            if self.page:
                self.page.update()

    def _clear_error(self, e=None):
        """Очищает сообщение об ошибке при изменении поля."""
        if self.error_text.value:
            self.error_text.value = ""
            if self.page:
                self.page.update()

    def _open_date_picker(self, e):
        """Открывает date picker для даты передачи."""
        self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработчик выбора даты передачи."""
        if e.control.value:
            self.transfer_date = e.control.value
            self.transfer_date_button.text = f"Дата передачи: {self.transfer_date.strftime('%d.%m.%Y')}"
            self._clear_error()
            if self.page:
                self.page.update()

    def _on_amount_change(self, e):
        """Обработчик изменения суммы — показывает разницу."""
        self._update_amount_difference()
        self._clear_error()

    def _update_amount_difference(self):
        """Обновляет отображение разницы с текущим остатком."""
        if not self.amount_field.value or not self.current_remaining_debt:
            self.amount_difference_text.value = ""
            if self.page:
                self.page.update()
            return

        try:
            transfer_amount = Decimal(self.amount_field.value)
            difference = transfer_amount - self.current_remaining_debt
            
            if difference == Decimal('0'):
                self.amount_difference_text.value = "Сумма соответствует текущему остатку"
                self.amount_difference_text.color = ft.Colors.ON_SURFACE_VARIANT
            elif difference > Decimal('0'):
                self.amount_difference_text.value = f"+{difference:,.2f} ₽ (пени, штрафы)"
                self.amount_difference_text.color = ft.Colors.ERROR
            else:
                self.amount_difference_text.value = f"{difference:,.2f} ₽ (скидка)"
                self.amount_difference_text.color = ft.Colors.PRIMARY
                
        except (InvalidOperation, ValueError):
            self.amount_difference_text.value = ""
            
        if self.page:
            self.page.update()

    def _on_create_lender(self, e):
        """Открывает модальное окно создания кредитора."""
        if self.page:
            self.lender_modal.open(self.page)

    def _on_lender_created(
        self, 
        name: str, 
        lender_type: LenderType, 
        description: Optional[str], 
        contact_info: Optional[str], 
        notes: Optional[str]
    ):
        """
        Callback при создании нового кредитора.
        
        Args:
            name: Название кредитора
            lender_type: Тип кредитора
            description: Описание
            contact_info: Контактная информация
            notes: Примечания
        """
        try:
            # Создаем нового кредитора в БД
            new_lender = create_lender(
                session=self.session,
                name=name,
                lender_type=lender_type,
                description=description,
                contact_info=contact_info,
                notes=notes
            )
            
            # Обновляем список кредиторов в dropdown
            self._load_lenders()
            
            # Автоматически выбираем созданного кредитора
            self.to_lender_dropdown.value = str(new_lender.id)
            
            # Очищаем ошибку
            self._clear_error()
            
            # Обновляем UI
            if self.page:
                self.page.update()
                
        except Exception as ex:
            self.error_text.value = f"Ошибка при создании кредитора: {str(ex)}"
            if self.page:
                self.page.update()

    def _validate_form(self) -> bool:
        """
        Валидация полей формы.

        Returns:
            True если все поля валидны, False иначе
        """
        # Проверка выбора нового держателя
        if (not self.to_lender_dropdown.value or 
            self.to_lender_dropdown.value == "0" or
            not any(opt.key == self.to_lender_dropdown.value and opt.key != "0" 
                   for opt in self.to_lender_dropdown.options)):
            self.error_text.value = "Выберите нового держателя долга или создайте нового кредитора"
            return False

        # Проверка даты передачи
        if not self.transfer_date:
            self.error_text.value = "Укажите дату передачи"
            return False

        # Проверка суммы передачи
        if not self.amount_field.value:
            self.error_text.value = "Укажите сумму долга при передаче"
            return False

        try:
            amount = Decimal(self.amount_field.value)
            if amount <= Decimal('0'):
                self.error_text.value = "Сумма передачи должна быть больше нуля"
                return False
        except (InvalidOperation, ValueError):
            self.error_text.value = "Некорректная сумма передачи"
            return False

        return True

    def _show_confirmation_dialog(self):
        """Показывает диалог подтверждения передачи."""
        # Получаем данные для подтверждения
        to_lender_name = next(
            (opt.text for opt in self.to_lender_dropdown.options 
             if opt.key == self.to_lender_dropdown.value),
            "Неизвестный кредитор"
        )
        
        current_holder_name = (
            self.loan.current_holder.name if self.loan.current_holder 
            else self.loan.lender.name
        )
        
        transfer_amount = Decimal(self.amount_field.value)
        
        # Создаем диалог подтверждения
        confirmation_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение передачи долга"),
            content=ft.Column([
                ft.Text(f"Кредит: {self.loan.name}", weight=ft.FontWeight.BOLD),
                ft.Text(f"От: {current_holder_name}"),
                ft.Text(f"К: {to_lender_name}"),
                ft.Text(f"Дата: {self.transfer_date.strftime('%d.%m.%Y')}"),
                ft.Text(f"Сумма: {transfer_amount:,.2f} ₽", weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Вы уверены, что хотите передать долг?"),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self.page.close(confirmation_dialog)),
                ft.ElevatedButton(
                    "Подтвердить передачу", 
                    on_click=lambda e: self._execute_transfer(confirmation_dialog)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.open(confirmation_dialog)

    def _execute_transfer(self, confirmation_dialog):
        """Выполняет передачу долга после подтверждения."""
        try:
            # Закрываем диалог подтверждения
            self.page.close(confirmation_dialog)
            
            # Получаем данные из формы
            to_lender_id = self.to_lender_dropdown.value
            transfer_amount = Decimal(self.amount_field.value)
            reason = self.reason_field.value.strip() if self.reason_field.value else None
            notes = self.notes_field.value.strip() if self.notes_field.value else None

            # Закрываем основной диалог
            self.close()

            # Вызываем callback
            if self.on_transfer_callback:
                self.on_transfer_callback(
                    self.loan.id,
                    to_lender_id,
                    self.transfer_date,
                    transfer_amount,
                    reason,
                    notes
                )

        except Exception as ex:
            self.error_text.value = f"Ошибка при передаче долга: {str(ex)}"
            if self.page:
                self.page.update()

    def _on_confirm(self, e):
        """Подтверждение передачи с диалогом подтверждения."""
        # Валидация
        if not self._validate_form():
            if self.page:
                self.page.update()
            return

        # Показываем диалог подтверждения
        self._show_confirmation_dialog()