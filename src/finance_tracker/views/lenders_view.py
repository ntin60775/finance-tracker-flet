"""
Экран управления займодателями.

Предоставляет UI для:
- Отображения списка всех займодателей
- Создания и редактирования займодателей
- Фильтрации по типу займодателя
- Удаления займодателей с проверкой активных кредитов
"""

import flet as ft
from typing import Optional

from finance_tracker.models.models import LenderDB
from finance_tracker.models.enums import LenderType
from finance_tracker.database import get_db_session
from finance_tracker.services.lender_service import (
    get_all_lenders,
    create_lender,
    update_lender,
    delete_lender
)
from finance_tracker.components.lender_modal import LenderModal
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class LendersView(ft.Column):
    """
    Экран управления займодателями.

    Позволяет пользователю:
    - Просматривать список всех займодателей
    - Фильтровать по типу займодателя
    - Создавать новых займодателей
    - Редактировать и удалять займодателей

    Согласно Requirements 9.2, 9.5:
    - Отображает список займодателей с возможностью редактирования и удаления
    - Проверка связанных кредитов при удалении
    """

    def __init__(self, page: ft.Page):
        """
        Инициализация экрана займодателей.

        Args:
            page: Страница Flet для отображения UI
        """
        super().__init__(expand=True, spacing=20, alignment=ft.MainAxisAlignment.START)
        self.page = page
        self.lender_type_filter: Optional[LenderType] = None
        self.selected_lender: Optional[LenderDB] = None

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # Modal
        self.lender_modal = LenderModal(
            session=self.session,
            on_save=self.on_create_lender,
            on_update=self.on_update_lender
        )

        # UI Components
        self._build_ui()
        self.load_lenders()

    def _build_ui(self):
        """Построение UI компонентов."""
        # Заголовок и кнопка создания
        self.header = ft.Row(
            controls=[
                ft.Text("Займодатели", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.ON_PRIMARY,
                    tooltip="Добавить займодателя",
                    on_click=self.open_create_dialog
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Фильтр по типу займодателя
        self.type_dropdown = ft.Dropdown(
            label="Тип займодателя",
            width=250,
            options=[
                ft.dropdown.Option(key="all", text="Все типы"),
                ft.dropdown.Option(key=LenderType.BANK.value, text="Банк"),
                ft.dropdown.Option(key=LenderType.MFO.value, text="МФО"),
                ft.dropdown.Option(key=LenderType.INDIVIDUAL.value, text="Физическое лицо"),
                ft.dropdown.Option(key=LenderType.COLLECTOR.value, text="Коллектор"),
                ft.dropdown.Option(key=LenderType.OTHER.value, text="Другое"),
            ],
            value="all",
            on_change=self.on_type_filter_change
        )

        # Список займодателей
        self.lenders_column = ft.Column(
            controls=[],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        # Собираем все компоненты
        self.controls = [
            self.header,
            self.type_dropdown,
            ft.Divider(height=1),
            self.lenders_column
        ]

    def load_lenders(self):
        """Загрузка списка займодателей из БД."""
        try:
            # Получаем займодателей с учетом фильтра
            lenders = get_all_lenders(
                self.session,
                lender_type=self.lender_type_filter
            )

            # Очищаем список
            self.lenders_column.controls.clear()

            if not lenders:
                self.lenders_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Нет займодателей. Добавьте первого!",
                            size=16,
                            color=ft.Colors.GREY_400,
                            text_align=ft.TextAlign.CENTER
                        ),
                        alignment=ft.alignment.center,
                        padding=40
                    )
                )
            else:
                for lender in lenders:
                    self.lenders_column.controls.append(
                        self._create_lender_card(lender)
                    )

            self.page.update()
            logger.info(f"Загружено {len(lenders)} займодателей")

        except Exception as e:
            logger.error(f"Ошибка при загрузке займодателей: {e}")
            self._show_error(f"Не удалось загрузить займодателей: {str(e)}")

    def _create_lender_card(self, lender: LenderDB) -> ft.Container:
        """
        Создаёт карточку займодателя.

        Args:
            lender: Объект займодателя из БД

        Returns:
            Container с информацией о займодателе
        """
        # Иконка по типу займодателя
        type_icon_map = {
            LenderType.BANK: ft.Icons.ACCOUNT_BALANCE,
            LenderType.MFO: ft.Icons.STORE,
            LenderType.INDIVIDUAL: ft.Icons.PERSON,
            LenderType.COLLECTOR: ft.Icons.GAVEL,  # Иконка молотка для коллекторов
            LenderType.OTHER: ft.Icons.HELP_OUTLINE,
        }

        # Цвет иконки по типу займодателя
        type_color_map = {
            LenderType.BANK: ft.Colors.PRIMARY,
            LenderType.MFO: ft.Colors.PRIMARY,
            LenderType.INDIVIDUAL: ft.Colors.PRIMARY,
            LenderType.COLLECTOR: ft.Colors.ORANGE,  # Оранжевый цвет для коллекторов
            LenderType.OTHER: ft.Colors.PRIMARY,
        }

        # Название типа на русском
        type_name_map = {
            LenderType.BANK: "Банк",
            LenderType.MFO: "МФО",
            LenderType.INDIVIDUAL: "Физлицо",
            LenderType.COLLECTOR: "Коллектор",
            LenderType.OTHER: "Другое",
        }

        lender_icon = type_icon_map.get(lender.lender_type, ft.Icons.HELP_OUTLINE)
        lender_icon_color = type_color_map.get(lender.lender_type, ft.Colors.PRIMARY)
        lender_type_name = type_name_map.get(lender.lender_type, lender.lender_type.value)

        # Основная информация
        info_column = ft.Column(
            controls=[
                ft.Text(lender.name, size=18, weight=ft.FontWeight.BOLD),
                ft.Text(lender_type_name, size=14, color=ft.Colors.GREY_700),
            ],
            spacing=5
        )

        # Дополнительная информация
        details = []
        if lender.contact_info:
            details.append(
                ft.Row([
                    ft.Icon(ft.Icons.PHONE, size=16, color=ft.Colors.GREY_600),
                    ft.Text(lender.contact_info, size=12, color=ft.Colors.GREY_600)
                ], spacing=5)
            )
        if lender.description:
            details.append(
                ft.Text(
                    lender.description,
                    size=12,
                    color=ft.Colors.GREY_600,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS
                )
            )

        if details:
            info_column.controls.extend(details)

        # Кнопки действий
        actions_row = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_size=20,
                    tooltip="Редактировать",
                    on_click=lambda e, lender=lender: self.open_edit_dialog(lender)
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_size=20,
                    icon_color=ft.Colors.ERROR,
                    tooltip="Удалить",
                    on_click=lambda e, lender=lender: self.confirm_delete_lender(lender)
                ),
            ],
            spacing=5
        )

        # Кликабельная область с информацией (без кнопок)
        # Клик на эту область откроет диалог редактирования
        clickable_info = ft.Container(
            content=info_column,
            expand=True,
            on_click=lambda e, lender=lender: self.open_edit_dialog(lender)
        )

        # Собираем карточку
        card_content = ft.Row(
            controls=[
                ft.Icon(lender_icon, size=40, color=lender_icon_color),
                clickable_info,
                actions_row
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.START
        )

        return ft.Container(
            content=card_content,
            bgcolor=ft.Colors.SURFACE,
            padding=15,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)
        )

    def on_create_lender(
        self,
        name: str,
        lender_type: LenderType,
        description: Optional[str],
        contact_info: Optional[str],
        notes: Optional[str]
    ):
        """
        Callback для создания займодателя из модального окна.

        Args:
            name: Название займодателя
            lender_type: Тип займодателя
            description: Описание
            contact_info: Контактная информация
            notes: Примечания
        """
        try:
            lender = create_lender(
                session=self.session,
                name=name,
                lender_type=lender_type,
                description=description,
                contact_info=contact_info,
                notes=notes
            )

            logger.info(f"Займодатель создан: {lender.name} (ID {lender.id})")
            self._show_success(f"Займодатель '{lender.name}' успешно создан")
            self.load_lenders()

        except ValueError as ve:
            logger.warning(f"Ошибка валидации при создании займодателя: {ve}")
            self._show_error(str(ve))
        except Exception as ex:
            logger.error(f"Неожиданная ошибка при создании займодателя: {ex}")
            self._show_error(f"Не удалось создать займодателя: {str(ex)}")

    def on_update_lender(
        self,
        lender_id: str,
        name: str,
        lender_type: LenderType,
        description: Optional[str],
        contact_info: Optional[str],
        notes: Optional[str]
    ):
        """
        Callback для обновления займодателя из модального окна.

        Args:
            lender_id: ID займодателя
            name: Название займодателя
            lender_type: Тип займодателя
            description: Описание
            contact_info: Контактная информация
            notes: Примечания
        """
        try:
            updated_lender = update_lender(
                session=self.session,
                lender_id=lender_id,
                name=name,
                lender_type=lender_type,
                description=description,
                contact_info=contact_info,
                notes=notes
            )

            logger.info(f"Займодатель обновлён: {updated_lender.name} (ID {updated_lender.id})")
            self._show_success(f"Займодатель '{updated_lender.name}' успешно обновлён")
            self.load_lenders()

        except ValueError as ve:
            logger.warning(f"Ошибка валидации при обновлении займодателя: {ve}")
            self._show_error(str(ve))
        except Exception as ex:
            logger.error(f"Неожиданная ошибка при обновлении займодателя: {ex}")
            self._show_error(f"Не удалось обновить займодателя: {str(ex)}")

    def on_type_filter_change(self, e):
        """Обработчик изменения фильтра по типу займодателя."""
        selected = self.type_dropdown.value
        if selected == "all":
            self.lender_type_filter = None
        else:
            try:
                self.lender_type_filter = LenderType(selected)
            except ValueError:
                self.lender_type_filter = None

        self.load_lenders()

    def open_create_dialog(self, e):
        """Открывает диалог создания нового займодателя."""
        self.selected_lender = None
        self.lender_modal.open(self.page, lender=None)

    def open_edit_dialog(self, lender: LenderDB):
        """
        Открывает диалог редактирования займодателя.

        Args:
            lender: Займодатель для редактирования
        """
        self.selected_lender = lender
        self.lender_modal.open(self.page, lender=lender)

    def confirm_delete_lender(self, lender: LenderDB):
        """
        Показывает диалог подтверждения удаления займодателя.

        Args:
            lender: Займодатель для удаления
        """
        def delete(e):
            try:
                delete_lender(self.session, lender.id)
                logger.info(f"Займодатель удалён: {lender.name} (ID {lender.id})")
                self._show_success(f"Займодатель '{lender.name}' успешно удалён")
                self.page.close(confirm_dialog)
                self.load_lenders()

            except ValueError as ve:
                logger.warning(f"Ошибка при удалении займодателя: {ve}")
                self._show_error(str(ve))
            except Exception as ex:
                logger.error(f"Неожиданная ошибка при удалении займодателя: {ex}")
                self._show_error(f"Не удалось удалить займодателя: {str(ex)}")

        def cancel(e):
            self.page.close(confirm_dialog)

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтвердите удаление"),
            content=ft.Text(
                f"Вы уверены, что хотите удалить займодателя '{lender.name}'?\n\n"
                "Удаление возможно только если нет связанных активных кредитов.",
                size=14
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel),
                ft.ElevatedButton(
                    "Удалить",
                    bgcolor=ft.Colors.ERROR,
                    color=ft.Colors.ON_ERROR,
                    on_click=delete
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(confirm_dialog)

    def _show_success(self, message: str):
        """Показывает snackbar с сообщением об успехе."""
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.ON_PRIMARY),
            bgcolor=ft.Colors.GREEN,
            duration=3000
        )
        self.page.open(snack)

    def _show_error(self, message: str):
        """Показывает snackbar с сообщением об ошибке."""
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.ON_ERROR),
            bgcolor=ft.Colors.ERROR,
            duration=5000
        )
        self.page.open(snack)

    def will_unmount(self):
        """Очистка ресурсов при размонтировании view."""
        if hasattr(self, 'cm') and self.cm is not None:
            try:
                self.cm.__exit__(None, None, None)
            except Exception as e:
                logger.error(f"Ошибка при закрытии сессии БД: {e}")
