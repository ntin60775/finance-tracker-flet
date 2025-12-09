"""
Модальное окно для создания и редактирования займодателя.
"""

from typing import Optional, Callable
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import LenderDB
from finance_tracker.models.enums import LenderType


class LenderModal:
    """
    Модальное окно для создания и редактирования займодателя.

    Позволяет пользователю:
    - Ввести название займодателя (обязательное)
    - Выбрать тип займодателя (банк, МФО, физлицо и т.д.)
    - Ввести описание
    - Ввести контактную информацию
    - Добавить примечания
    """

    def __init__(
        self,
        session: Session,
        on_save: Callable[[str, LenderType, Optional[str], Optional[str], Optional[str]], None],
        on_update: Optional[Callable[[str, str, LenderType, Optional[str], Optional[str], Optional[str]], None]] = None,
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД (не используется, но сохраняется для единообразия)
            on_save: Callback при создании нового займодателя
                     Параметры: name, lender_type, description, contact_info, notes
            on_update: Callback при обновлении существующего займодателя
                       Параметры: lender_id, name, lender_type, description, contact_info, notes
        """
        self.session = session
        self.on_save = on_save
        self.on_update = on_update
        self.page: Optional[ft.Page] = None
        self.edit_lender_id: Optional[str] = None

        # UI Controls
        self.name_field = ft.TextField(
            label="Название *",
            hint_text="Например: Сбербанк",
            autofocus=True,
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._clear_error
        )

        self.type_dropdown = ft.Dropdown(
            label="Тип займодателя *",
            value=LenderType.BANK.value,
            options=[
                ft.dropdown.Option(key=LenderType.BANK.value, text="Банк"),
                ft.dropdown.Option(key=LenderType.MFO.value, text="МФО"),
                ft.dropdown.Option(key=LenderType.INDIVIDUAL.value, text="Физическое лицо"),
                ft.dropdown.Option(key=LenderType.OTHER.value, text="Другое"),
            ],
            on_change=self._clear_error
        )

        self.description_field = ft.TextField(
            label="Описание",
            hint_text="Краткое описание займодателя",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_change=self._clear_error
        )

        self.contact_field = ft.TextField(
            label="Контактная информация",
            hint_text="Телефон, email, адрес",
            keyboard_type=ft.KeyboardType.TEXT,
            on_change=self._clear_error
        )

        self.notes_field = ft.TextField(
            label="Примечания",
            hint_text="Дополнительные заметки",
            multiline=True,
            min_lines=2,
            max_lines=4,
            on_change=self._clear_error
        )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый займодатель"),
            content=ft.Column(
                controls=[
                    self.name_field,
                    self.type_dropdown,
                    self.description_field,
                    self.contact_field,
                    self.notes_field,
                    self.error_text,
                ],
                width=500,
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
        lender: Optional[LenderDB] = None
    ):
        """
        Открытие модального окна.

        Args:
            page: Страница Flet для отображения диалога
            lender: Займодатель для редактирования (None = создание нового)
        """
        self.page = page

        # Режим редактирования или создания
        if lender:
            self.edit_lender_id = lender.id
            self.dialog.title = ft.Text(f"Редактировать: {lender.name}")
            self.name_field.value = lender.name
            self.type_dropdown.value = lender.lender_type.value
            self.description_field.value = lender.description or ""
            self.contact_field.value = lender.contact_info or ""
            self.notes_field.value = lender.notes or ""
        else:
            self.edit_lender_id = None
            self.dialog.title = ft.Text("Новый займодатель")
            self.name_field.value = ""
            self.type_dropdown.value = LenderType.BANK.value
            self.description_field.value = ""
            self.contact_field.value = ""
            self.notes_field.value = ""

        # Очищаем ошибку
        self.error_text.value = ""

        # Открываем диалог
        page.overlay.append(self.dialog)
        self.dialog.open = True
        page.update()

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self.page:
            self.dialog.open = False
            self.page.update()

    def _clear_error(self, e=None):
        """Очищает сообщение об ошибке при изменении поля."""
        if self.error_text.value:
            self.error_text.value = ""
            if self.page:
                self.page.update()

    def _validate_fields(self) -> bool:
        """
        Валидация полей формы.

        Returns:
            True если все поля валидны, False иначе
        """
        # Проверка обязательных полей
        if not self.name_field.value or not self.name_field.value.strip():
            self.error_text.value = "Название займодателя не может быть пустым"
            if self.page:
                self.page.update()
            return False

        return True

    def _save(self, e):
        """Сохранение данных займодателя."""
        # Валидация
        if not self._validate_fields():
            return

        try:
            # Получаем данные из формы
            name = self.name_field.value.strip()
            lender_type = LenderType(self.type_dropdown.value)
            description = self.description_field.value.strip() if self.description_field.value else None
            contact_info = self.contact_field.value.strip() if self.contact_field.value else None
            notes = self.notes_field.value.strip() if self.notes_field.value else None

            # ВАЖНО: Закрываем диалог ПЕРЕД вызовом callback'ов
            # Иначе callback может вызвать page.update(), который перерисует UI
            # и диалог останется открытым
            self.close()

            # Вызываем соответствующий callback ПОСЛЕ закрытия диалога
            if self.edit_lender_id is not None:
                # Режим редактирования
                if self.on_update:
                    self.on_update(
                        self.edit_lender_id,
                        name,
                        lender_type,
                        description,
                        contact_info,
                        notes
                    )
            else:
                # Режим создания
                if self.on_save:
                    self.on_save(
                        name,
                        lender_type,
                        description,
                        contact_info,
                        notes
                    )

        except ValueError as ve:
            self.error_text.value = str(ve)
            if self.page:
                self.page.update()
        except Exception as ex:
            self.error_text.value = f"Ошибка: {str(ex)}"
            if self.page:
                self.page.update()
