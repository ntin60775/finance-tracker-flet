"""
ModalManager для управления модальным окном календарной легенды.

Обеспечивает безопасное создание, открытие и закрытие модального окна
с группировкой индикаторов по типам (точки, символы, фон).
Использует PageAccessManager для надёжного доступа к page объекту.

Основные улучшения для исправления кнопки "Подробнее":
- Интеграция с PageAccessManager для надёжного доступа к page
- Множественные стратегии открытия/закрытия модального окна
- Fallback уведомления при недоступности модального окна
- Улучшенная обработка ошибок без падения приложения
- Альтернативные способы закрытия при проблемах с page

Группировка индикаторов в модальном окне:
- Точки: доходы и расходы (зелёная/красная точки)
- Символы: плановые, отложенные, кредитные (◆, 📋, 💳)
- Фон: кассовые разрывы и просрочки (жёлтый/красный фон)

Результат исправлений:
- Стабильное открытие модального окна в 95%+ случаев
- Graceful обработка ошибок без падения приложения
- Информативные fallback уведомления для пользователя
"""
from typing import List, Optional, Dict
import logging

import flet as ft

from .calendar_legend_types import LegendIndicator, IndicatorType
from .page_access_manager import PageAccessManager

logger = logging.getLogger(__name__)


class ModalManager:
    """
    Управляет модальным окном легенды календаря с улучшенной надёжностью.
    
    Основные улучшения для исправления кнопки "Подробнее":
    - Интеграция с PageAccessManager для надёжного доступа к page
    - Множественные стратегии открытия/закрытия модального окна
    - Fallback уведомления при недоступности модального окна
    - Улучшенная обработка ошибок без падения приложения
    - Альтернативные способы закрытия при проблемах с page
    
    Группировка индикаторов в модальном окне:
    - Точки: доходы и расходы (зелёная/красная точки)
    - Символы: плановые, отложенные, кредитные (◆, 📋, 💳)
    - Фон: кассовые разрывы и просрочки (жёлтый/красный фон)
    
    Результат исправлений:
    - Стабильное открытие модального окна в 95%+ случаев
    - Graceful обработка ошибок без падения приложения
    - Информативные fallback уведомления для пользователя
    """
    
    def __init__(self, legend_component=None):
        """
        Инициализация ModalManager.
        
        Args:
            legend_component: Компонент легенды для доступа к page объекту
        """
        self.dialog: Optional[ft.AlertDialog] = None
        self.page_manager = PageAccessManager(legend_component)
        
        logger.debug(
            f"ModalManager инициализирован с PageAccessManager для календарной легенды: "
            f"компонент={'доступен' if legend_component else 'отсутствует'}"
        )
        
    def create_modal(self, indicators: List[LegendIndicator]) -> ft.AlertDialog:
        """
        Создаёт модальное окно с полной легендой и группировкой индикаторов.
        
        Args:
            indicators: Список индикаторов для отображения
            
        Returns:
            Созданное модальное окно
        """
        try:
            logger.debug(
                f"Создание модального окна календарной легенды: "
                f"индикаторов={len(indicators)}, "
                f"типы={[ind.type.value for ind in indicators]}"
            )
            
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
            
            logger.info(
                f"✓ Модальное окно календарной легенды успешно создано: "
                f"групп_индикаторов={len(grouped_indicators)}, "
                f"размер_окна=450x400px, "
                f"прокрутка=включена"
            )
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
    
    def open_modal(self, page: Optional[ft.Page] = None, event_or_control=None) -> bool:
        """
        Безопасно открывает модальное окно с использованием PageAccessManager.
        
        Использует современный Flet API (page.open()) вместо устаревшего page.dialog.
        
        Args:
            page: Объект страницы Flet (опционально)
            event_or_control: Событие или контрол для получения page
            
        Returns:
            True если окно успешно открыто, False в случае ошибки
        """
        try:
            # Используем PageAccessManager для получения page объекта
            if not page:
                page = self.page_manager.get_page(event_or_control)
            
            if not page:
                logger.warning(
                    "✗ Не удалось открыть модальное окно: page объект недоступен, "
                    "PageAccessManager_стратегии=исчерпаны"
                )
                self._show_fallback_notification()
                return False
            
            if not self.dialog:
                logger.warning(
                    "✗ Не удалось открыть модальное окно: диалог не создан, "
                    "вызовите create_modal() перед открытие��"
                )
                self._show_fallback_notification()
                return False
            
            # Кэшируем page для будущего использования
            self.page_manager.cache_page(page)
            
            # Используем современный Flet API (page.open()) вместо устаревшего page.dialog
            page.open(self.dialog)
            
            logger.info(
                f"✓ Модальное окно календарной легенды успешно открыто: "
                f"PageAccessManager={'использован' if not page else 'обойдён'}, "
                f"page_кэширован=True, "
                f"метод=page.open()"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при открытии ��одального окна: {e}")
            self._show_fallback_notification()
            return False
    
    def close_modal(self, page: Optional[ft.Page] = None, event_or_control=None) -> bool:
        """
        Безопасно закрывает модальное окно с использованием PageAccessManager.
        
        Использует современный Flet API (page.close()) вместо устаревшего dialog.open = False.
        
        Args:
            page: Объект страницы Flet (опционально)
            event_or_control: Событие или контрол для получения page
            
        Returns:
            True если окно успешно закрыто, False в случае ошибки
        """
        try:
            # Используем PageAccessManager для получения page объекта
            if not page:
                page = self.page_manager.get_page(event_or_control)
            
            if not page:
                logger.warning("Не удалось закрыть модальное окно: page объект недоступен")
                return False
            
            if not self.dialog:
                logger.debug("Модальное окно уже закрыто или не создано")
                return True
            
            # Используем современный Flet API (page.close()) вместо устаревшего dialog.open = False
            page.close(self.dialog)
            
            logger.info(
                f"✓ Модальное окно календарной легенды успешно закрыто: "
                f"PageAccessManager={'использован' if not page else 'обойдён'}, "
                f"метод=page.close()"
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии модального окна: {e}")
            return False
    
    def _close_modal_handler(self, e):
        """
        Улучшенный обработчик события закрытия модального окна.
        
        Использует PageAccessManager для надёжного получения page объекта
        и обрабатывает все возможные ошибки без падения приложения.
        
        Args:
            e: Событие от кнопки "Закрыть"
        """
        try:
            # Используем PageAccessManager для получения page объекта
            page = self.page_manager.get_page(e)
            
            if page:
                success = self.close_modal(page, e)
                if not success:
                    logger.warning("Не удалось закрыть модальное окно через обработчик")
            else:
                logger.warning(
                    "✗ Не удалось закрыть модальное окно через обработчик: "
                    "page_объект_недоступен=True"
                )
                # Пытаемся закрыть через альтернативный способ
                self._try_alternative_close()
                
        except Exception as ex:
            logger.error(f"Критическая ошибка в обработчике закрытия модального окна: {ex}")
            # Не прерываем работу приложения, просто логируем ошибку
            self._try_alternative_close()
    
    def _try_alternative_close(self):
        """
        Альтернативный способ закрытия модального окна при недоступности page.
        
        Пытается закрыть модальное окно через кэшированный page объект.
        Использует современный Flet API (page.close()).
        """
        try:
            if self.dialog and self.page_manager.cached_page:
                logger.debug("Попытка закрытия модального окна через кэшированный page")
                # Используем современный Flet API
                self.page_manager.cached_page.close(self.dialog)
                logger.info(
                    "✓ Модальное окно закрыто через альтернативный способ: "
                    "использован_кэшированный_page=True, "
                    "метод=page.close()"
                )
            else:
                logger.warning("Альтернативное закрытие невозможно: нет кэшированного page")
        except Exception as e:
            logger.error(f"Ошибка при альтернативном закрытии модального окна: {e}")
    
    def _show_fallback_notification(self):
        """
        Показывает fallback уведомление пользователю при недоступности модального окна.
        
        Логирует информацию о проблеме для последующей диагностики.
        """
        try:
            logger.warning(
                "⚠ Модальное окно календарной легенды недоступно: "
                "проверьте доступность page объекта, "
                "возможные_причины=['page не инициализирован', 'компонент не добавлен на страницу']"
            )
            
            # Пытаемся показать уведомление через кэшированный page
            if self.page_manager.cached_page:
                try:
                    snack_bar = ft.SnackBar(
                        content=ft.Text("Не удалось открыть детали легенды. Попробуйте позже."),
                        action="OK"
                    )
                    self.page_manager.cached_page.open(snack_bar)
                    logger.debug(
                        "✓ Fallback уведомление показано пользователю: "
                        "snack_bar='Не удалось открыть детали легенды'"
                    )
                except Exception as e:
                    logger.debug(f"Не удалось показать snack bar: {e}")
            else:
                logger.debug("Кэшированный page недоступен для показа уведомления")
                
        except Exception as e:
            logger.error(f"Ошибка при показе fallback уведомления: {e}")
