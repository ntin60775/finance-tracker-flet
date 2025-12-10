from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Dict
from datetime import date

class IHomeViewCallbacks(ABC):
    """Интерфейс для обратных вызовов от Presenter к View."""
    
    @abstractmethod
    def update_calendar_data(self, transactions: List[Any], occurrences: List[Any]) -> None:
        """
        Обновить данные календаря.
        
        Args:
            transactions: Список транзакций
            occurrences: Список плановых вхождений
        """
        pass
    
    @abstractmethod
    def update_transactions(self, date_obj: date, transactions: List[Any], occurrences: List[Any]) -> None:
        """
        Обновить список транзакций для выбранной даты.
        
        Args:
            date_obj: Выбранная дата
            transactions: Список транзакций за дату
            occurrences: Список плановых вхождений за дату
        """
        pass
    
    @abstractmethod
    def update_planned_occurrences(self, occurrences: List[Tuple[Any, str, str]]) -> None:
        """
        Обновить список плановых операций.
        
        Args:
            occurrences: Список кортежей (occurrence, color, text_color)
        """
        pass
    
    @abstractmethod
    def update_pending_payments(self, payments: List[Any], statistics: Dict[str, Any]) -> None:
        """
        Обновить список отложенных платежей.
        
        Args:
            payments: Список отложенных платежей
            statistics: Статистика (количество, сумма)
        """
        pass
    
    @abstractmethod
    def show_message(self, message: str) -> None:
        """
        Показать информационное сообщение.
        
        Args:
            message: Текст сообщения
        """
        pass
    
    @abstractmethod
    def show_error(self, error: str) -> None:
        """
        Показать сообщение об ошибке.
        
        Args:
            error: Текст ошибки
        """
        pass
