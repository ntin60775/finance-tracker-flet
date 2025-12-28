import datetime
from typing import List, Any, Tuple, Dict, Optional, Callable

import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models.models import TransactionCreate, TransactionUpdate, TransactionDB, PlannedOccurrence, PendingPaymentCreate, PlannedTransactionCreate
from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget
from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.components.execute_occurrence_modal import ExecuteOccurrenceModal
from finance_tracker.components.execute_pending_payment_modal import ExecutePendingPaymentModal
from finance_tracker.components.pending_payment_modal import PendingPaymentModal
from finance_tracker.components.planned_transaction_modal import PlannedTransactionModal
from finance_tracker.utils.logger import get_logger
from finance_tracker.models.models import (
    PendingPaymentExecute,
    PendingPaymentCancel,
    LoanPaymentDB
)
from finance_tracker.views.home_presenter import HomePresenter
from finance_tracker.views.interfaces import IHomeViewCallbacks
from decimal import Decimal

logger = get_logger(__name__)


class HomeView(ft.Column, IHomeViewCallbacks):
    """
    Главный экран приложения (Календарь + Транзакции + Плановые операции).

    Состоит из трёх колонок:
    - Левая (2/7 ширины): Виджет плановых транзакций
    - Центральная (3/7 ширины): Календарь вверху, легенда и отложенные платежи внизу
    - Правая (2/7 ширины): Список транзакций выбранного дня и кнопка добавления

    Реализует паттерн MVP: View делегирует бизнес-логику в Presenter,
    получает обновления через IHomeViewCallbacks.
    
    Args:
        page: Объект страницы Flet для управления UI
        session: Активная сессия БД для работы с данными
        navigate_callback: Опциональный callback для навигации между разделами приложения.
                          Принимает индекс раздела (int) для переключения.
    """

    def __init__(
        self, 
        page: ft.Page, 
        session: Session,
        navigate_callback: Optional[Callable[[int], None]] = None
    ):
        super().__init__(expand=True, alignment=ft.MainAxisAlignment.START)
        self.page = page
        self.session = session
        self.selected_date = datetime.date.today()
        self.navigate_callback = navigate_callback

        # Создаем Presenter с инжекцией зависимостей
        self.presenter = HomePresenter(session, self)
        
        # UI Components
        self.calendar_widget = CalendarWidget(
            on_date_selected=self.on_date_selected,
            initial_date=self.selected_date
        )
        
        self.transactions_panel = TransactionsPanel(
            date_obj=self.selected_date,
            transactions=[],
            on_add_transaction=self.open_add_transaction_modal,
            on_execute_occurrence=self.on_execute_occurrence,
            on_skip_occurrence=self.on_skip_occurrence,
            on_execute_pending_payment=self.on_execute_payment,
            on_execute_loan_payment=self.on_execute_loan_payment,
            on_edit_transaction=self.on_edit_transaction,
            on_delete_transaction=self.on_delete_transaction
        )
        
        # Вычисляем ширину календаря для адаптивности легенды
        # Центральная колонка занимает 3/7 от общей ширины страницы
        # Вычитаем отступы и разделители для более точного расчета
        calendar_width = self._calculate_calendar_width()
        self.legend = CalendarLegend(calendar_width=calendar_width)

        self.planned_widget = PlannedTransactionsWidget(
            session=self.session,
            on_execute=self.on_execute_occurrence,
            on_skip=self.on_skip_occurrence,
            on_show_all=self.on_show_all_occurrences,
            on_add_planned_transaction=self.on_add_planned_transaction,
            on_occurrence_click=self.on_occurrence_clicked
        )

        self.pending_payments_widget = PendingPaymentsWidget(
            session=self.session,
            on_execute=self.on_execute_payment,
            on_cancel=self.on_cancel_payment,
            on_delete=self.on_delete_payment,
            on_show_all=self.on_show_all_payments,
            on_add_payment=self.on_add_pending_payment
        )

        # Modals
        self.transaction_modal = TransactionModal(
            session=self.session,
            on_save=self.on_transaction_saved,
            on_update=self.on_transaction_updated
        )

        self.execute_occurrence_modal = ExecuteOccurrenceModal(
            session=self.session,
            on_execute=self.on_occurrence_executed_confirm,
            on_skip=self.on_occurrence_skipped_confirm
        )

        self.execute_payment_modal = ExecutePendingPaymentModal(
            session=self.session,
            on_execute=self.on_payment_executed_confirm
        )

        self.payment_modal = PendingPaymentModal(
            session=self.session,
            on_save=self.on_pending_payment_saved,
            on_update=lambda _, __: None  # Не используется на главном экране
        )

        self.planned_transaction_modal = PlannedTransactionModal(
            session=self.session,
            on_save=self.on_planned_transaction_saved
        )

        # Layout
        self.controls = [
            ft.Row(
                controls=[
                    # Левая колонка (2/7): Плановые транзакции
                    ft.Column(
                        controls=[
                            self.planned_widget
                        ],
                        expand=2,
                        spacing=20,
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.VerticalDivider(width=1),
                    # Центральная колонка (3/7): Календарь вверху, легенда и отложенные платежи внизу
                    ft.Column(
                        controls=[
                            self.calendar_widget,
                            self.legend,
                            self.pending_payments_widget
                        ],
                        expand=3,
                        spacing=20,
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.VerticalDivider(width=1),
                    # Правая колонка (2/7): Панель транзакций
                    ft.Column(
                        controls=[
                            self.transactions_panel
                        ],
                        expand=2,
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.START
                    )
                ],
                expand=True,
                spacing=20,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        ]

        logger.info("HomeView инициализирован")

    def _calculate_calendar_width(self) -> int:
        """
        Вычисляет ширину календаря на основе размеров страницы и layout.
        
        Returns:
            Приблизительная ширина календаря в пикселях
        """
        try:
            # Получаем ширину страницы
            if hasattr(self.page, 'width') and self.page.width:
                page_width = self.page.width
            else:
                # Fallback к стандартной ширине
                page_width = 1200
            
            # Центральная колонка занимает 3/7 от общей ширины
            # Левая колонка: expand=2, Центральная: expand=3, Правая: expand=2
            # Общий expand = 2 + 3 + 2 = 7
            center_column_ratio = 3 / 7
            
            # Вычитаем отступы и разделители
            # spacing между колонками: 20px * 2 = 40px
            # VerticalDivider: width=1 * 2 = 2px
            # padding контейнера: примерно 20px с каждой стороны = 40px
            total_spacing = 40 + 2 + 40  # 82px
            
            # Вычисляем доступную ширину для колонок
            available_width = page_width - total_spacing
            
            # Ширина центральной колонки
            center_column_width = int(available_width * center_column_ratio)
            
            # Календарь занимает почти всю ширину центральной колонки
            # Вычитаем внутренние отступы колонки (примерно 20px)
            calendar_width = center_column_width - 20
            
            logger.debug(f"Вычислена ширина календаря: {calendar_width}px "
                        f"(страница: {page_width}px, центральная колонка: {center_column_width}px)")
            
            return max(calendar_width, 300)  # Минимальная ширина 300px
            
        except Exception as e:
            logger.error(f"Ошибка при вычислении ширины календаря: {e}")
            return 500  # Fallback к безопасному значению

    def update_calendar_width(self):
        """
        Обновляет ширину календаря в легенде при изменении размеров окна.
        
        Этот метод может быть вызван при изменении размеров окна
        для обновления адаптивности легенды.
        """
        try:
            new_width = self._calculate_calendar_width()
            if hasattr(self, 'legend') and self.legend:
                self.legend.update_calendar_width(new_width)
                logger.debug(f"Ширина календаря в легенде обновлена до {new_width}px")
        except Exception as e:
            logger.error(f"Ошибка при обновлении ширины календаря в легенде: {e}")

    def will_unmount(self):
        """Вызывается при удалении со страницы."""
        # Session НЕ закрывается - это ответственность создателя View
        logger.debug("HomeView размонтирован")

    def did_mount(self):
        """Вызывается после монтирования на страницу."""
        try:
            # Обновляем ширину календаря после монтирования, когда page.width доступен
            self.update_calendar_width()
            logger.debug("HomeView смонтирован, ширина календаря обновлена")
        except Exception as e:
            logger.error(f"Ошибка при монтировании HomeView: {e}")

    # ========== IHomeViewCallbacks Implementation ==========

    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        """Обновить данные календаря."""
        self.calendar_widget.set_transactions(transactions, occurrences)
        self.update()

    def update_transactions(self, date_obj: datetime.date, transactions: List[Any], occurrences: List[Any]) -> None:
        """Обновить список транзакций для выбранной даты."""
        self.selected_date = date_obj
        self.transactions_panel.set_data(date_obj, transactions, occurrences)
        self.update()

    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None:
        """Обновить список плановых операций."""
        self.planned_widget.set_occurrences(occurrences)
        self.update()

    def update_pending_payments(self, payments: List[Any], statistics: Dict[str, Any]) -> None:
        """Обновить список отложенных платежей."""
        self.pending_payments_widget.set_payments(payments, statistics)
        self.update()

    def show_message(self, message: str) -> None:
        """Показать информационное сообщение."""
        self.page.open(ft.SnackBar(content=ft.Text(message)))

    def show_error(self, error: str) -> None:
        """Показать сообщение об ошибке."""
        self.page.open(ft.SnackBar(content=ft.Text(error), bgcolor=ft.Colors.ERROR))
    
    def update_calendar_selection(self, date_obj: datetime.date) -> None:
        """Обновить выделение даты в календаре."""
        self.calendar_widget.select_date(date_obj)

    # ========== UI Event Handlers (делегируют в Presenter) ==========

    def on_date_selected(self, date_obj: datetime.date):
        """Обработка выбора даты в календаре - делегирует в Presenter."""
        self.presenter.on_date_selected(date_obj)

    def open_add_transaction_modal(self):
        """Открытие модального окна добавления транзакции."""
        try:
            logger.debug(f"Открытие модального окна добавления транзакции для даты: {self.selected_date}")
            
            if not self.page:
                logger.error("Page не инициализирована для открытия модального окна")
                return
                
            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return
                
            self.transaction_modal.open(self.page, self.selected_date)
            logger.info("Модальное окно добавления транзакции успешно открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна добавления транзакции: {e}", exc_info=True)
            if self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Не удалось открыть форму добавления транзакции"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")
    
    def _close_bottom_sheet(self):
        """Закрытие BottomSheet."""
        try:
            if hasattr(self, 'bottom_sheet'):
                self.page.close(self.bottom_sheet)
                logger.info("BottomSheet закрыт")
        except Exception as e:
            logger.error(f"Ошибка при закрытии BottomSheet: {e}")
    
    def _open_real_modal_from_sheet(self):
        """Открытие настоящего модального окна транзакции из BottomSheet."""
        try:
            # Закрываем BottomSheet
            self._close_bottom_sheet()
            
            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return
                
            self.transaction_modal.open(self.page, self.selected_date)
            logger.info("Настоящее модальное окно добавления транзакции открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии настоящего модального окна: {e}", exc_info=True)

    def on_transaction_saved(self, data: TransactionCreate):
        """Обработка сохранения новой транзакции - делегирует в Presenter."""
        self.presenter.create_transaction(data)

    def on_edit_transaction(self, transaction: TransactionDB):
        """Открытие модального окна редактирования транзакции."""
        try:
            logger.debug(f"Открытие модального окна редактирования для транзакции: {transaction.id}")
            
            if not self.page:
                logger.error("Page не инициализирована для открытия модального окна редактирования")
                return
                
            if not self.transaction_modal:
                logger.error("TransactionModal не инициализирован")
                return
                
            self.transaction_modal.open_edit(self.page, transaction)
            logger.info("Модальное окно редактирования транзакции успешно открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна редактирования транзакции: {e}", exc_info=True)
            if self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Не удалось открыть форму редактирования транзакции"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_delete_transaction(self, transaction: TransactionDB):
        """Показ диалога подтверждения удаления транзакции."""
        try:
            logger.debug(f"Запрос на удаление транзакции: {transaction.id}")
            
            # Получаем имя категории для отображения
            category_name = "Без категории"
            try:
                if transaction.category:
                    category_name = transaction.category.name
            except Exception:
                pass

            def confirm_delete(e):
                self.page.close(dialog)
                # Делегируем в Presenter
                self.presenter.delete_transaction(transaction.id)

            def cancel_delete(e):
                self.page.close(dialog)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Удалить транзакцию?"),
                content=ft.Column(
                    controls=[
                        ft.Text(f"Категория: {category_name}"),
                        ft.Text(f"Сумма: {transaction.amount:.2f} ₽"),
                        ft.Text(f"Описание: {transaction.description or 'Не указано'}"),
                        ft.Text(f"Дата: {transaction.transaction_date.strftime('%d.%m.%Y')}"),
                        ft.Divider(),
                        ft.Text("Это действие нельзя отменить!", color=ft.Colors.ERROR, weight=ft.FontWeight.BOLD),
                    ],
                    tight=True,
                    spacing=10,
                ),
                actions=[
                    ft.TextButton("Отмена", on_click=cancel_delete),
                    ft.ElevatedButton(
                        "Удалить", 
                        on_click=confirm_delete, 
                        bgcolor=ft.Colors.ERROR,
                        color=ft.Colors.ON_ERROR
                    ),
                ],
            )

            # Используем page.open() вместо page.dialog
            self.page.open(dialog)
            
            logger.info("Диалог подтверждения удаления транзакции показан")
            
        except Exception as e:
            logger.error(f"Ошибка при показе диалога удаления транзакции: {e}", exc_info=True)
            if self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Ошибка при открытии диалога удаления"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_transaction_updated(self, transaction_id: str, data: TransactionUpdate):
        """Обработка сохранения изменений транзакции - делегирует в Presenter."""
        try:
            logger.debug(f"Обработка обновления транзакции: {transaction_id}")
            self.presenter.update_transaction(transaction_id, data)
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления транзакции: {e}", exc_info=True)
            if self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Ошибка при сохранении изменений транзакции"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_execute_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для исполнения планового вхождения."""
        self.execute_occurrence_modal.open_execute(self.page, occurrence)

    def on_skip_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для пропуска планового вхождения."""
        self.execute_occurrence_modal.open_skip(self.page, occurrence)

    def on_occurrence_executed_confirm(self, occurrence: PlannedOccurrence, date: datetime.date, amount: float):
        """Подтверждение исполнения вхождения - делегирует в Presenter."""
        self.presenter.execute_occurrence(occurrence, date, amount)

    def on_occurrence_skipped_confirm(self, occurrence: PlannedOccurrence, reason: str):
        """Подтверждение пропуска вхождения - делегирует в Presenter."""
        self.presenter.skip_occurrence(occurrence, reason)

    def on_occurrence_clicked(self, occurrence: PlannedOccurrence):
        """
        Обработка клика на плановое вхождение в обзорном виджете.
        
        Переключает календарь на дату вхождения для отображения
        связанных транзакций в правой панели.
        
        Args:
            occurrence: Плановое вхождение, на которое кликнули.
        """
        try:
            logger.debug(
                f"Обработка клика на вхождение: {occurrence.id}, "
                f"дата: {occurrence.occurrence_date}"
            )
            # Делегируем в Presenter для обновления выбранной даты
            self.presenter.on_date_selected(occurrence.occurrence_date)
            logger.info(
                f"Календарь переключён на дату вхождения: {occurrence.occurrence_date}"
            )
        except Exception as e:
            logger.error(
                f"Ошибка при обработке клика на вхождение: {e}",
                exc_info=True
            )
            self.show_error("Не удалось переключить календарь на дату вхождения")

    def on_show_all_occurrences(self):
        """Переход к разделу всех плановых транзакций."""
        if self.navigate_callback:
            try:
                self.navigate_callback(1)
                logger.info("Переход к разделу плановых транзакций")
            except Exception as e:
                logger.error(f"Ошибка при навигации к плановым транзакциям: {e}")
        else:
            logger.warning("Метод навигации не доступен в HomeView")

    def on_execute_payment(self, payment):
        """Открытие модального окна для исполнения отложенного платежа."""
        self.execute_payment_modal.open(self.page, payment)

    def on_cancel_payment(self, payment):
        """Отмена отложенного платежа."""
        # Показываем диалог с подтверждением и полем для причины
        reason_field = ft.TextField(
            label="Причина отмены (опционально)",
            multiline=True,
            max_lines=3
        )

        def confirm_cancel(e):
            reason = reason_field.value or None
            self.page.close(dialog)
            # Делегируем в Presenter
            self.presenter.cancel_pending_payment(payment.id, reason)

        def cancel_dialog(e):
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Отменить платёж?"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Платёж: {payment.description}"),
                    ft.Text(f"Сумма: {payment.amount:.2f} ₽"),
                    ft.Divider(),
                    reason_field,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_dialog),
                ft.ElevatedButton("Отменить платёж", on_click=confirm_cancel),
            ],
        )

        self.page.open(dialog)

    def on_delete_payment(self, payment_id: int):
        """Удаление отложенного платежа."""
        def confirm_delete(e):
            self.page.close(dialog)
            # Делегируем в Presenter
            self.presenter.delete_pending_payment(payment_id)

        def cancel_delete(e):
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удалить платёж?"),
            content=ft.Text("Это действие нельзя отменить!"),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_delete),
                ft.ElevatedButton("Удалить", on_click=confirm_delete, bgcolor=ft.Colors.ERROR),
            ],
        )

        self.page.open(dialog)

    def on_payment_executed_confirm(self, payment_id: int, executed_amount: float, executed_date: datetime.date):
        """Подтверждение исполнения отложенного платежа - делегирует в Presenter."""
        self.presenter.execute_pending_payment(payment_id, executed_amount, executed_date)

    def on_show_all_payments(self):
        """Переход к разделу всех отложенных платежей."""
        try:
            logger.info("Переход к разделу отложенных платежей")
            
            # Проверяем наличие page
            if not self.page:
                logger.error("Page не инициализирована")
                return
            
            # Проверяем наличие метода навигации в MainWindow
            # MainWindow должен быть доступен через page.controls
            main_window = None
            if hasattr(self.page, 'controls') and self.page.controls:
                for control in self.page.controls:
                    if hasattr(control, 'navigate'):
                        main_window = control
                        break
            
            if main_window and hasattr(main_window, 'navigate'):
                # Вызываем метод навигации MainWindow
                # Индекс 3 соответствует разделу "Отложенные платежи"
                main_window.navigate(3)
                logger.info("Навигация к разделу отложенных платежей выполнена")
            else:
                # Fallback: показываем SnackBar если навигация не реализована
                logger.warning("Навигация к разделу отложенных платежей не реализована")
                self.page.open(ft.SnackBar(
                    content=ft.Text("Раздел 'Отложенные платежи' в разработке")
                ))
                
        except Exception as e:
            logger.error(f"Ошибка при переходе к разделу отложенных платежей: {e}", exc_info=True)
            if self.page:
                try:
                    self.page.open(ft.SnackBar(
                        content=ft.Text("Ошибка при переходе к разделу"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def on_add_pending_payment(self):
        """Открытие модального окна добавления отложенного платежа."""
        try:
            logger.debug("Открытие модального окна добавления отложенного платежа")
            
            if not self.page:
                logger.error("Page не инициализирована")
                return
                
            if not self.payment_modal:
                logger.error("PendingPaymentModal не инициализирован")
                return
                
            self.payment_modal.open(self.page)
            logger.info("Модальное окно добавления отложенного платежа открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
            if self.page:
                self.page.open(ft.SnackBar(
                    content=ft.Text("Не удалось открыть форму добавления платежа"),
                    bgcolor=ft.Colors.ERROR
                ))

    def on_pending_payment_saved(self, data: PendingPaymentCreate):
        """Обработка сохранения нового отложенного платежа."""
        self.presenter.create_pending_payment(data)

    def on_add_planned_transaction(self):
        """
        Открытие модального окна добавления плановой транзакции.
        
        Вызывается при нажатии кнопки "+" в виджете плановых транзакций.
        """
        try:
            logger.debug("Открытие модального окна добавления плановой транзакции")
            
            if not self.page:
                logger.error("Page не инициализирована")
                return
                
            self.planned_transaction_modal.open(self.page, self.selected_date)
            logger.info("Модальное окно добавления плановой транзакции открыто")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}", exc_info=True)
            self.show_error("Не удалось открыть форму добавления плановой транзакции")

    def on_planned_transaction_saved(self, data: PlannedTransactionCreate):
        """
        Обработка сохранения новой плановой транзакции.
        
        Args:
            data: Данные для создания плановой транзакции.
        """
        self.presenter.create_planned_transaction(data)

    def on_execute_loan_payment(self, payment: LoanPaymentDB):
        """Исполнение платежа по кредиту."""
        # Показываем диалог с подтверждением
        amount_field = ft.TextField(
            label="Сумма платежа",
            value=str(float(payment.total_amount)),
            keyboard_type=ft.KeyboardType.NUMBER,
            suffix_text="₽"
        )

        date_field = ft.TextField(
            label="Дата исполнения",
            value=datetime.date.today().strftime("%Y-%m-%d"),
            hint_text="YYYY-MM-DD"
        )

        def confirm_execute(e):
            # Валидация суммы
            try:
                amount = Decimal(amount_field.value)
                if amount <= 0:
                    raise ValueError("Сумма должна быть больше 0")
            except (ValueError, Exception) as ex:
                self.page.open(ft.SnackBar(content=ft.Text(f"Некорректная сумма: {ex}")))
                return

            # Валидация даты
            try:
                exec_date = datetime.datetime.strptime(date_field.value, "%Y-%m-%d").date()
            except ValueError:
                self.page.open(ft.SnackBar(content=ft.Text("Некорректный формат даты (ожидается YYYY-MM-DD)")))
                return

            self.page.close(dialog)
            # Делегируем в Presenter
            self.presenter.execute_loan_payment(payment, amount, exec_date)

        try:
            loan_name = payment.loan.name if payment.loan else "Неизвестный кредит"
        except Exception:
            loan_name = "Неизвестный кредит"

        def cancel_execute(e):
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Исполнить платёж по кредиту"),
            content=ft.Column(
                controls=[
                    ft.Text(f"Кредит: {loan_name}"),
                    ft.Text(f"Плановая сумма: {payment.total_amount:.2f} ₽"),
                    ft.Divider(),
                    amount_field,
                    date_field,
                ],
                tight=True,
                spacing=10,
                width=400,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_execute),
                ft.ElevatedButton("Исполнить", on_click=confirm_execute, bgcolor=ft.Colors.PRIMARY),
            ],
        )

        self.page.open(dialog)