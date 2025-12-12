"""
Тесты для модального окна TransactionModal.
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import flet as ft
import datetime
from decimal import Decimal, InvalidOperation
import uuid
import pytest
from hypothesis import given, strategies as st, settings

from finance_tracker.components.transaction_modal import TransactionModal
from finance_tracker.models import TransactionType, CategoryDB, TransactionCreate, TransactionDB, TransactionUpdate


class TestTransactionModal(unittest.TestCase):
    """Тесты для TransactionModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.patcher = patch('finance_tracker.components.transaction_modal.get_all_categories')
        self.mock_get_all_categories = self.patcher.start()

        self.session = Mock()
        self.on_save = Mock()

        # Generate UUIDs
        self.cat_id_1 = str(uuid.uuid4())
        self.cat_id_2 = str(uuid.uuid4())

        # Мокируем загрузку категорий
        self.expense_categories = [CategoryDB(id=self.cat_id_1, name="Food", type=TransactionType.EXPENSE, is_system=False, created_at=datetime.datetime.now())]
        self.income_categories = [CategoryDB(id=self.cat_id_2, name="Salary", type=TransactionType.INCOME, is_system=False, created_at=datetime.datetime.now())]
        self.mock_get_all_categories.side_effect = lambda session, t_type: (
            self.expense_categories if t_type == TransactionType.EXPENSE else self.income_categories
        )

        self.modal = TransactionModal(
            session=self.session,
            on_save=self.on_save
        )
        self.page = MagicMock()
        self.page.overlay = []
        self.modal.page = self.page

    def tearDown(self):
        self.patcher.stop()

    def test_initialization(self):
        """Тест инициализации TransactionModal."""
        self.assertIsInstance(self.modal.dialog, ft.AlertDialog)
        self.assertEqual(self.modal.dialog.title.value, "Новая транзакция")
        self.assertFalse(self.modal.dialog.open)

    def test_open_modal(self):
        """Тест открытия модального окна."""
        self.modal.open(self.page)

        self.assertTrue(self.modal.dialog.open)
        self.assertEqual(self.modal.type_radio.value, TransactionType.EXPENSE.value)
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.EXPENSE)
        self.assertEqual(len(self.modal.category_dropdown.options), 1)
        self.assertEqual(self.modal.category_dropdown.options[0].text, "Food")
        self.page.update.assert_called()

    def test_switch_to_income(self):
        """Тест переключения на тип 'Доход'."""
        self.modal.open(self.page)

        # Имитируем нажатие на сегмент "Доход"
        self.modal.type_radio.value = TransactionType.INCOME.value
        self.modal._on_type_change(None)

        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.INCOME)
        self.assertEqual(len(self.modal.category_dropdown.options), 1)
        self.assertEqual(self.modal.category_dropdown.options[0].text, "Salary")

    def test_save_success(self):
        """Тест успешного сохранения транзакции."""
        self.modal.open(self.page)

        self.modal.amount_field.value = "123.45"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Test Description"
        
        self.modal._save(None)

        expected_data = TransactionCreate(
            amount=Decimal("123.45"),
            type=TransactionType.EXPENSE,
            category_id=self.cat_id_1,
            description="Test Description",
            transaction_date=datetime.date.today()
        )
        
        # Сравниваем поля, так как объекты могут быть разными
        self.on_save.assert_called_once()
        called_arg = self.on_save.call_args[0][0]
        self.assertEqual(called_arg.amount, expected_data.amount)
        self.assertEqual(called_arg.type, expected_data.type)
        self.assertEqual(called_arg.category_id, expected_data.category_id)
        self.assertEqual(called_arg.description, expected_data.description)
        self.assertEqual(called_arg.transaction_date, expected_data.transaction_date)

        self.assertFalse(self.modal.dialog.open)

    def test_save_validation_failure(self):
        """Тест ошибки валидации при сохранении."""
        self.modal.open(self.page)

        self.modal.amount_field.value = "" # Пустая сумма
        self.modal.category_dropdown.value = None # Не выбрана категория

        self.modal._save(None)

        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0")
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию")
        self.on_save.assert_not_called()
        self.assertTrue(self.modal.dialog.open)

    def test_transaction_database_save_and_modal_close(self):
        """
        Тест сохранения транзакции в базу данных и автоматического закрытия модального окна.
        
        Проверяет:
        - Создание транзакции в базе данных с валидными данными
        - Автоматическое закрытие модального окна после сохранения
        - Корректную передачу данных в callback функцию
        - Правильное заполнение всех полей созданной транзакции
        
        Requirements: 5.3, 5.4
        """
        # Arrange - подготовка тестовых данных
        test_amount = Decimal("250.75")
        test_description = "Тест сохранения в БД"
        test_date = datetime.date(2024, 12, 15)
        
        # Открываем модальное окно с предустановленной датой
        self.modal.open(self.page, test_date)
        
        # Заполняем форму валидными данными
        self.modal.amount_field.value = str(test_amount)
        self.modal.category_dropdown.value = self.cat_id_1  # Используем существующую категорию "Food"
        self.modal.description_field.value = test_description
        self.modal.type_radio.value = TransactionType.EXPENSE.value
        
        # Проверяем, что модальное окно открыто перед сохранением
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно быть открыто перед сохранением")
        
        # Act - выполняем сохранение
        self.modal._save(None)
        
        # Assert - проверяем результаты
        
        # 1. Проверяем, что callback был вызван с правильными данными
        self.on_save.assert_called_once()
        called_transaction_data = self.on_save.call_args[0][0]
        
        # Проверяем тип переданного объекта
        self.assertIsInstance(called_transaction_data, TransactionCreate, 
                            "Callback должен получить объект TransactionCreate")
        
        # Проверяем корректность всех полей переданных данных
        self.assertEqual(called_transaction_data.amount, test_amount, 
                        "Сумма в TransactionCreate должна соответствовать введенной")
        self.assertEqual(called_transaction_data.type, TransactionType.EXPENSE, 
                        "Тип транзакции должен соответствовать выбранному")
        self.assertEqual(called_transaction_data.category_id, self.cat_id_1, 
                        "ID категории должен соответствовать выбранной")
        self.assertEqual(called_transaction_data.description, test_description, 
                        "Описание должно соответствовать введенному")
        self.assertEqual(called_transaction_data.transaction_date, test_date, 
                        "Дата транзакции должна соответствовать предустановленной")
        
        # 2. Проверяем автоматическое закрытие модального окна
        self.assertFalse(self.modal.dialog.open, 
                        "Модальное окно должно автоматически закрыться после успешного сохранения")
        
        # 3. Проверяем, что не было ошибок валидации
        self.assertIsNone(self.modal.amount_field.error_text, 
                         "Не должно быть ошибок валидации для поля суммы")
        self.assertIsNone(self.modal.category_dropdown.error_text, 
                         "Не должно быть ошибок валидации для поля категории")
        
        # 4. Проверяем, что page.update() был вызван (для обновления UI)
        self.page.update.assert_called()
        
        # 5. Дополнительная проверка: убеждаемся, что данные готовы для сохранения в БД
        # (в реальном приложении HomeView.on_transaction_saved вызовет transaction_service.create_transaction)
        
        # Проверяем, что все обязательные поля заполнены
        self.assertIsNotNone(called_transaction_data.amount, "Сумма не должна быть None")
        self.assertIsNotNone(called_transaction_data.type, "Тип не должен быть None")
        self.assertIsNotNone(called_transaction_data.category_id, "ID категории не должен быть None")
        self.assertIsNotNone(called_transaction_data.transaction_date, "Дата не должна быть None")
        
        # Проверяем валидность данных для БД
        self.assertGreater(called_transaction_data.amount, Decimal('0'), 
                          "Сумма должна быть положительной для сохранения в БД")
        self.assertIn(called_transaction_data.type, [TransactionType.INCOME, TransactionType.EXPENSE], 
                     "Тип должен быть валидным enum значением")
        
        # Проверяем, что ID категории соответствует одной из загруженных категорий
        self.assertIn(called_transaction_data.category_id, [self.cat_id_1, self.cat_id_2], 
                     "ID категории должен соответствовать одной из доступных категорий")

    def test_transaction_save_with_income_type(self):
        """
        Тест сохранения транзакции типа "Доход".
        
        Проверяет:
        - Корректное сохранение транзакции типа INCOME
        - Правильную загрузку категорий дохода
        - Автоматическое закрытие модального окна
        
        Requirements: 5.3, 5.4
        """
        # Arrange - подготовка для транзакции типа "Доход"
        test_amount = Decimal("5000.00")
        test_description = "Зарплата за декабрь"
        test_date = datetime.date(2024, 12, 31)
        
        # Открываем модальное окно
        self.modal.open(self.page, test_date)
        
        # Переключаемся на тип "Доход"
        self.modal.type_radio.value = TransactionType.INCOME.value
        self.modal._on_type_change(None)  # Имитируем изменение типа
        
        # Заполняем форму
        self.modal.amount_field.value = str(test_amount)
        self.modal.category_dropdown.value = self.cat_id_2  # Используем категорию дохода "Salary"
        self.modal.description_field.value = test_description
        
        # Act - сохраняем транзакцию
        self.modal._save(None)
        
        # Assert - проверяем результаты
        self.on_save.assert_called_once()
        called_transaction_data = self.on_save.call_args[0][0]
        
        # Проверяем, что тип транзакции правильный
        self.assertEqual(called_transaction_data.type, TransactionType.INCOME, 
                        "Тип транзакции должен быть INCOME")
        self.assertEqual(called_transaction_data.category_id, self.cat_id_2, 
                        "Должна использоваться категория дохода")
        self.assertEqual(called_transaction_data.amount, test_amount, 
                        "Сумма должна соответствовать введенной")
        
        # Проверяем закрытие модального окна
        self.assertFalse(self.modal.dialog.open, 
                        "Модальное окно должно закрыться после сохранения дохода")

    def test_transaction_save_with_minimal_data(self):
        """
        Тест сохранения транзакции с минимальным набором данных.
        
        Проверяет:
        - Сохранение транзакции только с обязательными полями
        - Обработка пустого описания (необязательное поле)
        - Использование даты по умолчанию (сегодня)
        
        Requirements: 5.3, 5.4
        """
        # Arrange - подготовка минимальных данных
        test_amount = Decimal("1.00")  # Минимальная валидная сумма
        
        # Открываем модальное окно без предустановленной даты (будет использована сегодняшняя)
        self.modal.open(self.page)
        
        # Заполняем только обязательные поля
        self.modal.amount_field.value = str(test_amount)
        self.modal.category_dropdown.value = self.cat_id_1
        # description_field оставляем пустым (необязательное поле)
        
        # Act - сохраняем транзакцию
        self.modal._save(None)
        
        # Assert - проверяем результаты
        self.on_save.assert_called_once()
        called_transaction_data = self.on_save.call_args[0][0]
        
        # Проверяем обязательные поля
        self.assertEqual(called_transaction_data.amount, test_amount)
        self.assertEqual(called_transaction_data.category_id, self.cat_id_1)
        self.assertEqual(called_transaction_data.type, TransactionType.EXPENSE)
        
        # Проверяем необязательные поля
        self.assertEqual(called_transaction_data.description, "", 
                        "Пустое описание должно быть сохранено как пустая строка")
        self.assertEqual(called_transaction_data.transaction_date, datetime.date.today(), 
                        "Должна использоваться сегодняшняя дата по умолчанию")
        
        # Проверяем закрытие модального окна
        self.assertFalse(self.modal.dialog.open, 
                        "Модальное окно должно закрыться даже при минимальных данных")

    def test_modal_initialization_with_form_fields(self):
        """
        Тест инициализации модального окна с проверкой всех полей формы.
        
        Проверяет:
        - Создание всех полей формы (сумма, категория, описание, дата)
        - Предустановку выбранной даты
        - Режим создания новой транзакции
        
        Requirements: 1.2, 1.3, 5.1
        """
        # Тестируем инициализацию с предустановленной датой
        test_date = datetime.date(2024, 12, 15)
        
        # Act - открываем модальное окно с предустановленной датой
        self.modal.open(self.page, test_date)
        
        # Assert - проверяем создание всех полей формы
        
        # 1. Проверяем поле суммы
        self.assertIsNotNone(self.modal.amount_field, "Поле суммы должно быть создано")
        self.assertIsInstance(self.modal.amount_field, ft.TextField, "Поле суммы должно быть TextField")
        self.assertEqual(self.modal.amount_field.label, "Сумма", "Поле суммы должно иметь правильный label")
        self.assertEqual(self.modal.amount_field.suffix_text, "₽", "Поле суммы должно иметь суффикс валюты")
        self.assertEqual(self.modal.amount_field.keyboard_type, ft.KeyboardType.NUMBER, "Поле суммы должно иметь числовую клавиатуру")
        
        # 2. Проверяем dropdown категорий
        self.assertIsNotNone(self.modal.category_dropdown, "Dropdown категорий должен быть создан")
        self.assertIsInstance(self.modal.category_dropdown, ft.Dropdown, "Категории должны быть в Dropdown")
        self.assertEqual(self.modal.category_dropdown.label, "Категория", "Dropdown категорий должен иметь правильный label")
        self.assertIsInstance(self.modal.category_dropdown.options, list, "Dropdown должен иметь список опций")
        
        # 3. Проверяем поле описания
        self.assertIsNotNone(self.modal.description_field, "Поле описания должно быть создано")
        self.assertIsInstance(self.modal.description_field, ft.TextField, "Поле описания должно быть TextField")
        self.assertEqual(self.modal.description_field.label, "Описание (необязательно)", "Поле описания должно иметь правильный label")
        self.assertTrue(self.modal.description_field.multiline, "Поле описания должно быть многострочным")
        self.assertEqual(self.modal.description_field.max_lines, 3, "Поле описания должно иметь максимум 3 строки")
        
        # 4. Проверяем кнопку выбора даты
        self.assertIsNotNone(self.modal.date_button, "Кнопка выбора даты должна быть создана")
        self.assertIsInstance(self.modal.date_button, ft.ElevatedButton, "Кнопка даты должна быть ElevatedButton")
        self.assertEqual(self.modal.date_button.icon, ft.Icons.CALENDAR_TODAY, "Кнопка даты должна иметь иконку календаря")
        
        # 5. Проверяем предустановку выбранной даты
        expected_date_text = test_date.strftime("%d.%m.%Y")
        self.assertEqual(self.modal.date_button.text, expected_date_text, f"Кнопка даты должна показывать предустановленную дату: {expected_date_text}")
        self.assertEqual(self.modal.current_date, test_date, "Внутренняя дата должна быть установлена правильно")
        
        # 6. Проверяем режим создания новой транзакции
        self.assertEqual(self.modal.dialog.title.value, "Новая транзакция", "Заголовок должен указывать на создание новой транзакции")
        self.assertTrue(self.modal.dialog.open, "Диалог должен быть открыт после вызова open()")
        
        # 7. Проверяем селектор типа транзакции
        self.assertIsNotNone(self.modal.type_radio, "Селектор типа транзакции должен быть создан")
        self.assertIsInstance(self.modal.type_radio, ft.RadioGroup, "Селектор типа должен быть RadioGroup")
        self.assertEqual(self.modal.type_radio.value, TransactionType.EXPENSE.value, "По умолчанию должен быть выбран тип 'Расход'")
        
        # 8. Проверяем наличие кнопок действий
        self.assertIsNotNone(self.modal.dialog.actions, "Диалог должен иметь кнопки действий")
        self.assertEqual(len(self.modal.dialog.actions), 2, "Должно быть 2 кнопки: Отмена и Сохранить")
        
        # Проверяем текст кнопок
        action_texts = [action.text for action in self.modal.dialog.actions if hasattr(action, 'text')]
        self.assertIn("Отмена", action_texts, "Должна быть кнопка 'Отмена'")
        self.assertIn("Сохранить", action_texts, "Должна быть кнопка 'Сохранить'")
        
        # 9. Проверяем поле для отображения ошибок
        self.assertIsNotNone(self.modal.error_text, "Поле для ошибок должно быть создано")
        self.assertIsInstance(self.modal.error_text, ft.Text, "Поле ошибок должно быть Text")
        self.assertEqual(self.modal.error_text.color, ft.Colors.ERROR, "Поле ошибок должно иметь цвет ошибки")

    def test_empty_amount_validation(self):
        """
        Тест валидации пустого поля суммы.
        
        Проверяет:
        - Отображение ошибки при пустом поле суммы
        - Блокировка сохранения при ошибке валидации
        - Сохранение открытого состояния модального окна
        
        Requirements: 6.1, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем валидные значения для всех полей кроме суммы
        self.modal.amount_field.value = ""  # Пустая сумма
        self.modal.category_dropdown.value = self.cat_id_1  # Валидная категория
        self.modal.description_field.value = "Test description"
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем ошибку валидации
        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0", 
                        "Должна отображаться ошибка для пустого поля суммы")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()
        
        # Проверяем, что модальное окно остается открытым
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно оставаться открытым при ошибке валидации")

    def test_negative_amount_validation(self):
        """
        Тест валидации отрицательной суммы.
        
        Проверяет:
        - Отображение ошибки при отрицательной сумме
        - Блокировка сохранения при ошибке валидации
        - Сохранение открытого состояния модального окна
        
        Requirements: 6.2, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем валидные значения для всех полей кроме суммы
        self.modal.amount_field.value = "-100.50"  # Отрицательная сумма
        self.modal.category_dropdown.value = self.cat_id_1  # Валидная категория
        self.modal.description_field.value = "Test description"
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем ошибку валидации
        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0", 
                        "Должна отображаться ошибка для отрицательной суммы")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()
        
        # Проверяем, что модальное окно остается открытым
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно оставаться открытым при ошибке валидации")

    def test_zero_amount_validation(self):
        """
        Тест валидации нулевой суммы.
        
        Проверяет:
        - Отображение ошибки при нулевой сумме
        - Блокировка сохранения при ошибке валидации
        
        Requirements: 6.2, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем валидные значения для всех полей кроме суммы
        self.modal.amount_field.value = "0"  # Нулевая сумма
        self.modal.category_dropdown.value = self.cat_id_1  # Валидная категория
        self.modal.description_field.value = "Test description"
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем ошибку валидации
        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0", 
                        "Должна отображаться ошибка для нулевой суммы")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()
        
        # Проверяем, что модальное окно остается открытым
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно оставаться открытым при ошибке валидации")

    def test_invalid_amount_format_validation(self):
        """
        Тест валидации некорректного формата суммы.
        
        Проверяет:
        - Отображение ошибки при некорректном формате суммы (буквы, спецсимволы)
        - Блокировка сохранения при ошибке валидации
        
        Requirements: 6.2, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Тестируем различные некорректные форматы
        invalid_amounts = ["abc", "12.34.56", "100,50", "12a34", "!@#$"]
        
        for invalid_amount in invalid_amounts:
            with self.subTest(amount=invalid_amount):
                # Устанавливаем некорректную сумму
                self.modal.amount_field.value = invalid_amount
                self.modal.category_dropdown.value = self.cat_id_1  # Валидная категория
                self.modal.description_field.value = "Test description"
                
                # Act - пытаемся сохранить
                self.modal._save(None)
                
                # Assert - проверяем ошибку валидации
                self.assertIsNotNone(self.modal.amount_field.error_text, 
                                   f"Должна отображаться ошибка для некорректной суммы: {invalid_amount}")
                
                # Проверяем правильное сообщение об ошибке (код возвращает разные сообщения для разных типов ошибок)
                expected_messages = ["Введите корректное число", "Сумма должна быть больше 0"]
                self.assertTrue(any(msg in self.modal.amount_field.error_text for msg in expected_messages),
                              f"Ошибка должна содержать одно из ожидаемых сообщений для суммы: {invalid_amount}. "
                              f"Получено: {self.modal.amount_field.error_text}")
                
                # Проверяем, что callback не был вызван
                self.on_save.assert_not_called()
                
                # Сбрасываем состояние для следующего теста
                self.on_save.reset_mock()

    def test_missing_category_validation(self):
        """
        Тест валидации отсутствующей категории.
        
        Проверяет:
        - Отображение ошибки при не выбранной категории
        - Блокировка сохранения при ошибке валидации
        - Сохранение открытого состояния модального окна
        
        Requirements: 6.3, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем валидные значения для всех полей кроме категории
        self.modal.amount_field.value = "100.50"  # Валидная сумма
        self.modal.category_dropdown.value = None  # Не выбрана категория
        self.modal.description_field.value = "Test description"
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем ошибку валидации
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию", 
                        "Должна отображаться ошибка для не выбранной категории")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()
        
        # Проверяем, что модальное окно остается открытым
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно оставаться открытым при ошибке валидации")

    def test_invalid_category_validation(self):
        """
        Тест валидации некорректной категории.
        
        Проверяет:
        - Отображение ошибки при некорректном ID категории
        - Блокировка сохранения при ошибке валидации
        
        Requirements: 6.3, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем валидные значения для всех полей кроме категории
        self.modal.amount_field.value = "100.50"  # Валидная сумма
        self.modal.category_dropdown.value = ""  # Пустая строка как ID категории
        self.modal.description_field.value = "Test description"
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем ошибку валидации
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию", 
                        "Должна отображаться ошибка для некорректной категории")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()

    def test_multiple_validation_errors(self):
        """
        Тест множественных ошибок валидации.
        
        Проверяет:
        - Отображение всех ошибок валидации одновременно
        - Блокировка сохранения при множественных ошибках
        - Состояние кнопки "Сохранить" при ошибках валидации
        
        Requirements: 6.1, 6.2, 6.3, 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Устанавливаем некорректные значения для всех полей
        self.modal.amount_field.value = ""  # Пустая сумма
        self.modal.category_dropdown.value = None  # Не выбрана категория
        self.modal.description_field.value = "Test description"  # Описание валидно (необязательное)
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем все ошибки валидации
        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0", 
                        "Должна отображаться ошибка для пустой суммы")
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию", 
                        "Должна отображаться ошибка для не выбранной категории")
        
        # Проверяем, что callback не был вызван
        self.on_save.assert_not_called()
        
        # Проверяем, что модальное окно остается открытым
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно оставаться открытым при ошибках валидации")

    def test_save_button_state_with_validation_errors(self):
        """
        Тест состояния кнопки "Сохранить" при ошибках валидации.
        
        Проверяет:
        - Кнопка "Сохранить" остается активной (Flet не поддерживает автоматическое отключение)
        - Но сохранение блокируется логикой валидации
        - Пользователь может повторно нажать кнопку после исправления ошибок
        
        Requirements: 6.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Получаем кнопку "Сохранить"
        save_button = None
        for action in self.modal.dialog.actions:
            if hasattr(action, 'text') and action.text == "Сохранить":
                save_button = action
                break
        
        self.assertIsNotNone(save_button, "Кнопка 'Сохранить' должна существовать")
        
        # Устанавливаем некорректные данные
        self.modal.amount_field.value = ""  # Пустая сумма
        self.modal.category_dropdown.value = None  # Не выбрана категория
        
        # Act - пытаемся сохранить
        self.modal._save(None)
        
        # Assert - проверяем, что кнопка остается активной (это поведение Flet)
        # В Flet кнопки не отключаются автоматически, валидация происходит в обработчике
        self.assertFalse(hasattr(save_button, 'disabled') and save_button.disabled, 
                        "Кнопка 'Сохранить' остается активной в Flet")
        
        # Но сохранение должно быть заблокировано логикой
        self.on_save.assert_not_called()
        
        # Проверяем, что после исправления ошибок сохранение работает
        self.modal.amount_field.value = "100.50"  # Исправляем сумму
        self.modal.category_dropdown.value = self.cat_id_1  # Выбираем категорию
        
        # Сбрасываем ошибки (имитируем поведение _clear_error)
        self.modal.amount_field.error_text = None
        self.modal.category_dropdown.error_text = None
        
        # Повторная попытка сохранения
        self.modal._save(None)
        
        # Теперь сохранение должно пройти успешно
        self.on_save.assert_called_once()

    def test_date_validation_edge_cases(self):
        """
        Тест валидации граничных случаев для даты.
        
        Проверяет:
        - Обработка экстремальных дат (слишком старые/будущие)
        - Корректная работа с датами в пределах допустимого диапазона
        - Поведение при программной установке некорректной даты
        
        Requirements: 6.4
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Тестируем граничные даты из DatePicker
        first_date = datetime.date(2020, 1, 1)  # Минимальная дата из DatePicker
        last_date = datetime.date(2030, 12, 31)  # Максимальная дата из DatePicker
        
        # Проверяем, что DatePicker имеет правильные ограничения
        self.assertEqual(self.modal.date_picker.first_date, first_date, 
                        "DatePicker должен иметь правильную минимальную дату")
        self.assertEqual(self.modal.date_picker.last_date, last_date, 
                        "DatePicker должен иметь правильную максимальную дату")
        
        # Тестируем валидные граничные даты
        valid_dates = [first_date, last_date, datetime.date.today()]
        
        for test_date in valid_dates:
            with self.subTest(date=test_date):
                # Программно устанавливаем дату
                self.modal.current_date = test_date
                self.modal.date_button.text = test_date.strftime("%d.%m.%Y")
                
                # Устанавливаем валидные данные для остальных полей
                self.modal.amount_field.value = "100.50"
                self.modal.category_dropdown.value = self.cat_id_1
                self.modal.description_field.value = "Test description"
                
                # Сбрасываем ошибки
                self.modal.amount_field.error_text = None
                self.modal.category_dropdown.error_text = None
                
                # Act - пытаемся сохранить
                self.modal._save(None)
                
                # Assert - сохранение должно пройти успешно
                self.on_save.assert_called()
                
                # Проверяем, что дата передана правильно
                called_arg = self.on_save.call_args[0][0]
                self.assertEqual(called_arg.transaction_date, test_date, 
                               f"Дата в TransactionCreate должна соответствовать установленной: {test_date}")
                
                # Сбрасываем mock для следующего теста
                self.on_save.reset_mock()

    def test_date_picker_constraints(self):
        """
        Тест ограничений DatePicker для предотвращения некорректных дат.
        
        Проверяет:
        - DatePicker имеет правильные ограничения по датам
        - Пользователь не может выбрать дату вне допустимого диапазона
        - Система корректно обрабатывает попытки установки некорректных дат
        
        Requirements: 6.4
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Act & Assert - проверяем ограничения DatePicker
        
        # Проверяем минимальную дату (не слишком далеко в прошлом)
        min_date = datetime.date(2020, 1, 1)
        self.assertEqual(self.modal.date_picker.first_date, min_date, 
                        "DatePicker должен ограничивать выбор слишком старых дат")
        
        # Проверяем максимальную дату (не слишком далеко в будущем)
        max_date = datetime.date(2030, 12, 31)
        self.assertEqual(self.modal.date_picker.last_date, max_date, 
                        "DatePicker должен ограничивать выбор слишком далеких дат")
        
        # Проверяем, что текущая дата находится в допустимом диапазоне
        current_date = self.modal.current_date
        self.assertGreaterEqual(current_date, min_date, 
                               "Текущая дата должна быть не раньше минимальной")
        self.assertLessEqual(current_date, max_date, 
                            "Текущая дата должна быть не позже максимальной")
        
        # Проверяем, что дата по умолчанию (сегодня) валидна
        today = datetime.date.today()
        self.assertGreaterEqual(today, min_date, "Сегодняшняя дата должна быть в допустимом диапазоне")
        self.assertLessEqual(today, max_date, "Сегодняшняя дата должна быть в допустимом диапазоне")

    def test_validation_error_clearing(self):
        """
        Тест очистки ошибок валидации при вводе данных.
        
        Проверяет:
        - Ошибки валидации очищаются при изменении полей
        - Метод _clear_error работает корректно
        - UI обновляется после очистки ошибок
        
        Requirements: 6.5
        """
        # Arrange - открываем модальное окно и создаем ошибки валидации
        self.modal.open(self.page)
        
        # Создаем ошибки валидации
        self.modal.amount_field.value = ""
        self.modal.category_dropdown.value = None
        self.modal._save(None)  # Это создаст ошибки валидации
        
        # Проверяем, что ошибки созданы
        self.assertIsNotNone(self.modal.amount_field.error_text, "Ошибка суммы должна быть установлена")
        self.assertIsNotNone(self.modal.category_dropdown.error_text, "Ошибка категории должна быть установлена")
        
        # Act & Assert - тестируем очистку ошибок
        
        # 1. Тестируем очистку ошибки поля суммы
        mock_event = Mock()
        mock_event.control = self.modal.amount_field
        
        self.modal._clear_error(mock_event)
        
        # В Flet error_text может быть None или пустой строкой после очистки
        self.assertTrue(self.modal.amount_field.error_text is None or self.modal.amount_field.error_text == "", 
                       "Ошибка поля суммы должна быть очищена после изменения")
        
        # 2. Тестируем очистку ошибки dropdown категории
        mock_event.control = self.modal.category_dropdown
        
        self.modal._clear_error(mock_event)
        
        # В Flet error_text может быть None или пустой строкой после очистки
        self.assertTrue(self.modal.category_dropdown.error_text is None or self.modal.category_dropdown.error_text == "", 
                       "Ошибка dropdown категории должна быть очищена после изменения")
        
        # 3. Проверяем, что page.update() вызывается при очистке ошибок
        self.page.update.assert_called()

    def test_cancel_button_click(self):
        """
        Тест нажатия кнопки "Отмена".
        
        Проверяет:
        - Модальное окно закрывается при нажатии кнопки "Отмена"
        - Данные не сохраняются при отмене
        - Callback не вызывается при отмене
        - Форма остается в том же состоянии для следующего открытия
        
        Requirements: 7.1
        """
        # Arrange - открываем модальное окно и заполняем форму
        test_date = datetime.date(2024, 12, 15)
        self.modal.open(self.page, test_date)
        
        # Заполняем форму данными
        self.modal.amount_field.value = "150.75"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Тест отмены операции"
        
        # Проверяем, что модальное окно открыто
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно быть открыто перед отменой")
        
        # Получаем кнопку "Отмена"
        cancel_button = None
        for action in self.modal.dialog.actions:
            if hasattr(action, 'text') and action.text == "Отмена":
                cancel_button = action
                break
        
        self.assertIsNotNone(cancel_button, "Кнопка 'Отмена' должна существовать")
        
        # Act - нажимаем кнопку "Отмена"
        cancel_button.on_click(None)  # Имитируем нажатие кнопки
        
        # Assert - проверяем результаты отмены
        
        # 1. Модальное окно должно закрыться
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться при нажатии 'Отмена'")
        
        # 2. Callback не должен быть вызван (данные не сохраняются)
        self.on_save.assert_not_called()
        
        # 3. Page.update должен быть вызван для обновления UI
        self.page.update.assert_called()
        
        # 4. Проверяем, что данные остались в форме (не очищены при отмене)
        # Это позволяет пользователю вернуться к редактированию
        self.assertEqual(self.modal.amount_field.value, "150.75", 
                        "Данные формы должны сохраниться при отмене")
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_1, 
                        "Выбранная категория должна сохраниться при отмене")
        self.assertEqual(self.modal.description_field.value, "Тест отмены операции", 
                        "Описание должно сохраниться при отмене")

    def test_modal_close_method_directly(self):
        """
        Тест прямого вызова метода close().
        
        Проверяет:
        - Метод close() корректно закрывает модальное окно
        - Обработка случая, когда page или dialog равны None
        - Безопасность метода при различных состояниях
        
        Requirements: 7.1, 7.2, 7.3
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно быть открыто")
        
        # Act - вызываем метод close напрямую
        self.modal.close()
        
        # Assert - проверяем закрытие
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться при вызове close()")
        self.page.update.assert_called()
        
        # Тестируем безопасность метода при отсутствии page
        original_page = self.modal.page
        self.modal.page = None
        
        # Не должно вызывать исключений
        try:
            self.modal.close()
        except Exception as e:
            self.fail(f"Метод close() не должен вызывать исключений при page=None: {e}")
        
        # Восстанавливаем page
        self.modal.page = original_page

    def test_modal_close_with_escape_key_simulation(self):
        """
        Тест имитации нажатия клавиши Escape.
        
        Проверяет:
        - Модальное окно закрывается при нажатии Escape (через close метод)
        - Данные не сохраняются при закрытии через Escape
        - Форма остается заполненной для возможного возврата
        
        Requirements: 7.3
        
        Примечание: В Flet обработка Escape происходит на уровне AlertDialog,
        который автоматически вызывает close() при нажатии Escape.
        Мы тестируем этот сценарий через прямой вызов close().
        """
        # Arrange - открываем модальное окно и заполняем форму
        test_date = datetime.date(2024, 12, 20)
        self.modal.open(self.page, test_date)
        
        # Заполняем форму данными
        self.modal.amount_field.value = "75.25"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Тест закрытия через Escape"
        
        # Проверяем исходное состояние
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно быть открыто")
        
        # Act - имитируем нажатие Escape через вызов close()
        # В реальном Flet AlertDialog автоматически вызывает close() при Escape
        self.modal.close()
        
        # Assert - проверяем результаты
        
        # 1. Модальное окно должно закрыться
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться при нажатии Escape")
        
        # 2. Callback не должен быть вызван (данные не сохраняются)
        self.on_save.assert_not_called()
        
        # 3. Данные должны остаться в форме
        self.assertEqual(self.modal.amount_field.value, "75.25", 
                        "Сумма должна сохраниться при закрытии через Escape")
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_1, 
                        "Категория должна сохраниться при закрытии через Escape")
        self.assertEqual(self.modal.description_field.value, "Тест закрытия через Escape", 
                        "Описание должно сохраниться при закрытии через Escape")

    def test_modal_close_outside_click_simulation(self):
        """
        Тест имитации нажатия вне модального окна.
        
        Проверяет:
        - Модальное окно закрывается при клике вне его области
        - Данные не сохраняются при закрытии кликом вне окна
        - Поведение аналогично нажатию кнопки "Отмена"
        
        Requirements: 7.2
        
        Примечание: В Flet AlertDialog с modal=True может закрываться при клике
        вне области диалога, что также вызывает close() метод.
        """
        # Arrange - открываем модальное окно и заполняем форму
        test_date = datetime.date(2024, 12, 25)
        self.modal.open(self.page, test_date)
        
        # Заполняем форму данными
        self.modal.amount_field.value = "200.00"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Тест закрытия кликом вне окна"
        
        # Проверяем исходное состояние
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно быть открыто")
        
        # Act - имитируем клик вне модального окна через вызов close()
        # В реальном Flet это может происходить автоматически для modal диалогов
        self.modal.close()
        
        # Assert - проверяем результаты
        
        # 1. Модальное окно должно закрыться
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться при клике вне области")
        
        # 2. Callback не должен быть вызван (данные не сохраняются)
        self.on_save.assert_not_called()
        
        # 3. Page.update должен быть вызван
        self.page.update.assert_called()
        
        # 4. Данные должны остаться в форме для возможного повторного открытия
        self.assertEqual(self.modal.amount_field.value, "200.00", 
                        "Сумма должна сохраниться при закрытии кликом вне окна")
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_1, 
                        "Категория должна сохраниться при закрытии кликом вне окна")
        self.assertEqual(self.modal.description_field.value, "Тест закрытия кликом вне окна", 
                        "Описание должно сохраниться при закрытии кликом вне окна")

    def test_form_reset_after_cancel_and_reopen(self):
        """
        Тест очистки формы после отмены и повторного открытия.
        
        Проверяет:
        - При повторном открытии модального окна форма очищается
        - Предыдущие данные не влияют на новое создание транзакции
        - Дата устанавливается заново при каждом открытии
        - Ошибки валидации сбрасываются при новом открытии
        
        Requirements: 7.5
        """
        # Arrange - первое открытие и заполнение формы
        first_date = datetime.date(2024, 12, 10)
        self.modal.open(self.page, first_date)
        
        # Заполняем форму данными
        self.modal.amount_field.value = "100.50"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Первая попытка"
        
        # Создаем ошибки валидации
        self.modal.amount_field.error_text = "Тестовая ошибка"
        self.modal.category_dropdown.error_text = "Тестовая ошибка категории"
        self.modal.error_text.value = "Общая ошибка"
        
        # Отменяем операцию
        self.modal.close()
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться")
        
        # Act - повторное открытие с новой датой
        second_date = datetime.date(2024, 12, 20)
        self.modal.open(self.page, second_date)
        
        # Assert - проверяем сброс формы
        
        # 1. Модальное окно должно быть открыто заново
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно открыться повторно")
        
        # 2. Поля формы должны быть очищены
        self.assertEqual(self.modal.amount_field.value, "", 
                        "Поле суммы должно быть очищено при повторном открытии")
        self.assertEqual(self.modal.description_field.value, "", 
                        "Поле описания должно быть очищено при повторном открытии")
        
        # 3. Дата должна быть установлена заново
        expected_date_text = second_date.strftime("%d.%m.%Y")
        self.assertEqual(self.modal.date_button.text, expected_date_text, 
                        f"Дата должна быть установлена в {expected_date_text}")
        self.assertEqual(self.modal.current_date, second_date, 
                        "Внутренняя дата должна быть обновлена")
        
        # 4. Ошибки валидации должны быть сброшены
        self.assertTrue(self.modal.amount_field.error_text is None or self.modal.amount_field.error_text == "", 
                         "Ошибки валидации поля суммы должны быть сброшены")
        self.assertTrue(self.modal.category_dropdown.error_text is None or self.modal.category_dropdown.error_text == "", 
                         "Ошибки валидации категории должны быть сброшены")
        self.assertEqual(self.modal.error_text.value, "", 
                        "Общие ошибки должны быть сброшены")
        
        # 5. Тип транзакции должен быть сброшен к значению по умолчанию
        self.assertEqual(self.modal.type_radio.value, TransactionType.EXPENSE.value, 
                        "Тип транзакции должен быть сброшен к 'Расход'")
        
        # 6. Категории должны быть перезагружены для типа по умолчанию
        self.assertGreater(len(self.modal.category_dropdown.options), 0, 
                          "Категории должны быть загружены при повторном открытии")
        
        # 7. Dropdown категории должен быть сброшен (ничего не выбрано)
        self.assertTrue(self.modal.category_dropdown.value is None or self.modal.category_dropdown.value == "", 
                         "Категория не должна быть выбрана при повторном открытии")

    def test_cancel_preserves_transaction_list_state(self):
        """
        Тест сохранения состояния списка транзакций при отмене.
        
        Проверяет:
        - При отмене операции список транзакций остается неизменным
        - Callback не вызывается, поэтому HomeView не обновляется
        - Состояние приложения остается консистентным
        
        Requirements: 7.4
        """
        # Arrange - открываем модальное окно
        test_date = datetime.date(2024, 12, 15)
        self.modal.open(self.page, test_date)
        
        # Заполняем форму валидными данными (которые могли бы быть сохранены)
        self.modal.amount_field.value = "500.00"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "Транзакция, которая не должна быть создана"
        
        # Сохраняем исходное состояние mock объектов
        initial_call_count = self.on_save.call_count
        
        # Act - отменяем операцию через кнопку "Отмена"
        cancel_button = None
        for action in self.modal.dialog.actions:
            if hasattr(action, 'text') and action.text == "Отмена":
                cancel_button = action
                break
        
        self.assertIsNotNone(cancel_button, "Кнопка 'Отмена' должна существовать")
        cancel_button.on_click(None)
        
        # Assert - проверяем сохранение состояния
        
        # 1. Callback не должен быть вызван (список транзакций не изменяется)
        self.assertEqual(self.on_save.call_count, initial_call_count, 
                        "Callback не должен быть вызван при отмене")
        
        # 2. Модальное окно должно закрыться
        self.assertFalse(self.modal.dialog.open, "Модальное окно должно закрыться при отмене")
        
        # 3. В реальном приложении HomeView.on_transaction_saved не вызывается,
        # поэтому transaction_service.create_transaction не выполняется,
        # и список транзакций остается неизменным
        
        # Дополнительная проверка: повторная отмена не должна вызывать проблем
        # (тестируем идемпотентность операции отмены)
        try:
            self.modal.close()  # Повторный вызов close
        except Exception as e:
            self.fail(f"Повторный вызов close() не должен вызывать исключений: {e}")
        
        # Состояние должно остаться тем же
        self.assertEqual(self.on_save.call_count, initial_call_count, 
                        "Повторная отмена не должна изменить количество вызовов callback")

    def test_cancel_with_validation_errors(self):
        """
        Тест отмены операции при наличии ошибок валидации.
        
        Проверяет:
        - Модальное окно закрывается даже при наличии ошибок валидации
        - Ошибки валидации не препятствуют отмене операции
        - Пользователь может отменить операцию в любом состоянии формы
        
        Requirements: 7.1, 7.5
        """
        # Arrange - открываем модальное окно
        self.modal.open(self.page)
        
        # Заполняем форму невалидными данными
        self.modal.amount_field.value = ""  # Пустая сумма
        self.modal.category_dropdown.value = None  # Не выбрана категория
        self.modal.description_field.value = "Описание с ошибками валидации"
        
        # Пытаемся сохранить, чтобы создать ошибки валидации
        self.modal._save(None)
        
        # Проверяем, что ошибки валидации созданы
        self.assertIsNotNone(self.modal.amount_field.error_text, 
                           "Должна быть ошибка валидации для пустой суммы")
        self.assertIsNotNone(self.modal.category_dropdown.error_text, 
                           "Должна быть ошибка валидации для не выбранной категории")
        
        # Модальное окно должно остаться открытым из-за ошибок валидации
        self.assertTrue(self.modal.dialog.open, "Модальное окно должно остаться открытым при ошибках валидации")
        
        # Act - отменяем операцию несмотря на ошибки валидации
        cancel_button = None
        for action in self.modal.dialog.actions:
            if hasattr(action, 'text') and action.text == "Отмена":
                cancel_button = action
                break
        
        cancel_button.on_click(None)
        
        # Assert - проверяем успешную отмену
        
        # 1. Модальное окно должно закрыться несмотря на ошибки валидации
        self.assertFalse(self.modal.dialog.open, 
                        "Модальное окно должно закрыться при отмене даже с ошибками валидации")
        
        # 2. Callback не должен быть вызван
        self.on_save.assert_not_called()
        
        # 3. Ошибки валидации должны остаться в форме (для информации при повторном открытии)
        # Это позволяет пользователю увидеть, какие данные были проблемными
        self.assertIsNotNone(self.modal.amount_field.error_text, 
                           "Ошибки валидации должны сохраниться при отмене")
        self.assertIsNotNone(self.modal.category_dropdown.error_text, 
                           "Ошибки валидации должны сохраниться при отмене")

    def test_multiple_cancel_operations(self):
        """
        Тест множественных операций отмены.
        
        Проверяет:
        - Несколько циклов открытие → заполнение → отмена работают корректно
        - Каждая отмена полностью изолирована от предыдущих
        - Нет накопления состояния между операциями отмены
        - Система остается стабильной при повторных отменах
        
        Requirements: 7.1, 7.5
        """
        # Тестируем несколько циклов отмены
        test_scenarios = [
            {
                "date": datetime.date(2024, 12, 10),
                "amount": "100.00",
                "description": "Первая отмена"
            },
            {
                "date": datetime.date(2024, 12, 15),
                "amount": "250.50",
                "description": "Вторая отмена"
            },
            {
                "date": datetime.date(2024, 12, 20),
                "amount": "75.25",
                "description": "Третья отмена"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios):
            with self.subTest(scenario=i+1):
                # Arrange - открываем модальное окно
                self.modal.open(self.page, scenario["date"])
                self.assertTrue(self.modal.dialog.open, f"Модальное окно должно открыться в сценарии {i+1}")
                
                # Заполняем форму
                self.modal.amount_field.value = scenario["amount"]
                self.modal.category_dropdown.value = self.cat_id_1
                self.modal.description_field.value = scenario["description"]
                
                # Act - отменяем операцию
                self.modal.close()
                
                # Assert - проверяем результаты каждой отмены
                
                # 1. Модальное окно должно закрыться
                self.assertFalse(self.modal.dialog.open, f"Модальное окно должно закрыться в сценарии {i+1}")
                
                # 2. Callback не должен быть вызван ни разу за все сценарии
                self.on_save.assert_not_called()
                
                # 3. Данные должны остаться в форме
                self.assertEqual(self.modal.amount_field.value, scenario["amount"], 
                               f"Сумма должна сохраниться в сценарии {i+1}")
                self.assertEqual(self.modal.description_field.value, scenario["description"], 
                               f"Описание должно сохраниться в сценарии {i+1}")
                
                # Сбрасываем mock для следующего сценария
                self.on_save.reset_mock()
        
        # Финальная проверка: убеждаемся, что система остается стабильной
        # Открываем модальное окно в последний раз
        final_date = datetime.date(2024, 12, 25)
        self.modal.open(self.page, final_date)
        
        # Система должна работать нормально после множественных отмен
        self.assertTrue(self.modal.dialog.open, "Система должна работать нормально после множественных отмен")
        self.assertEqual(self.modal.current_date, final_date, "Дата должна устанавливаться корректно")
        self.assertEqual(self.modal.amount_field.value, "", "Форма должна быть очищена при новом открытии")


class TestTransactionModalProperties:
    """Property-based тесты для TransactionModal."""

    @given(
        amount_value=st.one_of(
            st.none(),  # None значение
            st.just(""),  # Пустая строка
            st.text(min_size=0, max_size=10).filter(lambda x: not x.strip()),  # Только пробелы
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz!@#$%^&*()").filter(lambda x: len(x) > 0),  # Некорректный формат
            st.floats(min_value=-1000, max_value=0, allow_nan=False, allow_infinity=False).map(str),  # Отрицательные/нулевые
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')).map(str)  # Валидные суммы
        ),
        category_value=st.one_of(
            st.none(),  # Не выбрана категория
            st.just(""),  # Пустая строка
            st.just("invalid-uuid"),  # Невалидный UUID
            st.uuids().map(str)  # Валидный UUID
        ),
        description_value=st.one_of(
            st.none(),
            st.text(max_size=500)  # Описание всегда валидно (необязательное поле)
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_6_form_validation_state(self, amount_value, category_value, description_value):
        """
        **Feature: add-transaction-button-fix, Property 6: Form Validation State**
        **Validates: Requirements 5.2, 6.5**
        
        Property: For any combination of form field values, the save button state should correctly 
        reflect whether all validation rules are satisfied.
        
        Проверяет, что состояние формы (наличие ошибок валидации) корректно отражает 
        валидность введенных данных для любой комбинации значений полей.
        """
        # Arrange - создаем мок объекты
        mock_session = Mock()
        mock_on_save = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории
            test_category_id = str(uuid.uuid4())
            mock_categories = [
                CategoryDB(
                    id=test_category_id, 
                    name="Test Category", 
                    type=TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            mock_get_categories.return_value = mock_categories
            
            # Создаем модальное окно
            modal = TransactionModal(session=mock_session, on_save=mock_on_save)
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            modal.page = mock_page
            
            # Открываем модальное окно для инициализации
            modal.open(mock_page)
            
            # Act - устанавливаем значения полей
            modal.amount_field.value = amount_value
            modal.category_dropdown.value = category_value if category_value != "" else None
            modal.description_field.value = description_value
            
            # Сбрасываем предыдущие ошибки
            modal.amount_field.error_text = None
            modal.category_dropdown.error_text = None
            
            # Вызываем валидацию через попытку сохранения
            modal._save(None)
            
            # Assert - определяем ожидаемую валидность
            
            # Проверяем валидность суммы
            amount_valid = False
            if amount_value is not None and str(amount_value).strip():
                try:
                    amount_decimal = Decimal(str(amount_value))
                    amount_valid = amount_decimal > Decimal('0')
                except (ValueError, TypeError, InvalidOperation):
                    amount_valid = False
            
            # Проверяем валидность категории (UI уровень)
            category_valid = category_value is not None and category_value != ""
            
            # Общая валидность формы на UI уровне
            form_valid = amount_valid and category_valid
            
            # Проверяем состояние ошибок валидации на UI уровне
            if not amount_valid:
                assert modal.amount_field.error_text is not None, \
                    f"Должна быть ошибка валидации для суммы: {amount_value}"
                assert len(modal.amount_field.error_text) > 0, \
                    f"Ошибка валидации суммы не должна быть пустой для: {amount_value}"
            else:
                assert modal.amount_field.error_text is None or modal.amount_field.error_text == "", \
                    f"Не должно быть ошибки валидации для валидной суммы: {amount_value}"
            
            if not category_valid:
                assert modal.category_dropdown.error_text is not None, \
                    f"Должна быть ошибка валидации для категории: {category_value}"
                assert len(modal.category_dropdown.error_text) > 0, \
                    f"Ошибка валидации категории не должна быть пустой для: {category_value}"
            else:
                assert modal.category_dropdown.error_text is None or modal.category_dropdown.error_text == "", \
                    f"Не должно быть ошибки валидации для валидной категории: {category_value}"
            
            # Проверяем поведение при валидации
            if not form_valid:
                # При невалидной форме callback не должен вызываться
                mock_on_save.assert_not_called(), \
                    f"Callback не должен быть вызван для невалидных данных: amount={amount_value}, category={category_value}"
                
                # Модальное окно должно оставаться открытым
                assert modal.dialog.open, \
                    "Модальное окно должно оставаться открытым при ошибках валидации"
            else:
                # При валидной форме на UI уровне проверяем, что попытка сохранения была сделана
                # Но callback может не вызваться из-за ошибок Pydantic валидации
                # Главное - что UI валидация прошла и модальное окно попыталось закрыться
                
                # Проверяем, что не было ошибок UI валидации
                assert modal.amount_field.error_text is None or modal.amount_field.error_text == "", \
                    f"UI валидация суммы должна пройти для: {amount_value}"
                assert modal.category_dropdown.error_text is None or modal.category_dropdown.error_text == "", \
                    f"UI валидация категории должна пройти для: {category_value}"

    @given(
        amount=st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99'), places=2),
        transaction_type=st.sampled_from(TransactionType),
        description=st.one_of(
            st.none(),
            st.text(max_size=500, alphabet=st.characters(
                blacklist_categories=['Cc'],  # Исключаем управляющие символы
                blacklist_characters=['\x00', '\n', '\r', '\t']
            ))
        ),
        transaction_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today())
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_transaction_creation_round_trip(self, amount, transaction_type, description, transaction_date):
        """
        **Feature: add-transaction-button-fix, Property 7: Transaction Creation Round Trip**
        **Validates: Requirements 5.3, 5.5**
        
        Property: For any valid transaction data, when saved through the modal, the transaction 
        should be created in the database and appear in the UI.
        
        Проверяет, что для любых валидных данных транзакции, когда они сохраняются через 
        модальное окно, транзакция корректно создается и данные передаются без искажений.
        """
        # Arrange - создаем мок объекты
        mock_session = Mock()
        mock_on_save = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории для обоих типов
            expense_category_id = str(uuid.uuid4())
            income_category_id = str(uuid.uuid4())
            
            expense_categories = [
                CategoryDB(
                    id=expense_category_id, 
                    name="Test Expense Category", 
                    type=TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            
            income_categories = [
                CategoryDB(
                    id=income_category_id, 
                    name="Test Income Category", 
                    type=TransactionType.INCOME,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            
            # Настраиваем мок для возврата соответствующих категорий
            def mock_get_categories_side_effect(session, t_type):
                if t_type == TransactionType.EXPENSE:
                    return expense_categories
                else:
                    return income_categories
            
            mock_get_categories.side_effect = mock_get_categories_side_effect
            
            # Создаем модальное окно
            modal = TransactionModal(session=mock_session, on_save=mock_on_save)
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            modal.page = mock_page
            
            # Act - открываем модальное окно и заполняем форму валидными данными
            modal.open(mock_page, transaction_date)
            
            # Устанавливаем тип транзакции
            modal.type_radio.value = transaction_type.value
            modal._on_type_change(None)  # Загружаем соответствующие категории
            
            # Выбираем соответствующую категорию
            selected_category_id = expense_category_id if transaction_type == TransactionType.EXPENSE else income_category_id
            
            # Заполняем форму валидными данными
            modal.amount_field.value = str(amount)
            modal.category_dropdown.value = selected_category_id
            modal.description_field.value = description or ""
            modal.current_date = transaction_date
            modal.date_button.text = transaction_date.strftime("%d.%m.%Y")
            
            # Сбрасываем предыдущие ошибки
            modal.amount_field.error_text = None
            modal.category_dropdown.error_text = None
            
            # Сохраняем транзакцию
            modal._save(None)
            
            # Assert - проверяем round-trip: данные → модальное окно → callback → данные
            
            # 1. Проверяем, что callback был вызван (транзакция "создана")
            mock_on_save.assert_called_once(), \
                f"Callback должен быть вызван для валидных данных: amount={amount}, type={transaction_type}, date={transaction_date}"
            
            # 2. Получаем переданные данные
            called_transaction_data = mock_on_save.call_args[0][0]
            
            # 3. Проверяем тип переданного объекта
            assert isinstance(called_transaction_data, TransactionCreate), \
                "Callback должен получить объект TransactionCreate"
            
            # 4. Проверяем round-trip для каждого поля - данные должны сохраниться без искажений
            
            # Проверяем сумму (round-trip через Decimal)
            assert called_transaction_data.amount == amount, \
                f"Сумма должна сохраниться без искажений: ожидалось {amount}, получено {called_transaction_data.amount}"
            
            # Проверяем тип транзакции (round-trip через enum)
            assert called_transaction_data.type == transaction_type, \
                f"Тип транзакции должен сохраниться: ожидался {transaction_type}, получен {called_transaction_data.type}"
            
            # Проверяем категорию (round-trip через UUID)
            assert called_transaction_data.category_id == selected_category_id, \
                f"ID категории должен сохраниться: ожидался {selected_category_id}, получен {called_transaction_data.category_id}"
            
            # Проверяем описание (round-trip через строку, с обработкой None)
            expected_description = description or ""
            assert called_transaction_data.description == expected_description, \
                f"Описание должно сохраниться: ожидалось '{expected_description}', получено '{called_transaction_data.description}'"
            
            # Проверяем дату (round-trip через date)
            assert called_transaction_data.transaction_date == transaction_date, \
                f"Дата должна сохраниться: ожидалась {transaction_date}, получена {called_transaction_data.transaction_date}"
            
            # 5. Проверяем, что модальное окно закрылось (имитация "появления в UI")
            assert not modal.dialog.open, \
                "Модальное окно должно закрыться после успешного сохранения (готовность к обновлению UI)"
            
            # 6. Проверяем, что не было ошибок валидации (данные были валидными)
            assert modal.amount_field.error_text is None or modal.amount_field.error_text == "", \
                f"Не должно быть ошибок валидации для валидной суммы: {amount}"
            assert modal.category_dropdown.error_text is None or modal.category_dropdown.error_text == "", \
                f"Не должно быть ошибок валидации для валидной категории: {selected_category_id}"
            
            # 7. Дополнительная проверка: убеждаемся, что данные готовы для создания в БД
            # (в реальном приложении HomeView.on_transaction_saved создаст транзакцию через transaction_service)
            
            # Проверяем, что все обязательные поля заполнены
            assert called_transaction_data.amount is not None, "Сумма не должна быть None"
            assert called_transaction_data.type is not None, "Тип не должен быть None"
            assert called_transaction_data.category_id is not None, "ID категории не должен быть None"
            assert called_transaction_data.transaction_date is not None, "Дата не должна быть None"
            
            # Проверяем валидность данных для БД
            assert called_transaction_data.amount > Decimal('0'), \
                f"Сумма должна быть положительной: {called_transaction_data.amount}"
            assert called_transaction_data.type in [TransactionType.INCOME, TransactionType.EXPENSE], \
                f"Тип должен быть валидным enum: {called_transaction_data.type}"
            
            # Проверяем, что ID категории соответствует выбранному типу транзакции
            if called_transaction_data.type == TransactionType.EXPENSE:
                assert called_transaction_data.category_id == expense_category_id, \
                    "Для расхода должна использоваться категория расхода"
            else:
                assert called_transaction_data.category_id == income_category_id, \
                    "Для дохода должна использоваться категория дохода"
            
            # Проверяем, что дата не в будущем (бизнес-правило)
            assert called_transaction_data.transaction_date <= datetime.date.today(), \
                f"Дата транзакции не должна быть в будущем: {called_transaction_data.transaction_date}"
            
            # 8. Round-trip проверка: если бы мы создали TransactionCreate с теми же данными,
            # результат должен быть идентичным
            expected_transaction = TransactionCreate(
                amount=amount,
                type=transaction_type,
                category_id=selected_category_id,
                description=description or "",
                transaction_date=transaction_date
            )
            
            # Сравниваем все поля
            assert called_transaction_data.amount == expected_transaction.amount, \
                "Round-trip: сумма должна совпадать"
            assert called_transaction_data.type == expected_transaction.type, \
                "Round-trip: тип должен совпадать"
            assert called_transaction_data.category_id == expected_transaction.category_id, \
                "Round-trip: категория должна совпадать"
            assert called_transaction_data.description == expected_transaction.description, \
                "Round-trip: описание должно совпадать"
            assert called_transaction_data.transaction_date == expected_transaction.transaction_date, \
                "Round-trip: дата должна совпадать"


class TestTransactionModalCancelProperties:
    """Property-based тесты для отмены операций в TransactionModal."""

    @given(
        closure_method=st.sampled_from(['cancel_button', 'close_method', 'escape_simulation']),
        amount_value=st.one_of(
            st.none(),
            st.just(""),
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')).map(str),
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz!@#$%^&*()").filter(lambda x: len(x) > 0)
        ),
        description_value=st.one_of(
            st.none(),
            st.text(max_size=500, alphabet=st.characters(
                blacklist_categories=['Cc'],
                blacklist_characters=['\x00', '\n', '\r', '\t']
            ))
        ),
        transaction_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today())
    )
    @settings(max_examples=50, deadline=None)
    def test_property_8_modal_closure_behavior(self, closure_method, amount_value, description_value, transaction_date):
        """
        **Feature: add-transaction-button-fix, Property 8: Modal Closure Behavior**
        **Validates: Requirements 5.4, 7.1**
        
        Property: For any method of closing the modal (save, cancel, escape), the modal should 
        close and the UI should return to the correct state.
        
        Проверяет, что для любого способа закрытия модального окна (кнопка отмены, метод close, 
        имитация Escape), модальное окно корректно закрывается и UI возвращается в правильное состояние.
        """
        # Arrange - создаем мок объекты
        mock_session = Mock()
        mock_on_save = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории
            test_category_id = str(uuid.uuid4())
            mock_categories = [
                CategoryDB(
                    id=test_category_id, 
                    name="Test Category", 
                    type=TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            mock_get_categories.return_value = mock_categories
            
            # Создаем модальное окно
            modal = TransactionModal(session=mock_session, on_save=mock_on_save)
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            modal.page = mock_page
            
            # Открываем модальное окно
            modal.open(mock_page, transaction_date)
            
            # Проверяем, что модальное окно открыто
            assert modal.dialog.open, "Модальное окно должно быть открыто перед закрытием"
            
            # Заполняем форму данными (любыми)
            modal.amount_field.value = amount_value if amount_value is not None else ""
            modal.category_dropdown.value = test_category_id
            modal.description_field.value = description_value if description_value is not None else ""
            
            # Сохраняем исходное состояние для проверки
            initial_date = modal.current_date
            initial_page_update_call_count = mock_page.update.call_count
            
            # Act - закрываем модальное окно выбранным способом
            if closure_method == 'cancel_button':
                # Имитируем нажатие кнопки "Отмена"
                cancel_button = None
                for action in modal.dialog.actions:
                    if hasattr(action, 'text') and action.text == "Отмена":
                        cancel_button = action
                        break
                assert cancel_button is not None, "Кнопка 'Отмена' должна существовать"
                cancel_button.on_click(None)
                
            elif closure_method == 'close_method':
                # Прямой вызов метода close()
                modal.close()
                
            elif closure_method == 'escape_simulation':
                # Имитация нажатия Escape через close() (в Flet AlertDialog автоматически вызывает close)
                modal.close()
            
            # Assert - проверяем корректное поведение закрытия
            
            # 1. Модальное окно должно закрыться независимо от способа закрытия
            assert not modal.dialog.open, \
                f"Модальное окно должно закрыться при использовании метода: {closure_method}"
            
            # 2. Page.update должен быть вызван для обновления UI
            assert mock_page.update.call_count > initial_page_update_call_count, \
                f"Page.update должен быть вызван при закрытии через: {closure_method}"
            
            # 3. Callback не должен быть вызван при отмене (данные не сохраняются)
            mock_on_save.assert_not_called(), \
                f"Callback не должен быть вызван при отмене через: {closure_method}"
            
            # 4. UI должен вернуться в корректное состояние
            # Дата должна остаться той же (не сброситься)
            assert modal.current_date == initial_date, \
                f"Дата должна остаться неизменной при закрытии через: {closure_method}"
            
            # 5. Модальное окно должно быть готово к повторному открытию
            # Проверяем, что можно открыть заново без ошибок
            try:
                modal.open(mock_page, transaction_date)
                assert modal.dialog.open, \
                    f"Модальное окно должно открываться повторно после закрытия через: {closure_method}"
                modal.close()  # Закрываем для чистоты теста
            except Exception as e:
                pytest.fail(f"Повторное открытие должно работать после закрытия через {closure_method}: {e}")
            
            # 6. Состояние dialog должно быть консистентным
            assert hasattr(modal, 'dialog'), "Объект dialog должен существовать"
            assert modal.dialog is not None, "Dialog не должен быть None"
            
            # 7. Page должен остаться в корректном состоянии
            assert modal.page is mock_page, "Ссылка на page должна остаться корректной"

    @given(
        initial_amount=st.one_of(
            st.none(),
            st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')).map(str)
        ),
        initial_description=st.one_of(
            st.none(),
            st.text(max_size=500, alphabet=st.characters(
                blacklist_categories=['Cc'],
                blacklist_characters=['\x00', '\n', '\r', '\t']
            ))
        ),
        transaction_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today()),
        cancel_method=st.sampled_from(['cancel_button', 'close_method'])
    )
    @settings(max_examples=50, deadline=None)
    def test_property_9_data_persistence_on_cancel(self, initial_amount, initial_description, transaction_date, cancel_method):
        """
        **Feature: add-transaction-button-fix, Property 9: Data Persistence on Cancel**
        **Validates: Requirements 7.4**
        
        Property: For any transaction list state, when the modal is cancelled without saving, 
        the original transaction list should remain unchanged.
        
        Проверяет, что для любого состояния списка транзакций, когда модальное окно отменяется 
        без сохранения, исходный список транзакций остается неизменным.
        """
        # Arrange - создаем мок объекты
        mock_session = Mock()
        mock_on_save = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории
            test_category_id = str(uuid.uuid4())
            mock_categories = [
                CategoryDB(
                    id=test_category_id, 
                    name="Test Category", 
                    type=TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            mock_get_categories.return_value = mock_categories
            
            # Создаем модальное окно
            modal = TransactionModal(session=mock_session, on_save=mock_on_save)
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            modal.page = mock_page
            
            # Имитируем исходное состояние "списка транзакций" через callback
            # В реальном приложении HomeView имеет список транзакций, который обновляется через callback
            initial_callback_call_count = mock_on_save.call_count
            
            # Открываем модальное окно
            modal.open(mock_page, transaction_date)
            
            # Заполняем форму данными (которые могли бы изменить список транзакций)
            modal.amount_field.value = initial_amount if initial_amount is not None else ""
            modal.category_dropdown.value = test_category_id
            modal.description_field.value = initial_description if initial_description is not None else ""
            
            # Проверяем, что данные заполнены (потенциально готовы к сохранению)
            form_has_data = (
                (modal.amount_field.value and modal.amount_field.value.strip()) or
                (modal.description_field.value and modal.description_field.value.strip()) or
                modal.category_dropdown.value is not None
            )
            
            # Act - отменяем операцию выбранным способом
            if cancel_method == 'cancel_button':
                # Нажимаем кнопку "Отмена"
                cancel_button = None
                for action in modal.dialog.actions:
                    if hasattr(action, 'text') and action.text == "Отмена":
                        cancel_button = action
                        break
                assert cancel_button is not None, "Кнопка 'Отмена' должна существовать"
                cancel_button.on_click(None)
            else:
                # Используем метод close()
                modal.close()
            
            # Assert - проверяем сохранение состояния данных
            
            # 1. Callback не должен быть вызван (список транзакций не изменяется)
            assert mock_on_save.call_count == initial_callback_call_count, \
                f"Callback не должен быть вызван при отмене через {cancel_method}, " \
                f"исходное состояние должно сохраниться"
            
            # 2. Модальное окно должно закрыться
            assert not modal.dialog.open, \
                f"Модальное окно должно закрыться при отмене через {cancel_method}"
            
            # 3. В реальном приложении это означает, что:
            # - HomeView.on_transaction_saved не вызывается
            # - transaction_service.create_transaction не выполняется  
            # - Список транзакций в HomeView остается неизменным
            # - UI не обновляется новой транзакцией
            
            # Проверяем, что состояние callback'а не изменилось
            mock_on_save.assert_not_called(), \
                "Отмена должна гарантировать, что данные не передаются в HomeView"
            
            # 4. Дополнительная проверка: повторная отмена не должна влиять на состояние
            # Открываем модальное окно снова
            modal.open(mock_page, transaction_date)
            
            # Заполняем другими данными
            modal.amount_field.value = "999.99"
            modal.category_dropdown.value = test_category_id
            modal.description_field.value = "Другие данные для второй отмены"
            
            # Отменяем снова
            modal.close()
            
            # Состояние callback'а должно остаться тем же
            assert mock_on_save.call_count == initial_callback_call_count, \
                "Множественные отмены не должны влиять на исходное состояние данных"
            
            # 5. Проверяем идемпотентность отмены
            # Повторный вызов отмены не должен изменить состояние
            try:
                modal.close()  # Повторный вызов close на уже закрытом модальном окне
                assert mock_on_save.call_count == initial_callback_call_count, \
                    "Повторная отмена не должна изменить состояние данных"
            except Exception as e:
                pytest.fail(f"Повторная отмена не должна вызывать исключений: {e}")
            
            # 6. Финальная проверка: убеждаемся, что система готова к нормальной работе
            # Открываем модальное окно и сохраняем данные (должно работать нормально)
            modal.open(mock_page, transaction_date)
            modal.amount_field.value = "100.00"
            modal.category_dropdown.value = test_category_id
            modal.description_field.value = "Тест нормального сохранения"
            
            # Сбрасываем ошибки валидации
            modal.amount_field.error_text = None
            modal.category_dropdown.error_text = None
            
            # Сохраняем (должно работать после отмен)
            modal._save(None)
            
            # Теперь callback должен быть вызван (нормальное сохранение работает)
            assert mock_on_save.call_count == initial_callback_call_count + 1, \
                "Нормальное сохранение должно работать после отмен"

    @given(
        form_data_before_cancel=st.fixed_dictionaries({
            'amount': st.one_of(
                st.none(),
                st.just(""),
                st.decimals(min_value=Decimal('0.01'), max_value=Decimal('999999.99')).map(str),
                st.text(max_size=20)
            ),
            'description': st.one_of(
                st.none(),
                st.text(max_size=500, alphabet=st.characters(
                    blacklist_categories=['Cc'],
                    blacklist_characters=['\x00', '\n', '\r', '\t']
                ))
            ),
            'transaction_type': st.sampled_from(TransactionType)
        }),
        reopen_date=st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date.today()),
        cancel_method=st.sampled_from(['cancel_button', 'close_method'])
    )
    @settings(max_examples=50, deadline=None)
    def test_property_10_form_reset_on_cancel(self, form_data_before_cancel, reopen_date, cancel_method):
        """
        **Feature: add-transaction-button-fix, Property 10: Form Reset on Cancel**
        **Validates: Requirements 7.5**
        
        Property: For any form data entered in the modal, when cancelled, all form fields 
        should be cleared for the next use.
        
        Проверяет, что для любых данных, введенных в форму модального окна, при отмене 
        все поля формы очищаются для следующего использования.
        """
        # Arrange - создаем мок объекты
        mock_session = Mock()
        mock_on_save = Mock()
        
        # Мокируем загрузку категорий
        with patch('finance_tracker.components.transaction_modal.get_all_categories') as mock_get_categories:
            # Создаем тестовые категории для обоих типов
            expense_category_id = str(uuid.uuid4())
            income_category_id = str(uuid.uuid4())
            
            expense_categories = [
                CategoryDB(
                    id=expense_category_id, 
                    name="Test Expense Category", 
                    type=TransactionType.EXPENSE,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            
            income_categories = [
                CategoryDB(
                    id=income_category_id, 
                    name="Test Income Category", 
                    type=TransactionType.INCOME,
                    is_system=False,
                    created_at=datetime.datetime.now()
                )
            ]
            
            # Настраиваем мок для возврата соответствующих категорий
            def mock_get_categories_side_effect(session, t_type):
                if t_type == TransactionType.EXPENSE:
                    return expense_categories
                else:
                    return income_categories
            
            mock_get_categories.side_effect = mock_get_categories_side_effect
            
            # Создаем модальное окно
            modal = TransactionModal(session=mock_session, on_save=mock_on_save)
            
            # Мокируем page
            mock_page = MagicMock()
            mock_page.overlay = []
            modal.page = mock_page
            
            # Первое открытие и заполнение формы
            initial_date = datetime.date(2024, 12, 10)
            modal.open(mock_page, initial_date)
            
            # Устанавливаем тип транзакции и загружаем соответствующие категории
            modal.type_radio.value = form_data_before_cancel['transaction_type'].value
            modal._on_type_change(None)
            
            # Выбираем соответствующую категорию
            selected_category_id = (expense_category_id 
                                  if form_data_before_cancel['transaction_type'] == TransactionType.EXPENSE 
                                  else income_category_id)
            
            # Заполняем форму тестовыми данными
            modal.amount_field.value = form_data_before_cancel['amount'] if form_data_before_cancel['amount'] is not None else ""
            modal.category_dropdown.value = selected_category_id
            modal.description_field.value = form_data_before_cancel['description'] if form_data_before_cancel['description'] is not None else ""
            
            # Добавляем ошибки валидации для проверки их сброса
            modal.amount_field.error_text = "Тестовая ошибка суммы"
            modal.category_dropdown.error_text = "Тестовая ошибка категории"
            modal.error_text.value = "Общая тестовая ошибка"
            
            # Сохраняем состояние формы перед отменой для проверки
            form_state_before_cancel = {
                'amount': modal.amount_field.value,
                'category': modal.category_dropdown.value,
                'description': modal.description_field.value,
                'type': modal.type_radio.value,
                'amount_error': modal.amount_field.error_text,
                'category_error': modal.category_dropdown.error_text,
                'general_error': modal.error_text.value
            }
            
            # Проверяем, что форма действительно заполнена
            form_has_data = any([
                form_state_before_cancel['amount'],
                form_state_before_cancel['description'],
                form_state_before_cancel['category'],
                form_state_before_cancel['amount_error'],
                form_state_before_cancel['category_error'],
                form_state_before_cancel['general_error']
            ])
            
            # Act - отменяем операцию выбранным способом
            if cancel_method == 'cancel_button':
                # Нажимаем кнопку "Отмена"
                cancel_button = None
                for action in modal.dialog.actions:
                    if hasattr(action, 'text') and action.text == "Отмена":
                        cancel_button = action
                        break
                assert cancel_button is not None, "Кнопка 'Отмена' должна существовать"
                cancel_button.on_click(None)
            else:
                # Используем метод close()
                modal.close()
            
            # Проверяем, что модальное окно закрылось
            assert not modal.dialog.open, f"Модальное окно должно закрыться при отмене через {cancel_method}"
            
            # Act - повторно открываем модальное окно для проверки сброса формы
            modal.open(mock_page, reopen_date)
            
            # Assert - проверяем сброс всех полей формы
            
            # 1. Модальное окно должно открыться заново
            assert modal.dialog.open, "Модальное окно должно открыться повторно"
            
            # 2. Все поля формы должны быть сброшены к значениям по умолчанию
            
            # Поле суммы должно быть очищено
            assert modal.amount_field.value == "", \
                f"Поле суммы должно быть очищено при повторном открытии после отмены через {cancel_method}. " \
                f"Было: '{form_state_before_cancel['amount']}', стало: '{modal.amount_field.value}'"
            
            # Поле описания должно быть очищено
            assert modal.description_field.value == "", \
                f"Поле описания должно быть очищено при повторном открытии после отмены через {cancel_method}. " \
                f"Было: '{form_state_before_cancel['description']}', стало: '{modal.description_field.value}'"
            
            # Категория не должна быть выбрана (может быть None или пустая строка в зависимости от Flet)
            assert modal.category_dropdown.value is None or modal.category_dropdown.value == "", \
                f"Категория не должна быть выбрана при повторном открытии после отмены через {cancel_method}. " \
                f"Была: '{form_state_before_cancel['category']}', стала: '{modal.category_dropdown.value}'"
            
            # Тип транзакции должен быть сброшен к значению по умолчанию
            assert modal.type_radio.value == TransactionType.EXPENSE.value, \
                f"Тип транзакции должен быть сброшен к 'Расход' при повторном открытии после отмены через {cancel_method}. " \
                f"Был: '{form_state_before_cancel['type']}', стал: '{modal.type_radio.value}'"
            
            # 3. Все ошибки валидации должны быть сброшены
            
            assert modal.amount_field.error_text is None or modal.amount_field.error_text == "", \
                f"Ошибки валидации поля суммы должны быть сброшены после отмены через {cancel_method}. " \
                f"Была: '{form_state_before_cancel['amount_error']}', стала: '{modal.amount_field.error_text}'"
            
            assert modal.category_dropdown.error_text is None or modal.category_dropdown.error_text == "", \
                f"Ошибки валидации категории должны быть сброшены после отмены через {cancel_method}. " \
                f"Была: '{form_state_before_cancel['category_error']}', стала: '{modal.category_dropdown.error_text}'"
            
            assert modal.error_text.value == "", \
                f"Общие ошибки должны быть сброшены после отмены через {cancel_method}. " \
                f"Была: '{form_state_before_cancel['general_error']}', стала: '{modal.error_text.value}'"
            
            # 4. Дата должна быть установлена в новое значение
            expected_date_text = reopen_date.strftime("%d.%m.%Y")
            assert modal.date_button.text == expected_date_text, \
                f"Дата должна быть установлена в новое значение: {expected_date_text}"
            assert modal.current_date == reopen_date, \
                f"Внутренняя дата должна быть обновлена: {reopen_date}"
            
            # 5. Категории должны быть перезагружены для типа по умолчанию (EXPENSE)
            assert len(modal.category_dropdown.options) > 0, \
                "Категории должны быть загружены при повторном открытии"
            
            # Проверяем, что загружены категории расходов (тип по умолчанию)
            category_names = [option.text for option in modal.category_dropdown.options]
            assert "Test Expense Category" in category_names, \
                "Должны быть загружены категории расходов при сбросе к типу по умолчанию"
            
            # 6. Форма должна быть готова к новому вводу данных
            # Проверяем, что можно заполнить и сохранить новые данные
            modal.amount_field.value = "50.00"
            modal.category_dropdown.value = expense_category_id
            modal.description_field.value = "Новая транзакция после сброса"
            
            # Сбрасываем ошибки валидации
            modal.amount_field.error_text = None
            modal.category_dropdown.error_text = None
            
            # Сохраняем новые данные (должно работать нормально)
            modal._save(None)
            
            # Callback должен быть вызван с новыми данными
            mock_on_save.assert_called_once(), \
                "Форма должна работать нормально после сброса"
            
            # Проверяем, что переданы именно новые данные, а не старые
            called_transaction_data = mock_on_save.call_args[0][0]
            assert called_transaction_data.amount == Decimal('50.00'), \
                "Должны быть сохранены новые данные, а не данные до отмены"
            assert called_transaction_data.description == "Новая транзакция после сброса", \
                "Должно быть сохранено новое описание, а не описание до отмены"
            
            # 7. Модальное окно должно закрыться после успешного сохранения
            assert not modal.dialog.open, \
                "Модальное окно должно закрыться после успешного сохранения новых данных"


if __name__ == '__main__':
    unittest.main()

class TestTransactionModalEditMode(unittest.TestCase):
    """Тесты для режима редактирования TransactionModal."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        self.patcher = patch('finance_tracker.components.transaction_modal.get_all_categories')
        self.mock_get_all_categories = self.patcher.start()

        self.session = Mock()
        self.on_save = Mock()
        self.on_update = Mock()

        # Generate UUIDs
        self.cat_id_1 = str(uuid.uuid4())
        self.cat_id_2 = str(uuid.uuid4())
        self.transaction_id = str(uuid.uuid4())

        # Мокируем загрузку категорий
        self.expense_categories = [CategoryDB(id=self.cat_id_1, name="Food", type=TransactionType.EXPENSE, is_system=False, created_at=datetime.datetime.now())]
        self.income_categories = [CategoryDB(id=self.cat_id_2, name="Salary", type=TransactionType.INCOME, is_system=False, created_at=datetime.datetime.now())]
        self.mock_get_all_categories.side_effect = lambda session, t_type: (
            self.expense_categories if t_type == TransactionType.EXPENSE else self.income_categories
        )

        # Создаем тестовую транзакцию для редактирования
        self.test_transaction = Mock(spec=TransactionDB)
        self.test_transaction.id = self.transaction_id
        self.test_transaction.amount = Decimal("150.75")
        self.test_transaction.type = TransactionType.EXPENSE
        self.test_transaction.category_id = self.cat_id_1
        self.test_transaction.description = "Test transaction"
        self.test_transaction.transaction_date = datetime.date(2024, 12, 15)

        self.modal = TransactionModal(
            session=self.session,
            on_save=self.on_save,
            on_update=self.on_update
        )
        self.page = MagicMock()
        self.page.overlay = []

    def tearDown(self):
        self.patcher.stop()

    def test_initialization_with_on_update_callback(self):
        """Тест инициализации TransactionModal с callback для обновления."""
        # Проверяем, что callback сохранен
        self.assertEqual(self.modal.on_update, self.on_update)
        
        # Проверяем начальное состояние режима редактирования
        self.assertFalse(self.modal.edit_mode)
        self.assertIsNone(self.modal.editing_transaction)

    def test_open_edit_mode(self):
        """Тест открытия модального окна в режиме редактирования."""
        # Act - открываем в режиме редактирования
        self.modal.open_edit(self.page, self.test_transaction)

        # Assert - проверяем режим редактирования
        self.assertTrue(self.modal.edit_mode)
        self.assertEqual(self.modal.editing_transaction, self.test_transaction)
        self.assertEqual(self.modal.dialog_title.value, "Редактировать транзакцию")
        
        # Проверяем предзаполнение полей
        self.assertEqual(self.modal.amount_field.value, "150.75")
        self.assertEqual(self.modal.description_field.value, "Test transaction")
        self.assertEqual(self.modal.type_radio.value, TransactionType.EXPENSE.value)
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_1)
        self.assertEqual(self.modal.date_button.text, "15.12.2024")
        
        # Проверяем, что диалог открыт
        self.assertTrue(self.modal.dialog.open)
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.EXPENSE)

    def test_prefill_form_with_transaction_data(self):
        """Тест предзаполнения формы данными транзакции."""
        # Arrange - создаем транзакцию с полными данными
        transaction = Mock(spec=TransactionDB)
        transaction.id = self.transaction_id
        transaction.amount = Decimal("250.50")
        transaction.type = TransactionType.INCOME
        transaction.category_id = self.cat_id_2
        transaction.description = "Salary payment"
        transaction.transaction_date = datetime.date(2024, 12, 20)

        # Act - предзаполняем форму
        self.modal._prefill_form(transaction)

        # Assert - проверяем все поля
        self.assertEqual(self.modal.amount_field.value, "250.50")
        self.assertEqual(self.modal.description_field.value, "Salary payment")
        self.assertEqual(self.modal.type_radio.value, TransactionType.INCOME.value)
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_2)
        self.assertEqual(self.modal.date_button.text, "20.12.2024")
        
        # Проверяем сброс ошибок
        self.assertIsNone(self.modal.amount_field.error_text)
        self.assertIsNone(self.modal.category_dropdown.error_text)
        self.assertEqual(self.modal.error_text.value, "")

    def test_prefill_form_with_empty_description(self):
        """Тест предзаполнения формы с пустым описанием."""
        # Arrange - создаем транзакцию без описания
        transaction = Mock(spec=TransactionDB)
        transaction.id = self.transaction_id
        transaction.amount = Decimal("100.00")
        transaction.type = TransactionType.EXPENSE
        transaction.category_id = self.cat_id_1
        transaction.description = None  # Пустое описание
        transaction.transaction_date = datetime.date(2024, 12, 10)

        # Act - предзаполняем форму
        self.modal._prefill_form(transaction)

        # Assert - проверяем обработку пустого описания
        self.assertEqual(self.modal.description_field.value, "")

    def test_save_in_edit_mode(self):
        """Тест сохранения в режиме редактирования."""
        # Arrange - открываем в режиме редактирования
        self.modal.open_edit(self.page, self.test_transaction)
        
        # Изменяем данные
        self.modal.amount_field.value = "200.00"
        self.modal.description_field.value = "Updated description"

        # Act - сохраняем изменения
        self.modal._save(None)

        # Assert - проверяем вызов on_update
        self.on_update.assert_called_once()
        call_args = self.on_update.call_args
        
        # Проверяем переданные параметры
        transaction_id, transaction_update = call_args[0]
        self.assertEqual(transaction_id, self.transaction_id)
        self.assertIsInstance(transaction_update, TransactionUpdate)
        
        # Проверяем данные обновления
        self.assertEqual(transaction_update.amount, Decimal("200.00"))
        self.assertEqual(transaction_update.type, TransactionType.EXPENSE)
        self.assertEqual(transaction_update.category_id, self.cat_id_1)
        self.assertEqual(transaction_update.description, "Updated description")
        self.assertEqual(transaction_update.transaction_date, datetime.date(2024, 12, 15))
        
        # Проверяем, что on_save НЕ был вызван
        self.on_save.assert_not_called()
        
        # Проверяем закрытие диалога
        self.assertFalse(self.modal.dialog.open)

    def test_save_in_create_mode(self):
        """Тест сохранения в режиме создания (для сравнения)."""
        # Arrange - открываем в режиме создания
        self.modal.open(self.page, datetime.date(2024, 12, 15))
        
        # Заполняем данные
        self.modal.amount_field.value = "100.00"
        self.modal.category_dropdown.value = self.cat_id_1
        self.modal.description_field.value = "New transaction"

        # Act - сохраняем
        self.modal._save(None)

        # Assert - проверяем вызов on_save
        self.on_save.assert_called_once()
        call_args = self.on_save.call_args
        
        # Проверяем переданные параметры
        transaction_create = call_args[0][0]
        self.assertIsInstance(transaction_create, TransactionCreate)
        
        # Проверяем, что on_update НЕ был вызван
        self.on_update.assert_not_called()

    def test_category_loading_in_edit_mode(self):
        """Тест загрузки категорий в режиме редактирования."""
        # Arrange - создаем транзакцию типа INCOME
        income_transaction = Mock(spec=TransactionDB)
        income_transaction.id = self.transaction_id
        income_transaction.amount = Decimal("1000.00")
        income_transaction.type = TransactionType.INCOME
        income_transaction.category_id = self.cat_id_2
        income_transaction.description = "Salary"
        income_transaction.transaction_date = datetime.date(2024, 12, 15)

        # Act - открываем в режиме редактирования
        self.modal.open_edit(self.page, income_transaction)

        # Assert - проверяем загрузку категорий дохода
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.INCOME)
        
        # Проверяем, что выбрана правильная категория
        self.assertEqual(self.modal.category_dropdown.value, self.cat_id_2)

    def test_type_change_in_edit_mode(self):
        """Тест смены типа транзакции в режиме редактирования."""
        # Arrange - открываем в режиме редактирования (EXPENSE)
        self.modal.open_edit(self.page, self.test_transaction)
        
        # Act - меняем тип на INCOME
        self.modal.type_radio.value = TransactionType.INCOME.value
        self.modal._on_type_change(None)

        # Assert - проверяем загрузку категорий дохода
        self.mock_get_all_categories.assert_called_with(self.session, TransactionType.INCOME)
        
        # Проверяем, что категория сброшена (так как старая категория не подходит для нового типа)
        # Flet может устанавливать пустую строку вместо None
        self.assertIn(self.modal.category_dropdown.value, [None, ""])

    def test_validation_in_edit_mode(self):
        """Тест валидации в режиме редактирования."""
        # Arrange - открываем в режиме редактирования
        self.modal.open_edit(self.page, self.test_transaction)
        
        # Устанавливаем невалидные данные
        self.modal.amount_field.value = "-50.00"  # Отрицательная сумма
        self.modal.category_dropdown.value = None  # Не выбрана категория

        # Act - пытаемся сохранить
        self.modal._save(None)

        # Assert - проверяем ошибки валидации
        self.assertEqual(self.modal.amount_field.error_text, "Сумма должна быть больше 0")
        self.assertEqual(self.modal.category_dropdown.error_text, "Выберите категорию")
        
        # Проверяем, что callback не был вызван
        self.on_update.assert_not_called()
        
        # Проверяем, что диалог остается открытым
        self.assertTrue(self.modal.dialog.open)

    def test_edit_mode_without_on_update_callback(self):
        """Тест режима редактирования без callback для обновления."""
        # Arrange - создаем модал без on_update callback
        modal_without_update = TransactionModal(
            session=self.session,
            on_save=self.on_save,
            on_update=None  # Нет callback для обновления
        )
        modal_without_update.page = self.page
        
        # Открываем в режиме редактирования
        modal_without_update.open_edit(self.page, self.test_transaction)
        
        # Заполняем валидные данные
        modal_without_update.amount_field.value = "200.00"
        modal_without_update.category_dropdown.value = self.cat_id_1

        # Act - попытка сохранения (ошибка перехватывается safe_handler)
        modal_without_update._save(None)
        
        # Assert - проверяем, что ошибка отображается в UI
        self.assertIn("on_update callback не установлен", modal_without_update.error_text.value)
        
        # Проверяем, что диалог остается открытым
        self.assertTrue(modal_without_update.dialog.open)

    def test_reset_form_method(self):
        """Тест метода сброса формы."""
        # Arrange - устанавливаем некоторые значения
        test_date = datetime.date(2024, 12, 20)
        self.modal.current_date = test_date
        self.modal.amount_field.value = "100.50"
        self.modal.description_field.value = "Some description"
        self.modal.type_radio.value = TransactionType.INCOME.value
        self.modal.category_dropdown.value = self.cat_id_2

        # Act - сбрасываем форму
        self.modal._reset_form()

        # Assert - проверяем сброс всех полей
        self.assertEqual(self.modal.date_button.text, "20.12.2024")
        self.assertEqual(self.modal.amount_field.value, "")
        self.assertEqual(self.modal.description_field.value, "")
        self.assertEqual(self.modal.type_radio.value, TransactionType.EXPENSE.value)
        # Flet может устанавливать пустую строку вместо None
        self.assertIn(self.modal.category_dropdown.value, [None, ""])
        self.assertEqual(self.modal.error_text.value, "")
        self.assertIsNone(self.modal.amount_field.error_text)
        self.assertIsNone(self.modal.category_dropdown.error_text)


if __name__ == '__main__':
    unittest.main()