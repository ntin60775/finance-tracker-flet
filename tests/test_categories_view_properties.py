"""
Property-based тесты для CategoriesView.

Тестирует универсальные свойства UI фильтрации категорий.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings

from finance_tracker.views.categories_view import CategoriesView
from finance_tracker.models.enums import TransactionType
from test_view_base import ViewTestBase
from test_factories import create_test_category


class TestCategoriesViewProperties(ViewTestBase):
    """Property-based тесты для CategoriesView."""

    def setUp(self):
        """Настройка перед каждым тестом."""
        super().setUp()
        
        # Патчим get_db_session для возврата мока context manager
        self.mock_db_cm = self.create_mock_db_context()
        self.mock_get_db = self.add_patcher(
            'finance_tracker.views.categories_view.get_db_session',
            return_value=self.mock_db_cm
        )
        
        # Патчим сервисы категорий
        self.mock_get_all_categories = self.add_patcher(
            'finance_tracker.views.categories_view.get_all_categories',
            return_value=[]
        )

    @given(
        num_income=st.integers(min_value=0, max_value=10),
        num_expense=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_filter_data(self, num_income, num_expense):
        """
        Feature: ui-testing, Property 4: Фильтрация данных
        
        Validates: Requirements 3.1, 3.3, 6.2
        
        Для любого View с фильтрами, изменение фильтра должно вызывать 
        перезагрузку данных с новым фильтром и обновление UI.
        
        Проверяет:
        - При изменении фильтра вызывается сервис с правильным фильтром
        - UI обновляется после изменения фильтра
        - Фильтр "Все" загружает данные без фильтрации
        - Фильтр "Расходы" загружает только расходы
        - Фильтр "Доходы" загружает только доходы
        """
        # Создаем тестовые категории
        income_categories = [
            create_test_category(
                id=i,
                name=f"Доход {i}",
                type=TransactionType.INCOME
            )
            for i in range(1, num_income + 1)
        ]
        
        expense_categories = [
            create_test_category(
                id=num_income + i,
                name=f"Расход {i}",
                type=TransactionType.EXPENSE
            )
            for i in range(1, num_expense + 1)
        ]
        
        all_categories = income_categories + expense_categories
        
        # Создаем View
        view = CategoriesView(self.page)
        
        # Сбрасываем счетчик вызовов после инициализации
        self.mock_get_all_categories.reset_mock()
        self.page.update.reset_mock()
        
        # Тест 1: Фильтр "Все" (индекс 0)
        self.mock_get_all_categories.return_value = all_categories
        view.filter_tabs.selected_index = 0
        view.on_filter_change(None)
        
        # Проверяем, что фильтр сброшен
        self.assertIsNone(view.current_filter)
        
        # Проверяем, что сервис вызван без фильтра
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            None
        )
        
        # Проверяем, что UI обновлен
        self.assert_page_updated(self.page)
        
        # Проверяем количество элементов в списке
        if num_income + num_expense == 0:
            # Пустой список - должно быть сообщение
            self.assertEqual(len(view.categories_list.controls), 1)
        else:
            # Должны быть все категории
            self.assertEqual(len(view.categories_list.controls), num_income + num_expense)
        
        # Сбрасываем счетчики
        self.mock_get_all_categories.reset_mock()
        self.page.update.reset_mock()
        
        # Тест 2: Фильтр "Расходы" (индекс 1)
        self.mock_get_all_categories.return_value = expense_categories
        view.filter_tabs.selected_index = 1
        view.on_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(view.current_filter, TransactionType.EXPENSE)
        
        # Проверяем, что сервис вызван с фильтром EXPENSE
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            TransactionType.EXPENSE
        )
        
        # Проверяем, что UI обновлен
        self.assert_page_updated(self.page)
        
        # Проверяем количество элементов в списке
        if num_expense == 0:
            # Пустой список - должно быть сообщение
            self.assertEqual(len(view.categories_list.controls), 1)
        else:
            # Должны быть только расходы
            self.assertEqual(len(view.categories_list.controls), num_expense)
        
        # Сбрасываем счетчики
        self.mock_get_all_categories.reset_mock()
        self.page.update.reset_mock()
        
        # Тест 3: Фильтр "Доходы" (индекс 2)
        self.mock_get_all_categories.return_value = income_categories
        view.filter_tabs.selected_index = 2
        view.on_filter_change(None)
        
        # Проверяем, что фильтр установлен
        self.assertEqual(view.current_filter, TransactionType.INCOME)
        
        # Проверяем, что сервис вызван с фильтром INCOME
        self.assert_service_called(
            self.mock_get_all_categories,
            self.mock_session,
            TransactionType.INCOME
        )
        
        # Проверяем, что UI обновлен
        self.assert_page_updated(self.page)
        
        # Проверяем количество элементов в списке
        if num_income == 0:
            # Пустой список - должно быть сообщение
            self.assertEqual(len(view.categories_list.controls), 1)
        else:
            # Должны быть только доходы
            self.assertEqual(len(view.categories_list.controls), num_income)


if __name__ == '__main__':
    unittest.main()
