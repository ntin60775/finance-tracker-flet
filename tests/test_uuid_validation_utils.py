
import pytest
import uuid
from hypothesis import given, strategies as st
from finance_tracker.utils.validation import validate_uuid_format

def test_validate_uuid_format_valid():
    """Проверка валидации валидного UUID."""
    valid_uuid = str(uuid.uuid4())
    validate_uuid_format(valid_uuid, "test_id")  # Не должно выбросить ошибку

def test_validate_uuid_format_invalid():
    """Проверка валидации невалидного UUID."""
    with pytest.raises(ValueError, match="Невалидный формат"):
        validate_uuid_format("not-a-uuid", "test_id")

@given(st.text())
def test_uuid_validation_rejects_invalid_strings(invalid_string):
    """
    **Feature: uuid-migration, Property 8: Валидация UUID в сервисах**
    
    Проверяет, что любая невалидная строка отклоняется валидатором UUID.
    """
    # Исключаем случайно валидные UUID
    try:
        uuid.UUID(invalid_string)
        return  # Это валидный UUID, пропускаем
    except ValueError:
        pass
    
    # Проверяем, что валидатор отклоняет невалидную строку
    with pytest.raises(ValueError, match="Невалидный формат"):
        validate_uuid_format(invalid_string, "test_id")

@given(st.uuids())
def test_uuid_validation_accepts_valid_uuids(valid_uuid):
    """
    Проверяет, что валидные UUID принимаются.
    """
    validate_uuid_format(str(valid_uuid), "test_id")
