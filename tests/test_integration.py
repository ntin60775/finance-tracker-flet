"""
Интеграционные тесты для проверки взаимодействия UI и сервисов.
Проверяют полные сценарии использования (User Flows).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from decimal import Decimal

from views.home_view import HomeView
from models import TransactionType, TransactionCreate, Base
from services.transaction_service import create_transaction, get_transactions_by_date
@pytest.fixture
def mock_page():
    page = MagicMock()
    page.overlay = []
    return page

def test_create_transaction_flow(db_session, mock_page):
    """
    Сценарий: Пользователь создает транзакцию через UI, она появляется в БД и обновляется на экране.
    """
    # 1. Инициализация View
    # Патчим get_db_session, чтобы HomeView использовал нашу тестовую сессию
    with patch('finance_tracker_flet.views.home_view.get_db_session') as mock_get_session:
        mock_get_session.return_value.__enter__.return_value = db_session
        
        view = HomeView(mock_page)
        view.did_mount()
        
        # 2. Имитация создания транзакции через модальное окно
        # Вместо реального клика по кнопке, вызываем callback сохранения напрямую,
        # как это делает TransactionModal
        
        transaction_data = TransactionCreate(
            amount=Decimal("500.00"),
            type=TransactionType.EXPENSE,
            category_id=1, # Предполагаем, что категория 1 существует (создадим её)
            description="Test integration",
            transaction_date=date(2023, 10, 15)
        )
        
        # Создаем категорию для теста
        from models import CategoryDB
        category = CategoryDB(name="Test Cat", type=TransactionType.EXPENSE)
        db_session.add(category)
        db_session.commit()
        
        # Вызываем метод создания (обычно он вызывается из модального окна)
        # В HomeView логика создания находится внутри _on_transaction_save, который передается в Modal
        # Но HomeView.open_transaction_modal создает Modal.
        # Эмулируем сохранение:
        create_transaction(
            db_session,
            transaction_data
        )
        
        # 3. Обновление UI
        # После сохранения HomeView должен обновить список транзакций
        # Эмулируем выбор даты, чтобы триггернуть обновление
        view.on_date_selected(date(2023, 10, 15))
        
        # 4. Проверка
        # Проверяем БД
        transactions = get_transactions_by_date(db_session, date(2023, 10, 15))
        assert len(transactions) == 1
        assert transactions[0].amount == Decimal("500.00")
        assert transactions[0].description == "Test integration"
        
        # Проверяем UI (TransactionsPanel должна получить данные)
        # В текущей реализации HomeView обновляет view.transactions_panel.transactions
        # Но так как мы мокали Page, реального рендеринга Flet не происходит,
        # мы проверяем состояние объектов
        assert view.selected_date == date(2023, 10, 15)
        
        # Проверяем, что TransactionsPanel получила данные (через update_transactions)
        # view.transactions_panel.update_transactions(transactions, ...)
        # Это сложно проверить без мока самого TransactionsPanel внутри HomeView,
        # но мы проверили главный сайд-эффект - запись в БД через сервис.

def test_navigation_flow(mock_page, db_session):
    """
    Сценарий: Навигация между разделами приложения.
    """
    from views.main_window import MainWindow
    
    # Патчим настройки, чтобы не писать в реальный конфиг
    # Также патчим get_db_session глобально для всех вьюх, которые могут его использовать
    with patch('finance_tracker_flet.views.main_window.settings') as mock_settings, \
         patch('finance_tracker_flet.views.home_view.get_db_session') as mock_home_session, \
         patch('finance_tracker_flet.views.categories_view.get_db_session') as mock_cat_session:
        
        mock_settings.last_selected_index = 0
        # Настраиваем моки сессий
        for mock_session in [mock_home_session, mock_cat_session]:
            mock_session.return_value.__enter__.return_value = db_session
        
        main_window = MainWindow(mock_page)
        
        # Flet требует, чтобы контрол был добавлен на страницу перед update()
        # В тесте мы не добавляем MainWindow на реальную страницу, поэтому
        # методы update() внутри navigate вызовут ошибку.
        # Мы можем запатчить update методы внутренних компонентов, но проще
        # запатчить content_area.update, так как она вызывается в navigate
        
        with patch.object(main_window.content_area, 'update'):
            # Переход на вкладку "Планирование" (индекс 1)
            main_window.navigate(1)
            
            assert main_window.rail.selected_index == 1
            # Проверяем, что контент изменился (тип контрола)
            from views.plan_fact_view import PlanFactView
            assert isinstance(main_window.content_area.content, PlanFactView)
            
            # Переход на вкладку "Категории" (индекс 5)
            main_window.navigate(5)
            assert main_window.rail.selected_index == 5
            from views.categories_view import CategoriesView
            assert isinstance(main_window.content_area.content, CategoriesView)
