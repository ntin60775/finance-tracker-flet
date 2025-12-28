"""
Тесты навигации HomeView.

Проверяет, что кнопки "Показать всё" корректно вызывают navigate_callback
с правильными индексами разделов.
"""

import datetime
import pytest
import flet as ft
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from finance_tracker.views.home_view import HomeView


class TestHomeViewNavigation:
    """Тесты навигации между разделами через виджеты HomeView."""

    @pytest.fixture
    def mock_page(self):
        """Создаёт mock объекта Page."""
        page = Mock(spec=ft.Page)
        page.width = 1920
        page.height = 1080
        page.open = Mock()
        return page

    @pytest.fixture
    def mock_session(self):
        """Создаёт mock объекта Session."""
        return Mock(spec=Session)

    @pytest.fixture
    def navigate_callback(self):
        """Создаёт mock для navigate_callback."""
        return Mock()

    @pytest.fixture
    def home_view(self, mock_page, mock_session, navigate_callback):
        """Создаёт экземпляр HomeView с моками."""
        return HomeView(mock_page, mock_session, navigate_callback=navigate_callback)

    def test_navigate_callback_is_stored(self, home_view, navigate_callback):
        """Проверяет, что navigate_callback сохраняется в HomeView."""
        assert home_view.navigate_callback is navigate_callback

    def test_on_show_all_occurrences_calls_navigate_callback(
        self, home_view, navigate_callback
    ):
        """
        Проверяет, что on_show_all_occurrences вызывает navigate_callback с индексом 1.

        Индекс 1 соответствует разделу "Плановые транзакции" в NavigationRail.
        """
        # Act
        home_view.on_show_all_occurrences()

        # Assert
        navigate_callback.assert_called_once_with(1)

    def test_on_show_all_payments_calls_navigate_callback(
        self, home_view, navigate_callback
    ):
        """
        Проверяет, что on_show_all_payments вызывает navigate_callback с индексом 3.

        Индекс 3 соответствует разделу "Отложенные платежи" в NavigationRail.
        """
        # Act
        home_view.on_show_all_payments()

        # Assert
        navigate_callback.assert_called_once_with(3)

    def test_on_show_all_occurrences_handles_missing_callback(
        self, mock_page, mock_session
    ):
        """
        Проверяет, что on_show_all_occurrences не падает при отсутствии navigate_callback.

        Должен только залогировать предупреждение.
        """
        # Arrange
        home_view = HomeView(mock_page, mock_session, navigate_callback=None)

        # Act & Assert - не должно упасть
        home_view.on_show_all_occurrences()

    def test_on_show_all_payments_handles_missing_callback(
        self, mock_page, mock_session
    ):
        """
        Проверяет, что on_show_all_payments не падает при отсутствии navigate_callback.

        Должен только залогировать предупреждение.
        """
        # Arrange
        home_view = HomeView(mock_page, mock_session, navigate_callback=None)

        # Act & Assert - не должно упасть
        home_view.on_show_all_payments()

    def test_navigate_callback_exception_is_handled(
        self, home_view, navigate_callback
    ):
        """
        Проверяет, что исключения в navigate_callback обрабатываются корректно.

        Ошибка должна быть залогирована, но не должна прервать выполнение.
        """
        # Arrange
        navigate_callback.side_effect = Exception("Test exception")

        # Act & Assert - не должно упасть
        home_view.on_show_all_occurrences()
        home_view.on_show_all_payments()


class TestMainWindowNavigationRailUpdate:
    """Тесты обновления NavigationRail при программной навигации."""

    def test_navigate_updates_rail_selected_index(self):
        """
        Проверяет, что метод navigate обновляет rail.selected_index.

        При вызове navigate(index) должен установить rail.selected_index = index.
        """
        # Arrange - создаём mock для MainWindow без полной инициализации
        from finance_tracker.views.main_window import MainWindow

        # Создаём минимальный объект для тестирования navigate
        mock_window = Mock(spec=MainWindow)
        mock_window.rail = Mock()
        mock_window.content_area = Mock()
        mock_window.page = Mock()
        mock_window.page.window = Mock()

        # Копируем метод navigate из MainWindow для тестирования
        # Используем метод из реального класса, применяя его к нашему mock
        navigate_method = MainWindow.navigate.__get__(mock_window, MainWindow)

        # Мокируем зависимости метода navigate
        mock_window.get_view = Mock(return_value=Mock())
        mock_window.save_state = Mock()
        mock_window.update_balance = Mock()

        # Act
        navigate_method(3)

        # Assert
        assert mock_window.rail.selected_index == 3

    def test_navigate_calls_rail_update(self):
        """
        Проверяет, что метод navigate вызывает rail.update().

        Это необходимо для визуального обновления активного раздела в NavigationRail.
        """
        # Arrange
        from finance_tracker.views.main_window import MainWindow

        mock_window = Mock(spec=MainWindow)
        mock_window.rail = Mock()
        mock_window.content_area = Mock()
        mock_window.page = Mock()
        mock_window.page.window = Mock()

        navigate_method = MainWindow.navigate.__get__(mock_window, MainWindow)

        mock_window.get_view = Mock(return_value=Mock())
        mock_window.save_state = Mock()
        mock_window.update_balance = Mock()

        # Act
        navigate_method(1)

        # Assert - rail.update должен быть вызван
        mock_window.rail.update.assert_called_once()
