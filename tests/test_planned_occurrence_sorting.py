"""
Тесты для проверки сортировки просроченных плановых вхождений.

Проверяет требование 4.3: просроченные вхождения должны отображаться первыми.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from finance_tracker.models.models import (
    CategoryDB,
    PlannedTransactionDB,
    PlannedOccurrenceDB,
    RecurrenceRuleDB,
)
from finance_tracker.models.enums import (
    TransactionType,
    OccurrenceStatus,
    RecurrenceType,
)
from finance_tracker.services import planned_transaction_service


class TestPlannedOccurrenceSorting:
    """Тесты сортировки плановых вхождений."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Настройка перед каждым тестом."""
        self.session = db_session
        
        # Создаём тестовую категорию
        self.category = CategoryDB(
            id=str(uuid4()),
            name="Тестовая категория",
            type=TransactionType.EXPENSE
        )
        self.session.add(self.category)
        self.session.commit()

    def test_overdue_occurrences_sorted_first(self):
        """
        Тест: просроченные вхождения должны отображаться первыми.
        
        Requirement 4.3: THE Planned_Widget SHALL сортировать просроченные 
        вхождения в начале списка.
        """
        today = date.today()
        
        # Создаём плановую транзакцию
        planned_tx = PlannedTransactionDB(
            id=str(uuid4()),
            category_id=self.category.id,
            amount=Decimal("100.00"),
            description="Тестовая плановая транзакция",
            type=TransactionType.EXPENSE,
            start_date=today - timedelta(days=10)
        )
        self.session.add(planned_tx)
        self.session.commit()
        
        # Создаём вхождения с разными датами
        occurrences = [
            # Будущее вхождение (через 2 дня)
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today + timedelta(days=2),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            # Просроченное вхождение (5 дней назад)
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today - timedelta(days=5),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            # Будущее вхождение (завтра)
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today + timedelta(days=1),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            # Просроченное вхождение (3 дня назад)
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today - timedelta(days=3),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
        ]
        
        for occ in occurrences:
            self.session.add(occ)
        self.session.commit()
        
        # Получаем отсортированные вхождения
        sorted_occurrences = planned_transaction_service.get_pending_occurrences(
            self.session,
            limit=10
        )
        
        # Проверяем, что получили все 4 вхождения
        assert len(sorted_occurrences) == 4
        
        # Проверяем порядок сортировки
        # Первые два должны быть просроченными (старые первыми)
        assert sorted_occurrences[0].occurrence_date < today, \
            "Первое вхождение должно быть просроченным"
        assert sorted_occurrences[1].occurrence_date < today, \
            "Второе вхождение должно быть просроченным"
        
        # Просроченные должны быть отсортированы по дате (старые первыми)
        assert sorted_occurrences[0].occurrence_date == today - timedelta(days=5), \
            "Самое старое просроченное вхождение должно быть первым"
        assert sorted_occurrences[1].occurrence_date == today - timedelta(days=3), \
            "Второе просроченное вхождение должно быть вторым"
        
        # Следующие два должны быть будущими (ближайшие первыми)
        assert sorted_occurrences[2].occurrence_date >= today, \
            "Третье вхождение должно быть будущим"
        assert sorted_occurrences[3].occurrence_date >= today, \
            "Четвёртое вхождение должно быть будущим"
        
        # Будущие должны быть отсортированы по дате (ближайшие первыми)
        assert sorted_occurrences[2].occurrence_date == today + timedelta(days=1), \
            "Ближайшее будущее вхождение должно быть третьим"
        assert sorted_occurrences[3].occurrence_date == today + timedelta(days=2), \
            "Следующее будущее вхождение должно быть четвёртым"

    def test_only_overdue_occurrences(self):
        """
        Тест: только просроченные вхождения сортируются корректно.
        """
        today = date.today()
        
        # Создаём плановую транзакцию
        planned_tx = PlannedTransactionDB(
            id=str(uuid4()),
            category_id=self.category.id,
            amount=Decimal("100.00"),
            description="Тестовая плановая транзакция",
            type=TransactionType.EXPENSE,
            start_date=today - timedelta(days=10)
        )
        self.session.add(planned_tx)
        self.session.commit()
        
        # Создаём только просроченные вхождения
        occurrences = [
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today - timedelta(days=1),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today - timedelta(days=7),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today - timedelta(days=3),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
        ]
        
        for occ in occurrences:
            self.session.add(occ)
        self.session.commit()
        
        # Получаем отсортированные вхождения
        sorted_occurrences = planned_transaction_service.get_pending_occurrences(
            self.session,
            limit=10
        )
        
        # Проверяем, что все вхождения просроченные и отсортированы по дате
        assert len(sorted_occurrences) == 3
        
        for occ in sorted_occurrences:
            assert occ.occurrence_date < today
        
        # Проверяем порядок (старые первыми)
        assert sorted_occurrences[0].occurrence_date == today - timedelta(days=7)
        assert sorted_occurrences[1].occurrence_date == today - timedelta(days=3)
        assert sorted_occurrences[2].occurrence_date == today - timedelta(days=1)

    def test_only_future_occurrences(self):
        """
        Тест: только будущие вхождения сортируются корректно.
        """
        today = date.today()
        
        # Создаём плановую транзакцию
        planned_tx = PlannedTransactionDB(
            id=str(uuid4()),
            category_id=self.category.id,
            amount=Decimal("100.00"),
            description="Тестовая плановая транзакция",
            type=TransactionType.EXPENSE,
            start_date=today
        )
        self.session.add(planned_tx)
        self.session.commit()
        
        # Создаём только будущие вхождения
        occurrences = [
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today + timedelta(days=5),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today + timedelta(days=1),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
            PlannedOccurrenceDB(
                id=str(uuid4()),
                planned_transaction_id=planned_tx.id,
                occurrence_date=today + timedelta(days=3),
                amount=Decimal("100.00"),
                status=OccurrenceStatus.PENDING
            ),
        ]
        
        for occ in occurrences:
            self.session.add(occ)
        self.session.commit()
        
        # Получаем отсортированные вхождения
        sorted_occurrences = planned_transaction_service.get_pending_occurrences(
            self.session,
            limit=10
        )
        
        # Проверяем, что все вхождения будущие и отсортированы по дате
        assert len(sorted_occurrences) == 3
        
        for occ in sorted_occurrences:
            assert occ.occurrence_date >= today
        
        # Проверяем порядок (ближайшие первыми)
        assert sorted_occurrences[0].occurrence_date == today + timedelta(days=1)
        assert sorted_occurrences[1].occurrence_date == today + timedelta(days=3)
        assert sorted_occurrences[2].occurrence_date == today + timedelta(days=5)
