import flet as ft
from typing import Optional, List, Any, Callable, cast, Literal
from sqlalchemy.orm import Session

from finance_tracker.models import TransactionType, CategoryDB
from finance_tracker.database import get_db_session
from finance_tracker.services.category_service import (
    get_all_categories,
    get_expense_tree,
    create_category,
    update_category,
    delete_category,
)
from finance_tracker.utils.logger import get_logger
from finance_tracker.utils.error_handler import safe_handler

logger = get_logger(__name__)


class CategoryDialog(ft.AlertDialog):
    """
    Модальное окно для создания и редактирования категории.
    """

    ROOT_PARENT_KEY = "__root__"
    SELECT_PARENT_KEY = "__select_parent__"

    def __init__(
        self,
        session: Session,
        on_success: Callable[[], None],
        category: Optional[CategoryDB] = None,
        *,
        create_mode: Optional[Literal["income", "expense_root", "expense_child"]] = None,
    ):
        super().__init__()
        self.session = session
        self.on_success = on_success
        self.category = category  # Если передан - режим редактирования
        self.modal = True
        self._create_mode = create_mode

        self._legacy_create = self.category is None and self._create_mode is None

        if self.category:
            self._transaction_type = cast(TransactionType, cast(Any, self.category).type)
        else:
            self._transaction_type = (
                TransactionType.INCOME if self._create_mode == "income" else TransactionType.EXPENSE
            )

        # Заголовок зависит от режима
        if self.category:
            category_name = cast(str, cast(Any, self.category).name)
            self.title = ft.Text(f"Редактировать: {category_name}")
        else:
            if self._create_mode == "income":
                self.title = ft.Text("Новая категория доходов")
            elif self._create_mode == "expense_root":
                self.title = ft.Text("Новая категория расходов")
            elif self._create_mode == "expense_child":
                self.title = ft.Text("Новая подкатегория расходов")
            else:
                self.title = ft.Text("Новая категория")

        # Fields
        self.name_field = ft.TextField(
            label="Название",
            value=cast(str, cast(Any, category).name) if category else "",
            autofocus=True,
            on_submit=self.save_category,
        )

        if self._legacy_create:
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

        type_text = "Расход" if self._transaction_type == TransactionType.EXPENSE else "Доход"
        self.type_label = ft.Text(f"Тип: {type_text}", size=14, color=ft.Colors.GREY_700)

        root_options, child_ids, root_ids = self._build_expense_parent_options()
        self._expense_child_ids = child_ids
        self._expense_root_ids = root_ids
        self._expense_root_options = root_options

        parent_dropdown_visible = False
        parent_required = False
        parent_label = "Родительская категория"
        parent_default_value = self.ROOT_PARENT_KEY
        parent_options: List[ft.dropdown.Option] = []

        if self._legacy_create and self._transaction_type == TransactionType.EXPENSE:
            parent_dropdown_visible = True
            parent_label = "Родительская категория (необязательно)"
            parent_options = [
                ft.dropdown.Option(key=self.ROOT_PARENT_KEY, text="(Корневая категория)"),
                *root_options,
            ]
        elif self._transaction_type == TransactionType.EXPENSE:
            if self.category is not None:
                parent_dropdown_visible = True
                parent_options = [
                    ft.dropdown.Option(key=self.ROOT_PARENT_KEY, text="(Корневая категория)"),
                    *root_options,
                ]
            elif self._create_mode == "expense_child":
                parent_dropdown_visible = True
                parent_required = True
                parent_label = "Родительская категория (обязательно)"
                parent_default_value = self.SELECT_PARENT_KEY
                parent_options = [
                    ft.dropdown.Option(key=self.SELECT_PARENT_KEY, text="(Выберите родителя)"),
                    *root_options,
                ]

        self._parent_required = parent_required
        self.parent_dropdown = ft.Dropdown(
            label=parent_label,
            options=parent_options,
            value=parent_default_value,
            visible=parent_dropdown_visible,
        )

        if self.category and self.parent_dropdown.visible:
            current_parent_id = cast(Optional[str], cast(Any, self.category).parent_id)
            self.parent_dropdown.value = current_parent_id or self.ROOT_PARENT_KEY

        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12, visible=False)

        controls: List[Any] = [self.type_segment] if self._legacy_create else [self.type_label]
        if self.parent_dropdown.visible:
            controls.append(ft.Container(height=8))
            controls.append(self.parent_dropdown)
        controls.append(ft.Container(height=10))
        controls.extend([self.name_field, self.error_text])

        self.content = ft.Column(controls=controls, width=400, tight=True)

        # Кнопки
        button_text = "Сохранить" if category else "Создать"
        self.actions = [
            ft.TextButton("Отмена", on_click=self.close),
            ft.Button(button_text, on_click=self.save_category),
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def save_category(self, e):
        """Сохранение категории (создание или обновление)."""
        name = (self.name_field.value or "").strip()
        if not name:
            self.error_text.value = "Введите название категории"
            self.error_text.visible = True
            self._update_if_mounted()
            return

        try:
            parent_id: Optional[str] = None

            t_type = self._transaction_type

            if t_type == TransactionType.EXPENSE and self.parent_dropdown.visible:
                selected_parent_key = self.parent_dropdown.value or self.ROOT_PARENT_KEY

                if self._parent_required and selected_parent_key in {
                    self.ROOT_PARENT_KEY,
                    self.SELECT_PARENT_KEY,
                }:
                    self.error_text.value = "Выберите родительскую категорию"
                    self.error_text.visible = True
                    self._update_if_mounted()
                    return

                if self._parent_required and not self._expense_root_ids:
                    self.error_text.value = (
                        "Нет доступных корневых категорий расходов. "
                        "Сначала создайте корневую категорию."
                    )
                    self.error_text.visible = True
                    self._update_if_mounted()
                    return

                if selected_parent_key in self._expense_child_ids:
                    self.error_text.value = (
                        "Нельзя создать подкатегорию второго уровня. "
                        "Выберите корневую категорию в качестве родителя."
                    )
                    self.error_text.visible = True
                    self._update_if_mounted()
                    return

                if self.category:
                    category_id = cast(str, cast(Any, self.category).id)
                    if selected_parent_key == category_id:
                        self.error_text.value = "Категория не может быть родителем сама себе"
                        self.error_text.visible = True
                        self._update_if_mounted()
                        return

                if selected_parent_key in {self.ROOT_PARENT_KEY, self.SELECT_PARENT_KEY}:
                    parent_id = None
                else:
                    parent_id = selected_parent_key

            if self.category:
                # Режим редактирования
                category_id = cast(str, cast(Any, self.category).id)
                if t_type == TransactionType.EXPENSE:
                    update_category(self.session, category_id, name, parent_id=parent_id)
                else:
                    update_category(self.session, category_id, name)
            else:
                # Режим создания
                if t_type == TransactionType.EXPENSE:
                    create_category(self.session, name, t_type, parent_id=parent_id)
                else:
                    create_category(self.session, name, t_type)

            # Сбрасываем ошибки
            self.error_text.value = ""
            self.error_text.visible = False

            self.on_success()
            self.close(e)

        except ValueError as ve:
            self.error_text.value = str(ve)
            self.error_text.visible = True
            self._update_if_mounted()
        except Exception as ex:
            logger.error(f"Ошибка сохранения категории: {ex}")
            self.error_text.value = f"Ошибка: {ex}"
            self.error_text.visible = True
            self._update_if_mounted()

    def close(self, e):
        """Закрытие диалога."""
        page = getattr(self, "page", None) or getattr(self, "_page", None)
        if page:
            cast(Any, page).close(self)

    def _on_type_change(self, e) -> None:
        if not getattr(self, "type_segment", None):
            return

        selected_type_val = list(self.type_segment.selected)[0]
        self._transaction_type = TransactionType(selected_type_val)

        if self._transaction_type == TransactionType.EXPENSE:
            self.parent_dropdown.visible = True
            self.parent_dropdown.options = [
                ft.dropdown.Option(key=self.ROOT_PARENT_KEY, text="(Корневая категория)"),
                *getattr(self, "_expense_root_options", []),
            ]
        else:
            self.parent_dropdown.visible = False
            self.parent_dropdown.value = self.ROOT_PARENT_KEY

        self.error_text.value = ""
        self.error_text.visible = False
        self._update_if_mounted()

    def _update_if_mounted(self) -> None:
        if getattr(self, "page", None):
            self.update()

    def _build_expense_parent_options(
        self,
    ) -> tuple[List[ft.dropdown.Option], set[str], set[str]]:
        options: List[ft.dropdown.Option] = []
        child_ids: set[str] = set()
        root_ids: set[str] = set()

        if self._transaction_type != TransactionType.EXPENSE:
            return options, child_ids, root_ids

        try:
            expense_tree = get_expense_tree(self.session)
        except Exception as ex:
            logger.error(f"Ошибка загрузки дерева категорий для parent dropdown: {ex}")
            return options, child_ids, root_ids

        for node in expense_tree:
            root = cast(Any, node.get("category"))
            if root is None:
                continue

            root_id = str(root.id)
            root_name = str(root.name)
            root_ids.add(root_id)

            if self.category is None and (
                self._create_mode == "expense_child" or self._create_mode is None
            ):
                options.append(ft.dropdown.Option(key=root_id, text=root_name))
            elif self.category is not None:
                current_id = str(cast(Any, self.category).id)
                if root_id != current_id:
                    options.append(ft.dropdown.Option(key=root_id, text=root_name))

            children = cast(list[object], node.get("children", []))
            for child in children:
                child_obj = cast(Any, child)
                child_id = str(child_obj.id)
                child_name = str(child_obj.name)
                child_ids.add(child_id)
                _ = root_name
                _ = child_name

        return options, child_ids, root_ids


class CategoriesView(ft.Column):
    """
    Экран управления категориями.
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, alignment=ft.MainAxisAlignment.START)
        self._page = page

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # UI Components
        self.income_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.expense_list = ft.ListView(expand=True, spacing=5, padding=10)

        income_section = ft.Container(
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Доходы",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.GREEN,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_size=26,
                                tooltip="Добавить доходную категорию",
                                on_click=self.open_create_income_dialog,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1),
                    self.income_list,
                ],
                expand=True,
                spacing=8,
            ),
        )

        expense_section = ft.Container(
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                "Расходы",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.RED,
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                        icon_size=26,
                                        tooltip="Добавить корневую категорию расходов",
                                        on_click=self.open_create_expense_root_dialog,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                                        icon_size=26,
                                        tooltip="Добавить подкатегорию расходов",
                                        on_click=self.open_create_expense_child_dialog,
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1),
                    self.expense_list,
                ],
                expand=True,
                spacing=8,
            ),
        )

        self.split_layout = ft.Row(
            controls=[income_section, expense_section],
            expand=True,
            wrap=True,
            spacing=16,
            run_spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self.controls = [
            ft.Row(
                controls=[
                    ft.Text("Категории", size=24, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=1),
            self.split_layout,
        ]

    def did_mount(self):
        """Вызывается после монтирования контрола на страницу."""
        self.refresh_data()

    def will_unmount(self):
        if self.cm:
            self.cm.__exit__(None, None, None)

    def refresh_data(self):
        """Загрузка и отображение списка категорий."""
        try:
            income_categories = get_all_categories(self.session, TransactionType.INCOME)
            expense_tree = get_expense_tree(self.session)

            self.income_list.controls.clear()
            self.expense_list.controls.clear()

            if not income_categories:
                self.income_list.controls.append(
                    ft.Container(
                        content=ft.Text("Категории доходов не найдены", color="outline"),
                        alignment=ft.Alignment.CENTER,
                        padding=20,
                    )
                )
            else:
                for cat in income_categories:
                    self.income_list.controls.append(self._create_category_tile(cat))

            expense_item_count = 0
            for node in expense_tree:
                category = node.get("category")
                children = node.get("children")
                if isinstance(category, CategoryDB):
                    expense_item_count += 1
                if isinstance(children, list):
                    expense_item_count += len(children)

            if expense_item_count == 0:
                self.expense_list.controls.append(
                    ft.Container(
                        content=ft.Text("Категории расходов не найдены", color="outline"),
                        alignment=ft.Alignment.CENTER,
                        padding=20,
                    )
                )
            else:
                for node in expense_tree:
                    root = node.get("category")
                    children = node.get("children")

                    if isinstance(root, CategoryDB):
                        self.expense_list.controls.append(self._create_category_tile(root))
                    if isinstance(children, list):
                        for child in children:
                            if isinstance(child, CategoryDB):
                                self.expense_list.controls.append(
                                    self._create_category_tile(child, indent=22, is_child=True)
                                )

            if self._page:
                self._page.update()
            else:
                self.update()

        except Exception as e:
            logger.error(f"Ошибка загрузки категорий: {e}")
            # Показываем сообщение об ошибке пользователю
            if self._page:
                snack = ft.SnackBar(content=ft.Text(f"Ошибка загрузки категорий: {e}"))
                cast(Any, self._page).open(snack)

    def _create_category_tile(
        self,
        category: CategoryDB,
        indent: int = 0,
        is_child: bool = False,
    ) -> ft.Container:
        """Создание элемента списка для категории."""
        category_type = cast(TransactionType, cast(Any, category).type)
        category_name = cast(str, cast(Any, category).name)
        category_id = cast(str, cast(Any, category).id)
        is_system = bool(cast(Any, category).is_system)

        icon = (
            ft.Icons.ARROW_CIRCLE_DOWN
            if category_type == TransactionType.EXPENSE
            else ft.Icons.ARROW_CIRCLE_UP
        )
        color = ft.Colors.RED if category_type == TransactionType.EXPENSE else ft.Colors.GREEN

        # Основная информация о категории
        info_column = ft.Column(
            controls=[
                ft.Text(
                    category_name,
                    weight=ft.FontWeight.W_600 if not is_child else ft.FontWeight.NORMAL,
                    size=16 if not is_child else 15,
                ),
                ft.Text(
                    "Системная" if is_system else "Пользовательская",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
            ],
            spacing=2,
        )

        # Кнопки действий
        actions: List[Any] = []
        if not is_system:
            # Пользовательская категория - можно редактировать и удалять
            actions = [
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_color=ft.Colors.PRIMARY,
                    icon_size=20,
                    tooltip="Редактировать",
                    on_click=lambda e, cat=category: self.open_edit_dialog(cat),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.ERROR,
                    icon_size=20,
                    tooltip="Удалить",
                    on_click=lambda e, cid=category_id, cname=category_name: self.confirm_delete(
                        cid,
                        cname,
                    ),
                ),
            ]
        else:
            # Системная категория - только иконка замка
            actions = [
                ft.Icon(
                    ft.Icons.LOCK_OUTLINE,
                    color=ft.Colors.GREY_400,
                    size=20,
                    tooltip="Системная категория",
                )
            ]

        trailing = ft.Row(controls=actions, spacing=5)

        # Собираем строку
        content_row = ft.Row(
            controls=[
                ft.Icon(icon, color=color, size=32),
                ft.Container(width=10),  # Отступ
                ft.Container(
                    content=info_column, expand=True
                ),  # Без padding, чтобы не блокировать события
                trailing,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Container(
            content=ft.Container(
                content=content_row,
                bgcolor=ft.Colors.SURFACE,
                padding=12,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.OUTLINE),
                ink=False,  # Отключаем эффект ink, чтобы не перехватывать события кнопок
            ),
            padding=ft.Padding.only(left=indent) if indent > 0 else None,
        )

    def _open_create_dialog(
        self,
        e,
        create_mode: Literal["income", "expense_root", "expense_child"],
    ) -> None:
        page = e.control.page if e and getattr(e, "control", None) else self._page
        if not page:
            logger.error("Page не инициализирована")
            return

        dialog = CategoryDialog(
            session=self.session,
            on_success=self.refresh_data,
            category=None,
            create_mode=create_mode,
        )
        cast(Any, page).open(dialog)
        cast(Any, page).update()

    def open_create_dialog(self, e) -> None:
        page = e.control.page if e and getattr(e, "control", None) else self._page
        if not page:
            logger.error("Page не инициализирована")
            return

        dialog = CategoryDialog(
            session=self.session,
            on_success=self.refresh_data,
            category=None,
        )
        cast(Any, page).open(dialog)
        cast(Any, page).update()

    def open_create_income_dialog(self, e):
        self._open_create_dialog(e, create_mode="income")

    def open_create_expense_root_dialog(self, e):
        self._open_create_dialog(e, create_mode="expense_root")

    def open_create_expense_child_dialog(self, e):
        self._open_create_dialog(e, create_mode="expense_child")

    def open_edit_dialog(self, category: CategoryDB):
        """Открытие диалога редактирования категории."""
        category_name = cast(str, cast(Any, category).name)
        category_id = cast(str, cast(Any, category).id)
        logger.info(
            f"Открытие диалога редактирования для категории '{category_name}' (ID {category_id})"
        )

        if not self._page:
            logger.error("Page не инициализирована")
            return

        # Создаем диалог с передачей категории (режим редактирования)
        dialog = CategoryDialog(
            session=self.session, on_success=self.refresh_data, category=category
        )

        # Открываем диалог
        cast(Any, self._page).open(dialog)
        cast(Any, self._page).update()

    def confirm_delete(self, category_id: str, name: str):
        """Диалог подтверждения удаления."""

        page = cast(Any, self._page)

        @safe_handler()
        def delete_action(e):
            delete_category(self.session, category_id)
            page.close(dlg)
            self.refresh_data()
            page.open(ft.SnackBar(content=ft.Text(f"Категория '{name}' удалена")))

        def cancel_action(e):
            page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение удаления"),
            content=ft.Text(f"Вы действительно хотите удалить категорию '{name}'?"),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_action),
                ft.TextButton(
                    "Удалить", on_click=delete_action, style=ft.ButtonStyle(color=ft.Colors.ERROR)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dlg)
