import datetime

import flet as ft

from finance_tracker.database import get_db_session
from finance_tracker.models.models import TransactionCreate, PlannedOccurrence
from finance_tracker.services.transaction_service import (
    get_transactions_by_date,
    get_by_date_range,
    create_transaction,
)
from finance_tracker.services.planned_transaction_service import (
    get_pending_occurrences,
    get_occurrences_by_date,
    get_occurrences_by_date_range,
    execute_occurrence,
    skip_occurrence
)
from finance_tracker.components.calendar_widget import CalendarWidget
from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.components.calendar_legend import CalendarLegend
from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.components.planned_transactions_widget import PlannedTransactionsWidget
from finance_tracker.components.pending_payments_widget import PendingPaymentsWidget
from finance_tracker.components.execute_occurrence_modal import ExecuteOccurrenceModal
from finance_tracker.components.execute_pending_payment_modal import ExecutePendingPaymentModal
from finance_tracker.components.pending_payment_modal import PendingPaymentModal
from finance_tracker.utils.logger import get_logger
from finance_tracker.services.pending_payment_service import (
    get_all_pending_payments,
    get_pending_payments_statistics,
    execute_pending_payment,
    cancel_pending_payment,
    delete_pending_payment
)
from finance_tracker.services.loan_service import execute_payment as execute_loan_payment_service
from finance_tracker.models.models import (
    PendingPaymentExecute,
    PendingPaymentCancel,
    LoanPaymentDB
)
from decimal import Decimal

logger = get_logger(__name__)


class HomeView(ft.Column):
    """
    Главный экран приложения (Календарь + Транзакции + Плановые операции).
    
    Состоит из трёх колонок:
    - Левая (2/7 ширины): Виджет отложенных платежей
    - Центральная (3/7 ширины): Календарь вверху, легенда и плановые транзакции внизу
    - Правая (2/7 ширины): Список транзакций выбранного дня и кнопка добавления
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.page = page
        self.selected_date = datetime.date.today()
        
        # Создаем persistent сессию для этого view
        # Она будет использоваться для модального окна и загрузки данных
        self.cm = get_db_session()
        self.session = self.cm.__enter__()
        
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
            on_execute_loan_payment=self.on_execute_loan_payment
        )
        
        self.legend = CalendarLegend()

        self.planned_widget = PlannedTransactionsWidget(
            session=self.session,
            on_execute=self.on_execute_occurrence,
            on_skip=self.on_skip_occurrence,
            on_show_all=self.on_show_all_occurrences
        )

        self.pending_payments_widget = PendingPaymentsWidget(
            session=self.session,
            on_execute=self.on_execute_payment,
            on_cancel=self.on_cancel_payment,
            on_delete=self.on_delete_payment,
            on_show_all=self.on_show_all_payments
        )

        # Modals
        self.transaction_modal = TransactionModal(
            session=self.session,
            on_save=self.on_transaction_saved
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
            on_save=lambda _: None,  # Не используется на главном экране
            on_update=lambda _, __: None  # Не используется на главном экране
        )

        # Layout
        self.controls = [
            ft.Row(
                controls=[
                    # Левая колонка (2/7): Отложенные платежи
                    ft.Column(
                        controls=[
                            self.pending_payments_widget
                        ],
                        expand=2,
                        spacing=20,
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.START
                    ),
                    ft.VerticalDivider(width=1),
                    # Центральная колонка (3/7): Календарь вверху, легенда и плановые внизу
                    ft.Column(
                        controls=[
                            self.calendar_widget,
                            self.legend,
                            self.planned_widget
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
        
        # Initial load
        self.load_data()
        
        logger.info("HomeView инициализирован")

    # Removed did_mount as it is not automatically called

    def will_unmount(self):
        """Вызывается при удалении со страницы."""
        # Закрываем сессию при уничтожении view
        if self.cm:
            self.cm.__exit__(None, None, None)
            logger.debug("Сессия HomeView закрыта")

    def load_data(self):
        """Загрузка данных для календаря, выбранного дня и плановых транзакций."""
        if not self.session:
            return

        try:
            # 1. Загружаем данные для календаря (текущий месяц)
            
            # Определяем диапазон для календаря
            cal_date = self.calendar_widget.current_date
            start_date = datetime.date(cal_date.year, cal_date.month, 1) - datetime.timedelta(days=10) # с запасом
            # Конец месяца
            import calendar
            last_day = calendar.monthrange(cal_date.year, cal_date.month)[1]
            end_date = datetime.date(cal_date.year, cal_date.month, last_day) + datetime.timedelta(days=10)
            
            month_transactions = get_by_date_range(self.session, start_date, end_date)
            month_occurrences = get_occurrences_by_date_range(self.session, start_date, end_date)
            self.calendar_widget.set_transactions(month_transactions, month_occurrences)
            
            # 2. Загружаем транзакции для выбранного дня
            self.update_transactions_panel()

            # 3. Загружаем плановые транзакции
            self.update_planned_widget()

            # 4. Загружаем отложенные платежи
            self.update_pending_payments_widget()

        except Exception as e:
            logger.error(f"Ошибка при загрузке данных HomeView: {e}")
            if self.page:
                self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {e}")))

    def on_date_selected(self, date_obj: datetime.date):
        """Обработка выбора даты в календаре."""
        self.selected_date = date_obj
        self.update_transactions_panel()

    def update_transactions_panel(self):
        """Обновление панели транзакций для текущей даты."""
        try:
            transactions = get_transactions_by_date(self.session, self.selected_date)
            # Получаем плановые вхождения на эту дату
            occurrences = get_occurrences_by_date(self.session, self.selected_date)
            
            self.transactions_panel.set_data(self.selected_date, transactions, occurrences)
        except Exception as e:
            logger.error(f"Ошибка обновления панели транзакций: {e}")

    def update_planned_widget(self):
        """Обновление виджета плановых транзакций."""
        try:
            occurrences = get_pending_occurrences(self.session)
            # Преобразуем в формат для виджета (PlannedOccurrence, category_name, transaction_type)
            widget_data = []
            for occ in occurrences:
                # Загружаем связанные данные (категорию и плановую транзакцию), если lazy loading
                pt = occ.planned_transaction
                cat = pt.category
                widget_data.append((occ, cat.name, pt.type))
            
            self.planned_widget.set_occurrences(widget_data)
        except Exception as e:
            logger.error(f"Ошибка обновления виджета плановых транзакций: {e}")

    def open_add_transaction_modal(self):
        """Открытие модального окна добавления транзакции."""
        self.transaction_modal.open(self.page, self.selected_date)

    def on_transaction_saved(self, data: TransactionCreate):
        """Обработка сохранения новой транзакции."""
        try:
            # Сохраняем в БД
            create_transaction(self.session, data)
            
            # Обновляем UI
            self.load_data()
            self.page.open(ft.SnackBar(content=ft.Text("Транзакция добавлена!")))
            
        except Exception as e:
            logger.error(f"Ошибка сохранения транзакции: {e}")
            self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {e}")))

    def on_execute_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для исполнения планового вхождения."""
        self.execute_occurrence_modal.open_execute(self.page, occurrence)

    def on_skip_occurrence(self, occurrence: PlannedOccurrence):
        """Открытие модального окна для пропуска планового вхождения."""
        self.execute_occurrence_modal.open_skip(self.page, occurrence)

    def on_occurrence_executed_confirm(self, occurrence: PlannedOccurrence, date: datetime.date, amount: float):
        """Подтверждение исполнения вхождения."""
        try:
            execute_occurrence(self.session, occurrence.id, date, amount)
            self.session.commit()
            
            self.load_data() # Обновляем всё: и календарь (новая транзакция), и плановые
            self.page.open(ft.SnackBar(content=ft.Text("Плановый платеж исполнен")))
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка исполнения планового платежа: {e}")
            self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {e}")))

    def on_occurrence_skipped_confirm(self, occurrence: PlannedOccurrence, reason: str):
        """Подтверждение пропуска вхождения."""
        try:
            skip_occurrence(self.session, occurrence.id) # Здесь может потребоваться причина, если сервис поддерживает
            self.session.commit()
            
            self.update_planned_widget()
            self.page.open(ft.SnackBar(content=ft.Text("Плановый платеж пропущен")))
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка пропуска планового платежа: {e}")
            self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {e}")))

    def on_show_all_occurrences(self):
        """Переход к разделу всех плановых транзакций."""
        # TODO: Реализовать навигацию через MainWindow
        # Пока просто лог
        logger.info("Запрос на переход к разделу плановых транзакций")
        # Навигация должна быть реализована через callback в родительский компонент или глобальное событие
        # Здесь мы предполагаем, что у page есть доступ к main_window или роутингу, если он настроен.
        # В текущей архитектуре MainWindow управляет навигацией.
        # Можно найти MainWindow в дереве контролов, но это не всегда надежно.
        # Лучше передавать callback навигации в HomeView.
        # Для MVP пока оставим заглушку или попытаемся найти MainWindow.
        pass

    def update_pending_payments_widget(self):
        """Обновление виджета отложенных платежей."""
        try:
            payments = get_all_pending_payments(self.session)
            statistics = get_pending_payments_statistics(self.session)
            self.pending_payments_widget.set_payments(payments, statistics)
        except Exception as e:
            logger.error(f"Ошибка обновления виджета отложенных платежей: {e}")

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
            try:
                cancel_data = PendingPaymentCancel(cancel_reason=reason_field.value or None)
                cancel_pending_payment(self.session, payment.id, cancel_data)
                dialog.open = False
                self.page.update()
                self.page.open(ft.SnackBar(content=ft.Text("Платёж отменён")))
                self.load_data()
            except Exception as ex:
                logger.error(f"Ошибка отмены платежа: {ex}")
                self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}")))

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
                ft.TextButton("Отмена", on_click=lambda _: setattr(dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Отменить платёж", on_click=confirm_cancel),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def on_delete_payment(self, payment_id: int):
        """Удаление отложенного платежа."""
        def confirm_delete(e):
            try:
                delete_pending_payment(self.session, payment_id)
                dialog.open = False
                self.page.update()
                self.page.open(ft.SnackBar(content=ft.Text("Платёж удалён")))
                self.load_data()
            except Exception as ex:
                logger.error(f"Ошибка удаления платежа: {ex}")
                self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}")))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удалить платёж?"),
            content=ft.Text("Это действие нельзя отменить!"),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: setattr(dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Удалить", on_click=confirm_delete, bgcolor=ft.Colors.ERROR),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def on_payment_executed_confirm(self, payment_id: int, executed_amount: float, executed_date: datetime.date):
        """Подтверждение исполнения отложенного платежа."""
        try:
            execute_data = PendingPaymentExecute(
                executed_date=executed_date,
                executed_amount=executed_amount
            )
            execute_pending_payment(self.session, payment_id, execute_data)
            self.page.open(ft.SnackBar(content=ft.Text("Платёж исполнен")))
            self.load_data()
        except Exception as e:
            logger.error(f"Ошибка исполнения платежа: {e}")
            self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {e}")))

    def on_show_all_payments(self):
        """Переход к разделу всех отложенных платежей."""
        logger.info("Запрос на переход к разделу отложенных платежей")
        # TODO: Реализовать навигацию через MainWindow
        pass

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
            try:
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

                # Исполняем платёж
                execute_loan_payment_service(
                    self.session,
                    payment.id,
                    amount,
                    exec_date
                )
                
                dialog.open = False
                self.page.update()
                self.page.open(ft.SnackBar(content=ft.Text("Платёж по кредиту исполнен")))
                self.load_data()
                
            except Exception as ex:
                logger.error(f"Ошибка исполнения платежа по кредиту: {ex}")
                self.page.open(ft.SnackBar(content=ft.Text(f"Ошибка: {ex}")))

        try:
            loan_name = payment.loan.name if payment.loan else "Неизвестный кредит"
        except Exception:
            loan_name = "Неизвестный кредит"

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
                ft.TextButton("Отмена", on_click=lambda _: setattr(dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Исполнить", on_click=confirm_execute, bgcolor=ft.Colors.PRIMARY),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()