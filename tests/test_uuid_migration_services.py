
import pytest
from datetime import date
from decimal import Decimal

from finance_tracker.models.models import (
    TransactionCreate, PlannedTransactionCreate,
    TransactionType, LenderType, LoanType,
    PendingPaymentCreate, PendingPaymentPriority, OccurrenceStatus
)
from finance_tracker.services import (
    transaction_service, category_service, planned_transaction_service,
    loan_service, loan_payment_service, lender_service, pending_payment_service
)

def test_transaction_service_flow(db_session):
    """Test UUID flow in transaction_service."""
    # Create Category
    category = category_service.create_category(db_session, "Trans Cat", TransactionType.EXPENSE)
    assert len(category.id) == 36
    
    # Create Transaction
    tx_data = TransactionCreate(
        amount=Decimal('100.00'),
        type=TransactionType.EXPENSE,
        category_id=category.id,
        transaction_date=date.today()
    )
    tx = transaction_service.create_transaction(db_session, tx_data)
    
    assert len(tx.id) == 36
    assert tx.category_id == category.id
    
    # Delete Transaction
    assert transaction_service.delete_transaction(db_session, tx.id) is True
    assert transaction_service.delete_transaction(db_session, tx.id) is False

def test_planned_transaction_service_flow(db_session):
    """Test UUID flow in planned_transaction_service."""
    category = category_service.create_category(db_session, "Plan Cat 2", TransactionType.INCOME)
    
    planned_data = PlannedTransactionCreate(
        amount=Decimal('500.00'),
        category_id=category.id,
        type=TransactionType.INCOME,
        start_date=date.today()
    )
    
    planned = planned_transaction_service.create_planned_transaction(db_session, planned_data)
    assert len(planned.id) == 36
    
    # Check occurrences
    assert len(planned.occurrences) > 0
    occ = planned.occurrences[0]
    assert len(occ.id) == 36
    assert occ.planned_transaction_id == planned.id
    
    # Execute occurrence
    tx = planned_transaction_service.execute_occurrence(
        db_session, occ.id, date.today(), Decimal('500.00')
    )
    assert len(tx.id) == 36
    assert occ.status == OccurrenceStatus.EXECUTED
    assert occ.actual_transaction_id == tx.id

def test_loan_service_flow(db_session):
    """Test UUID flow in loan_service and loan_payment_service."""
    # Create Lender
    lender = lender_service.create_lender(db_session, "Bank UUID Test", LenderType.BANK)
    assert len(lender.id) == 36
    
    # Create Loan
    loan = loan_service.create_loan(
        db_session,
        name="Test Loan",
        lender_id=lender.id,
        loan_type=LoanType.CONSUMER,
        amount=Decimal('10000.00'),
        issue_date=date.today(),
        interest_rate=Decimal('10.0')
    )
    assert len(loan.id) == 36
    
    # Create Payment
    payment = loan_payment_service.create_payment(
        db_session,
        loan_id=loan.id,
        scheduled_date=date.today(),
        principal_amount=Decimal('1000.00'),
        interest_amount=Decimal('100.00'),
        total_amount=Decimal('1100.00')
    )
    assert len(payment.id) == 36
    assert payment.loan_id == loan.id
    
    # Need system categories for execution
    category_service.init_loan_categories(db_session)
    
    # Execute Payment
    executed_payment = loan_payment_service.execute_payment(db_session, payment.id)
    assert executed_payment.status.name.startswith("EXECUTED")
    assert executed_payment.actual_transaction_id is not None
    assert len(executed_payment.actual_transaction_id) == 36

def test_pending_payment_service_flow(db_session):
    """Test UUID flow in pending_payment_service."""
    category = category_service.create_category(db_session, "Pending Cat 2", TransactionType.EXPENSE)
    
    pending_data = PendingPaymentCreate(
        amount=Decimal('300.00'),
        category_id=category.id,
        description="Pending Test",
        priority=PendingPaymentPriority.MEDIUM
    )
    
    pending = pending_payment_service.create_pending_payment(db_session, pending_data)
    assert len(pending.id) == 36
    
    # Execute
    from finance_tracker.models.models import PendingPaymentExecute
    tx, updated_pending = pending_payment_service.execute_pending_payment(
        db_session, 
        pending.id, 
        PendingPaymentExecute(executed_date=date.today())
    )
    
    assert len(tx.id) == 36
    assert updated_pending.actual_transaction_id == tx.id

def test_service_uuid_validation_failure(db_session):
    """Test that services reject invalid UUIDs."""
    with pytest.raises(ValueError, match="Невалидный формат"):
        transaction_service.delete_transaction(db_session, "invalid-uuid")
        
    with pytest.raises(ValueError, match="Невалидный формат"):
        loan_service.get_loan_by_id(db_session, "bad-id")
