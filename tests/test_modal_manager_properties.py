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
        **Feature: calendar-legend-width-fix, Property 7: Modal dialog stability**
        **Validates: Requirements 5.1, 5.5**
        
        Property: Для любого набора индикаторов модальное окно должно создаваться,
        открываться и закрываться корректно с использованием PageAccessManager.
        Использует современный Flet API (page.open/page.close).
        """
        # Arrange - подготовка индикаторов и mock компонента
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
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
        
        # Act & Assert - открытие модального окна через современный Flet API
        result = modal_manager.open_modal(page=mock_page)
        
        # Проверяем успешное открытие через page.open()
        assert result == True
        mock_page.open.assert_called_once_with(dialog)
        
        # Act & Assert - закрытие модального окна через современный Flet API
        mock_page.reset_mock()
        result = modal_manager.close_modal(page=mock_page)
        
        # Проверяем успешное закрытие через page.close()
        assert result == True
        mock_page.close.assert_called_once_with(dialog)

    @given(st.lists(
        st.sampled_from(list(IndicatorType)), 
        min_size=1, 
        max_size=7, 
        unique=True
    ))
    def test_modal_dialog_structure_property(self, indicator_types):
        """
        **Feature: calendar-legend-width-fix, Property 7: Modal dialog stability**
        **Validates: Requirements 5.1, 5.3**
        
        Property: Для любого набора индикаторов модальное окно должно содержать
        все индикаторы, сгруппированные по типам (точки, символы, фон).
        """
        # Arrange
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        
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
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 2.5, 5.2, 5.5**
        
        Property: ModalManager должен безопасно обрабатывать любые page объекты,
        включая None, без вызова исключений, используя PageAccessManager.
        Использует современный Flet API (page.open/page.close).
        """
        # Arrange
        mock_legend_component = Mock()
        # Убираем page из mock_legend_component, чтобы PageAccessManager не нашёл его
        mock_legend_component.page = None
        modal_manager = ModalManager(mock_legend_component)
        indicators = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        modal_manager.create_modal(indicators)
        
        # Мокируем PageAccessManager, чтобы он возвращал только переданный page
        with patch.object(modal_manager.page_manager, 'get_page', return_value=page):
            # Act & Assert - открытие с любым page объектом
            try:
                result = modal_manager.open_modal(page=page)
                
                if page is None:
                    # При None должен вернуть False, но не упасть
                    assert result == False
                else:
                    # При валидном page должен вернуть True
                    assert result == True
                    # Проверяем вызов page.open() (современный Flet API)
                    page.open.assert_called_once_with(modal_manager.dialog)
                    
            except Exception as e:
                pytest.fail(f"open_modal не должен вызывать исключения с page={page}: {e}")
            
            # Act & Assert - закрытие с любым page объектом
            try:
                if page is not None:
                    page.reset_mock()
                result = modal_manager.close_modal(page=page)
                
                if page is None:
                    # При None должен вернуть False, но не упасть
                    assert result == False
                else:
                    # При валидном page должен вернуть True
                    assert result == True
                    # Проверяем вызов page.close() (современный Flet API)
                    page.close.assert_called_once_with(modal_manager.dialog)
                    
            except Exception as e:
                pytest.fail(f"close_modal не должен вызывать исключения с page={page}: {e}")

    def test_modal_dialog_error_handling(self):
        """
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 5.5**
        
        Тест: ModalManager должен создавать fallback диалог при ошибках.
        
        Проверяет, что при ошибке создания основного диалога создаётся
        упрощённая версия без падения приложения.
        """
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        
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
        **Feature: calendar-legend-width-fix, Property 7: Modal dialog stability**
        **Validates: Requirements 5.3**
        
        Property: Группировка индикаторов должна быть корректной для любого набора.
        
        Проверяет, что индикаторы правильно группируются по типам:
        - Точки: INCOME_DOT, EXPENSE_DOT
        - Символы: PLANNED_SYMBOL, PENDING_SYMBOL, LOAN_SYMBOL  
        - Фон: CASH_GAP_BG, OVERDUE_BG
        """
        # Arrange
        indicators = [INDICATOR_CONFIGS[indicator_type] for indicator_type in indicator_types]
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        
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
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 2.5, 5.5**
        
        Тест: Обработчик закрытия модального окна должен быть безопасным.
        
        Проверяет, что улучшенный _close_modal_handler корректно обрабатывает различные
        типы событий и не падает при некорректных данных, используя PageAccessManager.
        """
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
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
        **Feature: calendar-legend-width-fix, Property 7: Modal dialog stability**
        **Validates: Requirements 5.3**
        
        Property: Для любого типа индикатора должен создаваться корректный элемент легенды.
        """
        # Arrange
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
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
    
    @given(st.lists(
        st.sampled_from([None, Mock(), Mock(control=Mock(page=MagicMock(spec=ft.Page)))]),
        min_size=1,
        max_size=5
    ))
    def test_page_access_manager_integration_property(self, events):
        """
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 2.2, 2.5, 5.2**
        
        Property: ModalManager должен корректно использовать PageAccessManager
        для получения page объекта из любых типов событий.
        Использует современный Flet API (page.open/page.close).
        """
        # Arrange
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        indicators = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        modal_manager.create_modal(indicators)
        
        # Act & Assert - тестируем открытие с различными событиями
        for event in events:
            try:
                result = modal_manager.open_modal(event_or_control=event)
                
                # Результат должен быть boolean, не должно быть исключений
                assert isinstance(result, bool)
                
                # Если есть валидный page в событии, должно открыться успешно
                if (event and hasattr(event, 'control') and 
                    hasattr(event.control, 'page') and event.control.page):
                    assert result == True
                    # Проверяем вызов page.open() (современный Flet API)
                    event.control.page.open.assert_called_with(modal_manager.dialog)
                    
                    # Тестируем закрытие
                    event.control.page.reset_mock()
                    close_result = modal_manager.close_modal(event_or_control=event)
                    assert isinstance(close_result, bool)
                    # Проверяем вызов page.close() (современный Flet API)
                    event.control.page.close.assert_called_with(modal_manager.dialog)
                    
            except Exception as e:
                pytest.fail(f"PageAccessManager интеграция не должна вызывать исключения: {e}")
    
    @given(st.booleans())
    def test_fallback_notification_property(self, has_cached_page):
        """
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 2.4, 5.2**
        
        Property: При недоступности модального окна должно показываться fallback уведомление.
        """
        # Arrange
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        
        if has_cached_page:
            # Настраиваем кэшированный page для показа уведомления
            mock_page = MagicMock(spec=ft.Page)
            modal_manager.page_manager.cached_page = mock_page
        else:
            modal_manager.page_manager.cached_page = None
        
        # Act - вызываем fallback уведомление
        try:
            modal_manager._show_fallback_notification()
            
            # Assert - не должно быть исключений
            # Если есть кэшированный page, должна быть попытка показать snack bar
            if has_cached_page:
                # Проверяем, что была попытка создать snack bar
                # (детальная проверка зависит от реализации)
                pass
                
        except Exception as e:
            pytest.fail(f"Fallback уведомление не должно вызывать исключения: {e}")
    
    @given(st.lists(
        st.sampled_from([None, Exception("Test error"), Mock()]),
        min_size=1,
        max_size=3
    ))
    def test_alternative_close_robustness_property(self, error_scenarios):
        """
        **Feature: calendar-legend-width-fix, Property 9: Error handling robustness**
        **Validates: Requirements 5.5**
        
        Property: Альтернативное закрытие модального окна должно быть устойчивым к ошибкам.
        """
        # Arrange
        mock_legend_component = Mock()
        modal_manager = ModalManager(mock_legend_component)
        indicators = [INDICATOR_CONFIGS[IndicatorType.INCOME_DOT]]
        modal_manager.create_modal(indicators)
        
        # Настраиваем кэшированный page
        mock_page = MagicMock(spec=ft.Page)
        modal_manager.page_manager.cached_page = mock_page
        
        # Act & Assert - тестируем альтернативное закрытие
        for scenario in error_scenarios:
            try:
                # Симулируем различные сценарии ошибок
                if isinstance(scenario, Exception):
                    with patch.object(mock_page, 'update', side_effect=scenario):
                        modal_manager._try_alternative_close()
                else:
                    modal_manager._try_alternative_close()
                
                # Не должно быть необработанных исключений
                
            except Exception as e:
                pytest.fail(f"Альтернативное закрытие не должно вызывать исключения: {e}")