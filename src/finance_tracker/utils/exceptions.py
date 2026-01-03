"""
Модуль пользовательских исключений приложения.
"""

class FinanceTrackerError(Exception):
    """Базовый класс для всех исключений приложения."""
    pass

class ValidationError(FinanceTrackerError):
    """Исключение при ошибке валидации данных (пользовательский ввод)."""
    pass

class BusinessLogicError(FinanceTrackerError):
    """Исключение при нарушении бизнес-правил (например, удаление системной категории)."""
    pass

class DatabaseError(FinanceTrackerError):
    """Исключение при ошибках работы с базой данных."""
    pass

class LoanNotFoundError(FinanceTrackerError):
    """Исключение когда кредит не найден."""
    pass

class LenderNotFoundError(FinanceTrackerError):
    """Исключение когда кредитор не найден."""
    pass

class InvalidTransferError(BusinessLogicError):
    """Исключение при невалидной передаче долга."""
    pass
