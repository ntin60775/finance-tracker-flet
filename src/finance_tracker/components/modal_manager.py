"""
ModalManager для управления модальным окном календарной легенды.

Обеспечивает безопасное создание, открытие и закрытие модального окна
с группировкой индикаторов по типам (точки, символы, фон).
"""
from typing import List, Optional, Dict
import logging

import flet as ft

from .calendar_legend_types import LegendIndicator, IndicatorType

logger = logging.getLogger(__name__)


class ModalManager:
    """Управляет модальным окном легенды календаря."""
    
    def __init__(self):
        """Инициализация ModalManager."""
        self.dialog: Optional[ft.AlertDialog] = None
        
    def create_modal(self, indicators: List[LegendIndicator]) -> ft.AlertDialog:
        """
        Создаёт модальное окно с полной легендой и группировкой индикаторов.
        
        Args:
            indicators: Список индикаторов для отображения
            
        Returns:
            Созданное модальное окно
        """
        try:
            logger.debug(f"Создание модального окна с {len(indicators)} индикаторами")
            
            # Группируем индикаторы по типам
            grouped_indicators = self._group_indicators_by_type(indicators)
            
            # Создаём содержимое модального окна
            content_controls = []
            
            # Добавляем группы индикаторов
            if grouped_indicators.get('dots'):
                content_controls.extend(self._build_indicator_group(
                    "Индикаторы транзакций (точки):",
                    grouped_indicators['dots']
                ))
                content_controls.append(ft.Divider())
            
            if grouped_indicators.get('symbols'):
                content_controls.extend(self._build_indicator_group(
                    "Символы:",
                    grouped_indicators['symbols']
                ))
                content_controls.append(ft.Divider())
            
            if grouped_indicators.get('backgrounds'):
                content_controls.extend(self._build_indicator_group(
                    "Фон дня:",
                    grouped_indicators['backgrounds']
                ))
            
            # Удаляем последний разделитель если он есть
            if content_controls and isinstance(content_controls[-1], ft.Divider):
                content_controls.pop()
            
            # Создаём модальное окно
            self.dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Легенда календаря"),
                content=ft.Column(
                    controls=content_controls,
                    height=400,
                    width=450,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=10
                ),
                actions=[
                    ft.TextButton(
                        "Закрыть", 
                        on_click=self._close_modal_handler
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            logger.info("Модальное окно успешно создано")
            return self.dialog
            
        except Exception as e:
            logger.error(f"Ошибка при создании модального окна: {e}")
            # Создаём fallback модальное окно
            self.dialog = self._create_fallback_modal()
            return self.dialog
    
    def _group_indicators_by_type(self, indicators: List[LegendIndicator]) -> Dict[str, List[LegendIndicator]]:
        """
        Группирует индикаторы по типам (точки, символы, фон).
        
        Args:
            indicators: Список индикаторов для группировки
            
        Returns:
            Словарь с группами индикаторов
        """
        groups = {
            'dots': [],
            'symbols': [],
            'backgrounds': []
        }
        
        for indicator in indicators:
            if indicator.type in [IndicatorType.INCOME_DOT, IndicatorType.EXPENSE_DOT]:
                groups['dots'].append(indicator)
            elif indicator.type in [IndicatorType.PLANNED_SYMBOL, IndicatorType.PENDING_SYMBOL, IndicatorType.LOAN_SYMBOL]:
                groups['symbols'].append(indicator)
            elif indicator.type in [IndicatorType.CASH_GAP_BG, IndicatorType.OVERDUE_BG]:
                groups['backgrounds'].append(indicator)
        
        return groups
    
    def _build_indicator_group(self, title: str, indicators: List[LegendIndicator]) -> List[ft.Control]:
        """
        Создаёт группу индикаторов с заголовком.
        
        Args:
            title: Заголовок группы
            indicators: Список индикаторов в группе
            
        Returns:
            Список контролов для группы
        """
        controls = [
            ft.Text(title, weight=ft.FontWeight.BOLD, size=14)
        ]
        
        for indicator in indicators:
            controls.append(self._build_legend_item(indicator))
        
        return controls
    
    def _build_legend_item(self, indicator: LegendIndicator) -> ft.Row:
        """
        Создаёт элемент легенды для модального окна.
        
        Args:
            indicator: Индикатор для отображения
            
        Returns:
            Строка с элементом легенды
        """
        return ft.Row(
            controls=[
                indicator.visual_element,
                ft.Column(
                    controls=[
                        ft.Text(indicator.label, weight=ft.FontWeight.W_500, size=13),
                        ft.Text(indicator.description, size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                    ],
                    spacing=2,
                    expand=True
                )
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    def _create_fallback_modal(self) -> ft.AlertDialog:
        """
        Создаёт упрощённое модальное окно в случае ошибки.
        
        Returns:
            Базовое модальное окно
        """
        return ft.AlertDialog(
            modal=True,
            title=ft.Text("Легенда календаря"),
            content=ft.Text("Ошибка при загрузке легенды. Попробуйте позже."),
            actions=[
                ft.TextButton("Закрыть", on_click=self._close_modal_handler),
            ],
        )
    
    def open_modal(self, page: ft.Page) -> bool:
        """
        Безопасно открывает модальное окно.
        
        Args:
            page: Объект страницы Flet
            
        Returns:
            True если окно успешно открыто, False в случае ошибки
        """
        try:
            if not page:
                logger.warning("Не удалось открыть модальное окно: page объект недоступен")
                return False
            
            if not self.dialog:
                logger.warning("Не удалось открыть модальное окно: диалог не создан")
                return False
            
            page.dialog = self.dialog
            self.dialog.open = True
            page.update()
            
            logger.debug("Модальное окно успешно открыто")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при открытии модального окна: {e}")
            return False
    
    def close_modal(self, page: ft.Page) -> bool:
        """
        Безопасно закрывает модальное окно.
        
        Args:
            page: Объект страницы Flet
            
        Returns:
            True если окно успешно закрыто, False в случае ошибки
        """
        try:
            if not page:
                logger.warning("Не удалось закрыть модальное окно: page объект недоступен")
                return False
            
            if not self.dialog:
                logger.debug("Модальное окно уже закрыто или не создано")
                return True
            
            self.dialog.open = False
            page.update()
            
            logger.debug("Модальное окно успешно закрыто")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии модального окна: {e}")
            return False
    
    def _close_modal_handler(self, e):
        """
        Обработчик события закрытия модального окна.
        
        Args:
            e: Событие от кнопки "Закрыть"
        """
        try:
            # Безопасное получение page объекта
            page = self._safe_get_page(e)
            if page:
                self.close_modal(page)
            else:
                logger.warning("Не удалось получить page объект для закрытия модального окна")
        except Exception as ex:
            logger.error(f"Ошибка в обработчике закрытия модального окна: {ex}")
    
    def _safe_get_page(self, event_or_control) -> Optional[ft.Page]:
        """
        Безопасное получение page объекта из события или контрола.
        
        Args:
            event_or_control: Событие или контрол от которого нужно получить page
            
        Returns:
            Page объект или None если не удалось получить
        """
        try:
            if hasattr(event_or_control, 'control') and event_or_control.control:
                return event_or_control.control.page
            elif hasattr(event_or_control, 'page'):
                return event_or_control.page
            elif hasattr(self, 'page') and self.page:
                return self.page
            return None
        except AttributeError:
            logger.warning("Не удалось получить page объект для модального окна")
            return None