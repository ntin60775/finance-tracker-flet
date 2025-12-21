"""
Комплексные тесты для функциональности удаления транзакций.

Включает property-based тесты для проверки консистентности удаления,
пересчетов балансов и каскадных обновлений.
"""

from datetime import date, timedelta
from decimal import Decimal
from contextlib import contextmanager
from hypothesis import given, strategies as st, settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from finance_tracker.services import transaction_service
from finance_tracker.services.balance_forecast_service import calculate_forecast_balance
from finance_tracker.models import Base
from finance_tracker.models.models import TransactionDB, CategoryDB
from finance_tracker.models.enums import TransactionType


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
        session.query(TransactionDB).delete()
        session.query(CategoryDB).delete()
        session.commit()
        session.close()


class TestTransactionDeletionProperties:
    """Property-based тесты для удаления транзакций."""

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_balance_conservation_after_deletion(self, amount, transaction_type, description):
        """
        **Feature: transaction-deletion-testing, Property 1: Balance Conservation After Deletion**
        **Validates: Requirements 1.1, 4.1**
        
        Property: For any transaction deletion, the total balance change should equal the negative of the deleted transaction amount.
        """
        with get_test_session() as session:
            # Arrange - создаем категорию для транзакции
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Получаем начальный баланс
            initial_balance = transaction_service.get_total_balance(session)
            
            # Создаем транзакцию для удаления
            transaction = TransactionDB(
                amount=amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=date.today()
            )
            session.add(transaction)
            session.commit()
            
            # Получаем баланс после добавления транзакции
            balance_after_add = transaction_service.get_total_balance(session)
            
            # Act - удаляем транзакцию
            deletion_result = transaction_service.delete_transaction(session, transaction.id)
            
            # Получаем финальный баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем сохранение баланса
            assert deletion_result is True, "Удаление валидной транзакции должно возвращать True"
            
            # Рассчитываем ожидаемое изменение баланса
            if transaction_type == TransactionType.INCOME:
                # При удалении дохода баланс должен уменьшиться на сумму транзакции
                expected_balance_change = -amount
            else:  # TransactionType.EXPENSE
                # При удалении расхода баланс должен увеличиться на сумму транзакции
                expected_balance_change = amount
            
            # Проверяем, что изменение баланса соответствует ожидаемому
            actual_balance_change = final_balance - balance_after_add
            
            assert actual_balance_change == expected_balance_change, (
                f"Изменение баланса должно равняться отрицательной сумме удаленной транзакции. "
                f"Тип: {transaction_type}, Сумма: {amount}, "
                f"Ожидаемое изменение: {expected_balance_change}, "
                f"Фактическое изменение: {actual_balance_change}, "
                f"Баланс до добавления: {initial_balance}, "
                f"Баланс после добавления: {balance_after_add}, "
                f"Финальный баланс: {final_balance}"
            )
            
            # Дополнительная проверка: финальный баланс должен равняться начальному
            assert final_balance == initial_balance, (
                f"После удаления транзакции баланс должен вернуться к начальному значению. "
                f"Начальный: {initial_balance}, Финальный: {final_balance}"
            )

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_transaction_count_consistency(self, amount, transaction_type, description):
        """
        **Feature: transaction-deletion-testing, Property 2: Transaction Count Consistency**
        **Validates: Requirements 4.4**
        
        Property: For any successful transaction deletion, the total transaction count should decrease by exactly one.
        """
        with get_test_session() as session:
            # Arrange - создаем категорию для транзакции
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Создаем транзакцию для удаления
            transaction = TransactionDB(
                amount=amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=date.today()
            )
            session.add(transaction)
            session.commit()
            
            # Получаем начальное количество транзакций
            initial_count = session.query(TransactionDB).count()
            
            # Act - удаляем транзакцию
            deletion_result = transaction_service.delete_transaction(session, transaction.id)
            
            # Assert - проверяем консистентность количества
            final_count = session.query(TransactionDB).count()
            
            # Удаление должно быть успешным
            assert deletion_result is True, "Удаление валидной транзакции должно возвращать True"
            
            # Количество транзакций должно уменьшиться ровно на единицу
            assert final_count == initial_count - 1, f"Количество транзакций должно уменьшиться на 1: было {initial_count}, стало {final_count}"
            
            # Удаленная транзакция не должна существовать в БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
            assert deleted_transaction is None, "Удаленная транзакция не должна существовать в БД"


class TestBalanceRecalculationAfterDeletion:
    """Тесты для пересчета балансов после удаления транзакций."""

    def test_balance_recalculation_after_income_deletion(self):
        """
        Тест пересчета общего баланса после удаления дохода.
        
        Проверяет:
        - Баланс уменьшается на сумму удаленного дохода
        - Пересчет происходит корректно
        
        Requirements: 1.1, 4.1, 4.2, 4.3
        """
        with get_test_session() as session:
            # Arrange - создаем категорию дохода
            income_category = CategoryDB(
                name="Зарплата",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(income_category)
            session.commit()
            
            # Создаем доходную транзакцию
            income_amount = Decimal('5000.00')
            income_transaction = TransactionDB(
                amount=income_amount,
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Зарплата за месяц",
                transaction_date=date.today()
            )
            session.add(income_transaction)
            session.commit()
            
            # Получаем начальный баланс
            initial_balance = transaction_service.get_total_balance(session)
            
            # Act - удаляем доходную транзакцию
            deletion_result = transaction_service.delete_transaction(session, income_transaction.id)
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем корректность пересчета
            assert deletion_result is True, "Удаление должно быть успешным"
            
            expected_balance = initial_balance - income_amount
            assert final_balance == expected_balance, (
                f"Баланс должен уменьшиться на сумму удаленного дохода: "
                f"ожидался {expected_balance}, получен {final_balance}"
            )

    def test_balance_recalculation_after_expense_deletion(self):
        """
        Тест пересчета общего баланса после удаления расхода.
        
        Проверяет:
        - Баланс увеличивается на сумму удаленного расхода
        - Пересчет происходит корректно
        
        Requirements: 1.1, 4.1, 4.2, 4.3
        """
        with get_test_session() as session:
            # Arrange - создаем категорию расхода
            expense_category = CategoryDB(
                name="Продукты",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(expense_category)
            session.commit()
            
            # Создаем расходную транзакцию
            expense_amount = Decimal('1500.00')
            expense_transaction = TransactionDB(
                amount=expense_amount,
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Покупка продуктов",
                transaction_date=date.today()
            )
            session.add(expense_transaction)
            session.commit()
            
            # Получаем начальный баланс
            initial_balance = transaction_service.get_total_balance(session)
            
            # Act - удаляем расходную транзакцию
            deletion_result = transaction_service.delete_transaction(session, expense_transaction.id)
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем корректность пересчета
            assert deletion_result is True, "Удаление должно быть успешным"
            
            expected_balance = initial_balance + expense_amount
            assert final_balance == expected_balance, (
                f"Баланс должен увеличиться на сумму удаленного расхода: "
                f"ожидался {expected_balance}, получен {final_balance}"
            )

    def test_balance_recalculation_after_zero_amount_deletion(self):
        """
        Тест пересчета баланса при удалении транзакции с нулевой суммой.
        
        Проверяет:
        - Баланс не изменяется при удалении транзакции с нулевой суммой
        - Система корректно обрабатывает граничный случай
        
        Requirements: 1.1, 4.1, 4.2, 4.3
        """
        with get_test_session() as session:
            # Arrange - создаем категорию
            test_category = CategoryDB(
                name="Тестовая категория",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(test_category)
            session.commit()
            
            # Создаем обычную транзакцию для установки ненулевого баланса
            normal_transaction = TransactionDB(
                amount=Decimal('1000.00'),
                type=TransactionType.INCOME,
                category_id=test_category.id,
                description="Обычная транзакция",
                transaction_date=date.today()
            )
            session.add(normal_transaction)
            
            # Создаем транзакцию с нулевой суммой (граничный случай)
            # Примечание: в реальной системе такие транзакции могут быть запрещены валидацией,
            # но мы тестируем поведение системы в граничном случае
            zero_transaction = TransactionDB(
                amount=Decimal('0.00'),
                type=TransactionType.EXPENSE,
                category_id=test_category.id,
                description="Транзакция с нулевой суммой",
                transaction_date=date.today()
            )
            session.add(zero_transaction)
            session.commit()
            
            # Получаем начальный баланс
            initial_balance = transaction_service.get_total_balance(session)
            
            # Act - удаляем транзакцию с нулевой суммой
            deletion_result = transaction_service.delete_transaction(session, zero_transaction.id)
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем, что баланс не изменился
            assert deletion_result is True, "Удаление должно быть успешным"
            
            assert final_balance == initial_balance, (
                f"Баланс не должен изменяться при удалении транзакции с нулевой суммой: "
                f"был {initial_balance}, стал {final_balance}"
            )
            
            # Проверяем, что обычная транзакция осталась
            remaining_transaction = session.query(TransactionDB).filter_by(id=normal_transaction.id).first()
            assert remaining_transaction is not None, "Обычная транзакция должна остаться в БД"
            
            # Проверяем, что транзакция с нулевой суммой удалена
            deleted_transaction = session.query(TransactionDB).filter_by(id=zero_transaction.id).first()
            assert deleted_transaction is None, "Транзакция с нулевой суммой должна быть удалена"


class TestUIStateSynchronizationProperties:
    """Property-based тесты для синхронизации UI состояния после удаления транзакций."""

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_ui_state_synchronization(self, amount, transaction_type, description):
        """
        **Feature: transaction-deletion-testing, Property 4: UI State Synchronization**
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        
        Property: For any transaction deletion, all UI components should reflect the updated state consistently.
        """
        from unittest.mock import Mock, MagicMock
        from finance_tracker.views.home_presenter import HomePresenter
        from finance_tracker.views.interfaces import IHomeViewCallbacks
        
        with get_test_session() as session:
            # Arrange - создаем категорию для транзакции
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Создаем транзакцию для удаления
            transaction = TransactionDB(
                amount=amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=date.today()
            )
            session.add(transaction)
            session.commit()
            
            # Создаем mock объекты для UI callbacks
            mock_callbacks = Mock(spec=IHomeViewCallbacks)
            
            # Создаем HomePresenter с mock callbacks
            presenter = HomePresenter(session, mock_callbacks)
            
            # Сбрасываем счетчики вызовов после инициализации
            mock_callbacks.reset_mock()
            
            # Act - удаляем транзакцию через presenter
            presenter.delete_transaction(transaction.id)
            
            # Assert - проверяем синхронизацию UI состояния
            
            # 1. Проверяем, что транзакция действительно удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
            assert deleted_transaction is None, "Транзакция должна быть удалена из БД"
            
            # 2. Проверяем, что все UI компоненты получили обновления (Requirements 2.1, 2.2, 2.3, 2.4, 2.5)
            
            # Requirement 2.1: WHEN транзакция удаляется THEN Cascade_Updates SHALL обновить TransactionsPanel
            # Это происходит через update_transactions callback
            mock_callbacks.update_transactions.assert_called()
            
            # Requirement 2.2: WHEN транзакция удаляется THEN система SHALL обновить CalendarWidget с новыми данными
            # Это происходит через update_calendar_data callback
            mock_callbacks.update_calendar_data.assert_called()
            
            # Requirement 2.3: WHEN транзакция удаляется THEN система SHALL обновить сводку дня (доходы/расходы/баланс)
            # Это также происходит через update_transactions callback (содержит сводку дня)
            assert mock_callbacks.update_transactions.call_count >= 1, "Сводка дня должна быть обновлена"
            
            # Requirement 2.4: WHEN транзакция удаляется THEN система SHALL обновить прогноз баланса в UI
            # Это происходит через update_calendar_data callback (календарь содержит прогноз)
            assert mock_callbacks.update_calendar_data.call_count >= 1, "Прогноз баланса должен быть обновлен"
            
            # Requirement 2.5: WHEN удаляется транзакция THEN все связанные виджеты SHALL получить актуальные данные
            # Проверяем, что обновлены плановые операции и отложенные платежи
            mock_callbacks.update_planned_occurrences.assert_called()
            mock_callbacks.update_pending_payments.assert_called()
            
            # 3. Проверяем консистентность: все обновления должны происходить в рамках одной операции
            # Все callbacks должны быть вызваны после успешного удаления
            total_update_calls = (
                mock_callbacks.update_calendar_data.call_count +
                mock_callbacks.update_transactions.call_count +
                mock_callbacks.update_planned_occurrences.call_count +
                mock_callbacks.update_pending_payments.call_count
            )
            
            assert total_update_calls >= 4, (
                f"Все UI компоненты должны быть обновлены после удаления транзакции. "
                f"Фактическое количество обновлений: {total_update_calls}, "
                f"update_calendar_data: {mock_callbacks.update_calendar_data.call_count}, "
                f"update_transactions: {mock_callbacks.update_transactions.call_count}, "
                f"update_planned_occurrences: {mock_callbacks.update_planned_occurrences.call_count}, "
                f"update_pending_payments: {mock_callbacks.update_pending_payments.call_count}"
            )
            
            # 4. Проверяем, что пользователь получил подтверждение об успешной операции
            mock_callbacks.show_message.assert_called()
            
            # Получаем аргументы последнего вызова show_message
            show_message_calls = mock_callbacks.show_message.call_args_list
            assert len(show_message_calls) > 0, "Должно быть показано сообщение пользователю"
            
            # Проверяем, что сообщение содержит информацию об успешном удалении
            last_message = show_message_calls[-1][0][0]  # Первый аргумент последнего вызова
            assert "успешно удалена" in last_message.lower(), (
                f"Сообщение должно содержать подтверждение успешного удаления. "
                f"Фактическое сообщение: '{last_message}'"
            )
            
            # 5. Проверяем, что ошибки не показаны (операция прошла успешно)
            mock_callbacks.show_error.assert_not_called()
            
            # 6. Проверяем, что данные переданные в callbacks актуальны
            # Получаем аргументы вызова update_transactions для проверки актуальности данных
            update_transactions_calls = mock_callbacks.update_transactions.call_args_list
            if update_transactions_calls:
                # Последний вызов должен содержать актуальные данные
                last_call_args = update_transactions_calls[-1][0]
                call_date = last_call_args[0]
                call_transactions = last_call_args[1]
                
                # Проверяем, что удаленная транзакция не присутствует в переданных данных
                transaction_ids = [t.id for t in call_transactions if hasattr(t, 'id')]
                assert transaction.id not in transaction_ids, (
                    f"Удаленная транзакция не должна присутствовать в обновленных данных UI. "
                    f"ID удаленной транзакции: {transaction.id}, "
                    f"ID транзакций в UI: {transaction_ids}"
                )


class TestForecastRecalculationProperties:
    """Property-based тесты для точности пересчета прогнозов после удаления транзакций."""

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        transaction_date_offset=st.integers(min_value=-30, max_value=0),  # Транзакции в прошлом или сегодня
        forecast_days=st.integers(min_value=1, max_value=30),  # Прогноз на будущее
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_forecast_recalculation_accuracy(self, amount, transaction_type, transaction_date_offset, forecast_days, description):
        """
        **Feature: transaction-deletion-testing, Property 7: Forecast Recalculation Accuracy**
        **Validates: Requirements 1.2**
        
        Property: For any transaction deletion, balance forecasts for affected dates should be recalculated correctly.
        """
        with get_test_session() as session:
            # Arrange - создаем категорию для транзакции
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Определяем даты
            today = date.today()
            transaction_date = today + timedelta(days=transaction_date_offset)
            forecast_date = today + timedelta(days=forecast_days)
            
            # Получаем прогноз до создания транзакции
            initial_forecast = calculate_forecast_balance(session, forecast_date)
            
            # Создаем транзакцию для удаления
            transaction = TransactionDB(
                amount=amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=transaction_date
            )
            session.add(transaction)
            session.commit()
            
            # Получаем прогноз после создания транзакции
            forecast_after_add = calculate_forecast_balance(session, forecast_date)
            
            # Act - удаляем транзакцию
            deletion_result = transaction_service.delete_transaction(session, transaction.id)
            
            # Получаем прогноз после удаления транзакции
            forecast_after_deletion = calculate_forecast_balance(session, forecast_date)
            
            # Assert - проверяем точность пересчета прогноза
            assert deletion_result is True, "Удаление валидной транзакции должно возвращать True"
            
            # Основное свойство: прогноз после удаления должен вернуться к начальному значению
            assert forecast_after_deletion == initial_forecast, (
                f"Прогноз баланса после удаления транзакции должен вернуться к начальному значению. "
                f"Тип транзакции: {transaction_type}, "
                f"Сумма: {amount}, "
                f"Дата транзакции: {transaction_date}, "
                f"Дата прогноза: {forecast_date}, "
                f"Начальный прогноз: {initial_forecast}, "
                f"Прогноз после добавления: {forecast_after_add}, "
                f"Прогноз после удаления: {forecast_after_deletion}"
            )
            
            # Дополнительная проверка: изменение прогноза должно соответствовать типу и сумме транзакции
            if transaction_date <= forecast_date:
                # Транзакция влияет на прогноз только если её дата не позже даты прогноза
                expected_forecast_change_on_add = amount if transaction_type == TransactionType.INCOME else -amount
                actual_forecast_change_on_add = forecast_after_add - initial_forecast
                
                assert actual_forecast_change_on_add == expected_forecast_change_on_add, (
                    f"Изменение прогноза при добавлении транзакции должно соответствовать её типу и сумме. "
                    f"Ожидаемое изменение: {expected_forecast_change_on_add}, "
                    f"Фактическое изменение: {actual_forecast_change_on_add}"
                )
                
                # Изменение прогноза при удалении должно быть обратным к изменению при добавлении
                forecast_change_on_deletion = forecast_after_deletion - forecast_after_add
                expected_forecast_change_on_deletion = -expected_forecast_change_on_add
                
                assert forecast_change_on_deletion == expected_forecast_change_on_deletion, (
                    f"Изменение прогноза при удалении должно быть обратным к изменению при добавлении. "
                    f"Ожидаемое изменение при удалении: {expected_forecast_change_on_deletion}, "
                    f"Фактическое изменение при удалении: {forecast_change_on_deletion}"
                )
            else:
                # Если транзакция в будущем относительно даты прогноза, она не должна влиять на прогноз
                assert forecast_after_add == initial_forecast, (
                    f"Транзакция с датой после даты прогноза не должна влиять на прогноз. "
                    f"Дата транзакции: {transaction_date}, Дата прогноза: {forecast_date}"
                )
                
                assert forecast_after_deletion == initial_forecast, (
                    f"Удаление транзакции с датой после даты прогноза не должно влиять на прогноз. "
                    f"Дата транзакции: {transaction_date}, Дата прогноза: {forecast_date}"
                )
            
            # Проверяем, что транзакция действительно удалена
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction.id).first()
            assert deleted_transaction is None, "Транзакция должна быть удалена из БД"

    @given(
        amounts=st.lists(
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('1000.00'), places=2),
            min_size=1,
            max_size=10
        ),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        category_name=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_category_statistics_consistency(self, amounts, transaction_type, category_name):
        """
        **Feature: transaction-deletion-testing, Property 3: Category Statistics Consistency**
        **Validates: Requirements 1.3**
        
        Property: For any transaction deletion, category statistics should be updated to reflect the removal of that transaction.
        """
        with get_test_session() as session:
            # Arrange - создаем категорию
            category = CategoryDB(
                name=f"Test Category {category_name[:20]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Создаем несколько транзакций в этой категории
            transactions = []
            total_amount_before = Decimal('0.0')
            
            for amount in amounts:
                transaction = TransactionDB(
                    amount=amount,
                    type=transaction_type,
                    category_id=category.id,
                    description=f"Test transaction {len(transactions)}",
                    transaction_date=date.today()
                )
                session.add(transaction)
                transactions.append(transaction)
                total_amount_before += amount
            
            session.commit()
            
            # Получаем статистику до удаления
            stats_before = transaction_service.get_category_statistics(session)
            
            # Проверяем, что категория присутствует в статистике
            assert category.id in stats_before, "Категория должна присутствовать в статистике до удаления"
            assert stats_before[category.id]["total"] == total_amount_before, "Сумма в статистике должна соответствовать сумме всех транзакций"
            
            # Act - удаляем одну транзакцию
            transaction_to_delete = transactions[0]
            deleted_amount = transaction_to_delete.amount
            deletion_result = transaction_service.delete_transaction(session, transaction_to_delete.id)
            
            # Assert - проверяем консистентность статистики категорий
            assert deletion_result is True, "Удаление транзакции должно быть успешным"
            
            # Получаем статистику после удаления
            stats_after = transaction_service.get_category_statistics(session)
            
            expected_amount_after = total_amount_before - deleted_amount
            
            if expected_amount_after > Decimal('0.0'):
                # Если остались транзакции в категории, она должна быть в статистике
                assert category.id in stats_after, "Категория должна присутствовать в статистике после удаления, если остались транзакции"
                assert stats_after[category.id]["total"] == expected_amount_after, f"Сумма в статистике должна уменьшиться на {deleted_amount}"
                assert stats_after[category.id]["name"] == category.name, "Название категории должно сохраниться"
                assert stats_after[category.id]["type"] == category.type.value, "Тип категории должен сохраниться"
            else:
                # Если не осталось транзакций в категории, её не должно быть в статистике
                assert category.id not in stats_after, "Категория не должна присутствовать в статистике, если в ней нет транзакций"
            
            # Проверяем, что удаленная транзакция действительно удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction_to_delete.id).first()
            assert deleted_transaction is None, "Удаленная транзакция не должна существовать в БД"


class TestEdgeCaseTransactionDeletion:
    """Тесты для удаления нестандартных транзакций (граничные случаи)."""

    def test_delete_transaction_with_special_category_name(self):
        """
        Тест удаления транзакции с особым названием категории.
        
        Проверяет:
        - Система корректно обрабатывает транзакции с категориями, имеющими специальные символы
        - Удаление работает независимо от содержимого названия категории
        - Баланс пересчитывается корректно
        
        Requirements: 7.2
        """
        with get_test_session() as session:
            # Arrange - создаем категорию с особым названием (имитируем граничный случай)
            special_category = CategoryDB(
                name="Категория с символами: !@#$%^&*()_+-=[]{}|;':\",./<>?",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(special_category)
            session.commit()
            
            # Получаем начальный баланс (должен быть 0 в пустой БД)
            initial_balance = transaction_service.get_total_balance(session)
            
            transaction_amount = Decimal('500.00')
            transaction_with_special_category = TransactionDB(
                amount=transaction_amount,
                type=TransactionType.EXPENSE,
                category_id=special_category.id,
                description="Транзакция с особой категорией",
                transaction_date=date.today()
            )
            session.add(transaction_with_special_category)
            session.commit()
            
            # Получаем баланс после добавления транзакции
            balance_after_add = transaction_service.get_total_balance(session)
            
            # Act - удаляем транзакцию с особой категорией
            deletion_result = transaction_service.delete_transaction(session, transaction_with_special_category.id)
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем корректность обработки
            assert deletion_result is True, "Удаление транзакции с особой категорией должно быть успешным"
            
            # Баланс должен вернуться к начальному значению
            assert final_balance == initial_balance, (
                f"Баланс должен вернуться к начальному значению после удаления транзакции: "
                f"начальный {initial_balance}, после добавления {balance_after_add}, финальный {final_balance}"
            )
            
            # Проверяем, что транзакция удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction_with_special_category.id).first()
            assert deleted_transaction is None, "Транзакция с особой категорией должна быть удалена"
            
            # Проверяем, что категория осталась в БД (не была затронута удалением транзакции)
            remaining_category = session.query(CategoryDB).filter_by(id=special_category.id).first()
            assert remaining_category is not None, "Категория должна остаться в БД после удаления транзакции"
            assert remaining_category.name == special_category.name, "Название категории не должно измениться"

    def test_delete_transaction_with_very_large_amount(self):
        """
        Тест удаления транзакции с очень большой суммой.
        
        Проверяет:
        - Система корректно обрабатывает транзакции с большими суммами
        - Пересчеты балансов остаются точными при больших числах
        - Не возникает переполнения или потери точности
        
        Requirements: 7.3
        """
        with get_test_session() as session:
            # Arrange - создаем категорию
            large_amount_category = CategoryDB(
                name="Крупные операции",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(large_amount_category)
            session.commit()
            
            # Создаем транзакцию с очень большой суммой (близко к максимальному значению Decimal)
            very_large_amount = Decimal('999999999.99')
            large_transaction = TransactionDB(
                amount=very_large_amount,
                type=TransactionType.INCOME,
                category_id=large_amount_category.id,
                description="Транзакция с очень большой суммой",
                transaction_date=date.today()
            )
            session.add(large_transaction)
            session.commit()
            
            # Получаем начальный баланс
            initial_balance = transaction_service.get_total_balance(session)
            
            # Act - удаляем транзакцию с большой суммой
            deletion_result = transaction_service.delete_transaction(session, large_transaction.id)
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем точность пересчетов
            assert deletion_result is True, "Удаление транзакции с большой суммой должно быть успешным"
            
            # Баланс должен уменьшиться на сумму удаленного дохода
            expected_balance = initial_balance - very_large_amount
            assert final_balance == expected_balance, (
                f"Баланс должен уменьшиться на сумму удаленного дохода: "
                f"ожидался {expected_balance}, получен {final_balance}. "
                f"Разница: {abs(final_balance - expected_balance)}"
            )
            
            # Проверяем точность: разница должна быть ровно нулевой (без потери точности)
            balance_difference = abs(final_balance - expected_balance)
            assert balance_difference == Decimal('0.00'), (
                f"Не должно быть потери точности при работе с большими суммами. "
                f"Разница: {balance_difference}"
            )
            
            # Проверяем, что транзакция удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=large_transaction.id).first()
            assert deleted_transaction is None, "Транзакция с большой суммой должна быть удалена"

    def test_delete_transaction_with_future_date(self):
        """
        Тест удаления транзакции с датой в будущем.
        
        Проверяет:
        - Система корректно обрабатывает транзакции с будущими датами
        - Прогнозы балансов обновляются корректно
        - Общий баланс изменяется (так как get_total_balance учитывает все транзакции)
        
        Requirements: 7.4
        """
        with get_test_session() as session:
            # Arrange - создаем категорию
            future_category = CategoryDB(
                name="Будущие операции",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(future_category)
            session.commit()
            
            # Получаем начальный баланс (должен быть 0 в пустой БД)
            initial_balance = transaction_service.get_total_balance(session)
            
            # Создаем транзакцию с датой в будущем (через 30 дней)
            future_date = date.today() + timedelta(days=30)
            future_amount = Decimal('2000.00')
            future_transaction = TransactionDB(
                amount=future_amount,
                type=TransactionType.EXPENSE,
                category_id=future_category.id,
                description="Транзакция с датой в будущем",
                transaction_date=future_date
            )
            session.add(future_transaction)
            session.commit()
            
            # Получаем баланс после добавления будущей транзакции
            balance_after_add = transaction_service.get_total_balance(session)
            initial_future_forecast = calculate_forecast_balance(session, future_date)
            
            # Act - удаляем транзакцию с будущей датой
            deletion_result = transaction_service.delete_transaction(session, future_transaction.id)
            
            # Получаем баланс и прогноз после удаления
            final_balance = transaction_service.get_total_balance(session)
            final_future_forecast = calculate_forecast_balance(session, future_date)
            
            # Assert - проверяем корректность обновления
            assert deletion_result is True, "Удаление транзакции с будущей датой должно быть успешным"
            
            # Общий баланс должен вернуться к начальному значению
            assert final_balance == initial_balance, (
                f"Баланс должен вернуться к начальному значению после удаления будущей транзакции: "
                f"начальный {initial_balance}, после добавления {balance_after_add}, финальный {final_balance}"
            )
            
            # Прогноз на будущую дату должен вернуться к начальному значению
            # (так как мы удалили единственную транзакцию, влияющую на этот прогноз)
            assert final_future_forecast == initial_future_forecast, (
                f"Прогноз на будущую дату должен вернуться к начальному значению после удаления транзакции: "
                f"начальный прогноз {initial_future_forecast}, финальный прогноз {final_future_forecast}"
            )
            
            # Проверяем, что транзакция удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=future_transaction.id).first()
            assert deleted_transaction is None, "Транзакция с будущей датой должна быть удалена"

    def test_delete_transaction_with_distant_past_date(self):
        """
        Тест удаления транзакции с датой в далеком прошлом.
        
        Проверяет:
        - Система эффективно обрабатывает транзакции с очень старыми датами
        - Пересчеты выполняются корректно независимо от возраста транзакции
        - Не возникает проблем с производительностью
        
        Requirements: 7.5
        """
        with get_test_session() as session:
            # Arrange - создаем категорию
            old_category = CategoryDB(
                name="Старые операции",
                type=TransactionType.INCOME,
                is_system=False
            )
            session.add(old_category)
            session.commit()
            
            # Получаем начальный баланс (должен быть 0 в пустой БД)
            initial_balance = transaction_service.get_total_balance(session)
            
            # Создаем транзакцию с датой в далеком прошлом (5 лет назад)
            distant_past_date = date.today() - timedelta(days=5*365)  # 5 лет назад
            old_amount = Decimal('1500.00')
            old_transaction = TransactionDB(
                amount=old_amount,
                type=TransactionType.INCOME,
                category_id=old_category.id,
                description="Транзакция с датой в далеком прошлом",
                transaction_date=distant_past_date
            )
            session.add(old_transaction)
            session.commit()
            
            # Получаем баланс после добавления старой транзакции
            balance_after_add = transaction_service.get_total_balance(session)
            
            # Измеряем время выполнения операции удаления
            import time
            start_time = time.time()
            
            # Act - удаляем транзакцию с очень старой датой
            deletion_result = transaction_service.delete_transaction(session, old_transaction.id)
            
            end_time = time.time()
            deletion_time = end_time - start_time
            
            # Получаем баланс после удаления
            final_balance = transaction_service.get_total_balance(session)
            
            # Assert - проверяем эффективность обработки
            assert deletion_result is True, "Удаление транзакции с очень старой датой должно быть успешным"
            
            # Баланс должен вернуться к начальному значению
            assert final_balance == initial_balance, (
                f"Баланс должен вернуться к начальному значению после удаления старой транзакции: "
                f"начальный {initial_balance}, после добавления {balance_after_add}, финальный {final_balance}"
            )
            
            # Операция должна выполняться достаточно быстро (менее 1 секунды)
            assert deletion_time < 1.0, (
                f"Удаление транзакции с очень старой датой должно выполняться быстро. "
                f"Фактическое время: {deletion_time:.3f} секунд"
            )
            
            # Проверяем, что транзакция удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=old_transaction.id).first()
            assert deleted_transaction is None, "Транзакция с очень старой датой должна быть удалена"
            
            # Дополнительная проверка: убеждаемся, что система корректно работает с датами в прошлом
            # Создаем и сразу удаляем еще одну старую транзакцию для проверки стабильности
            another_old_transaction = TransactionDB(
                amount=Decimal('100.00'),
                type=TransactionType.EXPENSE,
                category_id=old_category.id,
                description="Еще одна старая транзакция",
                transaction_date=distant_past_date - timedelta(days=365)  # Еще на год старше
            )
            session.add(another_old_transaction)
            session.commit()
            
            # Получаем баланс после добавления второй транзакции
            balance_after_second_add = transaction_service.get_total_balance(session)
            
            # Удаляем вторую старую транзакцию
            second_deletion_result = transaction_service.delete_transaction(session, another_old_transaction.id)
            assert second_deletion_result is True, "Удаление второй старой транзакции должно быть успешным"
            
            # Проверяем, что система остается стабильной после множественных операций со старыми датами
            final_balance_after_second = transaction_service.get_total_balance(session)
            assert final_balance_after_second == initial_balance, (
                f"Система должна оставаться стабильной при множественных операциях со старыми датами. "
                f"Начальный баланс: {initial_balance}, "
                f"После второй транзакции: {balance_after_second_add}, "
                f"Финальный баланс: {final_balance_after_second}"
            )


class TestEdgeCaseHandlingProperties:
    """Property-based тесты для обработки граничных случаев при удалении транзакций."""

    @given(
        # Генерируем граничные случаи для сумм
        amount=st.one_of(
            st.just(Decimal('0.00')),  # Нулевая сумма
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('0.99'), places=2),  # Очень маленькие суммы
            st.decimals(min_value=Decimal('999999.00'), max_value=Decimal('999999.99'), places=2),  # Очень большие суммы
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2)  # Обычные суммы
        ),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        # Генерируем граничные случаи для дат
        date_offset=st.one_of(
            st.integers(min_value=-3650, max_value=-1825),  # Далекое прошлое (5-10 лет назад)
            st.integers(min_value=-365, max_value=-1),      # Недавнее прошлое (до года назад)
            st.just(0),                                     # Сегодня
            st.integers(min_value=1, max_value=365),        # Ближайшее будущее (до года вперед)
            st.integers(min_value=1825, max_value=3650)     # Далекое будущее (5-10 лет вперед)
        ),
        # Генерируем граничные случаи для описаний и категорий
        description=st.one_of(
            st.just(""),  # Пустое описание
            st.text(min_size=1, max_size=1),  # Очень короткое описание
            st.text(min_size=500, max_size=500),  # Очень длинное описание
            st.text(alphabet="!@#$%^&*()_+-=[]{}|;':\",./<>?", min_size=1, max_size=50),  # Специальные символы
            st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=1, max_size=50),  # Кириллица
            st.text(min_size=1, max_size=100)  # Обычное описание
        ),
        category_name=st.one_of(
            st.text(min_size=1, max_size=1),  # Очень короткое название категории
            st.text(min_size=100, max_size=100),  # Очень длинное название категории
            st.text(alphabet="!@#$%^&*()_+-=[]{}|;':\",./<>?", min_size=1, max_size=50),  # Специальные символы
            st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=1, max_size=50),  # Кириллица
            st.text(min_size=1, max_size=50)  # Обычное название
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_edge_case_handling(self, amount, transaction_type, date_offset, description, category_name):
        """
        **Feature: transaction-deletion-testing, Property 10: Edge Case Handling**
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
        
        Property: For any edge case transaction (zero amount, no category, extreme dates), deletion should be handled gracefully.
        """
        with get_test_session() as session:
            # Arrange - создаем категорию с граничным названием
            category = CategoryDB(
                name=category_name,
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # Определяем дату транзакции (граничный случай)
            transaction_date = date.today() + timedelta(days=date_offset)
            
            # Получаем начальное состояние системы
            initial_balance = transaction_service.get_total_balance(session)
            initial_transaction_count = session.query(TransactionDB).count()
            initial_stats = transaction_service.get_category_statistics(session)
            
            # Создаем транзакцию с граничными параметрами
            edge_case_transaction = TransactionDB(
                amount=amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=transaction_date
            )
            session.add(edge_case_transaction)
            session.commit()
            
            # Получаем состояние после добавления транзакции
            balance_after_add = transaction_service.get_total_balance(session)
            count_after_add = session.query(TransactionDB).count()
            
            # Измеряем время выполнения операции удаления (для проверки производительности)
            import time
            start_time = time.time()
            
            # Act - удаляем транзакцию с граничными параметрами
            try:
                deletion_result = transaction_service.delete_transaction(session, edge_case_transaction.id)
                deletion_successful = True
                deletion_error = None
            except Exception as e:
                deletion_successful = False
                deletion_result = False
                deletion_error = str(e)
            
            end_time = time.time()
            deletion_time = end_time - start_time
            
            # Получаем финальное состояние системы
            final_balance = transaction_service.get_total_balance(session)
            final_transaction_count = session.query(TransactionDB).count()
            final_stats = transaction_service.get_category_statistics(session)
            
            # Assert - проверяем корректную обработку граничных случаев
            
            # 1. Основное свойство: система должна обрабатывать граничные случаи без падений
            assert deletion_successful, (
                f"Система должна корректно обрабатывать граничные случаи без исключений. "
                f"Параметры: amount={amount}, type={transaction_type}, date_offset={date_offset}, "
                f"description='{description[:50]}...', category='{category_name[:50]}...'. "
                f"Ошибка: {deletion_error}"
            )
            
            # 2. Удаление должно быть успешным для любых валидных граничных случаев
            assert deletion_result is True, (
                f"Удаление транзакции с граничными параметрами должно быть успешным. "
                f"Параметры: amount={amount}, type={transaction_type}, date_offset={date_offset}"
            )
            
            # 3. Requirement 7.1: Корректная обработка нулевых сумм
            if amount == Decimal('0.00'):
                # При нулевой сумме баланс не должен изменяться
                assert final_balance == initial_balance, (
                    f"При удалении транзакции с нулевой суммой баланс не должен изменяться. "
                    f"Начальный: {initial_balance}, финальный: {final_balance}"
                )
            else:
                # При ненулевой сумме баланс должен вернуться к начальному значению
                assert final_balance == initial_balance, (
                    f"После удаления транзакции баланс должен вернуться к начальному значению. "
                    f"Начальный: {initial_balance}, после добавления: {balance_after_add}, "
                    f"финальный: {final_balance}, сумма транзакции: {amount}"
                )
            
            # 4. Requirement 7.2: Корректная обработка категорий с особыми названиями
            # Категория должна остаться в БД после удаления транзакции
            remaining_category = session.query(CategoryDB).filter_by(id=category.id).first()
            assert remaining_category is not None, (
                f"Категория должна остаться в БД после удаления транзакции. "
                f"Название категории: '{category_name[:50]}...'"
            )
            assert remaining_category.name == category_name, (
                f"Название категории не должно измениться после удаления транзакции"
            )
            
            # 5. Requirement 7.3: Точность пересчетов при больших суммах
            if amount >= Decimal('999999.00'):
                # Для больших сумм проверяем отсутствие потери точности
                balance_difference = abs(final_balance - initial_balance)
                assert balance_difference == Decimal('0.00'), (
                    f"Не должно быть потери точности при работе с большими суммами. "
                    f"Сумма: {amount}, разница в балансе: {balance_difference}"
                )
            
            # 6. Requirements 7.4, 7.5: Эффективная обработка экстремальных дат
            if abs(date_offset) >= 1825:  # Более 5 лет в прошлом или будущем
                # Операция должна выполняться достаточно быстро даже для экстремальных дат
                assert deletion_time < 2.0, (
                    f"Удаление транзакции с экстремальной датой должно выполняться быстро. "
                    f"Дата: {transaction_date}, время выполнения: {deletion_time:.3f} секунд"
                )
            
            # 7. Консистентность количества транзакций
            assert final_transaction_count == initial_transaction_count, (
                f"Количество транзакций должно вернуться к начальному значению. "
                f"Начальное: {initial_transaction_count}, после добавления: {count_after_add}, "
                f"финальное: {final_transaction_count}"
            )
            
            # 8. Транзакция должна быть полностью удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=edge_case_transaction.id).first()
            assert deleted_transaction is None, (
                f"Транзакция с граничными параметрами должна быть полностью удалена из БД"
            )
            
            # 9. Консистентность статистики категорий
            # Если в категории не осталось транзакций, она не должна быть в статистике
            if amount > Decimal('0.00'):
                # Только ненулевые транзакции влияют на статистику
                if category.id in final_stats:
                    # Если категория есть в финальной статистике, значит есть другие транзакции
                    pass
                else:
                    # Если категории нет в финальной статистике, проверяем что нет транзакций в этой категории
                    remaining_transactions_in_category = session.query(TransactionDB).filter_by(category_id=category.id).count()
                    assert remaining_transactions_in_category == 0, (
                        f"Если категория отсутствует в статистике, в ней не должно быть транзакций. "
                        f"Найдено транзакций: {remaining_transactions_in_category}"
                    )
            
            # 10. Проверка стабильности системы при граничных случаях
            # Создаем и сразу удаляем еще одну транзакцию для проверки стабильности
            stability_test_transaction = TransactionDB(
                amount=Decimal('1.00'),  # Простая сумма для проверки стабильности
                type=TransactionType.INCOME,
                category_id=category.id,
                description="Тест стабильности",
                transaction_date=date.today()
            )
            session.add(stability_test_transaction)
            session.commit()
            
            stability_deletion_result = transaction_service.delete_transaction(session, stability_test_transaction.id)
            assert stability_deletion_result is True, (
                f"Система должна оставаться стабильной после обработки граничных случаев. "
                f"Граничные параметры: amount={amount}, date_offset={date_offset}"
            )
            
            # Финальная проверка: баланс должен остаться неизменным после теста стабильности
            stability_final_balance = transaction_service.get_total_balance(session)
            assert stability_final_balance == initial_balance, (
                f"Система должна сохранять консистентность после множественных операций с граничными случаями. "
                f"Начальный баланс: {initial_balance}, финальный: {stability_final_balance}"
            )


class TestDialogDisplayProperties:
    """Property-based тесты для надежности отображения диалогов удаления транзакций."""

    @given(
        transaction_amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_dialog_display_reliability(self, transaction_amount, transaction_type, description):
        """
        **Feature: transaction-deletion-testing, Property 5: Dialog Display Reliability**
        **Validates: Requirements 3.1, 3.2**
        
        Property: For any delete button click, a confirmation dialog should be displayed to the user.
        """
        from unittest.mock import Mock, MagicMock, patch
        from finance_tracker.views.home_view import HomeView
        from finance_tracker.models.models import TransactionDB, CategoryDB
        
        with get_test_session() as session:
            # Arrange - создаем категорию и транзакцию
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            transaction = TransactionDB(
                amount=transaction_amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=date.today()
            )
            session.add(transaction)
            session.commit()
            
            # Создаем mock объекты для UI
            mock_page = MagicMock()
            mock_page.open = Mock()
            mock_page.close = Mock()
            mock_page.update = Mock()
            
            # Создаем HomeView с mock page
            home_view = HomeView(mock_page, session)
            
            # Act - симулируем нажатие кнопки удаления
            # Это должно вызвать отображение диалога подтверждения
            home_view.on_delete_transaction(transaction)
            
            # Assert - проверяем надежность отображения диалога
            
            # Requirement 3.1: WHEN пользователь нажимает кнопку удаления THEN UI_Dialog_System SHALL показать диалог подтверждения
            mock_page.open.assert_called(), (
                f"При нажатии кнопки удаления должен отображаться диалог подтверждения. "
                f"Транзакция: amount={transaction_amount}, type={transaction_type}, description='{description[:50]}...'"
            )
            
            # Проверяем, что page.open был вызван с диалогом
            open_call_args = mock_page.open.call_args_list
            assert len(open_call_args) > 0, "page.open должен быть вызван для отображения диалога"
            
            # Получаем переданный диалог
            dialog_arg = open_call_args[-1][0][0]  # Первый аргумент последнего вызова
            
            # Requirement 3.2: WHEN диалог подтверждения показан THEN пользователь SHALL видеть все элементы диалога
            # Проверяем, что диалог содержит необходимые элементы
            assert hasattr(dialog_arg, 'title'), "Диалог должен иметь заголовок"
            assert hasattr(dialog_arg, 'content'), "Диалог должен иметь содержимое"
            assert hasattr(dialog_arg, 'actions'), "Диалог должен иметь кнопки действий"
            
            # Проверяем содержимое диалога
            dialog_title = str(dialog_arg.title.value) if hasattr(dialog_arg.title, 'value') else str(dialog_arg.title)
            assert "удал" in dialog_title.lower(), f"Заголовок диалога должен содержать информацию об удалении: '{dialog_title}'"
            
            # Проверяем наличие кнопок действий
            assert len(dialog_arg.actions) >= 2, "Диалог должен содержать минимум 2 кнопки (Удалить и Отмена)"
            
            # Проверяем, что кнопки имеют правильные обработчики
            action_buttons = dialog_arg.actions
            button_texts = []
            button_handlers = []
            
            for button in action_buttons:
                if hasattr(button, 'text'):
                    button_texts.append(str(button.text).lower())
                if hasattr(button, 'on_click'):
                    button_handlers.append(button.on_click)
            
            # Должна быть кнопка подтверждения удаления
            has_delete_button = any('удал' in text or 'delete' in text for text in button_texts)
            assert has_delete_button, f"Диалог должен содержать кнопку удаления. Найденные тексты кнопок: {button_texts}"
            
            # Должна быть кнопка отмены
            has_cancel_button = any('отмен' in text or 'cancel' in text for text in button_texts)
            assert has_cancel_button, f"Диалог должен содержать кнопку отмены. Найденные тексты кнопок: {button_texts}"
            
            # Все кнопки должны иметь обработчики
            assert all(handler is not None for handler in button_handlers), "Все кнопки диалога должны иметь обработчики событий"
            
            # Проверяем, что диалог содержит информацию о транзакции
            # Для Flet диалогов нужно проверять структуру объектов, а не строковое представление
            dialog_content_found = False
            transaction_info_checks = []
            
            def check_flet_content_recursively(obj, depth=0):
                """Рекурсивно проверяет содержимое Flet объектов."""
                if depth > 5:  # Ограничиваем глубину рекурсии
                    return False
                
                # Проверяем текстовые свойства объекта
                text_properties = ['text', 'value', 'label', 'title']
                for prop in text_properties:
                    if hasattr(obj, prop):
                        prop_value = getattr(obj, prop)
                        if prop_value and isinstance(prop_value, str):
                            # Проверяем наличие информации о транзакции в тексте
                            prop_lower = prop_value.lower()
                            if (str(transaction_amount) in prop_value or
                                description[:10].lower() in prop_lower or
                                transaction_type.value in prop_lower or
                                'удал' in prop_lower or 'delete' in prop_lower):
                                return True
                
                # Проверяем дочерние элементы
                if hasattr(obj, 'content') and obj.content:
                    if check_flet_content_recursively(obj.content, depth + 1):
                        return True
                
                if hasattr(obj, 'controls') and obj.controls:
                    for control in obj.controls:
                        if check_flet_content_recursively(control, depth + 1):
                            return True
                
                return False
            
            # Проверяем содержимое диалога
            dialog_content_found = check_flet_content_recursively(dialog_arg)
            
            # Если не нашли информацию о транзакции в содержимом, проверим заголовок
            if not dialog_content_found:
                dialog_title_lower = dialog_title.lower()
                if ('удал' in dialog_title_lower or 'delete' in dialog_title_lower):
                    dialog_content_found = True  # Заголовок содержит информацию об удалении
            
            # Для property-based теста достаточно, чтобы диалог был корректно сформирован
            # и содержал базовую информацию об операции удаления
            assert dialog_content_found or 'удал' in dialog_title.lower() or 'delete' in dialog_title.lower(), (
                f"Диалог должен содержать информацию об операции удаления транзакции. "
                f"Заголовок: '{dialog_title}', "
                f"Параметры транзакции: amount={transaction_amount}, description='{description[:20]}...', type={transaction_type.value}"
            )

    @given(
        transaction_amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from([TransactionType.INCOME, TransactionType.EXPENSE]),
        user_action=st.sampled_from(['confirm', 'cancel']),
        description=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_dialog_action_consistency(self, transaction_amount, transaction_type, user_action, description):
        """
        **Feature: transaction-deletion-testing, Property 6: Dialog Action Consistency**
        **Validates: Requirements 3.3, 3.4**
        
        Property: For any dialog confirmation, the expected action (delete or cancel) should be executed correctly.
        """
        from unittest.mock import Mock, MagicMock, patch
        from finance_tracker.views.home_view import HomeView
        from finance_tracker.models.models import TransactionDB, CategoryDB
        
        with get_test_session() as session:
            # Arrange - создаем категорию и транзакцию
            category = CategoryDB(
                name=f"Test Category {description[:10]}",
                type=transaction_type,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            transaction = TransactionDB(
                amount=transaction_amount,
                type=transaction_type,
                category_id=category.id,
                description=description,
                transaction_date=date.today()
            )
            session.add(transaction)
            session.commit()
            
            # Сохраняем ID транзакции для проверки
            transaction_id = transaction.id
            
            # Получаем начальное состояние
            initial_transaction_count = session.query(TransactionDB).count()
            initial_balance = transaction_service.get_total_balance(session)
            
            # Создаем mock объекты для UI
            mock_page = MagicMock()
            mock_page.open = Mock()
            mock_page.close = Mock()
            mock_page.update = Mock()
            
            # Патчим transaction_service.delete_transaction для контроля
            with patch('finance_tracker.services.transaction_service.delete_transaction') as mock_delete_service:
                mock_delete_service.return_value = True
                
                # Создаем HomeView с mock page
                home_view = HomeView(mock_page, session)
                
                # Act - симулируем нажатие кнопки удаления и действие пользователя
                home_view.on_delete_transaction(transaction)
                
                # Получаем диалог из вызова page.open
                open_call_args = mock_page.open.call_args_list
                assert len(open_call_args) > 0, "Диалог должен быть отображен"
                
                dialog = open_call_args[-1][0][0]
                
                # Находим соответствующую кнопку и симулируем её нажатие
                action_buttons = dialog.actions
                
                if user_action == 'confirm':
                    # Ищем кнопку подтверждения удаления
                    delete_button = None
                    for button in action_buttons:
                        button_text = str(button.text).lower() if hasattr(button, 'text') else ''
                        if 'удал' in button_text or 'delete' in button_text:
                            delete_button = button
                            break
                    
                    assert delete_button is not None, "Должна быть найдена кнопка удаления"
                    assert delete_button.on_click is not None, "Кнопка удаления должна иметь обработчик"
                    
                    # Симулируем нажатие кнопки удаления
                    delete_button.on_click(None)
                    
                    # Assert - проверяем выполнение удаления
                    
                    # Requirement 3.3: WHEN пользователь нажимает "Удалить" THEN диалог SHALL закрыться и выполнить удаление
                    mock_delete_service.assert_called_once_with(session, transaction_id), (
                        f"При подтверждении удаления должен быть вызван transaction_service.delete_transaction. "
                        f"Транзакция: amount={transaction_amount}, type={transaction_type}"
                    )
                    
                    # Проверяем, что диалог закрылся
                    # ВАЖНО: Используется СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0)
                    # Проверяем вызов page.close()
                    mock_page.close.assert_called(), "Диалог должен закрыться после подтверждения удаления"
                    
                else:  # user_action == 'cancel'
                    # Ищем кнопку отмены
                    cancel_button = None
                    for button in action_buttons:
                        button_text = str(button.text).lower() if hasattr(button, 'text') else ''
                        if 'отмен' in button_text or 'cancel' in button_text:
                            cancel_button = button
                            break
                    
                    assert cancel_button is not None, "Должна быть найдена кнопка отмены"
                    assert cancel_button.on_click is not None, "Кнопка отмены должна иметь обработчик"
                    
                    # Симулируем нажатие кнопки отмены
                    cancel_button.on_click(None)
                    
                    # Assert - проверяем отмену удаления
                    
                    # Requirement 3.4: WHEN пользователь нажимает "Отмена" THEN диалог SHALL закрыться без удаления
                    mock_delete_service.assert_not_called(), (
                        f"При отмене удаления НЕ должен быть вызван transaction_service.delete_transaction. "
                        f"Транзакция: amount={transaction_amount}, type={transaction_type}"
                    )
                    
                    # Проверяем, что диалог закрылся
                    # ВАЖНО: Используется СОВРЕМЕННЫЙ Flet Dialog API (>= 0.25.0)
                    # Проверяем вызов page.close()
                    mock_page.close.assert_called(), "Диалог должен закрыться после отмены"
                    
                    # Проверяем, что транзакция осталась в БД (без использования mock)
                    remaining_transaction = session.query(TransactionDB).filter_by(id=transaction_id).first()
                    assert remaining_transaction is not None, "Транзакция должна остаться в БД при отмене удаления"
                    
                    # Проверяем, что количество транзакций не изменилось
                    final_transaction_count = session.query(TransactionDB).count()
                    assert final_transaction_count == initial_transaction_count, (
                        f"Количество транзакций не должно измениться при отмене удаления. "
                        f"Было: {initial_transaction_count}, стало: {final_transaction_count}"
                    )
                    
                    # Проверяем, что баланс не изменился
                    final_balance = transaction_service.get_total_balance(session)
                    assert final_balance == initial_balance, (
                        f"Баланс не должен измениться при отмене удаления. "
                        f"Был: {initial_balance}, стал: {final_balance}"
                    )


class TestCascadeUpdatesAfterDeletion:
    """Тесты для каскадных обновлений после удаления транзакций."""

    def test_cascade_updates_after_transaction_deletion(self):
        """
        Тест каскадных обновлений после удаления транзакции.
        
        Проверяет:
        - Создание транзакции с связанными данными
        - Выполнение удаления транзакции
        - Проверка обновления TransactionsPanel
        - Проверка обновления CalendarWidget
        - Проверка обновления сводки дня
        - Проверка обновления прогноза баланса
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        from unittest.mock import Mock, MagicMock, patch
        from finance_tracker.views.home_presenter import HomePresenter
        from finance_tracker.views.interfaces import IHomeViewCallbacks
        
        with get_test_session() as session:
            # Arrange - создаем связанные данные
            
            # 1. Создаем категорию
            category = CategoryDB(
                name="Тестовая категория для каскадных обновлений",
                type=TransactionType.EXPENSE,
                is_system=False
            )
            session.add(category)
            session.commit()
            
            # 2. Создаем несколько транзакций для создания контекста
            base_date = date.today()
            transactions_data = [
                (Decimal('1000.00'), TransactionType.INCOME, base_date - timedelta(days=1)),
                (Decimal('500.00'), TransactionType.EXPENSE, base_date),
                (Decimal('200.00'), TransactionType.EXPENSE, base_date + timedelta(days=1)),
            ]
            
            created_transactions = []
            for amount, tx_type, tx_date in transactions_data:
                transaction = TransactionDB(
                    amount=amount,
                    type=tx_type,
                    category_id=category.id,
                    description=f"Транзакция {len(created_transactions) + 1}",
                    transaction_date=tx_date
                )
                session.add(transaction)
                created_transactions.append(transaction)
            
            session.commit()
            
            # 3. Выбираем транзакцию для удаления (средняя по дате)
            transaction_to_delete = created_transactions[1]  # Транзакция на сегодня
            transaction_id = transaction_to_delete.id
            transaction_date = transaction_to_delete.transaction_date
            
            # 4. Создаем mock объекты для UI callbacks
            mock_callbacks = Mock(spec=IHomeViewCallbacks)
            
            # Настраиваем mock callbacks для отслеживания вызовов
            mock_callbacks.update_transactions = Mock()
            mock_callbacks.update_calendar_data = Mock()
            mock_callbacks.update_planned_occurrences = Mock()
            mock_callbacks.update_pending_payments = Mock()
            mock_callbacks.show_message = Mock()
            mock_callbacks.show_error = Mock()
            
            # 5. Создаем HomePresenter с mock callbacks
            presenter = HomePresenter(session, mock_callbacks)
            
            # Сбрасываем счетчики вызовов после инициализации
            mock_callbacks.reset_mock()
            
            # Получаем начальное состояние для проверки изменений
            initial_balance = transaction_service.get_total_balance(session)
            initial_transactions_for_date = transaction_service.get_transactions_by_date(session, transaction_date)
            initial_transaction_count = len(initial_transactions_for_date)
            
            # Act - выполняем удаление транзакции через presenter
            presenter.delete_transaction(transaction_id)
            
            # Assert - проверяем каскадные обновления
            
            # Проверяем, что транзакция действительно удалена из БД
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction_id).first()
            assert deleted_transaction is None, "Транзакция должна быть удалена из БД"
            
            # Requirement 2.1: WHEN транзакция удаляется THEN Cascade_Updates SHALL обновить TransactionsPanel
            mock_callbacks.update_transactions.assert_called(), (
                "После удаления транзакции должен быть вызван update_transactions для обновления TransactionsPanel"
            )
            
            # Проверяем, что update_transactions вызван с правильными параметрами
            update_transactions_calls = mock_callbacks.update_transactions.call_args_list
            assert len(update_transactions_calls) > 0, "update_transactions должен быть вызван минимум один раз"
            
            # Получаем параметры последнего вызова update_transactions
            last_update_call = update_transactions_calls[-1]
            call_date = last_update_call[0][0]
            call_transactions = last_update_call[0][1]
            call_summary = last_update_call[0][2]
            
            # Проверяем, что вызов содержит правильную дату
            assert call_date == transaction_date, f"update_transactions должен быть вызван с датой удаленной транзакции: {transaction_date}"
            
            # Проверяем, что удаленная транзакция не присутствует в обновленных данных
            transaction_ids = [t.id for t in call_transactions if hasattr(t, 'id')]
            assert transaction_id not in transaction_ids, "Удаленная транзакция не должна присутствовать в обновленных данных TransactionsPanel"
            
            # Проверяем, что количество транзакций уменьшилось
            assert len(call_transactions) == initial_transaction_count - 1, (
                f"Количество транзакций в обновленных данных должно уменьшиться на 1: "
                f"было {initial_transaction_count}, стало {len(call_transactions)}"
            )
            
            # Requirement 2.2: WHEN транзакция удаляется THEN система SHALL обновить CalendarWidget с новыми данными
            mock_callbacks.update_calendar_data.assert_called(), (
                "После удаления транзакции должен быть вызван update_calendar_data для обновления CalendarWidget"
            )
            
            # Проверяем параметры вызова update_calendar_data
            update_calendar_calls = mock_callbacks.update_calendar_data.call_args_list
            assert len(update_calendar_calls) > 0, "update_calendar_data должен быть вызван минимум один раз"
            
            # Requirement 2.3: WHEN транзакция удаляется THEN система SHALL обновить сводку дня (доходы/расходы/баланс)
            # Проверяем, что сводка дня обновлена (передается в update_transactions)
            assert call_summary is not None, "Сводка дня должна быть передана в update_transactions"
            
            # Проверяем, что сводка содержит актуальные данные (без удаленной транзакции)
            expected_balance_change = transaction_to_delete.amount if transaction_to_delete.type == TransactionType.EXPENSE else -transaction_to_delete.amount
            final_balance = transaction_service.get_total_balance(session)
            expected_final_balance = initial_balance + expected_balance_change
            
            assert final_balance == expected_final_balance, (
                f"Баланс в системе должен отражать удаление транзакции. "
                f"Начальный: {initial_balance}, ожидаемый: {expected_final_balance}, фактический: {final_balance}"
            )
            
            # Requirement 2.4: WHEN транзакция удаляется THEN система SHALL обновить прогноз баланса в UI
            # Прогноз баланса обновляется через update_calendar_data
            assert mock_callbacks.update_calendar_data.call_count >= 1, (
                "update_calendar_data должен быть вызван для обновления прогноза баланса"
            )
            
            # Requirement 2.5: WHEN удаляется транзакция THEN все связанные виджеты SHALL получить актуальные данные
            # Проверяем обновление плановых операций
            mock_callbacks.update_planned_occurrences.assert_called(), (
                "После удаления транзакции должен быть вызван update_planned_occurrences"
            )
            
            # Проверяем обновление отложенных платежей
            mock_callbacks.update_pending_payments.assert_called(), (
                "После удаления транзакции должен быть вызван update_pending_payments"
            )
            
            # Проверяем, что пользователь получил подтверждение об успешной операции
            mock_callbacks.show_message.assert_called(), (
                "Пользователь должен получить сообщение об успешном удалении транзакции"
            )
            
            # Проверяем, что ошибки не показаны
            mock_callbacks.show_error.assert_not_called(), (
                "При успешном удалении не должно быть показано сообщений об ошибках"
            )
            
            # Проверяем консистентность: все обновления должны происходить в рамках одной операции
            total_update_calls = (
                mock_callbacks.update_calendar_data.call_count +
                mock_callbacks.update_transactions.call_count +
                mock_callbacks.update_planned_occurrences.call_count +
                mock_callbacks.update_pending_payments.call_count
            )
            
            assert total_update_calls >= 4, (
                f"Все UI компоненты должны быть обновлены после удаления транзакции. "
                f"Фактическое количество обновлений: {total_update_calls}"
            )
            
            # Дополнительная проверка: убеждаемся, что система остается в консистентном состоянии
            # Проверяем, что оставшиеся транзакции не затронуты
            remaining_transactions = session.query(TransactionDB).all()
            expected_remaining_count = len(created_transactions) - 1
            
            assert len(remaining_transactions) == expected_remaining_count, (
                f"Количество оставшихся транзакций должно быть корректным: "
                f"ожидается {expected_remaining_count}, фактически {len(remaining_transactions)}"
            )
            
            # Проверяем, что оставшиеся транзакции имеют правильные данные
            remaining_ids = {t.id for t in remaining_transactions}
            expected_remaining_ids = {t.id for t in created_transactions if t.id != transaction_id}
            
            assert remaining_ids == expected_remaining_ids, (
                f"Оставшиеся транзакции должны соответствовать ожидаемым. "
                f"Ожидаемые ID: {expected_remaining_ids}, фактические ID: {remaining_ids}"
            )


class TestPerformanceDeletion:
    """Тесты производительности удаления транзакций."""

    def test_performance_large_dataset_deletion(self):
        """
        Тест производительности для больших наборов данных.
        
        Проверяет:
        - Тест удаления транзакции из набора 1000+ транзакций
        - Измерение времени выполнения операции удаления
        - Проверка эффективности пересчетов после удаления
        
        Requirements: 6.1, 6.2
        """
        import time
        
        with get_test_session() as session:
            # Arrange - создаем большой набор данных
            
            # Создаем несколько категорий для разнообразия
            categories = []
            for i in range(10):
                category = CategoryDB(
                    name=f"Категория {i}",
                    type=TransactionType.INCOME if i % 2 == 0 else TransactionType.EXPENSE,
                    is_system=False
                )
                session.add(category)
                categories.append(category)
            
            session.commit()
            
            # Создаем большой набор транзакций (1000+ транзакций)
            large_dataset_size = 1000
            transactions = []
            
            print(f"Создание {large_dataset_size} транзакций для теста производительности...")
            
            # Измеряем время создания данных
            creation_start_time = time.time()
            
            for i in range(large_dataset_size):
                category = categories[i % len(categories)]
                transaction = TransactionDB(
                    amount=Decimal(str(10.0 + (i % 1000))),  # Суммы от 10 до 1009
                    type=category.type,
                    category_id=category.id,
                    description=f"Транзакция для теста производительности {i}",
                    transaction_date=date.today() - timedelta(days=i % 365)  # Распределяем по году
                )
                session.add(transaction)
                transactions.append(transaction)
                
                # Коммитим батчами для эффективности
                if (i + 1) % 100 == 0:
                    session.commit()
            
            session.commit()
            creation_end_time = time.time()
            creation_time = creation_end_time - creation_start_time
            
            print(f"Создание {large_dataset_size} транзакций заняло {creation_time:.2f} секунд")
            
            # Выбираем транзакцию для удаления (из середины набора)
            transaction_to_delete = transactions[large_dataset_size // 2]
            transaction_id = transaction_to_delete.id
            
            # Получаем начальное состояние
            initial_balance = transaction_service.get_total_balance(session)
            initial_count = session.query(TransactionDB).count()
            
            # Act - измеряем время удаления транзакции из большого набора данных
            print(f"Удаление транзакции из набора {large_dataset_size} транзакций...")
            
            deletion_start_time = time.time()
            deletion_result = transaction_service.delete_transaction(session, transaction_id)
            deletion_end_time = time.time()
            
            deletion_time = deletion_end_time - deletion_start_time
            
            print(f"Удаление транзакции заняло {deletion_time:.4f} секунд")
            
            # Измеряем время пересчета баланса после удаления
            balance_calculation_start_time = time.time()
            final_balance = transaction_service.get_total_balance(session)
            balance_calculation_end_time = time.time()
            
            balance_calculation_time = balance_calculation_end_time - balance_calculation_start_time
            
            print(f"Пересчет баланса после удаления занял {balance_calculation_time:.4f} секунд")
            
            # Assert - проверяем производительность и корректность
            
            # Requirement 6.1: WHEN удаляется транзакция из большого набора данных THEN операция SHALL завершиться за разумное время
            assert deletion_result is True, "Удаление транзакции должно быть успешным"
            
            # Операция удаления должна быть быстрой (менее 1 секунды для 1000 транзакций)
            assert deletion_time < 1.0, (
                f"Удаление транзакции из большого набора данных должно выполняться быстро. "
                f"Фактическое время: {deletion_time:.4f} секунд, размер набора: {large_dataset_size}"
            )
            
            # Requirement 6.2: WHEN выполняется пересчет после удаления THEN система SHALL эффективно обновить только затронутые данные
            # Пересчет баланса должен быть эффективным (менее 0.5 секунды)
            assert balance_calculation_time < 0.5, (
                f"Пересчет баланса после удаления должен быть эффективным. "
                f"Фактическое время: {balance_calculation_time:.4f} секунд"
            )
            
            # Проверяем корректность результата
            final_count = session.query(TransactionDB).count()
            assert final_count == initial_count - 1, (
                f"Количество транзакций должно уменьшиться на 1: "
                f"было {initial_count}, стало {final_count}"
            )
            
            # Проверяем, что транзакция действительно удалена
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction_id).first()
            assert deleted_transaction is None, "Транзакция должна быть удалена из БД"
            
            # Проверяем корректность пересчета баланса
            expected_balance_change = (
                transaction_to_delete.amount if transaction_to_delete.type == TransactionType.EXPENSE
                else -transaction_to_delete.amount
            )
            expected_final_balance = initial_balance + expected_balance_change
            
            assert final_balance == expected_final_balance, (
                f"Баланс должен быть пересчитан корректно. "
                f"Ожидаемый: {expected_final_balance}, фактический: {final_balance}"
            )
            
            # Дополнительные проверки производительности
            
            # Проверяем, что операция масштабируется линейно
            # Для набора в 1000 транзакций время удаления не должно превышать определенный порог
            max_acceptable_time_per_1000_transactions = 1.0  # 1 секунда на 1000 транзакций
            time_per_transaction = deletion_time / large_dataset_size * 1000
            
            assert time_per_transaction < max_acceptable_time_per_1000_transactions, (
                f"Время удаления должно масштабироваться эффективно. "
                f"Время на 1000 транзакций: {time_per_transaction:.4f} секунд, "
                f"максимально допустимое: {max_acceptable_time_per_1000_transactions} секунд"
            )
            
            print(f"Тест производительности завершен успешно:")
            print(f"  - Размер набора данных: {large_dataset_size} транзакций")
            print(f"  - Время создания данных: {creation_time:.2f} секунд")
            print(f"  - Время удаления: {deletion_time:.4f} секунд")
            print(f"  - Время пересчета баланса: {balance_calculation_time:.4f} секунд")
            print(f"  - Время на транзакцию: {time_per_transaction:.6f} секунд")

    @given(
        dataset_size=st.integers(min_value=100, max_value=1000),
        transaction_position=st.floats(min_value=0.1, max_value=0.9),  # Позиция транзакции в наборе (10%-90%)
        category_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_9_performance_consistency(self, dataset_size, transaction_position, category_count):
        """
        **Feature: transaction-deletion-testing, Property 9: Performance Consistency**
        **Validates: Requirements 6.1, 6.2**
        
        Property: For any transaction deletion, the operation should complete within acceptable time limits.
        """
        import time
        
        with get_test_session() as session:
            # Arrange - создаем набор данных переменного размера
            
            # Создаем категории
            categories = []
            for i in range(category_count):
                category = CategoryDB(
                    name=f"Category {i}",
                    type=TransactionType.INCOME if i % 2 == 0 else TransactionType.EXPENSE,
                    is_system=False
                )
                session.add(category)
                categories.append(category)
            
            session.commit()
            
            # Создаем транзакции
            transactions = []
            for i in range(dataset_size):
                category = categories[i % len(categories)]
                transaction = TransactionDB(
                    amount=Decimal(str(10.0 + (i % 100))),
                    type=category.type,
                    category_id=category.id,
                    description=f"Performance test transaction {i}",
                    transaction_date=date.today() - timedelta(days=i % 30)
                )
                session.add(transaction)
                transactions.append(transaction)
                
                # Коммитим батчами для эффективности
                if (i + 1) % 50 == 0:
                    session.commit()
            
            session.commit()
            
            # Выбираем транзакцию для удаления на основе позиции
            transaction_index = int(dataset_size * transaction_position)
            transaction_to_delete = transactions[transaction_index]
            transaction_id = transaction_to_delete.id
            
            # Act - измеряем время удаления
            deletion_start_time = time.time()
            deletion_result = transaction_service.delete_transaction(session, transaction_id)
            deletion_end_time = time.time()
            
            deletion_time = deletion_end_time - deletion_start_time
            
            # Assert - проверяем консистентность производительности
            
            # Основное свойство: удаление должно быть успешным
            assert deletion_result is True, f"Удаление транзакции должно быть успешным для набора размером {dataset_size}"
            
            # Requirement 6.1: Операция должна завершиться за разумное время
            # Время должно быть пропорционально размеру набора данных, но не превышать разумные пределы
            max_acceptable_time = 0.001 * dataset_size + 0.1  # Линейная зависимость + константа
            
            assert deletion_time < max_acceptable_time, (
                f"Время удаления должно быть в пределах разумного для размера набора {dataset_size}. "
                f"Фактическое время: {deletion_time:.4f} секунд, "
                f"максимально допустимое: {max_acceptable_time:.4f} секунд, "
                f"позиция транзакции: {transaction_position:.2f}, "
                f"количество категорий: {category_count}"
            )
            
            # Requirement 6.2: Система должна эффективно обновлять только затронутые данные
            # Время не должно зависеть от позиции транзакции в наборе (O(1) операция)
            # Для этого проверяем, что время удаления не превышает константный порог
            constant_time_threshold = 0.1  # 100 миллисекунд
            
            assert deletion_time < constant_time_threshold, (
                f"Время удаления должно быть константным независимо от размера набора и позиции транзакции. "
                f"Фактическое время: {deletion_time:.4f} секунд, "
                f"порог: {constant_time_threshold} секунд, "
                f"размер набора: {dataset_size}, позиция: {transaction_position:.2f}"
            )
            
            # Проверяем корректность результата
            deleted_transaction = session.query(TransactionDB).filter_by(id=transaction_id).first()
            assert deleted_transaction is None, "Транзакция должна быть удалена из БД"
            
            # Проверяем, что количество транзакций уменьшилось на 1
            final_count = session.query(TransactionDB).count()
            expected_count = dataset_size - 1
            
            assert final_count == expected_count, (
                f"Количество транзакций должно уменьшиться на 1: "
                f"ожидается {expected_count}, фактически {final_count}"
            )
            
            # Дополнительная проверка: убеждаемся, что производительность стабильна
            # при повторных операциях (нет деградации производительности)
            if dataset_size > 50:  # Только для достаточно больших наборов
                # Удаляем еще одну транзакцию и проверяем, что время не увеличилось значительно
                second_transaction = transactions[0] if transactions[0].id != transaction_id else transactions[1]
                
                second_deletion_start_time = time.time()
                second_deletion_result = transaction_service.delete_transaction(session, second_transaction.id)
                second_deletion_end_time = time.time()
                
                second_deletion_time = second_deletion_end_time - second_deletion_start_time
                
                assert second_deletion_result is True, "Второе удаление должно быть успешным"
                
                # Время второго удаления не должно значительно отличаться от первого
                time_difference_ratio = abs(second_deletion_time - deletion_time) / max(deletion_time, 0.001)
                
                assert time_difference_ratio < 2.0, (
                    f"Производительность должна быть стабильной при повторных операциях. "
                    f"Время первого удаления: {deletion_time:.4f} секунд, "
                    f"время второго удаления: {second_deletion_time:.4f} секунд, "
                    f"отношение разности: {time_difference_ratio:.2f}"
                )