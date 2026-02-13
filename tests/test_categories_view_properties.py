"""
Property-based тесты для CategoriesView.

Тестирует универсальные свойства split layout (income + expense tree).
"""

import unittest
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
            "finance_tracker.views.categories_view.get_db_session", return_value=self.mock_db_cm
        )

        # Патчим сервисы категорий
        self.mock_get_all_categories = self.add_patcher(
            "finance_tracker.views.categories_view.get_all_categories", return_value=[]
        )
        self.mock_get_expense_tree = self.add_patcher(
            "finance_tracker.views.categories_view.get_expense_tree", return_value=[]
        )

    @given(
        num_income=st.integers(min_value=0, max_value=10),
        num_expense_roots=st.integers(min_value=0, max_value=10),
        children_per_root=st.lists(st.integers(min_value=0, max_value=3), min_size=0, max_size=10),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_split_layout_data(self, num_income, num_expense_roots, children_per_root):
        """
        Feature: ui-testing, Property: Split layout data

        Validates: Requirements 3.1, 3.3, 6.2

        Для любого View со split layout, refresh_data должен загружать income список
        и expense дерево, обновляя UI.

        Проверяет:
        - Вызываются сервисы income + expense
        - UI обновляется после refresh_data
        - Income и expense секции заполняются с корректным количеством элементов
        """
        # Создаем тестовые категории
        income_categories = [
            create_test_category(id=f"inc-{i}", name=f"Доход {i}", type=TransactionType.INCOME)
            for i in range(1, num_income + 1)
        ]

        roots_count = min(num_expense_roots, len(children_per_root))
        if roots_count == 0:
            roots_count = num_expense_roots

        expense_tree = []
        total_children = 0
        for i in range(roots_count):
            root_id = f"exp-root-{i}"
            root = create_test_category(
                id=root_id,
                name=f"Расход root {i}",
                type=TransactionType.EXPENSE,
            )
            children_count = children_per_root[i] if i < len(children_per_root) else 0
            children = []
            for j in range(children_count):
                child = create_test_category(
                    id=f"exp-child-{i}-{j}",
                    name=f"Расход child {i}-{j}",
                    type=TransactionType.EXPENSE,
                    parent_id=root_id,
                )
                children.append(child)
            total_children += len(children)
            expense_tree.append({"category": root, "children": children})

        # Создаем View
        view = CategoriesView(self.page)

        self.mock_get_all_categories.return_value = income_categories
        self.mock_get_expense_tree.return_value = expense_tree

        self.mock_get_all_categories.reset_mock()
        self.mock_get_expense_tree.reset_mock()
        self.page.update.reset_mock()

        view.refresh_data()

        self.assert_service_called(
            self.mock_get_all_categories, self.mock_session, TransactionType.INCOME
        )
        self.assert_service_called(self.mock_get_expense_tree, self.mock_session)
        self.assert_page_updated(self.page)

        if num_income == 0:
            self.assertEqual(len(view.income_list.controls), 1)
        else:
            self.assertEqual(len(view.income_list.controls), num_income)

        expected_expense_items = roots_count + total_children
        if expected_expense_items == 0:
            self.assertEqual(len(view.expense_list.controls), 1)
        else:
            self.assertEqual(len(view.expense_list.controls), expected_expense_items)


if __name__ == "__main__":
    unittest.main()
