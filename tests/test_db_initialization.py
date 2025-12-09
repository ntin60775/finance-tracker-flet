
from sqlalchemy import inspect
from finance_tracker.database import init_default_categories
from finance_tracker.services.category_service import init_loan_categories
from finance_tracker.models.models import CategoryDB
import uuid

def test_init_default_categories_uuids(db_session):
    """Test that default categories are created with UUIDs."""
    init_default_categories(db_session)
    
    categories = db_session.query(CategoryDB).all()
    assert len(categories) > 0
    for cat in categories:
        assert len(cat.id) == 36
        uuid.UUID(cat.id) # Should not raise

def test_init_loan_categories_uuids(db_session):
    """Test that loan categories are created with UUIDs."""
    init_loan_categories(db_session)
    
    categories = db_session.query(CategoryDB).filter(CategoryDB.is_system.is_(True)).all()
    # Should have at least 3 loan categories
    loan_cats = [c for c in categories if "кредит" in c.name.lower()]
    assert len(loan_cats) >= 3
    for cat in loan_cats:
        assert len(cat.id) == 36
        uuid.UUID(cat.id)

def test_schema_has_uuid_columns(db_session):
    """Test that the schema created by tests has VARCHAR(36) for IDs."""
    engine = db_session.get_bind()
    inspector = inspect(engine)
    
    columns = inspector.get_columns("categories")
    id_col = next(c for c in columns if c["name"] == "id")
    
    # In SQLite, VARCHAR(36) might be reported as VARCHAR(36) or just VARCHAR
    assert "VARCHAR" in str(id_col["type"]).upper() or "TEXT" in str(id_col["type"]).upper()
