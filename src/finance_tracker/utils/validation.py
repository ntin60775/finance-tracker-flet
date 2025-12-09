
import uuid
import logging

logger = logging.getLogger(__name__)

def validate_uuid_format(id_value: str, field_name: str = "ID") -> None:
    """
    Валидация формата UUID.
    
    Args:
        id_value: Значение для проверки
        field_name: Название поля для сообщения об ошибке
        
    Raises:
        ValueError: Если формат невалидный
    """
    try:
        uuid.UUID(id_value)
    except ValueError:
        error_msg = f'Невалидный формат {field_name}: {id_value}. Ожидается UUID формата: 550e8400-e29b-41d4-a716-446655440000'
        logger.error(error_msg)
        raise ValueError(error_msg)
