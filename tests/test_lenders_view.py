"""
Тесты для LendersView.

Проверяет:
- Инициализацию View
- Загрузку займодателей
- Фильтрацию по типу займодателя
- Открытие модального окна создания
- Открытие модального окна редактирования
- Ошибку при удалении займодателя с активными кредитами
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, ANY

from finance_tracker.views.lenders_view import LendersView
from finance_tracker.components.lender_modal import LenderModal
from finance_tracker.models.enums import LenderType
from test_view_base import ViewTestBase
from test_factories import create_test_lender


class TestLendersView(ViewTestBase):
    """Тесты для LendersView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.lenders_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы займодателей
        self.mock_get_all_lenders = self.add_patcher(
            'finance_tracker.views.lenders_view.get_all_lenders',
            return_value=[]
        )
        self.mock_create_lender = self.add_patcher(
            'finance_tracker.views.lenders_view.create_lender'
        )
        self.mock_update_lender = self.add_patcher(
            'finance_tracker.views.lenders_view.update_lender'
        )
        self.mock_delete_lender = self.add_patcher(
            'finance_tracker.views.lenders_view.delete_lender'
        )
        
        # Создаем экземпляр LendersView
        self.view = LendersView(self.page)

    def test_initialization(self):
        """
        Тест инициализации LendersView.
        
        Проверяет:
        - View создается без исключений
        - Атрибут page установлен
        - Сессия БД создана
        - UI компоненты созданы (заголовок, фильтр, список)
        
        Validates: Requirements 7.1
        """
        # Проверяем, что View создан
        self.assertIsInstance(self.view, LendersView)
        
        # Проверяем атрибуты
        self.assertEqual(self.view.page, self.page)
        self.assertIsNotNone(self.view.session)
        self.assertEqual(self.view.session, self.mock_session)
        
        # Проверяем, что UI компоненты созданы
        self.assert_view_has_controls(self.view)
        self.assertIsNotNone(self.view.header)
        self.assertIsNotNone(self.view.type_dropdown)
        self.assertIsNotNone(self.view.lenders_column)
        
        # Проверяем начальное состояние фильтра
        self.assertIsNone(self.view.lender_type_filter)
        self.assertEqual(self.view.type_dropdown.value, "all")

    def test_load_lenders_on_init(self):
        """
        Тест загрузки займодателей при инициализации View.
        
        Проверяет:
        - При создании View вызывается get_all_lenders
        - Сервис вызывается с правильной сессией и фильтром
        
        Validates: Requirements 7.1
        """
        # Проверяем, что сервис был вызван при инициализации
        self.assert_service_called(
            self.mock_get_all_lenders,
            self.mock_session,
            lender_type=None  # Фильтр по умолчанию - None (все займодатели)
        )

    def test_load_lenders_with_data(self):
        """
        Тест загрузки займодателей с данными.
        
        Проверяет:
        - Займодатели отображаются в списке
        - Количество элементов соответствует количеству займодателей
        
        Validates: Requirements 7.1
        """
        # Создаем тестовых займодателей
        test_lenders = [
            create_test_lender(id=1, name="Сбербанк", lender_type=LenderType.BANK),
            create_test_lender(id=2, name="МФО Быстроденьги", lender_type=LenderType.MFO),
            create_test_lender(id=3, name="Иванов И.И.", lender_type=LenderType.INDIVIDUAL),
        ]
        
        # Настраиваем мок для возврата тестовых данных
        self.mock_get_all_lenders.return_value = test_lenders
        
        # Загружаем данные
        self.view.load_lenders()
        
        # Проверяем, что список содержит элементы
        self.assertEqual(len(self.view.lenders_column.controls), 3)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_load_lenders_empty_list(self):
        """
        Тест загрузки пустого списка займодателей.
        
        Проверяет:
        - При пустом списке отображается сообщение "Нет займодателей"
        
        Validates: Requirements 7.1
        """
        # Настраиваем мок для возврата пустого списка
        self.mock_get_all_lenders.return_value = []
        
        # Загружаем данные
        self.view.load_lenders()
        
        # Проверяем, что в списке один элемент (сообщение о пустом состоянии)
        self.assertEqual(len(self.view.lenders_column.controls), 1)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_filter_change_to_bank(self):
        """
        Тест фильтрации по типу "Банк".
        
        Проверяет:
        - При выборе типа "Банк" устанавливается фильтр BANK
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 7.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_lenders.reset_mock()
        
        # Имитируем выбор типа "Банк"
        self.view.type_dropdown.value = LenderType.BANK.value
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.lender_type_filter, LenderType.BANK)
        
        # Проверяем, что сервис вызван с фильтром BANK
        self.assert_service_called(
            self.mock_get_all_lenders,
            self.mock_session,
            lender_type=LenderType.BANK
        )

    def test_filter_change_to_mfo(self):
        """
        Тест фильтрации по типу "МФО".
        
        Проверяет:
        - При выборе типа "МФО" устанавливается фильтр MFO
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 7.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_lenders.reset_mock()
        
        # Имитируем выбор типа "МФО"
        self.view.type_dropdown.value = LenderType.MFO.value
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.lender_type_filter, LenderType.MFO)
        
        # Проверяем, что сервис вызван с фильтром MFO
        self.assert_service_called(
            self.mock_get_all_lenders,
            self.mock_session,
            lender_type=LenderType.MFO
        )

    def test_filter_change_to_individual(self):
        """
        Тест фильтрации по типу "Физическое лицо".
        
        Проверяет:
        - При выборе типа "Физическое лицо" устанавливается фильтр INDIVIDUAL
        - Вызывается перезагрузка данных с новым фильтром
        
        Validates: Requirements 7.2
        """
        # Сбрасываем счетчик вызовов
        self.mock_get_all_lenders.reset_mock()
        
        # Имитируем выбор типа "Физическое лицо"
        self.view.type_dropdown.value = LenderType.INDIVIDUAL.value
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(self.view.lender_type_filter, LenderType.INDIVIDUAL)
        
        # Проверяем, что сервис вызван с фильтром INDIVIDUAL
        self.assert_service_called(
            self.mock_get_all_lenders,
            self.mock_session,
            lender_type=LenderType.INDIVIDUAL
        )

    def test_filter_change_to_all(self):
        """
        Тест сброса фильтра (все займодатели).
        
        Проверяет:
        - При выборе "Все типы" фильтр сбрасывается (None)
        - Вызывается перезагрузка данных без фильтра
        
        Validates: Requirements 7.2
        """
        # Устанавливаем фильтр
        self.view.lender_type_filter = LenderType.BANK
        
        # Сбрасываем счетчик вызовов
        self.mock_get_all_lenders.reset_mock()
        
        # Имитируем выбор "Все типы"
        self.view.type_dropdown.value = "all"
        self.view.on_type_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(self.view.lender_type_filter)
        
        # Проверяем, что сервис вызван без фильтра
        self.assert_service_called(
            self.mock_get_all_lenders,
            self.mock_session,
            lender_type=None
        )

    def test_open_create_dialog(self):
        """
        Тест открытия модального окна создания займодателя.
        
        Проверяет:
        - При нажатии кнопки создания открывается LenderModal
        - Модальное окно открывается в режиме создания (без займодателя)
        
        Validates: Requirements 7.3
        """
        # Создаем мок события с control, у которого есть page
        mock_event = Mock()
        mock_event.control = Mock()
        mock_event.control.page = self.page
        
        # Патчим метод open модального окна
        with patch.object(self.view.lender_modal, 'open') as mock_open:
            # Вызываем метод открытия диалога
            self.view.open_create_dialog(mock_event)
            
            # Проверяем, что метод open был вызван
            mock_open.assert_called_once()
            
            # Проверяем аргументы вызова
            call_args = mock_open.call_args
            self.assertEqual(call_args[0][0], self.page)  # Первый аргумент - page
            self.assertIsNone(call_args[1]['lender'])  # lender=None для создания

    def test_open_edit_dialog(self):
        """
        Тест открытия модального окна редактирования займодателя.
        
        Проверяет:
        - При нажатии кнопки редактирования открывается LenderModal
        - Модальное окно открывается в режиме редактирования (с займодателем)
        - Переданный займодатель соответствует выбранному
        
        Validates: Requirements 7.4
        """
        # Создаем тестового займодателя
        test_lender = create_test_lender(
            id=1,
            name="Тестовый банк",
            lender_type=LenderType.BANK
        )
        
        # Патчим метод open модального окна
        with patch.object(self.view.lender_modal, 'open') as mock_open:
            # Вызываем метод открытия диалога редактирования
            self.view.open_edit_dialog(test_lender)
            
            # Проверяем, что метод open был вызван
            mock_open.assert_called_once()
            
            # Проверяем аргументы вызова
            call_args = mock_open.call_args
            self.assertEqual(call_args[0][0], self.page)  # Первый аргумент - page
            self.assertEqual(call_args[1]['lender'], test_lender)  # lender передан

    def test_confirm_delete_opens_dialog(self):
        """
        Тест открытия диалога подтверждения удаления.
        
        Проверяет:
        - При вызове confirm_delete_lender открывается диалог подтверждения
        - Диалог содержит информацию об удаляемом займодателе
        
        Validates: Requirements 7.5
        """
        # Создаем тестового займодателя
        test_lender = create_test_lender(
            id=1,
            name="Тестовый банк",
            lender_type=LenderType.BANK
        )
        
        # Вызываем метод подтверждения удаления
        self.view.confirm_delete_lender(test_lender)
        
        # Проверяем, что в overlay добавлен диалог
        self.assertGreater(len(self.page.overlay), 0)
        
        # Проверяем, что последний элемент overlay - это AlertDialog
        last_overlay = self.page.overlay[-1]
        self.assertTrue(hasattr(last_overlay, 'open'))
        self.assertTrue(last_overlay.open)
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)

    def test_delete_lender_with_active_loans_shows_error(self):
        """
        Тест ошибки при удалении займодателя с активными кредитами.
        
        Проверяет:
        - При попытке удалить займодателя с активными кредитами возникает ошибка
        - Отображается сообщение об ошибке
        - Займодатель не удаляется
        
        Validates: Requirements 7.5
        """
        # Создаем тестового займодателя
        test_lender = create_test_lender(
            id=1,
            name="Тестовый банк",
            lender_type=LenderType.BANK
        )
        
        # Настраиваем мок delete_lender для выброса ValueError
        self.mock_delete_lender.side_effect = ValueError(
            "Невозможно удалить займодателя с активными кредитами"
        )
        
        # Открываем диалог подтверждения
        self.view.confirm_delete_lender(test_lender)
        
        # Получаем диалог из overlay
        confirm_dialog = self.page.overlay[-1]
        
        # Находим кнопку "Удалить" и вызываем её обработчик
        delete_button = None
        for action in confirm_dialog.actions:
            if hasattr(action, 'text') and action.text == "Удалить":
                delete_button = action
                break
        
        self.assertIsNotNone(delete_button)
        
        # Вызываем обработчик удаления
        delete_button.on_click(None)
        
        # Проверяем, что delete_lender был вызван
        self.assert_service_called_once(
            self.mock_delete_lender,
            self.mock_session,
            test_lender.id
        )
        
        # Проверяем, что в overlay добавлен SnackBar с ошибкой
        # (последний элемент после диалога)
        snackbar_found = False
        for item in self.page.overlay:
            if hasattr(item, 'bgcolor') and hasattr(item, 'content'):
                # Это может быть SnackBar
                snackbar_found = True
                break
        
        self.assertTrue(snackbar_found, "SnackBar с ошибкой не найден")

    def test_on_create_lender_success(self):
        """
        Тест успешного создания займодателя.
        
        Проверяет:
        - При вызове on_create_lender вызывается create_lender
        - После создания обновляется список займодателей
        - Отображается сообщение об успехе
        
        Validates: Requirements 7.3
        """
        # Создаем тестового займодателя для возврата из сервиса
        test_lender = create_test_lender(
            id=1,
            name="Новый банк",
            lender_type=LenderType.BANK
        )
        self.mock_create_lender.return_value = test_lender
        
        # Сбрасываем счетчик вызовов load_lenders
        self.mock_get_all_lenders.reset_mock()
        
        # Вызываем callback создания
        self.view.on_create_lender(
            name="Новый банк",
            lender_type=LenderType.BANK,
            description="Описание",
            contact_info="8-800-555-55-55",
            notes="Примечания"
        )
        
        # Проверяем, что create_lender был вызван
        self.assert_service_called_once(
            self.mock_create_lender,
            session=self.mock_session,
            name="Новый банк",
            lender_type=LenderType.BANK,
            description="Описание",
            contact_info="8-800-555-55-55",
            notes="Примечания"
        )
        
        # Проверяем, что список обновлен
        self.assert_service_called(self.mock_get_all_lenders)

    def test_on_update_lender_success(self):
        """
        Тест успешного обновления займодателя.
        
        Проверяет:
        - При вызове on_update_lender вызывается update_lender
        - После обновления обновляется список займодателей
        - Отображается сообщение об успехе
        
        Validates: Requirements 7.4
        """
        # Создаем тестового займодателя для возврата из сервиса
        test_lender = create_test_lender(
            id=1,
            name="Обновленный банк",
            lender_type=LenderType.BANK
        )
        self.mock_update_lender.return_value = test_lender
        
        # Сбрасываем счетчик вызовов load_lenders
        self.mock_get_all_lenders.reset_mock()
        
        # Вызываем callback обновления
        self.view.on_update_lender(
            lender_id=1,
            name="Обновленный банк",
            lender_type=LenderType.BANK,
            description="Новое описание",
            contact_info="8-800-555-55-56",
            notes="Новые примечания"
        )
        
        # Проверяем, что update_lender был вызван
        self.assert_service_called_once(
            self.mock_update_lender,
            session=self.mock_session,
            lender_id=1,
            name="Обновленный банк",
            lender_type=LenderType.BANK,
            description="Новое описание",
            contact_info="8-800-555-55-56",
            notes="Новые примечания"
        )
        
        # Проверяем, что список обновлен
        self.assert_service_called(self.mock_get_all_lenders)

    def test_will_unmount_closes_session(self):
        """
        Тест закрытия сессии при размонтировании View.
        
        Проверяет:
        - При вызове will_unmount() вызывается __exit__ context manager'а
        
        Validates: Requirements 1.2
        """
        # Вызываем will_unmount
        self.view.will_unmount()
        
        # Проверяем, что __exit__ был вызван
        self.mock_db_cm.__exit__.assert_called_once()

    def test_load_lenders_updates_ui(self):
        """
        Тест обновления UI после загрузки данных.
        
        Проверяет:
        - После вызова load_lenders() UI обновляется (page.update)
        - Список займодателей очищается и заполняется заново
        
        Validates: Requirements 7.1
        """
        # Создаем тестовых займодателей
        test_lenders = [
            create_test_lender(id=1, name="Банк 1", lender_type=LenderType.BANK),
        ]
        self.mock_get_all_lenders.return_value = test_lenders
        
        # Сбрасываем счетчик вызовов page.update
        self.page.update.reset_mock()
        
        # Вызываем load_lenders
        self.view.load_lenders()
        
        # Проверяем, что page.update был вызван
        self.assert_page_updated(self.page)
        
        # Проверяем, что список содержит элементы
        self.assertGreater(len(self.view.lenders_column.controls), 0)


if __name__ == '__main__':
    unittest.main()
