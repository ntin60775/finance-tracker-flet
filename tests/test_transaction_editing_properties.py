"""
Property-based тесты для функциональности редактирования транзакций.

Тестирует:
- Property 1: Кнопки действий для всех транзакций
- Property 2: Предзаполнение полей при редактировании
- Property 3: Валидация суммы
- Property 6: Сохранение вызывает update_transaction
- Property 8: Отмена не сохраняет данные
- Property 9: Удаление вызывает delete_transaction
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import uuid
import flet as ft

from finance_tracker.components.transactions_panel import TransactionsPanel
from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.models.models import TransactionDB, TransactionUpdate, CategoryDB
from finance_tracker.models.enums import TransactionType
from property_generators import (
    transaction_dates,
    valid_amounts,
    transaction_descriptions,
    callback_functions
)


class TestTransactionEditingProperties:
    """Property-based тесты для функциональности редактирования транзакций."""

    @given(
        transactions=st.lists(
            st.fixed_dictionaries({
                'id': st.uuids().map(str),
                'amount': valid_amounts(),
                'type': st.sampled_from(TransactionType),
                'description': transaction_descriptions(),
                'category_id': st.uuids().map(str),
                'transaction_date': transaction_dates()
            }),
            min_size=1,
            max_size=10
        ),
        edit_callback=callback_functions(),
        delete_callback=callback_functions()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_action_buttons_for_all_transactions(self, transactions, edit_callback, delete_callback):
        """
        **Feature: transaction-editing, Property 1: Кнопки действий для всех транзакций**
        **Validates: Requirements 1.1, 1.5**
        
        Property: For any транзакция в списке, элемент списка должен содержать кнопки 
        редактирования и удаления с корректными callback функциями.
        """
        # Arrange - создаем mock транзакции
        mock_transactions = []
        for tx_data in transactions:
            mock_tx = Mock(spec=TransactionDB)
            mock_tx.id = tx_data['id']
            mock_tx.amount = tx_data['amount']
            mock_tx.type = tx_data['type']
            mock_tx.description = tx_data['description']
            mock_tx.category_id = tx_data['category_id']
            mock_tx.transaction_date = tx_data['transaction_date']
            mock_transactions.append(mock_tx)
        
        test_date = date.today()
        
        # Act - создаем TransactionsPanel с callback'ами для редактирования и удаления
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=mock_transactions,
            on_add_transaction=Mock(),
            on_edit_transaction=edit_callback,
            on_delete_transaction=delete_callback
        )
        
        # Assert - проверяем наличие кнопок действий для каждой транзакции
        for i, transaction in enumerate(mock_transactions):
            # Получаем элемент списка для данной транзакции
            transaction_container = panel._build_transaction_tile(transaction)
            
            # Проверяем, что это Container с ListTile внутри
            assert isinstance(transaction_container, ft.Container), \
                f"Элемент транзакции {i} должен быть Container"
            
            # Получаем ListTile из Container
            list_tile = transaction_container.content
            assert isinstance(list_tile, ft.ListTile), \
                f"Содержимое контейнера транзакции {i} должно быть ListTile"
            
            # Проверяем наличие trailing элемента с кнопками действий
            assert list_tile.trailing is not None, \
                f"Транзакция {i} должна иметь trailing элемент с кнопками действий"
            
            # В реализации всегда есть кнопки (активные или неактивные)
            # Проверяем структуру trailing элемента
            if isinstance(list_tile.trailing, ft.Row):
                # Если есть кнопки действий, trailing это Row с суммой и кнопками
                trailing_row = list_tile.trailing
                controls = trailing_row.controls
                
                # Первый элемент - сумма (Text), остальные - кнопки
                assert len(controls) >= 1, f"Trailing должен содержать минимум сумму"
                assert isinstance(controls[0], ft.Text), f"Первый элемент должен быть суммой (Text)"
                
                # Проверяем кнопки (всегда есть 2 кнопки - edit и delete, но могут быть disabled)
                action_buttons = controls[1:]  # Все кроме суммы
                assert len(action_buttons) == 2, f"Должно быть 2 кнопки действий (edit и delete)"
                
                # Проверяем кнопку редактирования (первая)
                edit_button = action_buttons[0]
                assert isinstance(edit_button, ft.IconButton), \
                    f"Кнопка редактирования транзакции {i} должна быть IconButton"
                assert edit_button.icon == ft.Icons.EDIT, \
                    f"Кнопка редактирования транзакции {i} должна иметь иконку EDIT"
                
                if edit_callback is not None:
                    assert edit_button.tooltip == "Редактировать", \
                        f"Активная кнопка редактирования должна иметь tooltip 'Редактировать'"
                    assert edit_button.disabled != True, \
                        f"Кнопка редактирования должна быть активна при наличии callback"
                else:
                    assert edit_button.tooltip == "Редактирование недоступно", \
                        f"Неактивная кнопка редактирования должна иметь соответствующий tooltip"
                    assert edit_button.disabled == True, \
                        f"Кнопка редактирования должна быть неактивна при отсутствии callback"
                
                # Проверяем кнопку удаления (вторая)
                delete_button = action_buttons[1]
                assert isinstance(delete_button, ft.IconButton), \
                    f"Кнопка удаления транзакции {i} должна быть IconButton"
                assert delete_button.icon == ft.Icons.DELETE, \
                    f"Кнопка удаления транзакции {i} должна иметь иконку DELETE"
                
                if delete_callback is not None:
                    assert delete_button.tooltip == "Удалить", \
                        f"Активная кнопка удаления должна иметь tooltip 'Удалить'"
                    assert delete_button.disabled != True, \
                        f"Кнопка удаления должна быть активна при наличии callback"
                else:
                    assert delete_button.tooltip == "Удаление недоступно", \
                        f"Неактивная кнопка удаления должна иметь соответствующий tooltip"
                    assert delete_button.disabled == True, \
                        f"Кнопка удаления должна быть неактивна при отсутствии callback"
            else:
                # Если нет кнопок действий, trailing это просто Text с суммой
                assert isinstance(list_tile.trailing, ft.Text), \
                    f"При отсутствии кнопок trailing должен быть Text с суммой"

    @given(
        transaction_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'amount': valid_amounts(),
            'type': st.sampled_from(TransactionType),
            'description': transaction_descriptions(),
            'category_id': st.uuids().map(str),
            'transaction_date': transaction_dates()
        })
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_field_prefilling_on_edit(self, transaction_data):
        """
        **Feature: transaction-editing, Property 2: Предзаполнение полей при редактировании**
        **Validates: Requirements 1.3**
        
        Property: For any транзакция, при открытии модального окна в режиме редактирования 
        все поля формы должны содержать данные этой транзакции.
        """
        # Arrange - создаем mock транзакцию
        mock_transaction = Mock(spec=TransactionDB)
        mock_transaction.id = transaction_data['id']
        mock_transaction.amount = transaction_data['amount']
        mock_transaction.type = transaction_data['type']
        mock_transaction.description = transaction_data['description']
        mock_transaction.category_id = transaction_data['category_id']
        mock_transaction.transaction_date = transaction_data['transaction_date']
        
        mock_session = Mock()
        mock_on_save = Mock()
        mock_on_update = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории для обоих типов
            test_categories = [
                CategoryDB(
                    id=transaction_data['category_id'],
                    name="Test Category",
                    type=transaction_data['type'],
                    is_system=False,
                    created_at=datetime.now()
                ),
                CategoryDB(
                    id=str(uuid.uuid4()),
                    name="Other Category",
                    type=TransactionType.INCOME if transaction_data['type'] == TransactionType.EXPENSE else TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.now()
                )
            ]
            mock_get_categories.return_value = test_categories
            
            # Создаем модальное окно
            modal = TransactionModal(
                session=mock_session,
                on_save=mock_on_save,
                on_update=mock_on_update
            )
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            
            # Act - открываем модальное окно в режиме редактирования
            modal.open_edit(mock_page, mock_transaction)
            
            # Assert - проверяем предзаполнение всех полей
            
            # 1. Режим редактирования должен быть установлен
            assert modal.edit_mode == True, "Должен быть установлен режим редактирования"
            assert modal.editing_transaction == mock_transaction, \
                "Должна быть сохранена ссылка на редактируемую транзакцию"
            
            # 2. Заголовок должен быть изменен
            assert modal.dialog_title.value == "Редактировать транзакцию", \
                "Заголовок должен быть 'Редактировать транзакцию'"
            
            # 3. Поле суммы должно быть предзаполнено
            expected_amount_str = str(transaction_data['amount'])
            assert modal.amount_field.value == expected_amount_str, \
                f"Поле суммы должно содержать '{expected_amount_str}', получено '{modal.amount_field.value}'"
            
            # 4. Тип транзакции должен быть предзаполнен
            assert modal.type_radio.value == transaction_data['type'].value, \
                f"Тип транзакции должен быть '{transaction_data['type'].value}', " \
                f"получено '{modal.type_radio.value}'"
            
            # 5. Категория должна быть предзаполнена
            assert modal.category_dropdown.value == transaction_data['category_id'], \
                f"Категория должна быть '{transaction_data['category_id']}', " \
                f"получено '{modal.category_dropdown.value}'"
            
            # 6. Описание должно быть предзаполнено
            expected_description = transaction_data['description'] or ""
            assert modal.description_field.value == expected_description, \
                f"Описание должно быть '{expected_description}', " \
                f"получено '{modal.description_field.value}'"
            
            # 7. Дата должна быть предзаполнена (в кнопке даты)
            expected_date_str = transaction_data['transaction_date'].strftime("%d.%m.%Y")
            assert modal.date_button.text == expected_date_str, \
                f"Дата должна быть '{expected_date_str}', получено '{modal.date_button.text}'"

    @given(
        amount_value=st.one_of(
            st.decimals(max_value=Decimal('0'), places=2, allow_nan=False, allow_infinity=False),  # Отрицательные и нулевые
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2, allow_nan=False, allow_infinity=False)  # Положительные
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_amount_validation(self, amount_value):
        """
        **Feature: transaction-editing, Property 3: Валидация суммы**
        **Validates: Requirements 2.1, 5.1**
        
        Property: For any сумма <= 0, при попытке сохранения должна отображаться ошибка 
        валидации и сохранение не должно происходить.
        """
        # Arrange - создаем модальное окно в режиме редактирования
        mock_session = Mock()
        mock_on_save = Mock()
        mock_on_update = Mock()
        
        # Создаем mock транзакцию для редактирования
        mock_transaction = Mock(spec=TransactionDB)
        mock_transaction.id = str(uuid.uuid4())
        mock_transaction.amount = Decimal('100.00')
        mock_transaction.type = TransactionType.EXPENSE
        mock_transaction.description = "Test transaction"
        mock_transaction.category_id = str(uuid.uuid4())
        mock_transaction.transaction_date = date.today()
        
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовую категорию
            test_category = CategoryDB(
                id=mock_transaction.category_id,
                name="Test Category",
                type=TransactionType.EXPENSE,
                is_system=False,
                created_at=datetime.now()
            )
            mock_get_categories.return_value = [test_category]
            
            modal = TransactionModal(
                session=mock_session,
                on_save=mock_on_save,
                on_update=mock_on_update
            )
            
            mock_page = MagicMock()
            mock_page.overlay = []
            
            # Открываем в режиме редактирования
            modal.open_edit(mock_page, mock_transaction)
            
            # Act - устанавливаем тестируемую сумму
            modal.amount_field.value = str(amount_value)
            modal.category_dropdown.value = mock_transaction.category_id
            modal.description_field.value = "Test description"
            
            # Сбрасываем предыдущие ошибки
            modal.amount_field.error_text = None
            
            # Попытка сохранения
            modal._save(None)
            
            # Assert - проверяем поведение в зависимости от валидности суммы
            is_valid_amount = amount_value > Decimal('0')
            
            if not is_valid_amount:
                # При невалидной сумме должна быть ошибка валидации
                assert modal.amount_field.error_text is not None, \
                    f"Должна быть ошибка валидации для суммы {amount_value}"
                assert len(modal.amount_field.error_text) > 0, \
                    f"Ошибка валидации не должна быть пустой для суммы {amount_value}"
                
                # Callback обновления не должен быть вызван
                mock_on_update.assert_not_called()
                
                # Модальное окно должно оставаться открытым
                assert modal.dialog.open == True, \
                    "Модальное окно должно оставаться открытым при ошибке валидации"
            else:
                # При валидной сумме не должно быть ошибки валидации
                assert modal.amount_field.error_text is None or modal.amount_field.error_text == "", \
                    f"Не должно быть ошибки валидации для валидной суммы {amount_value}"

    @given(
        transaction_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'amount': valid_amounts(),
            'type': st.sampled_from(TransactionType),
            'description': transaction_descriptions(),
            'category_id': st.uuids().map(str),
            'transaction_date': transaction_dates()
        }),
        new_amount=valid_amounts(),
        new_description=transaction_descriptions()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_6_save_calls_update_transaction(self, transaction_data, new_amount, new_description):
        """
        **Feature: transaction-editing, Property 6: Сохранение вызывает update_transaction**
        **Validates: Requirements 3.1, 7.3, 8.3**
        
        Property: For any валидные данные редактирования, при сохранении должен вызываться 
        transaction_service.update_transaction с правильными параметрами.
        """
        # Arrange - создаем mock транзакцию
        mock_transaction = Mock(spec=TransactionDB)
        mock_transaction.id = transaction_data['id']
        mock_transaction.amount = transaction_data['amount']
        mock_transaction.type = transaction_data['type']
        mock_transaction.description = transaction_data['description']
        mock_transaction.category_id = transaction_data['category_id']
        mock_transaction.transaction_date = transaction_data['transaction_date']
        
        mock_session = Mock()
        mock_on_save = Mock()
        mock_on_update = Mock()
        
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовую категорию
            test_category = CategoryDB(
                id=transaction_data['category_id'],
                name="Test Category",
                type=transaction_data['type'],
                is_system=False,
                created_at=datetime.now()
            )
            mock_get_categories.return_value = [test_category]
            
            modal = TransactionModal(
                session=mock_session,
                on_save=mock_on_save,
                on_update=mock_on_update
            )
            
            mock_page = MagicMock()
            mock_page.overlay = []
            
            # Открываем в режиме редактирования
            modal.open_edit(mock_page, mock_transaction)
            
            # Act - изменяем данные и сохраняем
            modal.amount_field.value = str(new_amount)
            modal.description_field.value = new_description or ""
            modal.category_dropdown.value = transaction_data['category_id']
            
            # Сохраняем
            modal._save(None)
            
            # Assert - проверяем вызов callback с правильными параметрами
            mock_on_update.assert_called_once()
            
            # Получаем аргументы вызова
            call_args = mock_on_update.call_args
            called_transaction_id = call_args[0][0]
            called_update_data = call_args[0][1]
            
            # Проверяем ID транзакции
            assert called_transaction_id == transaction_data['id'], \
                f"Должен быть передан ID транзакции '{transaction_data['id']}', " \
                f"получен '{called_transaction_id}'"
            
            # Проверяем данные обновления
            assert isinstance(called_update_data, TransactionUpdate), \
                "Должен быть передан объект TransactionUpdate"
            
            assert called_update_data.amount == new_amount, \
                f"Сумма в TransactionUpdate должна быть {new_amount}, " \
                f"получена {called_update_data.amount}"
            
            assert called_update_data.type == transaction_data['type'], \
                f"Тип в TransactionUpdate должен быть {transaction_data['type']}, " \
                f"получен {called_update_data.type}"
            
            assert called_update_data.category_id == transaction_data['category_id'], \
                f"ID категории в TransactionUpdate должен быть {transaction_data['category_id']}, " \
                f"получен {called_update_data.category_id}"
            
            expected_description = new_description or ""
            assert called_update_data.description == expected_description, \
                f"Описание в TransactionUpdate должно быть '{expected_description}', " \
                f"получено '{called_update_data.description}'"
            
            # on_save не должен быть вызван в режиме редактирования
            mock_on_save.assert_not_called()

    @given(
        transaction_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'amount': valid_amounts(),
            'type': st.sampled_from(TransactionType),
            'description': transaction_descriptions(),
            'category_id': st.uuids().map(str),
            'transaction_date': transaction_dates()
        }),
        cancel_method=st.sampled_from(['close_button', 'escape_key', 'outside_click'])
    )
    @settings(max_examples=50, deadline=None)
    def test_property_8_cancel_does_not_save_data(self, transaction_data, cancel_method):
        """
        **Feature: transaction-editing, Property 8: Отмена не сохраняет данные**
        **Validates: Requirements 4.1, 4.4**
        
        Property: For any редактирование, при нажатии "Отмена" данные транзакции в БД 
        должны остаться неизменными.
        """
        # Arrange - создаем mock транзакцию
        mock_transaction = Mock(spec=TransactionDB)
        mock_transaction.id = transaction_data['id']
        mock_transaction.amount = transaction_data['amount']
        mock_transaction.type = transaction_data['type']
        mock_transaction.description = transaction_data['description']
        mock_transaction.category_id = transaction_data['category_id']
        mock_transaction.transaction_date = transaction_data['transaction_date']
        
        mock_session = Mock()
        mock_on_save = Mock()
        mock_on_update = Mock()
        
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовую категорию
            test_category = CategoryDB(
                id=transaction_data['category_id'],
                name="Test Category",
                type=transaction_data['type'],
                is_system=False,
                created_at=datetime.now()
            )
            mock_get_categories.return_value = [test_category]
            
            modal = TransactionModal(
                session=mock_session,
                on_save=mock_on_save,
                on_update=mock_on_update
            )
            
            mock_page = MagicMock()
            mock_page.overlay = []
            
            # Открываем в режиме редактирования
            modal.open_edit(mock_page, mock_transaction)
            
            # Act - изменяем данные (но не сохраняем)
            original_amount = modal.amount_field.value
            original_description = modal.description_field.value
            
            # Изменяем поля
            modal.amount_field.value = str(Decimal('999.99'))
            modal.description_field.value = "Changed description"
            
            # Отменяем различными способами
            if cancel_method == 'close_button':
                # Нажимаем кнопку "Отмена"
                modal.close()
            elif cancel_method == 'escape_key':
                # Симулируем нажатие Escape (закрытие диалога)
                modal.dialog.open = False
            elif cancel_method == 'outside_click':
                # Симулируем клик вне диалога (закрытие)
                modal.dialog.open = False
            
            # Assert - проверяем, что данные не были сохранены
            
            # 1. Callback обновления не должен быть вызван
            mock_on_update.assert_not_called()
            
            # 2. Callback создания также не должен быть вызван
            mock_on_save.assert_not_called()
            
            # 3. Модальное окно должно быть закрыто
            assert modal.dialog.open == False, \
                "Модальное окно должно быть закрыто после отмены"
            
            # 4. При повторном открытии поля должны быть предзаполнены оригинальными данными
            modal.open_edit(mock_page, mock_transaction)
            
            # Проверяем, что поля содержат оригинальные данные, а не измененные
            assert modal.amount_field.value == str(transaction_data['amount']), \
                f"После отмены и повторного открытия сумма должна быть оригинальной " \
                f"'{transaction_data['amount']}', получена '{modal.amount_field.value}'"
            
            expected_original_description = transaction_data['description'] or ""
            assert modal.description_field.value == expected_original_description, \
                f"После отмены и повторного открытия описание должно быть оригинальным " \
                f"'{expected_original_description}', получено '{modal.description_field.value}'"

    @given(
        transaction_data=st.fixed_dictionaries({
            'id': st.uuids().map(str),
            'amount': valid_amounts(),
            'type': st.sampled_from(TransactionType),
            'description': transaction_descriptions(),
            'category_id': st.uuids().map(str),
            'transaction_date': transaction_dates()
        }),
        delete_callback=callback_functions().filter(lambda x: x is not None)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_9_delete_calls_delete_transaction(self, transaction_data, delete_callback):
        """
        **Feature: transaction-editing, Property 9: Удаление вызывает delete_transaction**
        **Validates: Requirements 6.2**
        
        Property: For any подтверждённое удаление, должен вызываться 
        transaction_service.delete_transaction с правильным id транзакции.
        """
        # Arrange - создаем mock транзакцию
        mock_transaction = Mock(spec=TransactionDB)
        mock_transaction.id = transaction_data['id']
        mock_transaction.amount = transaction_data['amount']
        mock_transaction.type = transaction_data['type']
        mock_transaction.description = transaction_data['description']
        mock_transaction.category_id = transaction_data['category_id']
        mock_transaction.transaction_date = transaction_data['transaction_date']
        
        test_date = date.today()
        
        # Создаем TransactionsPanel с callback для удаления
        panel = TransactionsPanel(
            date_obj=test_date,
            transactions=[mock_transaction],
            on_add_transaction=Mock(),
            on_edit_transaction=Mock(),
            on_delete_transaction=delete_callback
        )
        
        # Act - симулируем нажатие кнопки удаления
        # Получаем элемент транзакции
        transaction_container = panel._build_transaction_tile(mock_transaction)
        
        # Получаем ListTile из Container
        list_tile = transaction_container.content
        
        # Находим кнопку удаления в trailing элементе
        trailing_row = list_tile.trailing
        assert isinstance(trailing_row, ft.Row), "Trailing должен быть Row с кнопками"
        
        controls = trailing_row.controls
        action_buttons = controls[1:]  # Все кроме суммы (первый элемент)
        
        # Кнопка удаления должна быть второй (после edit)
        assert len(action_buttons) >= 2, "Должно быть минимум 2 кнопки действий"
        delete_button = action_buttons[1]  # Вторая кнопка - delete
        
        assert delete_button.icon == ft.Icons.DELETE, "Вторая кнопка должна быть кнопкой удаления"
        assert delete_button.disabled != True, "Кнопка удаления должна быть активна"
        
        # Симулируем нажатие кнопки удаления через безопасный метод
        panel._safe_delete_transaction(mock_transaction)
        
        # Assert - проверяем вызов callback с правильными параметрами
        if isinstance(delete_callback, (Mock, MagicMock)):
            delete_callback.assert_called_once()
            
            # Получаем аргументы вызова
            call_args = delete_callback.call_args
            called_transaction = call_args[0][0]
            
            # Проверяем, что передана правильная транзакция
            assert called_transaction == mock_transaction, \
                f"Должна быть передана транзакция с ID '{transaction_data['id']}', " \
                f"получена транзакция с ID '{called_transaction.id if hasattr(called_transaction, 'id') else 'unknown'}'"
        
        # Проверяем, что кнопка удаления правильно настроена
        assert delete_button.tooltip == "Удалить", \
            "Кнопка удаления должна иметь tooltip 'Удалить'"
        assert delete_button.on_click is not None, \
            "Кнопка удаления должна иметь обработчик on_click"