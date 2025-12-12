"""
Базовый класс для тестов View компонентов.

Предоставляет общие вспомогательные методы для тестирования View:
- Создание моков для page и session
- Проверка вызовов сервисов
- Проверка открытия модальных окон
- Общие setUp/tearDown методы
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import Optional, Any, List
import flet as ft


class ViewTestBase(unittest.TestCase):
    """
    Базовый класс для тестов View компонентов.
    
    Предоставляет общие методы для:
    - Создания моков page и session
    - Проверки вызовов сервисов
    - Проверки открытия модальных окон
    - Управления патчами
    """
    
    def setUp(self):
        """
        Базовая настройка перед каждым тестом.
        
        Создаёт:
        - Мок для page
        - Мок для session
        - Список активных патчей для автоматической очистки
        """
        self.page = self.create_mock_page()
        self.mock_session = self.create_mock_session()
        self.patchers: List[Any] = []
        
    def tearDown(self):
        """
        Очистка после каждого теста.
        
        Останавливает все активные патчи.
        """
        for patcher in self.patchers:
            patcher.stop()
        self.patchers.clear()
    
    def create_mock_page(self) -> MagicMock:
        """
        Создание мока для Flet Page.
        
        Returns:
            MagicMock: Мок объекта page с настроенными атрибутами:
                - overlay: пустой список для модальных окон
                - dialog: None (для диалогов)
                - update(): метод для обновления UI
                - open(): метод для открытия диалогов
                - close(): метод для закрытия диалогов
                - show_snack_bar(): метод для показа SnackBar
        """
        page = MagicMock(spec=ft.Page)
        page.overlay = []
        page.dialog = None
        page.update = MagicMock()
        page.open = MagicMock()
        page.close = MagicMock()
        page.show_snack_bar = MagicMock()
        return page
    
    def create_mock_session(self) -> Mock:
        """
        Создание мока для SQLAlchemy Session.
        
        Returns:
            Mock: Мок объекта session с настроенными методами:
                - commit(): фиксация транзакции
                - rollback(): откат транзакции
                - close(): закрытие сессии
                - query(): создание запроса
        """
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        session.query = Mock()
        return session
    
    def create_mock_db_context(self, session: Optional[Mock] = None) -> Mock:
        """
        Создание мока для context manager get_db_session().
        
        Args:
            session: Мок сессии для возврата. Если None, используется self.mock_session
            
        Returns:
            Mock: Мок context manager'а, который возвращает session при входе
            
        Example:
            mock_cm = self.create_mock_db_context()
            with patch('module.get_db_session', return_value=mock_cm):
                # Тестируемый код
        """
        if session is None:
            session = self.mock_session
            
        mock_cm = Mock()
        mock_cm.__enter__ = Mock(return_value=session)
        mock_cm.__exit__ = Mock(return_value=None)
        return mock_cm
    
    def add_patcher(self, target: str, **kwargs) -> Mock:
        """
        Создание и запуск патча с автоматической регистрацией для очистки.
        
        Args:
            target: Строка с путём к патчируемому объекту
            **kwargs: Дополнительные аргументы для patch()
            
        Returns:
            Mock: Мок объект патча
            
        Example:
            mock_service = self.add_patcher('module.service_function', return_value=[])
        """
        patcher = patch(target, **kwargs)
        mock_obj = patcher.start()
        self.patchers.append(patcher)
        return mock_obj
    
    def assert_service_called(
        self,
        mock_service: Mock,
        *args,
        **kwargs
    ):
        """
        Проверка, что сервис был вызван с указанными аргументами.
        
        Args:
            mock_service: Мок сервиса для проверки
            *args: Позиционные аргументы вызова
            **kwargs: Именованные аргументы вызова
            
        Raises:
            AssertionError: Если сервис не был вызван с указанными аргументами
            
        Example:
            self.assert_service_called(mock_get_categories, self.mock_session, None)
        """
        if args or kwargs:
            mock_service.assert_called_with(*args, **kwargs)
        else:
            mock_service.assert_called()
    
    def assert_service_called_once(
        self,
        mock_service: Mock,
        *args,
        **kwargs
    ):
        """
        Проверка, что сервис был вызван ровно один раз с указанными аргументами.
        
        Args:
            mock_service: Мок сервиса для проверки
            *args: Позиционные аргументы вызова
            **kwargs: Именованные аргументы вызова
            
        Raises:
            AssertionError: Если сервис не был вызван ровно один раз
            
        Example:
            self.assert_service_called_once(mock_create_category, self.mock_session, "Test", TransactionType.EXPENSE)
        """
        if args or kwargs:
            mock_service.assert_called_once_with(*args, **kwargs)
        else:
            mock_service.assert_called_once()
    
    def assert_service_not_called(self, mock_service: Mock):
        """
        Проверка, что сервис не был вызван.
        
        Args:
            mock_service: Мок сервиса для проверки
            
        Raises:
            AssertionError: Если сервис был вызван
            
        Example:
            self.assert_service_not_called(mock_delete_category)
        """
        mock_service.assert_not_called()
    
    def assert_modal_opened(
        self,
        page_mock: MagicMock,
        modal_type: Optional[type] = None
    ):
        """
        Проверка, что модальное окно было открыто.
        
        Args:
            page_mock: Мок объекта page
            modal_type: Ожидаемый тип модального окна (опционально)
            
        Raises:
            AssertionError: Если модальное окно не было открыто или тип не совпадает
            
        Example:
            self.assert_modal_opened(self.page, ft.AlertDialog)
        """
        # Проверяем, что page.open был вызван
        page_mock.open.assert_called()
        
        if modal_type is not None:
            # Получаем аргумент вызова page.open
            call_args = page_mock.open.call_args
            if call_args:
                # call_args[0] - позиционные аргументы, call_args[1] - именованные
                opened_dialog = call_args[0][0] if call_args[0] else None
                self.assertIsInstance(
                    opened_dialog,
                    modal_type,
                    f"Ожидался тип {modal_type.__name__}, получен {type(opened_dialog).__name__}"
                )
    
    def assert_modal_not_opened(self, page_mock: MagicMock):
        """
        Проверка, что модальное окно не было открыто.
        
        Args:
            page_mock: Мок объекта page
            
        Raises:
            AssertionError: Если модальное окно было открыто
            
        Example:
            self.assert_modal_not_opened(self.page)
        """
        page_mock.open.assert_not_called()
    
    def assert_page_updated(self, page_mock: MagicMock, times: Optional[int] = None):
        """
        Проверка, что page.update() был вызван.
        
        Args:
            page_mock: Мок объекта page
            times: Ожидаемое количество вызовов (опционально)
            
        Raises:
            AssertionError: Если page.update() не был вызван нужное количество раз
            
        Example:
            self.assert_page_updated(self.page)
            self.assert_page_updated(self.page, times=2)
        """
        if times is not None:
            self.assertEqual(
                page_mock.update.call_count,
                times,
                f"Ожидалось {times} вызовов page.update(), получено {page_mock.update.call_count}"
            )
        else:
            page_mock.update.assert_called()
    
    def assert_snackbar_shown(
        self,
        page_mock: MagicMock,
        message_contains: Optional[str] = None
    ):
        """
        Проверка, что был показан SnackBar.
        
        Args:
            page_mock: Мок объекта page
            message_contains: Подстрока, которая должна содержаться в сообщении (опционально)
            
        Raises:
            AssertionError: Если SnackBar не был показан или сообщение не содержит подстроку
            
        Example:
            self.assert_snackbar_shown(self.page, "успешно")
        """
        # Проверяем, что page.open был вызван
        page_mock.open.assert_called()
        
        if message_contains is not None:
            # Ищем вызов с SnackBar, содержащим нужное сообщение
            found = False
            for call in page_mock.open.call_args_list:
                if call[0]:  # Есть позиционные аргументы
                    arg = call[0][0]
                    if isinstance(arg, ft.SnackBar):
                        # Получаем текст из SnackBar
                        if hasattr(arg.content, 'value'):
                            text = arg.content.value
                            if message_contains.lower() in text.lower():
                                found = True
                                break
            
            self.assertTrue(
                found,
                f"SnackBar с сообщением, содержащим '{message_contains}', не найден"
            )
    
    def get_view_controls_count(self, view) -> int:
        """
        Получение количества контролов в View.
        
        Args:
            view: Экземпляр View для проверки
            
        Returns:
            int: Количество контролов
            
        Example:
            count = self.get_view_controls_count(self.view)
            self.assertGreater(count, 0)
        """
        if hasattr(view, 'controls'):
            return len(view.controls)
        return 0
    
    def assert_view_has_controls(self, view):
        """
        Проверка, что View содержит контролы.
        
        Args:
            view: Экземпляр View для проверки
            
        Raises:
            AssertionError: Если View не содержит контролов
            
        Example:
            self.assert_view_has_controls(self.view)
        """
        count = self.get_view_controls_count(view)
        self.assertGreater(
            count,
            0,
            f"View должен содержать контролы, но их количество: {count}"
        )
    
    def assert_button_click_calls_callback(self, button, callback_mock: Mock):
        """
        Проверяет, что нажатие кнопки вызывает callback.
        
        Args:
            button: Кнопка для тестирования
            callback_mock: Мок callback функции
            
        Raises:
            AssertionError: Если callback не был вызван
            
        Example:
            self.assert_button_click_calls_callback(add_button, mock_callback)
        """
        # Симулируем нажатие кнопки
        if hasattr(button, 'on_click') and button.on_click:
            button.on_click(None)
            callback_mock.assert_called_once()
        else:
            self.fail("Кнопка не имеет обработчика on_click")
    
    def assert_form_field_has_value(self, field, expected_value: Any, field_name: str = "field"):
        """
        Проверяет значение поля формы.
        
        Args:
            field: Поле формы для проверки
            expected_value: Ожидаемое значение
            field_name: Название поля для сообщения об ошибке
            
        Raises:
            AssertionError: Если значение не соответствует ожидаемому
            
        Example:
            self.assert_form_field_has_value(modal.amount_field, "100.50", "amount")
        """
        actual_value = getattr(field, 'value', None)
        self.assertEqual(
            actual_value,
            expected_value,
            f"Поле {field_name}: ожидалось '{expected_value}', получено '{actual_value}'"
        )
    
    def assert_button_enabled(self, button, expected_enabled: bool = True, button_name: str = "button"):
        """
        Проверяет состояние кнопки (активна/неактивна).
        
        Args:
            button: Кнопка для проверки
            expected_enabled: Ожидаемое состояние (True = активна)
            button_name: Название кнопки для сообщения об ошибке
            
        Raises:
            AssertionError: Если состояние не соответствует ожидаемому
            
        Example:
            self.assert_button_enabled(modal.save_button, False, "save")
        """
        is_disabled = getattr(button, 'disabled', False)
        actual_enabled = not is_disabled
        self.assertEqual(
            actual_enabled,
            expected_enabled,
            f"Кнопка {button_name}: ожидалось enabled={expected_enabled}, получено {actual_enabled}"
        )
    
    def simulate_form_input(self, field, value: Any):
        """
        Симулирует ввод данных в поле формы.
        
        Args:
            field: Поле формы
            value: Вводимое значение
            
        Example:
            self.simulate_form_input(modal.amount_field, "150.75")
        """
        field.value = value
        # Симулируем событие изменения, если есть обработчик
        if hasattr(field, 'on_change') and field.on_change:
            field.on_change(None)
    
    def get_modal_from_page_open_calls(self, page_mock: MagicMock):
        """
        Извлекает модальное окно из вызовов page.open().
        
        Args:
            page_mock: Мок объекта page
            
        Returns:
            Модальное окно или None если не найдено
            
        Example:
            modal = self.get_modal_from_page_open_calls(self.page)
            self.assertIsNotNone(modal)
        """
        if page_mock.open.called:
            call_args = page_mock.open.call_args
            if call_args and call_args[0]:
                return call_args[0][0]
        return None
