
import uuid
from datetime import date
from decimal import Decimal

from finance_tracker.models.models import (
    CategoryDB, TransactionDB, PlannedTransactionDB, 
    RecurrenceRuleDB, LenderDB, 
    LoanDB, PendingPaymentDB
)
from finance_tracker.models.enums import (
    TransactionType, RecurrenceType, PendingPaymentPriority
)

def test_category_uuid_generation(db_session):
    """Проверка автогенерации UUID для категории."""
    category = CategoryDB(name="Тест UUID", type=TransactionType.INCOME)
    db_session.add(category)
    db_session.commit()
    
    assert category.id is not None
    assert len(category.id) == 36
    uuid.UUID(category.id)  # Валидация формата
    assert category.created_at is not None
    assert category.updated_at is not None

def test_transaction_foreign_key_uuid(db_session):
    """Проверка UUID в внешнем ключе."""
    category = CategoryDB(name="Тест FK", type=TransactionType.INCOME)
    db_session.add(category)
    db_session.commit()
    
    transaction = TransactionDB(
        amount=Decimal('100.00'),
        type=TransactionType.INCOME,
        category_id=category.id,  # UUID
        transaction_date=date.today()
    )
    db_session.add(transaction)
    db_session.commit()
    
    assert transaction.id is not None
    uuid.UUID(transaction.id)
    assert transaction.category_id == category.id
    assert len(transaction.category_id) == 36

def test_lender_loan_flow_uuid(db_session):
    """Проверка потока Займодатель -> Кредит с UUID."""
    lender = LenderDB(name="Bank UUID")
    db_session.add(lender)
    db_session.commit()
    
    assert lender.id is not None
    uuid.UUID(lender.id)
    
    loan = LoanDB(
        lender_id=lender.id,
        name="Credit UUID",
        amount=Decimal('1000.00'),
        issue_date=date.today()
    )
    db_session.add(loan)
    db_session.commit()
    
    assert loan.id is not None
    uuid.UUID(loan.id)
    assert loan.lender_id == lender.id

def test_recurrence_rule_uuid(db_session):
    """Проверка UUID для правил повторения."""
    # Нужна категория для плановой транзакции
    category = CategoryDB(name="Plan Cat", type=TransactionType.EXPENSE)
    db_session.add(category)
    db_session.commit()
    
    planned = PlannedTransactionDB(
        amount=Decimal('50.00'),
        category_id=category.id,
        type=TransactionType.EXPENSE,
        start_date=date.today()
    )
    db_session.add(planned)
    db_session.commit()
    
    rule = RecurrenceRuleDB(
        planned_transaction_id=planned.id,
        recurrence_type=RecurrenceType.MONTHLY,
        interval=1
    )
    db_session.add(rule)
    db_session.commit()
    
    assert rule.id is not None
    uuid.UUID(rule.id)
    assert rule.planned_transaction_id == planned.id
    assert rule.updated_at is not None

def test_pending_payment_uuid(db_session):
    """Проверка UUID для отложенных платежей."""
    category = CategoryDB(name="Pending Cat", type=TransactionType.EXPENSE)
    db_session.add(category)
    db_session.commit()
    
    pending = PendingPaymentDB(
        amount=Decimal('200.00'),
        category_id=category.id,
        description="Pending UUID",
        priority=PendingPaymentPriority.HIGH
    )
    db_session.add(pending)
    db_session.commit()
    
    assert pending.id is not None
    uuid.UUID(pending.id)
    assert pending.category_id == category.id
