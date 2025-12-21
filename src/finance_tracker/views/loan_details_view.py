"""
Экран деталей кредита.

Предоставляет UI для:
- Отображения основной информации о кредите
- Просмотра графика платежей
- История исполнения платежей
- Исполнение платежей
- Досрочное погашение кредита
"""

import flet as ft
from typing import Optional

from finance_tracker.models import (
    LoanDB,
    LoanPaymentDB,
    PaymentStatus,
    LoanStatus
)
from finance_tracker.database import get_db_session
from finance_tracker.services.loan_service import get_loan_by_id
from finance_tracker.services.loan_payment_service import (
    get_payments_by_loan,
    execute_payment,
    early_repayment_full,
    early_repayment_partial
)
from finance_tracker.services.lender_service import get_lender_by_id
from finance_tracker.components.early_repayment_modal import EarlyRepaymentModal
from finance_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class LoanDetailsView(ft.Column):
    """
    Экран деталей кредита.

    Позволяет пользователю:
    - Просматривать основную информацию о кредите
    - Видеть график платежей
    - Просматривать историю исполнения
    - Исполнять платежи
    - Делать досрочное погашение

    Согласно Requirements 10.6, 10.7:
    - Отображает детали кредита с графиком платежей
    - Позволяет исполнять платежи и делать досрочное погашение
    """

    def __init__(self, page: ft.Page, loan_id: str, on_back: callable):
        """
        Инициализация экрана деталей кредита.

        Args:
            page: Страница Flet для отображения UI
            loan_id: ID кредита для отображения
            on_back: Callback для возврата к списку кредитов
        """
        super().__init__(expand=True, spacing=20, alignment=ft.MainAxisAlignment.START)
        self.page = page
        self.loan_id = loan_id
        self.on_back = on_back
        self.loan: Optional[LoanDB] = None

        # Persistent session pattern for View
        self.cm = get_db_session()
        self.session = self.cm.__enter__()

        # Dialogs
        self.execute_payment_dialog = None
        self.early_repayment_dialog = None

        # UI Components
        self._build_ui()
        self.load_loan_details()

    def _build_ui(self):
        """Построение UI компонентов."""
        # Заголовок с кнопкой "Назад"
        self.header = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Назад к списку кредитов",
                    on_click=lambda _: self.on_back()
                ),
                ft.Text("Детали кредита", size=24, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START
        )

        # Карточка основной информации
        self.info_card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Загрузка...", size=16)
                ],
                spacing=10
            ),
            bgcolor=ft.Colors.SURFACE,
            padding=20,
            border_radius=10,
        )

        # Кнопки действий
        self.action_buttons = ft.Row(
            controls=[
                ft.ElevatedButton(
                    text="Редактировать",
                    icon=ft.Icons.EDIT,
                    on_click=self.open_edit_dialog
                ),
                ft.ElevatedButton(
                    text="Досрочное погашение",
                    icon=ft.Icons.PAYMENTS,
                    on_click=self.open_early_repayment_dialog,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE
                ),
            ],
            spacing=10
        )

        # Табы для графика и истории
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="График платежей", icon=ft.Icons.CALENDAR_MONTH),
                ft.Tab(text="История", icon=ft.Icons.HISTORY),
            ],
            on_change=self.on_tab_change,
            expand=True
        )

        # Список платежей
        self.payments_list = ft.ListView(expand=True, spacing=5, padding=10)

        # Статистика по платежам
        self.payment_stats = ft.Container(
            content=ft.Row(
                controls=[],
                spacing=20,
                wrap=True
            ),
            padding=10,
            bgcolor=ft.Colors.SURFACE,
            border_radius=10
        )

        self.controls = [
            self.header,
            ft.Divider(height=1),
            self.info_card,
            self.action_buttons,
            ft.Divider(height=1),
            self.payment_stats,
            self.tabs,
            self.payments_list,
        ]

    def load_loan_details(self):
        """Загрузка деталей кредита из БД."""
        try:
            # Загружаем кредит
            self.loan = get_loan_by_id(self.session, self.loan_id)
            if not self.loan:
                logger.error(f"Кредит ID {self.loan_id} не найден")
                self.show_error("Кредит не найден")
                return

            # Обновляем карточку информации
            self.update_info_card()

            # Загружаем платежи
            self.load_payments()

            # Обновляем статистику
            self.update_payment_stats()

        except Exception as e:
            logger.error(f"Ошибка при загрузке деталей кредита: {e}")
            self.show_error(f"Ошибка при загрузке: {e}")

    def update_info_card(self):
        """Обновление карточки основной информации."""
        if not self.loan:
            return

        # Загружаем займодателя
        lender = get_lender_by_id(self.session, self.loan.lender_id)
        lender_name = lender.name if lender else "Неизвестно"

        # Форматируем суммы
        amount_str = f"{self.loan.amount:,.2f} ₽".replace(",", " ")

        # Рассчитываем остаток долга (упрощённо)
        remaining = self.loan.amount  # TODO: вычесть оплаченные платежи
        remaining_str = f"{remaining:,.2f} ₽".replace(",", " ")

        # Статус
        status_colors = {
            LoanStatus.ACTIVE: ft.Colors.GREEN,
            LoanStatus.PAID_OFF: ft.Colors.BLUE,
            LoanStatus.OVERDUE: ft.Colors.RED
        }
        status_color = status_colors.get(self.loan.status, ft.Colors.GREY)

        self.info_card.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(self.loan.name, size=20, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(
                                self.loan.status.value,
                                size=12,
                                color=ft.Colors.WHITE
                            ),
                            bgcolor=status_color,
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=5
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Divider(height=1),
                self._create_info_row("Займодатель:", lender_name),
                self._create_info_row("Тип:", self.loan.loan_type.value),
                self._create_info_row("Сумма кредита:", amount_str),
                self._create_info_row("Остаток долга:", remaining_str),
                self._create_info_row(
                    "Процентная ставка:",
                    f"{self.loan.interest_rate}%" if self.loan.interest_rate else "—"
                ),
                self._create_info_row(
                    "Дата выдачи:",
                    self.loan.issue_date.strftime("%d.%m.%Y")
                ),
                self._create_info_row(
                    "Дата окончания:",
                    self.loan.end_date.strftime("%d.%m.%Y") if self.loan.end_date else "—"
                ),
                self._create_info_row(
                    "Номер договора:",
                    self.loan.contract_number if self.loan.contract_number else "—"
                ),
            ],
            spacing=5
        )

        if self.page:
            self.info_card.update()

    def _create_info_row(self, label: str, value: str) -> ft.Row:
        """
        Создаёт строку информации.

        Args:
            label: Название поля
            value: Значение поля

        Returns:
            Row с информацией
        """
        return ft.Row(
            controls=[
                ft.Text(label, size=14, color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD),
                ft.Text(value, size=14),
            ],
            spacing=10
        )

    def load_payments(self):
        """Загрузка списка платежей."""
        try:
            # Определяем фильтр по статусу в зависимости от выбранного таба
            if self.tabs.selected_index == 0:  # График платежей
                # Показываем все неоплаченные (PENDING, OVERDUE)
                payments = get_payments_by_loan(self.session, self.loan_id)
                payments = [p for p in payments if p.status in (
                    PaymentStatus.PENDING,
                    PaymentStatus.OVERDUE
                )]
            else:  # История
                # Показываем исполненные
                payments = get_payments_by_loan(self.session, self.loan_id)
                payments = [p for p in payments if p.status in (
                    PaymentStatus.EXECUTED,
                    PaymentStatus.EXECUTED_LATE
                )]

            self.payments_list.controls.clear()

            if not payments:
                self.payments_list.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Нет платежей",
                            size=16,
                            color=ft.Colors.GREY_600
                        ),
                        padding=20,
                        alignment=ft.alignment.center
                    )
                )
            else:
                for payment in payments:
                    self.payments_list.controls.append(
                        self._create_payment_card(payment)
                    )

            if self.page:
                self.payments_list.update()

        except Exception as e:
            logger.error(f"Ошибка при загрузке платежей: {e}")
            self.show_error(f"Ошибка при загрузке платежей: {e}")

    def _create_payment_card(self, payment: LoanPaymentDB) -> ft.Container:
        """
        Создаёт карточку платежа.

        Args:
            payment: Объект платежа

        Returns:
            Container с карточкой платежа
        """
        # Цвета статусов
        status_colors = {
            PaymentStatus.PENDING: ft.Colors.ORANGE,
            PaymentStatus.OVERDUE: ft.Colors.RED,
            PaymentStatus.EXECUTED: ft.Colors.GREEN,
            PaymentStatus.EXECUTED_LATE: ft.Colors.AMBER
        }
        status_color = status_colors.get(payment.status, ft.Colors.GREY)

        # Форматирование дат
        scheduled_date_str = payment.scheduled_date.strftime("%d.%m.%Y")
        executed_date_str = payment.executed_date.strftime("%d.%m.%Y") if payment.executed_date else "—"

        # Форматирование сумм
        total_str = f"{payment.total_amount:,.2f} ₽".replace(",", " ")
        principal_str = f"{payment.principal_amount:,.2f} ₽".replace(",", " ")
        interest_str = f"{payment.interest_amount:,.2f} ₽".replace(",", " ")

        # Кнопка исполнения для неоплаченных
        action_button = None
        if payment.status in (PaymentStatus.PENDING, PaymentStatus.OVERDUE):
            action_button = ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE,
                tooltip="Исполнить платёж",
                icon_color=ft.Colors.GREEN,
                on_click=lambda _, p=payment: self.execute_payment_action(p)
            )

        controls = [
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.PAYMENTS, size=20, color=status_color),
                    ft.Column(
                        controls=[
                            ft.Text(
                                f"Платёж на {scheduled_date_str}",
                                size=14,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                f"Статус: {payment.status.value}",
                                size=12,
                                color=status_color
                            ),
                        ],
                        spacing=2,
                        expand=True
                    ),
                    action_button if action_button else ft.Container(),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(height=1),
            ft.Row(
                controls=[
                    ft.Text(f"Всего: {total_str}", size=13),
                    ft.Text(f"Основной долг: {principal_str}", size=13),
                    ft.Text(f"Проценты: {interest_str}", size=13),
                ],
                spacing=15,
                wrap=True
            ),
        ]

        # Добавляем информацию об исполнении для оплаченных
        if payment.executed_date:
            controls.append(
                ft.Text(
                    f"Исполнено: {executed_date_str}",
                    size=12,
                    color=ft.Colors.GREY_600
                )
            )
            if payment.overdue_days and payment.overdue_days > 0:
                controls.append(
                    ft.Text(
                        f"Просрочка: {payment.overdue_days} дн.",
                        size=12,
                        color=ft.Colors.RED
                    )
                )

        return ft.Container(
            content=ft.Column(
                controls=controls,
                spacing=5
            ),
            bgcolor=ft.Colors.SURFACE,
            padding=15,
            border_radius=10,
            border=ft.border.all(1, status_color),
        )

    def update_payment_stats(self):
        """Обновление статистики по платежам."""
        try:
            payments = get_payments_by_loan(self.session, self.loan_id)

            total_count = len(payments)
            pending = sum(1 for p in payments if p.status == PaymentStatus.PENDING)
            overdue = sum(1 for p in payments if p.status == PaymentStatus.OVERDUE)
            executed = sum(1 for p in payments if p.status in (
                PaymentStatus.EXECUTED,
                PaymentStatus.EXECUTED_LATE
            ))

            total_amount = sum(p.total_amount for p in payments)
            paid_amount = sum(
                p.total_amount for p in payments
                if p.status in (PaymentStatus.EXECUTED, PaymentStatus.EXECUTED_LATE)
            )
            remaining_amount = total_amount - paid_amount

            self.payment_stats.content = ft.Row(
                controls=[
                    self._create_stat_item(
                        "Всего платежей",
                        str(total_count),
                        ft.Icons.PAYMENTS
                    ),
                    self._create_stat_item(
                        "Ожидают оплаты",
                        str(pending),
                        ft.Icons.SCHEDULE,
                        ft.Colors.ORANGE
                    ),
                    self._create_stat_item(
                        "Просрочено",
                        str(overdue),
                        ft.Icons.WARNING,
                        ft.Colors.RED
                    ),
                    self._create_stat_item(
                        "Оплачено",
                        str(executed),
                        ft.Icons.CHECK_CIRCLE,
                        ft.Colors.GREEN
                    ),
                    self._create_stat_item(
                        "Остаток к оплате",
                        f"{remaining_amount:,.2f} ₽".replace(",", " "),
                        ft.Icons.ATTACH_MONEY,
                        ft.Colors.BLUE
                    ),
                ],
                spacing=20,
                wrap=True
            )

            if self.page:
                self.payment_stats.update()

        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {e}")

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
                    ft.Icon(icon, size=20, color=color or ft.Colors.PRIMARY),
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
        )

    def on_tab_change(self, e):
        """Обработчик изменения таба."""
        self.load_payments()

    def execute_payment_action(self, payment: LoanPaymentDB):
        """
        Действие исполнения платежа.

        Args:
            payment: Платёж для исполнения
        """
        try:
            # Исполняем платёж (с датой сегодня по умолчанию)
            execute_payment(self.session, payment.id)

            logger.info(f"Платёж ID {payment.id} успешно исполнен")

            # Обновляем UI
            self.load_loan_details()

            # Показываем уведомление
            if self.page:
                snack = ft.SnackBar(
                    content=ft.Text("Платёж успешно исполнен"),
                    bgcolor=ft.Colors.GREEN
                )
                self.page.open(snack)

        except Exception as e:
            logger.error(f"Ошибка при исполнении платежа: {e}")
            self.show_error(f"Ошибка при исполнении платежа: {e}")

    def open_edit_dialog(self, e):
        """Открыть диалог редактирования кредита."""
        # TODO: реализовать редактирование через LoanModal
        if self.page:
            snack = ft.SnackBar(
                content=ft.Text("Редактирование кредита в разработке"),
                bgcolor=ft.Colors.AMBER
            )
            self.page.open(snack)

    def open_early_repayment_dialog(self, e):
        """Открыть диалог досрочного погашения."""
        try:
            # Создаём и открываем модальное окно
            modal = EarlyRepaymentModal(
                session=self.session,
                loan=self.loan,
                on_repay=self.handle_early_repayment
            )
            modal.open(self.page)

        except Exception as ex:
            logger.error(f"Ошибка при открытии диалога досрочного погашения: {ex}")
            self.show_error(f"Ошибка при открытии диалога: {ex}")

    def handle_early_repayment(self, is_full: bool, amount, repayment_date):
        """
        Обработчик досрочного погашения кредита.

        Args:
            is_full: True для полного погашения, False для частичного
            amount: Сумма погашения (Decimal)
            repayment_date: Дата погашения (date)
        """
        try:
            if is_full:
                # Полное досрочное погашение
                result = early_repayment_full(
                    self.session,
                    self.loan_id,
                    amount,
                    repayment_date
                )

                logger.info(
                    f"Полное досрочное погашение кредита ID {self.loan_id}: "
                    f"отменено платежей={result['cancelled_payments_count']}"
                )

                # Показываем уведомление
                if self.page:
                    snack = ft.SnackBar(
                        content=ft.Text(
                            f"Кредит полностью погашен! Отменено платежей: {result['cancelled_payments_count']}"
                        ),
                        bgcolor=ft.Colors.GREEN
                    )
                    self.page.open(snack)
            else:
                # Частичное досрочное погашение
                result = early_repayment_partial(
                    self.session,
                    self.loan_id,
                    amount,
                    repayment_date
                )

                logger.info(
                    f"Частичное досрочное погашение кредита ID {self.loan_id}: "
                    f"новый остаток={result['new_balance']}"
                )

                # Показываем уведомление с предупреждением
                if self.page:
                    snack = ft.SnackBar(
                        content=ft.Text(
                            f"Частичное погашение выполнено! {result['warning']}"
                        ),
                        bgcolor=ft.Colors.AMBER,
                        duration=5000
                    )
                    self.page.open(snack)

            # Обновляем UI
            self.load_loan_details()

        except ValueError as e:
            logger.error(f"Ошибка валидации при досрочном погашении: {e}")
            self.show_error(str(e))
        except Exception as e:
            logger.error(f"Ошибка при досрочном погашении кредита: {e}")
            self.show_error(f"Ошибка при досрочном погашении: {e}")

    def show_error(self, message: str):
        """
        Показывает сообщение об ошибке.

        Args:
            message: Текст ошибки
        """
        if self.page:
            snack = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.RED
            )
            self.page.open(snack)
    def will_unmount(self):
        """Очистка ресурсов при размонтировании view."""
        if hasattr(self, 'cm') and self.cm is not None:
            try:
                self.cm.__exit__(None, None, None)
                logger.debug("Сессия LoanDetailsView закрыта")
            except Exception as e:
                logger.error(f"Ошибка при закрытии сессии БД в LoanDetailsView: {e}")
