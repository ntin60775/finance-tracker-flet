import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from finance_tracker.views.interfaces import IHomeViewCallbacks
# Import services
from finance_tracker.services import (
    transaction_service,
    planned_transaction_service,
    pending_payment_service,
    loan_payment_service,
)
# Assuming logger is setup via utils.logger
from finance_tracker.utils.logger import get_logger
logger = get_logger(__name__)
from finance_tracker.models.models import (
    TransactionCreate, # for create_transaction
    TransactionUpdate, # for update_transaction
    PendingPaymentExecute, # for execute_pending_payment
    PendingPaymentCancel, # for cancel_pending_payment
    PendingPaymentCreate, # for create_pending_payment
)

class HomePresenter:
    """Presenter для HomeView, содержит всю бизнес-логику."""
    
    def __init__(self, session: Session, callbacks: IHomeViewCallbacks):
        self.session = session
        self.callbacks = callbacks
        self.selected_date = date.today()
    
    # Data Loading Methods
    def load_initial_data(self) -> None:
        """Загрузить все данные при инициализации."""
        try:
            self.load_calendar_data(date.today())
            self.load_planned_occurrences()
            self.load_pending_payments()
            # Also need to load data for the currently selected date, which is `date.today()` initially
            self.on_date_selected(self.selected_date)
        except Exception as e:
            self._handle_error("Ошибка загрузки начальных данных", e)
    
    def load_calendar_data(self, calendar_date: date) -> None:
        """Загрузить данные для календаря."""
        try:
            # Determine the range for the calendar, assuming current month.
            first_day_of_month = date(calendar_date.year, calendar_date.month, 1)
            # Find the last day of the month
            next_month = calendar_date.replace(day=28) + timedelta(days=4)
            last_day_of_month = next_month - timedelta(days=next_month.day)
            
            transactions = transaction_service.get_by_date_range(self.session, first_day_of_month, last_day_of_month)
            occurrences = planned_transaction_service.get_occurrences_by_date_range(self.session, first_day_of_month, last_day_of_month)
            self.callbacks.update_calendar_data(transactions, occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки данных календаря", e)
    
    def on_date_selected(self, selected_date: date) -> None:
        """Обработать выбор даты."""
        try:
            self.selected_date = selected_date
            transactions = transaction_service.get_transactions_by_date(self.session, selected_date)
            occurrences = planned_transaction_service.get_occurrences_by_date(self.session, selected_date)
            self.callbacks.update_transactions(selected_date, transactions, occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки данных для выбранной даты", e)
    
    def load_planned_occurrences(self) -> None:
        """Загрузить плановые операции."""
        try:
            occurrences = planned_transaction_service.get_pending_occurrences(self.session)
            formatted_occurrences = self._format_occurrences_for_ui(occurrences) # This needs implementation
            self.callbacks.update_planned_occurrences(formatted_occurrences)
        except Exception as e:
            self._handle_error("Ошибка загрузки плановых операций", e)
    
    def load_pending_payments(self) -> None:
        """Загрузить отложенные платежи."""
        try:
            payments = pending_payment_service.get_all_pending_payments(self.session)
            statistics = pending_payment_service.get_pending_payments_statistics(self.session)
            
            # Проверяем, что statistics - это словарь
            if not isinstance(statistics, dict):
                logger.warning(f"statistics имеет неожиданный тип: {type(statistics)}")
                statistics = {"total_active": 0, "total_amount": 0.0}
            
            self.callbacks.update_pending_payments(payments, statistics)
        except Exception as e:
            self._handle_error("Ошибка загрузки отложенных платежей", e)
    
    # Transaction Operations
    def create_transaction(self, transaction_data: TransactionCreate) -> None: # Assuming TransactionCreate Pydantic model
        """Создать новую транзакцию."""
        try:
            transaction_service.create_transaction(self.session, transaction_data)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Транзакция успешно создана")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка создания транзакции", e)
    
    def update_transaction(self, transaction_id: str, transaction_data: TransactionUpdate) -> None:
        """Обновить существующую транзакцию."""
        try:
            logger.debug(f"Обновление транзакции ID: {transaction_id} с данными: {transaction_data}")
            
            updated_transaction = transaction_service.update_transaction(
                self.session, 
                transaction_id, 
                transaction_data
            )
            
            if updated_transaction is None:
                self.callbacks.show_error("Транзакция не найдена")
                return
            
            self.session.commit()
            logger.info(f"Транзакция {transaction_id} успешно обновлена")
            self._refresh_data()
            self.callbacks.show_message("Транзакция успешно обновлена")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка обновления транзакции {transaction_id}: {e}", extra={
                "transaction_id": transaction_id,
                "transaction_data": transaction_data.model_dump() if transaction_data else None,
                "selected_date": self.selected_date
            })
            self._handle_error("Ошибка обновления транзакции", e)
    
    def delete_transaction(self, transaction_id: str) -> None:
        """Удалить транзакцию."""
        try:
            logger.debug(f"Удаление транзакции ID: {transaction_id}")
            
            deleted = transaction_service.delete_transaction(self.session, transaction_id)
            
            if not deleted:
                self.callbacks.show_error("Транзакция не найдена")
                return
            
            self.session.commit()
            logger.info(f"Транзакция {transaction_id} успешно удалена")
            self._refresh_data()
            self.callbacks.show_message("Транзакция успешно удалена")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка удаления транзакции {transaction_id}: {e}", extra={
                "transaction_id": transaction_id,
                "selected_date": self.selected_date
            })
            self._handle_error("Ошибка удаления транзакции", e)
    
    # Planned Occurrence Operations
    def execute_occurrence(self, occurrence: Any, execution_date: date, amount: Decimal) -> None: # amount should be Decimal
        """Исполнить плановое вхождение."""
        try:
            planned_transaction_service.execute_occurrence(self.session, occurrence.id, execution_date, amount)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Плановая операция успешно исполнена")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения плановой операции", e)
    
    def skip_occurrence(self, occurrence: Any) -> None: # reason parameter removed as it's not in service
        """Пропустить плановое вхождение."""
        try:
            planned_transaction_service.skip_occurrence(self.session, occurrence.id) 
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Плановая операция пропущена")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка пропуска плановой операции", e)
    
    # Pending Payment Operations
    def create_pending_payment(self, payment_data: PendingPaymentCreate) -> None:
        """
        Создать новый отложенный платёж.
        
        Args:
            payment_data: Данные для создания платежа
        """
        try:
            logger.debug(f"Создание отложенного платежа: {payment_data}")
            
            pending_payment_service.create_pending_payment(self.session, payment_data)
            self.session.commit()
            
            logger.info("Отложенный платёж успешно создан")
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж успешно создан")
            
        except ValueError as ve:
            self.session.rollback()
            logger.error(f"Ошибка валидации при создании платежа: {ve}")
            self.callbacks.show_error(f"Ошибка валидации: {str(ve)}")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка создания отложенного платежа: {e}", exc_info=True)
            self._handle_error("Ошибка создания отложенного платежа", e)
    
    def execute_pending_payment(self, payment_id: str, executed_amount: Decimal, executed_date: date) -> None: 
        """Исполнить отложенный платёж."""
        try:
            execute_data = PendingPaymentExecute(executed_date=executed_date, executed_amount=executed_amount)
            pending_payment_service.execute_pending_payment(self.session, payment_id, execute_data)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж успешно исполнен")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения отложенного платежа", e)
    
    def cancel_pending_payment(self, payment_id: str, reason: Optional[str] = None) -> None:
        """Отменить отложенный платёж."""
        try:
            cancel_data = PendingPaymentCancel(cancel_reason=reason or "Не указана")
            pending_payment_service.cancel_pending_payment(self.session, payment_id, cancel_data)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж отменён")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка отмены отложенного платежа", e)
    
    def delete_pending_payment(self, payment_id: str) -> None:
        """Удалить отложенный платёж."""
        try:
            pending_payment_service.delete_pending_payment(self.session, payment_id)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Отложенный платёж удалён")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка удаления отложенного платежа", e)
    
    # Loan Payment Operations
    def execute_loan_payment(self, payment: Any, amount: Decimal, execution_date: date) -> None: # amount should be Decimal
        """Исполнить платёж по кредиту."""
        try:
            # loan_payment_service.execute_payment does not use the `amount` parameter, it gets it from the payment object.
            # `transaction_date` is the parameter for the execution date.
            loan_payment_service.execute_payment(self.session, payment.id, transaction_date=execution_date)
            self.session.commit()
            self._refresh_data()
            self.callbacks.show_message("Платёж по кредиту успешно исполнен")
        except Exception as e:
            self.session.rollback()
            self._handle_error("Ошибка исполнения платежа по кредиту", e)
    
    # Modal Operations
    def prepare_modal_data(self, modal_type: str, entity_id: Optional[str] = None) -> Any: 
        """Подготовить данные для модального окна."""
        try:
            if modal_type == "transaction":
                return self._prepare_transaction_modal_data(entity_id)
            elif modal_type == "occurrence":
                return self._prepare_occurrence_modal_data(entity_id)
            # ... другие типы модальных окон
            return None # Should return None if type not matched
        except Exception as e:
            self._handle_error("Ошибка подготовки данных для модального окна", e)
            return None
    
    # Private Methods
    def _refresh_data(self) -> None:
        """Обновить все данные после изменений."""
        self.load_calendar_data(self.selected_date)
        self.on_date_selected(self.selected_date) # Refresh transactions for selected date
        self.load_planned_occurrences()
        self.load_pending_payments()
    
    def _handle_error(self, message: str, exception: Exception) -> None:
        """Обработать ошибку с логированием и уведомлением View."""
        logger.error(f"{message}: {exception}", extra={
            "selected_date": self.selected_date,
            "session_active": self.session.is_active
        })
        self.callbacks.show_error(f"{message}: {str(exception)}")
    
    def _format_occurrences_for_ui(self, occurrences: List[Any]) -> List[Tuple[Any, str, str]]:
        """Преобразовать данные плановых операций для UI."""
        # This is a placeholder, actual logic will depend on UI component
        # For now, return a dummy list.
        formatted = []
        for occ in occurrences:
            # Example formatting: (occurrence_object, color_string, text_color_string)
            formatted.append((occ, "blue", "white")) 
        return formatted
    
    def _prepare_transaction_modal_data(self, transaction_id: Optional[str]) -> Any:
        """Подготовить данные для модального окна транзакции."""
        # Logic to fetch transaction data if transaction_id is provided
        if transaction_id:
            # Assuming a get_transaction_by_id or similar function exists in transaction_service
            # For now, placeholder.
            pass
        return {} # Placeholder for modal data
    
    def _prepare_occurrence_modal_data(self, occurrence_id: Optional[str]) -> Any:
        """Подготовить данные для модального окна планового вхождения."""
        # Logic to fetch occurrence data
        if occurrence_id:
            # Assuming get_occurrence_by_id in planned_transaction_service
            pass
        return {} # Placeholder for modal data
