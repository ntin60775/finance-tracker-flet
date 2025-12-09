"""
Экран управления кредитами.

Предоставляет UI для:
- Отображения списка всех кредитов
- Фильтрации по статусу кредита
- Создания и просмотра деталей кредитов
- Отображения статистики по кредитам
"""

import flet as ft
from typing import Optional

from finance_tracker.models.models import LoanDB
from finance_tracker.models.enums import LoanStatus, LoanType
from finance_tracker.database import get_db_session
from finance_tracker.services.loan_service import (
    get_all_loans,
    delete_loan
)
from finance_tracker.services.loan_statistics_service import (
    get_summary_statistics,
    get_monthly_burden_statistics
)
from finance_tracker.services.loan_service import (
    create_loan,
    update_loan
)
from finance_tracker.components.loan_modal import LoanModal
from finance_tracker.views.loan_details_view import LoanDetailsView
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class LoansView(ft.Column):
    """
    Экран управления кредитами.

    Позволяет пользователю:
    - Просматривать список всех кредитов
    - Фильтровать по статусу кредита
    - Создавать новые кредиты
    - Просматривать детали кредита
    - Видеть статистику по кредитам

    Согласно Requirements 10.6, 12.1, 12.2, 12.3, 12.4, 12.6:
    - Отображает список кредитов с возможностью фильтрации
    - Показывает статистику по активным кредитам
    - Позволяет создавать и просматривать кредиты
    """

    def __init__(self, page: ft.Page):
        """
        Инициализация экрана кредитов.

        Args:
            page: Страница Flet для отображения UI
        """
        super().__init__(expand=True, spacing=20, alignment=ft.MainAxisAlignment.START)
        self.page = page
        self.status_filter: Optional[LoanStatus] = None
        self.selected_loan: Optional[LoanDB] = None

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # Modal
        self.loan_modal = LoanModal(
            session=self.session,
            on_save=self.on_create_loan,
            on_update=self.on_update_loan
        )

        # UI Components
        self._build_ui()
        self.load_statistics()
        self.load_loans()

    def _build_ui(self):
        """Построение UI компонентов."""
        # Заголовок и кнопка создания
        self.header = ft.Row(
            controls=[
                ft.Text("Кредиты", size=24, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.ADD,
                    bgcolor=ft.Colors.PRIMARY,
                    icon_color=ft.Colors.ON_PRIMARY,
                    tooltip="Добавить кредит",
                    on_click=self.open_create_dialog
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Статистика
        self.stats_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Загрузка статистики...", size=14)
                ],
                spacing=10
            ),
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
            padding=15,
            border_radius=10,
        )

        # Фильтр по статусу
        self.status_dropdown = ft.Dropdown(
            label="Статус кредита",
            width=250,
            options=[
                ft.dropdown.Option(key="all", text="Все статусы"),
                ft.dropdown.Option(key=LoanStatus.ACTIVE.value, text="Активные"),
                ft.dropdown.Option(key=LoanStatus.PAID_OFF.value, text="Погашенные"),
                ft.dropdown.Option(key=LoanStatus.OVERDUE.value, text="Просроченные"),
            ],
            value="all",
            on_change=self.on_status_filter_change
        )

        # Список кредитов
        self.loans_column = ft.Column(
            controls=[],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        # Собираем все компоненты
        self.controls = [
            self.header,
            self.stats_card,
            self.status_dropdown,
            ft.Divider(height=1),
            self.loans_column
        ]

    def load_statistics(self):
        """Загрузка статистики по кредитам."""
        try:
            # Получаем общую статистику
            summary = get_summary_statistics(self.session)
            burden = get_monthly_burden_statistics(self.session)

            # Форматируем статистику
            stats_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self._create_stat_item(
                                "Активных кредитов",
                                str(summary["total_active_loans"]),
                                ft.Icons.ACCOUNT_BALANCE
                            ),
                            self._create_stat_item(
                                "Общая сумма",
                                f"{summary['total_active_amount']:,.2f} ₽",
                                ft.Icons.PAYMENTS
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Row(
                        controls=[
                            self._create_stat_item(
                                "Ежемесячные платежи",
                                f"{summary['monthly_payments_sum']:,.2f} ₽",
                                ft.Icons.CALENDAR_MONTH
                            ),
                            self._create_stat_item(
                                "Кредитная нагрузка",
                                f"{burden['burden_percent']:.1f}%",
                                ft.Icons.TRENDING_UP,
                                color=ft.Colors.GREEN if burden["is_healthy"] else ft.Colors.RED
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                ],
                spacing=15
            )

            self.stats_card.content = stats_content
            self.page.update()

            logger.info(f"Загружена статистика: активных кредитов={summary['total_active_loans']}")

        except Exception as e:
            logger.error(f"Ошибка при загрузке статистики: {e}")
            self.stats_card.content = ft.Text(
                "Не удалось загрузить статистику",
                color=ft.Colors.ERROR
            )
            self.page.update()

    def _create_stat_item(
        self,
        label: str,
        value: str,
        icon: str,
        color: Optional[str] = None
    ) -> ft.Container:
        """
        Создаёт элемент статистики.

        Args:
            label: Название показателя
            value: Значение показателя
            icon: Иконка
            color: Цвет значения (опционально)

        Returns:
            Container с элементом статистики
        """
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=20, color=ft.Colors.PRIMARY),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=12, color=ft.Colors.GREY_700),
                            ft.Text(
                                value,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=color or ft.Colors.ON_SURFACE
                            ),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.START
                    )
                ],
                spacing=10
            ),
            padding=10,
            expand=True
        )

    def load_loans(self):
        """Загрузка списка кредитов из БД."""
        try:
            # Получаем кредиты с учетом фильтра
            loans = get_all_loans(
                self.session,
                status=self.status_filter
            )

            # Очищаем список
            self.loans_column.controls.clear()

            if not loans:
                self.loans_column.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Нет кредитов. Добавьте первый!",
                            size=16,
                            color=ft.Colors.GREY_400,
                            text_align=ft.TextAlign.CENTER
                        ),
                        alignment=ft.alignment.center,
                        padding=40
                    )
                )
            else:
                for loan in loans:
                    self.loans_column.controls.append(
                        self._create_loan_card(loan)
                    )

            self.page.update()
            logger.info(f"Загружено {len(loans)} кредитов")

        except Exception as e:
            logger.error(f"Ошибка при загрузке кредитов: {e}")
            self._show_error(f"Не удалось загрузить кредиты: {str(e)}")

    def _create_loan_card(self, loan: LoanDB) -> ft.Container:
        """
        Создаёт карточку кредита.

        Args:
            loan: Объект кредита из БД

        Returns:
            Container с информацией о кредите
        """
        # Иконка по типу кредита
        type_icon_map = {
            LoanType.CONSUMER: ft.Icons.SHOPPING_CART,
            LoanType.MORTGAGE: ft.Icons.HOME,
            LoanType.MICROLOAN: ft.Icons.MONEY,
            LoanType.PERSONAL: ft.Icons.PERSON,
            LoanType.OTHER: ft.Icons.HELP_OUTLINE,
        }

        # Название типа на русском
        type_name_map = {
            LoanType.CONSUMER: "Потребительский",
            LoanType.MORTGAGE: "Ипотека",
            LoanType.MICROLOAN: "Микрокредит",
            LoanType.PERSONAL: "Личный займ",
            LoanType.OTHER: "Другое",
        }

        # Цвет статуса
        status_color_map = {
            LoanStatus.ACTIVE: ft.Colors.GREEN,
            LoanStatus.PAID_OFF: ft.Colors.BLUE,
            LoanStatus.OVERDUE: ft.Colors.RED,
        }

        # Название статуса на русском
        status_name_map = {
            LoanStatus.ACTIVE: "Активный",
            LoanStatus.PAID_OFF: "Погашен",
            LoanStatus.OVERDUE: "Просрочен",
        }

        loan_icon = type_icon_map.get(loan.loan_type, ft.Icons.HELP_OUTLINE)
        loan_type_name = type_name_map.get(loan.loan_type, loan.loan_type.value)
        status_color = status_color_map.get(loan.status, ft.Colors.GREY)
        status_name = status_name_map.get(loan.status, loan.status.value)

        # Основная информация
        info_column = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(loan.name, size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(status_name, size=12, color=ft.Colors.WHITE),
                            bgcolor=status_color,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=12
                        )
                    ],
                    spacing=10
                ),
                ft.Text(
                    f"{loan.lender.name} • {loan_type_name}",
                    size=14,
                    color=ft.Colors.GREY_700
                ),
            ],
            spacing=5
        )

        # Финансовые показатели
        amount_info = ft.Column(
            controls=[
                ft.Text(
                    f"{loan.amount:,.2f} ₽",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PRIMARY
                ),
                ft.Text(
                    f"Ставка: {loan.interest_rate:.2f}%" if loan.interest_rate else "Без процентов",
                    size=12,
                    color=ft.Colors.GREY_600
                ),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.END
        )

        # Даты
        dates_row = ft.Row(
            controls=[
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=ft.Colors.GREY_600),
                ft.Text(
                    f"{loan.issue_date.strftime('%d.%m.%Y')}",
                    size=12,
                    color=ft.Colors.GREY_600
                ),
                ft.Text("→", size=12, color=ft.Colors.GREY_600),
                ft.Text(
                    f"{loan.end_date.strftime('%d.%m.%Y')}" if loan.end_date else "Бессрочно",
                    size=12,
                    color=ft.Colors.GREY_600
                ),
            ],
            spacing=5
        )

        # Кнопки действий
        actions_row = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.VISIBILITY,
                    icon_size=20,
                    tooltip="Просмотр деталей",
                    on_click=lambda e, loan=loan: self.open_loan_details(loan)
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_size=20,
                    icon_color=ft.Colors.ERROR,
                    tooltip="Удалить",
                    on_click=lambda e, loan=loan: self.confirm_delete_loan(loan)
                ),
            ],
            spacing=5
        )

        # Собираем карточку
        card_content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(loan_icon, size=40, color=ft.Colors.PRIMARY),
                        ft.Container(content=info_column, expand=True),
                        amount_info
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START
                ),
                dates_row,
                ft.Divider(height=1),
                ft.Row(
                    controls=[
                        ft.Text(
                            loan.description or "Нет описания",
                            size=12,
                            color=ft.Colors.GREY_600,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True
                        ),
                        actions_row
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            ],
            spacing=10
        )

        return ft.Container(
            content=card_content,
            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
            padding=15,
            border_radius=10,
            on_click=lambda e, loan=loan: self.open_loan_details(loan)
        )

    def on_status_filter_change(self, e):
        """Обработчик изменения фильтра по статусу кредита."""
        selected = self.status_dropdown.value
        if selected == "all":
            self.status_filter = None
        else:
            try:
                self.status_filter = LoanStatus(selected)
            except ValueError:
                self.status_filter = None

        self.load_loans()

    def on_create_loan(
        self,
        lender_id: str,
        name: str,
        loan_type: LoanType,
        amount: float,
        issue_date,
        interest_rate: Optional[float],
        end_date: Optional,
        contract_number: Optional[str],
        description: Optional[str]
    ):
        """
        Callback для создания кредита из модального окна.

        Args:
            lender_id: ID займодателя
            name: Название кредита
            loan_type: Тип кредита
            amount: Сумма кредита
            issue_date: Дата выдачи
            interest_rate: Процентная ставка
            end_date: Дата окончания
            contract_number: Номер договора
            description: Описание
        """
        try:
            loan = create_loan(
                session=self.session,
                name=name,
                lender_id=lender_id,
                loan_type=loan_type,
                amount=amount,
                issue_date=issue_date,
                interest_rate=interest_rate,
                end_date=end_date,
                contract_number=contract_number,
                description=description
            )

            logger.info(f"Кредит создан: {loan.name} (ID {loan.id})")
            self._show_success(f"Кредит '{loan.name}' успешно создан")
            self.load_statistics()
            self.load_loans()

        except ValueError as ve:
            logger.warning(f"Ошибка валидации при создании кредита: {ve}")
            self._show_error(str(ve))
        except Exception as ex:
            logger.error(f"Неожиданная ошибка при создании кредита: {ex}")
            self._show_error(f"Не удалось создать кредит: {str(ex)}")

    def on_update_loan(
        self,
        loan_id: str,
        name: Optional[str],
        loan_type: Optional[LoanType],
        amount: Optional[float],
        issue_date: Optional,
        interest_rate: Optional[float],
        end_date: Optional,
        contract_number: Optional[str],
        description: Optional[str]
    ):
        """
        Callback для обновления кредита из модального окна.

        Args:
            loan_id: ID кредита
            name: Название кредита
            loan_type: Тип кредита
            amount: Сумма кредита
            issue_date: Дата выдачи
            interest_rate: Процентная ставка
            end_date: Дата окончания
            contract_number: Номер договора
            description: Описание
        """
        try:
            updated_loan = update_loan(
                session=self.session,
                loan_id=loan_id,
                name=name,
                loan_type=loan_type,
                amount=amount,
                issue_date=issue_date,
                interest_rate=interest_rate,
                end_date=end_date,
                contract_number=contract_number,
                description=description
            )

            logger.info(f"Кредит обновлён: {updated_loan.name} (ID {updated_loan.id})")
            self._show_success(f"Кредит '{updated_loan.name}' успешно обновлён")
            self.load_statistics()
            self.load_loans()

        except ValueError as ve:
            logger.warning(f"Ошибка валидации при обновлении кредита: {ve}")
            self._show_error(str(ve))
        except Exception as ex:
            logger.error(f"Неожиданная ошибка при обновлении кредита: {ex}")
            self._show_error(f"Не удалось обновить кредит: {str(ex)}")

    def open_create_dialog(self, e):
        """Открывает диалог создания нового кредита."""
        self.selected_loan = None
        self.loan_modal.open(self.page, loan=None)

    def open_loan_details(self, loan: LoanDB):
        """
        Открывает экран деталей кредита.

        Args:
            loan: Кредит для просмотра
        """
        try:
            # Создаём LoanDetailsView и показываем его вместо списка
            details_view = LoanDetailsView(
                page=self.page,
                loan_id=loan.id,
                on_back=self.return_from_details
            )

            # Сохраняем текущие контролы для возврата
            self._saved_controls = self.controls.copy()

            # Заменяем контролы на LoanDetailsView
            self.controls.clear()
            self.controls.extend(details_view.controls)

            if self.page:
                self.update()

            logger.info(f"Открыт экран деталей кредита ID {loan.id}")

        except Exception as e:
            logger.error(f"Ошибка при открытии деталей кредита: {e}")
            self._show_error(f"Не удалось открыть детали кредита: {str(e)}")

    def return_from_details(self):
        """Возврат из экрана деталей к списку кредитов."""
        try:
            # Восстанавливаем сохранённые контролы
            if hasattr(self, '_saved_controls'):
                self.controls.clear()
                self.controls.extend(self._saved_controls)
                delattr(self, '_saved_controls')

            # Перезагружаем данные
            self.load_statistics()
            self.load_loans()

            if self.page:
                self.update()

            logger.info("Возврат к списку кредитов")

        except Exception as e:
            logger.error(f"Ошибка при возврате к списку: {e}")
            self._show_error(f"Ошибка при возврате: {str(e)}")

    def confirm_delete_loan(self, loan: LoanDB):
        """
        Показывает диалог подтверждения удаления кредита.

        Args:
            loan: Кредит для удаления
        """
        def delete(e):
            try:
                # По умолчанию сохраняем транзакции при удалении
                delete_loan(self.session, loan.id, keep_transactions=True)
                logger.info(f"Кредит удалён: {loan.name} (ID {loan.id})")
                self._show_success(f"Кредит '{loan.name}' успешно удалён")
                confirm_dialog.open = False
                self.page.update()
                self.load_statistics()
                self.load_loans()

            except ValueError as ve:
                logger.warning(f"Ошибка при удалении кредита: {ve}")
                self._show_error(str(ve))
            except Exception as ex:
                logger.error(f"Неожиданная ошибка при удалении кредита: {ex}")
                self._show_error(f"Не удалось удалить кредит: {str(ex)}")

        def cancel(e):
            confirm_dialog.open = False
            self.page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтвердите удаление"),
            content=ft.Text(
                f"Вы уверены, что хотите удалить кредит '{loan.name}'?\n\n"
                "Связанные транзакции будут сохранены.",
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

        self.page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        self.page.update()

    def _show_success(self, message: str):
        """Показывает snackbar с сообщением об успехе."""
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.ON_PRIMARY),
            bgcolor=ft.Colors.GREEN,
            duration=3000
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _show_error(self, message: str):
        """Показывает snackbar с сообщением об ошибке."""
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.ON_ERROR),
            bgcolor=ft.Colors.ERROR,
            duration=5000
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def _show_info(self, message: str):
        """Показывает snackbar с информационным сообщением."""
        snack = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.BLUE,
            duration=3000
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def will_unmount(self):
        """Очистка ресурсов при размонтировании view."""
        if hasattr(self, 'cm') and self.cm is not None:
            try:
                self.cm.__exit__(None, None, None)
            except Exception as e:
                logger.error(f"Ошибка при закрытии сессии БД: {e}")