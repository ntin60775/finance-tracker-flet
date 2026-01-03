"""
Property-based тесты для статистики по держателям долга.

Тестирует:
- Property 11: Корректность группировки задолженностей по держателям
"""

from datetime import date
from contextlib import contextmanager
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st, settings, assume
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.models.models import (
    Base,
    LenderDB,
    LoanDB,
)
from finance_tracker.models.enums import (
    LenderType,
    LoanType,
    LoanStatus,
)
from finance_tracker.services.lender_service import create_lender
from finance_tracker.services.loan_service import (
    create_loan,
    get_debt_by_holder_statistics,
)

# Создаём тестовый движок БД в памяти
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False}
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Включает поддержку foreign keys в SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Base.metadata.create_all(test_engine)
TestSessionLocal = sessionmaker(bind=test_engine)


@contextmanager
def get_test_session():
    """Контекстный менеджер для создания тестовой сессии БД."""
    session = TestSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем данные после использования
        session.query(LoanDB).delete()
        session.query(LenderDB).delete()
        session.commit()
        session.close()


# --- Strategies ---
lender_names = st.text(min_size=1, max_size=100).map(lambda x: x.strip()).filter(lambda x: len(x) > 0)
loan_names = st.text(min_size=1, max_size=100).map(lambda x: x.strip()).filter(lambda x: len(x) > 0)
loan_types = st.sampled_from(LoanType)
loan_amounts = st.decimals(
    min_value=Decimal('1000.00'),
    max_value=Decimal('10000000.00'),
    places=2
)
dates = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))


class TestDebtTransferHolderStatisticsProperties:
    """Property-based тесты для статистики по держателям долга."""

    @given(
        num_holders=st.integers(min_value=1, max_value=5),
        loans_per_holder=st.integers(min_value=1, max_value=3),
        holder_names=st.lists(lender_names, min_size=1, max_size=5, unique=True),
        loan_names_list=st.lists(loan_names, min_size=1, max_size=15, unique=True),
        amounts=st.lists(loan_amounts, min_size=1, max_size=15),
        issue_dates=st.lists(dates, min_size=1, max_size=15),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_holder_statistics_grouping(
        self,
        num_holders,
        loans_per_holder,
        holder_names,
        loan_names_list,
        amounts,
        issue_dates,
    ):
        """
        **Feature: debt-transfer, Property 11: Корректность группировки задолженностей по держателям**
        **Validates: Requirements 7.2, 7.3**

        Property: *For any* запрос статистики по кредитору, сумма задолженности должна
        включать только кредиты, где `loan.effective_holder_id` равен ID этого кредитора.

        Проверяет, что:
        1. Каждый кредит учитывается ровно один раз в статистике
        2. Кредит учитывается в статистике текущего держателя (current_holder_id или lender_id)
        3. Сумма задолженности по держателю равна сумме остатков его кредитов
        4. Количество кредитов совпадает с фактическим количеством
        """
        with get_test_session() as session:
            # Ограничиваем количество держателей и кредитов для тестирования
            num_holders = min(num_holders, len(holder_names))
            total_loans = min(num_holders * loans_per_holder, len(loan_names_list))

            # Создаём держателей
            holders = []
            for i in range(num_holders):
                holder = create_lender(
                    session=session,
                    name=holder_names[i],
                    lender_type=LenderType.BANK
                )
                holders.append(holder)

            # Создаём кредиты и распределяем их по держателям
            loans_by_holder = {holder.id: [] for holder in holders}
            
            for loan_idx in range(total_loans):
                # Выбираем держателя для этого кредита
                holder_idx = loan_idx % num_holders
                holder = holders[holder_idx]

                # Выбираем параметры кредита
                amount = amounts[loan_idx % len(amounts)]
                issue_date = issue_dates[loan_idx % len(issue_dates)]
                loan_name = loan_names_list[loan_idx]

                # Создаём кредит
                loan = create_loan(
                    session=session,
                    name=loan_name,
                    lender_id=holder.id,
                    loan_type=LoanType.CONSUMER,
                    amount=amount,
                    issue_date=issue_date
                )

                loans_by_holder[holder.id].append(loan)

            # Получаем статистику
            stats = get_debt_by_holder_statistics(session)

            # Проверка 1: Каждый держатель с кредитами в статистике
            for holder in holders:
                if len(loans_by_holder[holder.id]) > 0:
                    assert holder.id in stats, f"Держатель {holder.id} с кредитами отсутствует в статистике"

            # Проверка 2: Количество кредитов совпадает
            for holder in holders:
                if len(loans_by_holder[holder.id]) > 0:
                    expected_count = len(loans_by_holder[holder.id])
                    actual_count = stats[holder.id]["loan_count"]
                    assert actual_count == expected_count, (
                        f"Для держателя {holder.id}: ожидается {expected_count} кредитов, "
                        f"получено {actual_count}"
                    )

            # Проверка 3: Сумма задолженности совпадает
            for holder in holders:
                if len(loans_by_holder[holder.id]) > 0:
                    expected_total = sum(
                        loan.amount for loan in loans_by_holder[holder.id]
                    )
                    actual_total = stats[holder.id]["total_debt"]
                    assert actual_total == expected_total, (
                        f"Для держателя {holder.id}: ожидается сумма {expected_total}, "
                        f"получено {actual_total}"
                    )

            # Проверка 4: Каждый кредит учитывается ровно один раз
            total_loans_in_stats = sum(
                stat["loan_count"] for stat in stats.values()
            )
            assert total_loans_in_stats == total_loans, (
                f"Ожидается {total_loans} кредитов в статистике, "
                f"получено {total_loans_in_stats}"
            )

    @given(
        num_holders=st.integers(min_value=1, max_value=3),
        num_loans=st.integers(min_value=1, max_value=5),
        holder_names=st.lists(lender_names, min_size=1, max_size=3, unique=True),
        loan_names_list=st.lists(loan_names, min_size=1, max_size=5, unique=True),
        amounts=st.lists(loan_amounts, min_size=1, max_size=5),
        issue_dates=st.lists(dates, min_size=1, max_size=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_transferred_loans_grouping(
        self,
        num_holders,
        num_loans,
        holder_names,
        loan_names_list,
        amounts,
        issue_dates,
    ):
        """
        **Feature: debt-transfer, Property 11: Корректность группировки задолженностей по держателям**
        **Validates: Requirements 7.2, 7.3**

        Property: *For any* запрос статистики по кредитору, кредиты с переданным долгом
        должны учитываться в статистике текущего держателя, а не исходного кредитора.

        Проверяет, что:
        1. Переданный кредит учитывается в статистике нового держателя
        2. Переданный кредит НЕ учитывается в статистике исходного кредитора
        3. Сумма задолженности обновляется корректно после передачи
        """
        with get_test_session() as session:
            # Ограничиваем количество держателей и кредитов
            num_holders = min(num_holders, len(holder_names))
            num_loans = min(num_loans, len(loan_names_list))

            # Создаём держателей
            holders = []
            for i in range(num_holders):
                holder = create_lender(
                    session=session,
                    name=holder_names[i],
                    lender_type=LenderType.BANK
                )
                holders.append(holder)

            # Нужно минимум 2 держателя для передачи
            if len(holders) < 2:
                assume(False)

            # Создаём кредиты у первого держателя
            original_holder = holders[0]
            new_holder = holders[1]

            loans = []
            for loan_idx in range(num_loans):
                amount = amounts[loan_idx % len(amounts)]
                issue_date = issue_dates[loan_idx % len(issue_dates)]
                loan_name = loan_names_list[loan_idx]

                loan = create_loan(
                    session=session,
                    name=loan_name,
                    lender_id=original_holder.id,
                    loan_type=LoanType.CONSUMER,
                    amount=amount,
                    issue_date=issue_date
                )
                loans.append(loan)

            # Передаём часть кредитов новому держателю
            transferred_count = max(1, num_loans // 2)
            for i in range(transferred_count):
                loans[i].current_holder_id = new_holder.id
            session.commit()

            # Получаем статистику
            stats = get_debt_by_holder_statistics(session)

            # Проверка 1: Исходный держатель имеет только непередённые кредиты
            original_holder_stat = stats.get(original_holder.id)
            if original_holder_stat:
                expected_original_count = num_loans - transferred_count
                assert original_holder_stat["loan_count"] == expected_original_count, (
                    f"Исходный держатель должен иметь {expected_original_count} кредитов, "
                    f"получено {original_holder_stat['loan_count']}"
                )

            # Проверка 2: Новый держатель имеет переданные кредиты
            new_holder_stat = stats.get(new_holder.id)
            assert new_holder_stat is not None, "Новый держатель отсутствует в статистике"
            assert new_holder_stat["loan_count"] == transferred_count, (
                f"Новый держатель должен иметь {transferred_count} кредитов, "
                f"получено {new_holder_stat['loan_count']}"
            )

            # Проверка 3: Сумма задолженности нового держателя корректна
            expected_new_holder_debt = sum(
                loans[i].amount for i in range(transferred_count)
            )
            assert new_holder_stat["total_debt"] == expected_new_holder_debt, (
                f"Новый держатель должен иметь задолженность {expected_new_holder_debt}, "
                f"получено {new_holder_stat['total_debt']}"
            )

    @given(
        num_holders=st.integers(min_value=1, max_value=3),
        num_loans=st.integers(min_value=1, max_value=5),
        holder_names=st.lists(lender_names, min_size=1, max_size=3, unique=True),
        loan_names_list=st.lists(loan_names, min_size=1, max_size=5, unique=True),
        amounts=st.lists(loan_amounts, min_size=1, max_size=5),
        issue_dates=st.lists(dates, min_size=1, max_size=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_status_filter_grouping(
        self,
        num_holders,
        num_loans,
        holder_names,
        loan_names_list,
        amounts,
        issue_dates,
    ):
        """
        **Feature: debt-transfer, Property 11: Корректность группировки задолженностей по держателям**
        **Validates: Requirements 7.2, 7.3**

        Property: *For any* запрос статистики с фильтром по статусу, должны учитываться
        только кредиты с указанным статусом.

        Проверяет, что:
        1. При фильтре по статусу учитываются только кредиты с этим статусом
        2. Кредиты с другими статусами исключаются из статистики
        3. Сумма задолженности рассчитывается только для отфильтрованных кредитов
        """
        with get_test_session() as session:
            # Ограничиваем количество держателей и кредитов
            num_holders = min(num_holders, len(holder_names))
            num_loans = min(num_loans, len(loan_names_list))

            # Создаём держателей
            holders = []
            for i in range(num_holders):
                holder = create_lender(
                    session=session,
                    name=holder_names[i],
                    lender_type=LenderType.BANK
                )
                holders.append(holder)

            # Создаём кредиты с разными статусами
            original_holder = holders[0]
            active_loans = []
            paid_off_loans = []

            for loan_idx in range(num_loans):
                amount = amounts[loan_idx % len(amounts)]
                issue_date = issue_dates[loan_idx % len(issue_dates)]
                loan_name = loan_names_list[loan_idx]

                loan = create_loan(
                    session=session,
                    name=loan_name,
                    lender_id=original_holder.id,
                    loan_type=LoanType.CONSUMER,
                    amount=amount,
                    issue_date=issue_date
                )

                # Половину кредитов делаем погашенными
                if loan_idx % 2 == 0:
                    loan.status = LoanStatus.PAID_OFF
                    paid_off_loans.append(loan)
                else:
                    active_loans.append(loan)

            session.commit()

            # Получаем статистику только по активным кредитам
            stats_active = get_debt_by_holder_statistics(session, status=LoanStatus.ACTIVE)

            # Проверка 1: Только активные кредиты учитываются
            if original_holder.id in stats_active:
                assert stats_active[original_holder.id]["loan_count"] == len(active_loans), (
                    f"Должно быть {len(active_loans)} активных кредитов, "
                    f"получено {stats_active[original_holder.id]['loan_count']}"
                )

            # Проверка 2: Сумма задолженности только для активных кредитов
            expected_active_debt = sum(loan.amount for loan in active_loans)
            if original_holder.id in stats_active:
                assert stats_active[original_holder.id]["total_debt"] == expected_active_debt, (
                    f"Сумма активных кредитов должна быть {expected_active_debt}, "
                    f"получено {stats_active[original_holder.id]['total_debt']}"
                )

            # Получаем статистику только по погашенным кредитам
            stats_paid_off = get_debt_by_holder_statistics(session, status=LoanStatus.PAID_OFF)

            # Проверка 3: Только погашенные кредиты учитываются
            if original_holder.id in stats_paid_off:
                assert stats_paid_off[original_holder.id]["loan_count"] == len(paid_off_loans), (
                    f"Должно быть {len(paid_off_loans)} погашенных кредитов, "
                    f"получено {stats_paid_off[original_holder.id]['loan_count']}"
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
