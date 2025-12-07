import flet as ft
from typing import Optional
from sqlalchemy.orm import Session

from models import TransactionType, CategoryDB
from database import get_db_session
from services.category_service import (
    get_all_categories,
    create_category,
    update_category,
    delete_category
)
from utils.logger import get_logger
from utils.error_handler import safe_handler

logger = get_logger(__name__)


class CategoryDialog(ft.AlertDialog):
    """
    Модальное окно для создания и редактирования категории.
    """
    def __init__(self, session: Session, on_success: callable, category: Optional[CategoryDB] = None):
        super().__init__()
        self.session = session
        self.on_success = on_success
        self.category = category  # Если передан - режим редактирования
        self.modal = True

        # Заголовок зависит от режима
        if self.category:
            self.title = ft.Text(f"Редактировать: {category.name}")
        else:
            self.title = ft.Text("Новая категория")

        # Fields
        self.name_field = ft.TextField(
            label="Название",
            value=category.name if category else "",
            autofocus=True,
            on_submit=self.save_category
        )

        # Тип транзакции (только для создания)
        if not category:
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
                selected={TransactionType.EXPENSE.value},
            )
        else:
            # При редактировании показываем тип как текст (нельзя изменить)
            type_text = "Расход" if category.type == TransactionType.EXPENSE else "Доход"
            self.type_label = ft.Text(
                f"Тип: {type_text}",
                size=14,
                color=ft.Colors.GREY_700
            )

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12, visible=False)

        # Формируем содержимое в зависимости от режима
        controls = []
        if not category:
            controls.append(self.type_segment)
            controls.append(ft.Container(height=10))
        else:
            controls.append(self.type_label)
            controls.append(ft.Container(height=5))

        controls.extend([
            self.name_field,
            self.error_text
        ])

        self.content = ft.Column(
            controls=controls,
            width=400,
            tight=True
        )

        # Кнопки
        button_text = "Сохранить" if category else "Создать"
        self.actions = [
            ft.TextButton("Отмена", on_click=self.close),
            ft.ElevatedButton(button_text, on_click=self.save_category),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def save_category(self, e):
        """Сохранение категории (создание или обновление)."""
        name = (self.name_field.value or "").strip()
        if not name:
            self.error_text.value = "Введите название категории"
            self.error_text.visible = True
            self.update()
            return

        try:
            if self.category:
                # Режим редактирования
                update_category(self.session, self.category.id, name)
            else:
                # Режим создания
                selected_type_val = list(self.type_segment.selected)[0]
                t_type = TransactionType(selected_type_val)
                create_category(self.session, name, t_type)

            # Сбрасываем ошибки
            self.error_text.value = ""
            self.error_text.visible = False

            self.on_success()
            self.close(e)

        except ValueError as ve:
            self.error_text.value = str(ve)
            self.error_text.visible = True
            self.update()
        except Exception as ex:
            logger.error(f"Ошибка сохранения категории: {ex}")
            self.error_text.value = f"Ошибка: {ex}"
            self.error_text.visible = True
            self.update()

    def close(self, e):
        """Закрытие диалога."""
        self.open = False
        if self.page:
            self.page.close(self)
            self.page.update()


class CategoriesView(ft.Column):
    """
    Экран управления категориями.
    """
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.page = page
        self.current_filter: Optional[TransactionType] = None
        
        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()
        
        # UI Components
        self.filter_tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Все"),
                ft.Tab(text="Расходы", icon=ft.Icons.ARROW_CIRCLE_DOWN),
                ft.Tab(text="Доходы", icon=ft.Icons.ARROW_CIRCLE_UP),
            ],
            on_change=self.on_filter_change
        )
        
        self.categories_list = ft.ListView(expand=True, spacing=5, padding=10)
        
        self.controls = [
            ft.Row(
                controls=[
                    ft.Text("Категории", size=24, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.ADD_CIRCLE,
                        icon_size=40,
                        tooltip="Добавить категорию",
                        on_click=self.open_create_dialog
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            self.filter_tabs,
            ft.Divider(height=1),
            self.categories_list
        ]

    def did_mount(self):
        """Вызывается после монтирования контрола на страницу."""
        self.refresh_data()

    def will_unmount(self):
        if self.cm:
            self.cm.__exit__(None, None, None)

    def on_filter_change(self, e):
        """Обработка смены вкладки фильтра."""
        index = self.filter_tabs.selected_index
        if index == 0:
            self.current_filter = None
        elif index == 1:
            self.current_filter = TransactionType.EXPENSE
        elif index == 2:
            self.current_filter = TransactionType.INCOME
        
        self.refresh_data()

    def refresh_data(self):
        """Загрузка и отображение списка категорий."""
        try:
            categories = get_all_categories(self.session, self.current_filter)
            
            self.categories_list.controls.clear()
            
            if not categories:
                self.categories_list.controls.append(
                    ft.Container(
                        content=ft.Text("Категории не найдены", color="outline"),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                )
            else:
                for cat in categories:
                    self.categories_list.controls.append(self._create_category_tile(cat))

            self.update()

        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")
            # Показываем сообщение об ошибке пользователю
            if self.page and hasattr(self.page, 'snack_bar'):
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Ошибка загрузки категорий: {e}"))
                self.page.snack_bar.open = True
                self.page.update()

    def _create_category_tile(self, category: CategoryDB) -> ft.Container:
        """Создание элемента списка для категории."""
        icon = ft.Icons.ARROW_CIRCLE_DOWN if category.type == TransactionType.EXPENSE else ft.Icons.ARROW_CIRCLE_UP
        color = ft.Colors.RED if category.type == TransactionType.EXPENSE else ft.Colors.GREEN

        # Основная информация о категории
        info_column = ft.Column(
            controls=[
                ft.Text(category.name, weight=ft.FontWeight.BOLD, size=16),
                ft.Text(
                    "Системная" if category.is_system else "Пользовательская",
                    size=12,
                    color=ft.Colors.GREY_700
                ),
            ],
            spacing=2
        )

        # Кнопки действий
        actions = []
        if not category.is_system:
            # Пользовательская категория - можно редактировать и удалять
            actions = [
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_color=ft.Colors.PRIMARY,
                    icon_size=20,
                    tooltip="Редактировать",
                    on_click=lambda e, cat=category: self.open_edit_dialog(cat)
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.ERROR,
                    icon_size=20,
                    tooltip="Удалить",
                    on_click=lambda e, cid=category.id, cname=category.name: self.confirm_delete(cid, cname)
                ),
            ]
        else:
            # Системная категория - только иконка замка
            actions = [
                ft.Icon(
                    ft.Icons.LOCK_OUTLINE,
                    color=ft.Colors.GREY_400,
                    size=20,
                    tooltip="Системная категория"
                )
            ]

        trailing = ft.Row(
            controls=actions,
            spacing=5
        )

        # Собираем строку
        content_row = ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=32),
                ft.Container(width=10),  # Отступ
                ft.Container(content=info_column, expand=True),  # Без padding, чтобы не блокировать события
                trailing
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        return ft.Container(
            content=content_row,
            bgcolor=ft.Colors.SURFACE,
            padding=12,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            ink=False  # Отключаем эффект ink, чтобы не перехватывать события кнопок
        )

    def open_create_dialog(self, e):
        """Открытие диалога создания категории."""
        logger.info("Нажата кнопка создания категории")

        # Получаем page из event control (кнопка добавления)
        page = e.control.page if e and e.control else self.page
        if not page:
            logger.error("Page не инициализирована")
            return

        logger.info("Создание диалога")
        # Создаем новый экземпляр диалога без категории (режим создания)
        dialog = CategoryDialog(
            session=self.session,
            on_success=self.refresh_data,
            category=None
        )

        # Устанавливаем и открываем диалог
        page.open(dialog)
        logger.info("Диалог открыт")
        page.update()

    def open_edit_dialog(self, category: CategoryDB):
        """Открытие диалога редактирования категории."""
        logger.info(f"Открытие диалога редактирования для категории '{category.name}' (ID {category.id})")

        if not self.page:
            logger.error("Page не инициализирована")
            return

        # Создаем диалог с передачей категории (режим редактирования)
        dialog = CategoryDialog(
            session=self.session,
            on_success=self.refresh_data,
            category=category
        )

        # Открываем диалог
        self.page.open(dialog)
        self.page.update()

    def confirm_delete(self, category_id: int, name: str):
        """Диалог подтверждения удаления."""
        @safe_handler()
        def delete_action(e):
            delete_category(self.session, category_id)
            dlg.open = False
            self.page.update()
            self.refresh_data()
            self.page.open(ft.SnackBar(content=ft.Text(f"Категория '{name}' удалена")))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение удаления"),
            content=ft.Text(f"Вы действительно хотите удалить категорию '{name}'?"),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: setattr(dlg, 'open', False) or self.page.update()),
                ft.TextButton("Удалить", on_click=delete_action, style=ft.ButtonStyle(color=ft.Colors.ERROR)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()