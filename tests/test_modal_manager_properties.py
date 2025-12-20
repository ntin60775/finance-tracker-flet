"""
Property-based тесты для ModalManager календарной легенды.

Проверяет корректность создания, открытия и закрытия модального окна,
а также группировку индикаторов по типам.
"""
import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, MagicMock, patch
from typing import List

import flet as ft

from finance_tracker.components.modal_manager import ModalManager
from finance_tracker.components.calendar_legend_types import (
    IndicatorType,
    LegendIndicator,
    INDICATOR_CONFIGS
)


class TestModalManagerProperties:
    """Property-based тесты для ModalManager."""

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=1, 
        max_size=7, 
        unique=True
    ))
    def test_modal_dialog_functionality_property(self, indicator_types):
        """
        **Feature: calendar-legend-improvement, Property 5: Modal dialog functionality**
        **Validates: Requirements 3.1, 3.2, 3.4**
        
        Property: Для любого набора индикаторов модальное окно должно создаваться,
        открываться и закрываться корректно.
        """
        # Arrange - подготовка индикаторов
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        modal_manager = ModalManager()
        mock_page = MagicMock(spec=ft.Page)
        
        # Act & Assert - создание модального окна
        dialog = modal_manager.create_modal(indicators)
        
        # Проверяем, что диалог создан корректно
        assert dialog is not None
        assert isinstance(dialog, ft.AlertDialog)
        assert dialog.modal == True
        assert dialog.title.value == "Легенда календаря"
        assert dialog.content is not None
        assert len(dialog.actions) == 1
        assert dialog.actions[0].text == "Закрыть"
        
        # Act & Assert - открытие модального окна
        result = modal_manager.open_modal(mock_page)
        
        # Проверяем успешное открытие
        assert result == True
        assert mock_page.dialog == dialog
        assert dialog.open == True
        mock_page.update.assert_called_once()
        
        # Act & Assert - закрытие модального окна
        mock_page.update.reset_mock()
        result = modal_manager.close_modal(mock_page)
        
        # Проверяем успешное закрытие
        assert result == True
        assert dialog.open == False
        mock_page.update.assert_called_once()

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=1, 
        max_size=7, 
        unique=True
    ))
    def test_modal_dialog_structure_property(self, indicator_types):
        """
        **Feature: calendar-legend-improvement, Property 6: Modal dialog structure**
        **Validates: Requirements 3.2, 3.3**
        
        Property: Для любого набора индикаторов модальное окно должно содержать
        все индикаторы, сгруппированные по типам (точки, символы, фон).
        """
        # Arrange
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        modal_manager = ModalManager()
        
        # Act
        dialog = modal_manager.create_modal(indicators)
        
        # Assert - проверяем структуру диалога
        assert isinstance(dialog.content, ft.Column)
        content_controls = dialog.content.controls
        
        # Проверяем, что все индикаторы присутствуют в содержимом
        content_text = self._extract_text_from_controls(content_controls)
        
        for indicator in indicators:
            assert indicator.label in content_text, f"Индикатор '{indicator.label}' отсутствует в модальном окне"
            assert indicator.description in content_text, f"Описание '{indicator.description}' отсутствует в модальном окне"
        
        # Проверяем группировку по типам
        expected_groups = self._get_expected_groups(indicators)
        
        if expected_groups['dots']:
            assert "Индикаторы транзакций (точки):" in content_text
        if expected_groups['symbols']:
            assert "Символы:" in content_text
        if expected_groups['backgrounds']:
            assert "Фон дня:" in content_text

    @given(st.one_of(st.none(), st.just(MagicMock(spec=ft.Page))))
    def test_page_object_handling_property(self, page):
        """
        **Feature: calendar-legend-improvement, Property 7: Page object handling**
        **Validates: Requirements 3.5, 5.2**
        
        Property: ModalManager должен безопасно обрабатывать любые page объекты,
        включая None, без вызова исключений.
        """
        # Arrange
        modal_manager = ModalManager()
        indicators = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        modal_manager.create_modal(indicators)
        
        # Act & Assert - открытие с любым page объектом
        try:
            result = modal_manager.open_modal(page)
            
            if page is None:
                # При None должен вернуть False, но не упасть
                assert result == False
            else:
                # При валидном page должен вернуть True
                assert result == True
                assert page.dialog == modal_manager.dialog
                assert modal_manager.dialog.open == True
                
        except Exception as e:
            pytest.fail(f"open_modal не должен вызывать исключения с page={page}: {e}")
        
        # Act & Assert - закрытие с любым page объектом
        try:
            result = modal_manager.close_modal(page)
            
            if page is None:
                # При None должен вернуть False, но не упасть
                assert result == False
            else:
                # При валидном page должен вернуть True
                assert result == True
                assert modal_manager.dialog.open == False
                
        except Exception as e:
            pytest.fail(f"close_modal не должен вызывать исключения с page={page}: {e}")

    def test_modal_dialog_error_handling(self):
        """
        Тест: ModalManager должен создавать fallback диалог при ошибках.
        
        Проверяет, что при ошибке создания основного диалога создаётся
        упрощённая версия без падения приложения.
        """
        modal_manager = ModalManager()
        
        # Создаём некорректные индикаторы, которые могут вызвать ошибку
        invalid_indicators = [
            LegendIndicator(
                type=IndicatorType.INCOME_DOT,
                visual_element=None,  # Некорректный элемент
                label="",  # Пустая метка
                description="",  # Пустое описание
                priority=-1,  # Некорректный приоритет
                estimated_width=-10  # Некорректная ширина
            )
        ]
        
        # Мокируем ошибку в процессе создания
        with patch.object(modal_manager, '_build_indicator_group', side_effect=Exception("Test error")):
            dialog = modal_manager.create_modal(invalid_indicators)
            
            # Проверяем, что fallback диалог создан
            assert dialog is not None
            assert isinstance(dialog, ft.AlertDialog)
            assert dialog.title.value == "Легенда календаря"
            assert "Ошибка при загрузке легенды" in dialog.content.value

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=0, 
        max_size=7, 
        unique=True
    ))
    def test_indicator_grouping_correctness_property(self, indicator_types):
        """
        Property: Группировка индикаторов должна быть корректной для любого набора.
        
        Проверяет, что индикаторы правильно группируются по типам:
        - Точки: INCOME_DOT, EXPENSE_DOT
        - Символы: PLANNED_SYMBOL, PENDING_SYMBOL, LOAN_SYMBOL  
        - Фон: CASH_GAP_BG, OVERDUE_BG
        """
        # Arrange
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        modal_manager = ModalManager()
        
        # Act
        groups = modal_manager._group_indicators_by_type(indicators)
        
        # Assert - проверяем корректность группировки
        assert isinstance(groups, dict)
        assert set(groups.keys()) == {'dots', 'symbols', 'backgrounds'}
        
        # Проверяем, что все индикаторы попали в правильные группы
        total_grouped = len(groups['dots']) + len(groups['symbols']) + len(groups['backgrounds'])
        assert total_grouped == len(indicators)
        
        # Проверяем корректность группировки по типам
        for indicator in groups['dots']:
            assert indicator.type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT]
        
        for indicator in groups['symbols']:
            assert indicator.type in [IndicatorType.PLANNED_SYMBOL, IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]
        
        for indicator in groups['backgrounds']:
            assert indicator.type in [IndicatorType.CASH_GAP_BG, IndicatorType.OVERDUE_BG]

    def test_close_modal_handler_safety(self):
        """
        Тест: Обработчик закрытия модального окна должен быть безопасным.
        
        Проверяет, что _close_modal_handler корректно обрабатывает различные
        типы событий и не падает при некорректных данных.
        """
        modal_manager = ModalManager()
        indicators = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        modal_manager.create_modal(indicators)
        
        # Тестируем различные типы событий
        test_events = [
            None,
            Mock(),
            Mock(control=None),
            Mock(control=Mock(page=None)),
            Mock(control=Mock(page=MagicMock(spec=ft.Page)))
        ]
        
        for event in test_events:
            try:
                modal_manager._close_modal_handler(event)
                # Не должно быть исключений
            except Exception as e:
                pytest.fail(f"_close_modal_handler не должен падать с event={event}: {e}")

    @given(st.sampled_from(list(IndicatorType)))
    def test_legend_item_creation_property(self, indicator_type):
        """
        Property: Для любого типа индикатора должен создаваться корректный элемент легенды.
        """
        # Arrange
        modal_manager = ModalManager()
        indicator = INDICATOR_CONFIGS[indicator_type]
        
        # Act
        legend_item = modal_manager._build_legend_item(indicator)
        
        # Assert
        assert isinstance(legend_item, ft.Row)
        assert len(legend_item.controls) == 2
        
        # Первый элемент - визуальный индикатор
        visual_element = legend_item.controls[0]
        assert visual_element == indicator.visual_element
        
        # Второй элемент - колонка с текстом
        text_column = legend_item.controls[1]
        assert isinstance(text_column, ft.Column)
        assert len(text_column.controls) == 2
        
        # Проверяем текстовые элементы
        label_text = text_column.controls[0]
        description_text = text_column.controls[1]
        
        assert isinstance(label_text, ft.Text)
        assert isinstance(description_text, ft.Text)
        assert label_text.value == indicator.label
        assert description_text.value == indicator.description

    def _extract_text_from_controls(self, controls: List[ft.Control]) -> str:
        """
        Извлекает весь текст из списка контролов для проверки содержимого.
        
        Args:
            controls: Список Flet контролов
            
        Returns:
            Объединённый текст из всех контролов
        """
        text_parts = []
        
        for control in controls:
            if isinstance(control, ft.Text):
                text_parts.append(control.value or "")
            elif isinstance(control, ft.Column):
                text_parts.append(self._extract_text_from_controls(control.controls))
            elif isinstance(control, ft.Row):
                text_parts.append(self._extract_text_from_controls(control.controls))
            elif hasattr(control, 'controls'):
                text_parts.append(self._extract_text_from_controls(control.controls))
        
        return " ".join(text_parts)
    
    def _get_expected_groups(self, indicators: List[LegendIndicator]) -> dict:
        """
        Определяет ожидаемые группы для набора индикаторов.
        
        Args:
            indicators: Список индикаторов
            
        Returns:
            Словарь с ожидаемыми группами
        """
        groups = {'dots': [], 'symbols': [], 'backgrounds': []}
        
        for indicator in indicators:
            if indicator.type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT]:
                groups['dots'].append(indicator)
            elif indicator.type in [IndicatorType.PLANNED_SYMBOL, IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]:
                groups['symbols'].append(indicator)
            elif indicator.type in [IndicatorType.CASH_GAP_BG, IndicatorType.OVERDUE_BG]:
                groups['backgrounds'].append(indicator)
        
        return groups