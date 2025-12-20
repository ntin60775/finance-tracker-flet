from typing import Optional, List, Dict
import logging

import flet as ft

from .calendar_legend_types import (
    IndicatorType, 
    DisplayMode, 
    LegendIndicator, 
    INDICATOR_CONFIGS
)
from .modal_manager import ModalManager

logger = logging.getLogger(__name__)


class CalendarLegend(ft.Container):
    """
    Улучшенная легенда календаря с адаптивным отображением.
    
    Показывает все доступные индикаторы календаря в одну строку при достаточной ширине,
    или отображает приоритетные индикаторы с кнопкой "Подробнее" при ограниченном пространстве.
    
    Поддерживает:
    - Автоматическое определение доступной ширины
    - Приоритизацию индикаторов при ограниченном пространстве
    - Безопасную работу с модальным окном
    - Адаптивное поведение при изменении размеров
    """

    def __init__(self, calendar_width: Optional[int] = None):
        """
        Инициализация улучшенной календарной легенды.
        
        Args:
            calendar_width: Ширина календаря для адаптивности (опционально)
        """
        super().__init__()
        
        # Настройки компонента
        self.calendar_width = calendar_width
        self.display_mode = DisplayMode.AUTO
        
        # Получаем все доступные индикаторы из конфигурации
        self.all_indicators = self._get_all_indicators()
        
        # Создаём менеджер модального окна
        self.modal_manager = ModalManager()
        
        # Инициализируем UI
        self._initialize_ui()
        
        logger.debug(f"CalendarLegend инициализирован с шириной {calendar_width}")

    def _get_all_indicators(self) -> List[LegendIndicator]:
        """
        Возвращает все доступные индикаторы, отсортированные по приоритету.
        
        Returns:
            Список всех индикаторов, отсортированных по приоритету (1 = высший)
        """
        try:
            indicators = list(INDICATOR_CONFIGS.values())
            # Сортируем по приоритету (1 = высший приоритет)
            indicators.sort(key=lambda x: x.priority)
            
            logger.debug(f"Загружено {len(indicators)} индикаторов")
            return indicators
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке индикаторов: {e}")
            return []

    def _calculate_required_width(self) -> int:
        """
        Вычисляет необходимую ширину для отображения всех индикаторов.
        
        Returns:
            Необходимая ширина в пикселях
        """
        try:
            if not self.all_indicators:
                return 100  # Минимальная ширина
            
            # Суммируем ширину всех индикаторов
            total_indicator_width = sum(
                indicator.estimated_width for indicator in self.all_indicators
            )
            
            # Добавляем отступы между элементами (20px между каждой парой)
            spacing = (len(self.all_indicators) - 1) * 20
            
            # Добавляем padding контейнера
            padding = 40
            
            required_width = total_indicator_width + spacing + padding
            
            logger.debug(f"Вычисленная необходимая ширина: {required_width}px "
                        f"(индикаторы: {total_indicator_width}px, "
                        f"отступы: {spacing}px, padding: {padding}px)")
            
            return required_width
            
        except Exception as e:
            logger.error(f"Ошибка при вычислении ширины легенды: {e}")
            return 800  # Fallback к безопасному значению

    def _should_show_full_legend(self) -> bool:
        """
        Определяет, показывать ли полную легенду или сокращённую с кнопкой.
        
        Returns:
            True если нужно показать полную легенду, False для сокращённой
        """
        try:
            # Если ширина календаря не задана, показываем полную легенду
            if self.calendar_width is None:
                logger.debug("Ширина календаря не задана, показываем полную легенду")
                return True
            
            required_width = self._calculate_required_width()
            can_fit_all = self.calendar_width >= required_width
            
            logger.debug(f"Проверка помещения: календарь {self.calendar_width}px, "
                        f"требуется {required_width}px, помещается: {can_fit_all}")
            
            return can_fit_all
            
        except Exception as e:
            logger.error(f"Ошибка при определении режима отображения: {e}")
            return True  # По умолчанию показываем полную легенду

    def _get_priority_indicators_for_width(self, available_width: int) -> List[LegendIndicator]:
        """
        Возвращает индикаторы, которые помещаются в доступную ширину, по приоритету.
        
        Args:
            available_width: Доступная ширина в пикселях
            
        Returns:
            Список индикаторов, которые помещаются в доступную ширину
        """
        try:
            selected_indicators = []
            current_width = 40  # Начальный padding
            
            # Резервируем место для кнопки "Подробнее"
            button_width = 80
            usable_width = available_width - button_width
            
            for indicator in self.all_indicators:
                # Вычисляем ширину, необходимую для добавления этого индикатора
                needed_width = indicator.estimated_width
                if selected_indicators:
                    needed_width += 20  # spacing между элементами
                
                if current_width + needed_width <= usable_width:
                    selected_indicators.append(indicator)
                    current_width += needed_width
                    logger.debug(f"Добавлен индикатор {indicator.type}, "
                               f"текущая ширина: {current_width}px")
                else:
                    logger.debug(f"Индикатор {indicator.type} не помещается, "
                               f"нужно {current_width + needed_width}px, "
                               f"доступно {usable_width}px")
                    break
            
            logger.debug(f"Выбрано {len(selected_indicators)} индикаторов "
                        f"для ширины {available_width}px")
            
            return selected_indicators
            
        except Exception as e:
            logger.error(f"Ошибка при выборе приоритетных индикаторов: {e}")
            # Возвращаем хотя бы первые два (доходы и расходы)
            return self.all_indicators[:2] if len(self.all_indicators) >= 2 else self.all_indicators

    def _initialize_ui(self):
        """
        Инициализирует пользовательский интерфейс легенды с улучшенным стилем.
        
        Реализует:
        - Создание модального окна
        - Выбор подходящего режима отображения
        - Настройку контейнера с правильными отступами
        - Обработку ошибок с fallback UI
        """
        try:
            # Создаём модальное окно
            self.modal_manager.create_modal(self.all_indicators)
            
            # Определяем режим отображения и строим соответствующий UI
            if self._should_show_full_legend():
                content = self._build_full_legend()
                logger.debug("Построена полная легенда с визуальной группировкой")
            else:
                content = self._build_compact_legend()
                logger.debug("Построена сокращённая легенда с приоритизацией")
            
            # Настраиваем контейнер с улучшенным стилем
            self.padding = ft.padding.symmetric(horizontal=10, vertical=5)
            self.margin = ft.margin.symmetric(vertical=2)
            self.bgcolor = None  # Прозрачный фон для интеграции с календарём
            self.border_radius = 4
            self.content = content
            
            logger.debug("UI легенды успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации UI легенды: {e}")
            # Fallback к простому UI
            self._build_fallback_ui()

    def _build_full_legend(self) -> ft.Row:
        """
        Строит полную легенду со всеми индикаторами в одну строку.
        
        Реализует:
        - Отображение всех 7 индикаторов
        - Визуальную группировку похожих индикаторов
        - Правильное выравнивание по центру
        - Консистентные отступы между элементами
        
        Returns:
            Row с полной легендой, выровненной по центру
        """
        try:
            controls = []
            
            # Группируем индикаторы для лучшей визуальной организации
            grouped_indicators = self._group_indicators_visually(self.all_indicators)
            
            for group_name, indicators in grouped_indicators.items():
                # Добавляем индикаторы группы
                for indicator in indicators:
                    legend_item = self._build_legend_item(
                        indicator.visual_element,
                        indicator.label
                    )
                    controls.append(legend_item)
                
                # Добавляем визуальный разделитель между группами (кроме последней)
                if group_name != list(grouped_indicators.keys())[-1] and len(indicators) > 0:
                    separator = self._create_group_separator()
                    controls.append(separator)
            
            return ft.Row(
                controls=controls,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,  # Стандартный отступ 20px между элементами
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=False  # Не переносим элементы на новую строку
            )
            
        except Exception as e:
            logger.error(f"Ошибка при построении полной легенды: {e}")
            return self._build_fallback_legend()

    def _build_compact_legend(self) -> ft.Row:
        """
        Строит сокращённую легенду с приоритетными индикаторами и кнопкой "Подробнее".
        
        Реализует:
        - Отображение приоритетных индикаторов по важности
        - Кнопку "Подробнее" с правильным стилем
        - Адаптивный выбор индикаторов по доступной ширине
        - Консистентное выравнивание
        
        Returns:
            Row с сокращённой легендой и кнопкой "Подробнее"
        """
        try:
            controls = []
            
            # Получаем индикаторы, которые помещаются в доступную ширину
            if self.calendar_width:
                priority_indicators = self._get_priority_indicators_for_width(self.calendar_width)
            else:
                # Если ширина не задана, берём первые 3 самых приоритетных
                priority_indicators = self.all_indicators[:3]
            
            # Добавляем приоритетные индикаторы
            for indicator in priority_indicators:
                legend_item = self._build_legend_item(
                    indicator.visual_element,
                    indicator.label
                )
                controls.append(legend_item)
            
            # Добавляем стилизованную кнопку "Подробнее"
            details_button = self._create_details_button()
            controls.append(details_button)
            
            return ft.Row(
                controls=controls,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,  # Консистентный отступ 20px
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=False
            )
            
        except Exception as e:
            logger.error(f"Ошибка при построении сокращённой легенды: {e}")
            return self._build_fallback_legend()

    def _group_indicators_visually(self, indicators: List[LegendIndicator]) -> Dict[str, List[LegendIndicator]]:
        """
        Группирует индикаторы по визуальным типам для лучшей организации.
        
        Args:
            indicators: Список всех индикаторов
            
        Returns:
            Словарь с группами индикаторов: {группа: [индикаторы]}
        """
        try:
            groups = {
                "dots": [],      # Точечные индикаторы (доходы, расходы)
                "symbols": [],   # Символьные индикаторы (плановые, отложенные, кредиты)
                "backgrounds": [] # Фоновые индикаторы (разрывы, просрочки)
            }
            
            for indicator in indicators:
                visual_element = indicator.visual_element
                
                if isinstance(visual_element, ft.Container):
                    if visual_element.border_radius == 5:
                        # Круглые контейнеры = точки
                        groups["dots"].append(indicator)
                    elif visual_element.border_radius == 2:
                        # Прямоугольные контейнеры = фоновые индикаторы
                        groups["backgrounds"].append(indicator)
                elif isinstance(visual_element, ft.Text):
                    # Текстовые элементы = символы
                    groups["symbols"].append(indicator)
            
            # Удаляем пустые группы и сортируем индикаторы в группах по приоритету
            result = {}
            for group_name, group_indicators in groups.items():
                if group_indicators:
                    group_indicators.sort(key=lambda x: x.priority)
                    result[group_name] = group_indicators
            
            logger.debug(f"Индикаторы сгруппированы: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при группировке индикаторов: {e}")
            # Fallback - возвращаем все индикаторы в одной группе
            return {"all": sorted(indicators, key=lambda x: x.priority)}

    def _create_group_separator(self) -> ft.Container:
        """
        Создаёт визуальный разделитель между группами индикаторов.
        
        Returns:
            Тонкий вертикальный разделитель
        """
        return ft.Container(
            width=1,
            height=16,
            bgcolor=ft.Colors.OUTLINE_VARIANT,
            margin=ft.margin.symmetric(horizontal=5)
        )

    def _create_details_button(self) -> ft.TextButton:
        """
        Создаёт стилизованную кнопку "Подробнее" с правильным дизайном.
        
        Returns:
            Кнопка "Подробнее" с консистентным стилем
        """
        return ft.TextButton(
            text="Подробнее...",
            on_click=self._open_modal_safe,
            height=30,
            style=ft.ButtonStyle(
                color=ft.Colors.PRIMARY,
                text_style=ft.TextStyle(
                    size=12,
                    weight=ft.FontWeight.NORMAL
                ),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                shape=ft.RoundedRectangleBorder(radius=4)
            ),
            tooltip="Показать все индикаторы календаря"
        )

    def _build_fallback_legend(self) -> ft.Row:
        """
        Строит упрощённую легенду в случае ошибки с консистентным стилем.
        
        Returns:
            Row с базовой легендой, использующей безопасные значения
        """
        try:
            # Создаём базовые индикаторы с консистентным стилем
            income_item = self._build_legend_item(ft.Colors.GREEN, "Доход")
            expense_item = self._build_legend_item(ft.Colors.RED, "Расход")
            details_button = self._create_details_button()
            
            return ft.Row(
                controls=[income_item, expense_item, details_button],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка при создании fallback легенды: {e}")
            # Минимальный fallback
            return ft.Row(
                controls=[
                    ft.Text("Легенда недоступна", size=12, color=ft.Colors.ERROR)
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )

    def _build_fallback_ui(self):
        """
        Строит упрощённый UI в случае критической ошибки с консистентным стилем.
        """
        try:
            self.padding = ft.padding.symmetric(horizontal=10, vertical=5)
            self.content = ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.WARNING_AMBER_OUTLINED, 
                        size=16, 
                        color=ft.Colors.WARNING
                    ),
                    ft.Text(
                        "Легенда недоступна", 
                        size=12, 
                        color=ft.Colors.ON_SURFACE,
                        weight=ft.FontWeight.NORMAL
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
            logger.warning("Использован fallback UI для легенды")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при создании fallback UI: {e}")
            # Минимальный fallback без дополнительных элементов
            self.padding = 5
            self.content = ft.Text("?", size=12, color=ft.Colors.ERROR)

    def _build_legend_item(self, visual_element_or_color, text: str) -> ft.Row:
        """
        Создаёт элемент легенды с поддержкой всех типов индикаторов.
        
        Поддерживает:
        - Точечные индикаторы (Container с круглой формой)
        - Символьные индикаторы (Text с эмодзи и символами)
        - Фоновые индикаторы (Container с прямоугольной формой)
        - Обратную совместимость с цветами
        
        Args:
            visual_element_or_color: Визуальный элемент (Container/Text/Icon) или цвет для совместимости
            text: Текст метки
            
        Returns:
            Row с элементом легенды, выровненным по центру с правильными отступами
        """
        try:
            # Поддерживаем обратную совместимость с цветами
            if isinstance(visual_element_or_color, str):
                # Это цвет - создаём Container как раньше для точечных индикаторов
                visual_element = ft.Container(
                    width=10, 
                    height=10, 
                    border_radius=5, 
                    bgcolor=visual_element_or_color
                )
            else:
                # Это уже готовый визуальный элемент из конфигурации
                visual_element = visual_element_or_color
            
            # Создаём текстовую метку с консистентным стилем
            text_label = ft.Text(
                text, 
                size=12,
                color=ft.Colors.ON_SURFACE,  # Используем стандартный цвет текста
                weight=ft.FontWeight.NORMAL
            )
            
            # Создаём элемент легенды с правильным выравниванием
            legend_item = ft.Row(
                controls=[
                    visual_element,
                    text_label
                ],
                spacing=5,  # 5px между визуальным элементом и текстом
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True  # Компактное расположение элементов
            )
            
            logger.debug(f"Создан элемент легенды: {text}")
            return legend_item
            
        except Exception as e:
            logger.error(f"Ошибка при создании элемента легенды '{text}': {e}")
            # Fallback элемент с безопасными значениями
            return self._create_fallback_legend_item(text)

    def _create_fallback_legend_item(self, text: str) -> ft.Row:
        """
        Создаёт fallback элемент легенды в случае ошибки.
        
        Args:
            text: Текст метки
            
        Returns:
            Безопасный элемент легенды
        """
        try:
            fallback_visual = ft.Container(
                width=10, 
                height=10, 
                border_radius=5, 
                bgcolor=ft.Colors.GREY_400
            )
            
            fallback_text = ft.Text(
                text or "Элемент", 
                size=12,
                color=ft.Colors.ON_SURFACE
            )
            
            return ft.Row(
                controls=[fallback_visual, fallback_text],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка при создании fallback элемента: {e}")
            # Минимальный fallback
            return ft.Row(
                controls=[ft.Text("•", size=12), ft.Text(text or "?", size=12)],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )

    def _open_modal_safe(self, e):
        """
        Безопасное открытие модального окна с обработкой ошибок.
        
        Args:
            e: Событие от кнопки "Подробнее"
        """
        try:
            # Безопасное получение page объекта
            page = self._safe_get_page(e)
            if not page:
                logger.warning("Не удалось открыть модальное окно: page недоступен")
                return
            
            # Открываем модальное окно через ModalManager
            success = self.modal_manager.open_modal(page)
            if success:
                logger.debug("Модальное окно успешно открыто")
            else:
                logger.warning("Не удалось открыть модальное окно")
                
        except Exception as ex:
            logger.error(f"Ошибка при открытии модального окна: {ex}")

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

    def update_calendar_width(self, new_width: Optional[int]):
        """
        Обновляет ширину календаря и перестраивает легенду при необходимости.
        
        Args:
            new_width: Новая ширина календаря
        """
        try:
            old_width = self.calendar_width
            self.calendar_width = new_width
            
            # Проверяем, изменился ли режим отображения
            old_mode = DisplayMode.FULL if old_width is None or old_width >= self._calculate_required_width() else DisplayMode.COMPACT
            new_mode = DisplayMode.FULL if new_width is None or new_width >= self._calculate_required_width() else DisplayMode.COMPACT
            
            if old_mode != new_mode:
                logger.debug(f"Режим отображения изменился с {old_mode} на {new_mode}")
                self._rebuild_ui()
            else:
                logger.debug(f"Режим отображения не изменился: {new_mode}")
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении ширины календаря: {e}")

    def _rebuild_ui(self):
        """
        Перестраивает UI легенды при изменении режима отображения с сохранением стиля.
        """
        try:
            # Определяем новый режим и перестраиваем контент
            if self._should_show_full_legend():
                self.content = self._build_full_legend()
                logger.debug("UI перестроен в полный режим с группировкой")
            else:
                self.content = self._build_compact_legend()
                logger.debug("UI перестроен в сокращённый режим с приоритизацией")
            
            # Обновляем стиль контейнера
            self.padding = ft.padding.symmetric(horizontal=10, vertical=5)
            self.margin = ft.margin.symmetric(vertical=2)
                
            # Обновляем отображение если есть доступ к page
            if hasattr(self, 'page') and self.page:
                self.page.update()
                logger.debug("UI легенды обновлён на странице")
                
        except Exception as e:
            logger.error(f"Ошибка при перестройке UI: {e}")
            # Fallback к безопасному состоянию
            self._build_fallback_ui()

    # Методы для обратной совместимости с существующим кодом
    def _build_full_legend_content(self):
        """Метод для обратной совместимости - создание контента модального окна."""
        # Этот метод больше не используется, так как модальное окно создаётся через ModalManager
        # Оставляем для совместимости
        return ft.Column(
            controls=[
                ft.Text("Используйте кнопку 'Подробнее' для просмотра полной легенды", size=12)
            ]
        )

    def _open_dlg(self, e):
        """Метод для обратной совместимости - открытие диалога."""
        # Перенаправляем на новый безопасный метод
        self._open_modal_safe(e)

    def _close_dlg(self, e):
        """Метод для обратной совместимости - закрытие диалога."""
        # Закрытие теперь обрабатывается через ModalManager
        try:
            page = self._safe_get_page(e)
            if page:
                self.modal_manager.close_modal(page)
        except Exception as ex:
            logger.error(f"Ошибка при закрытии диалога: {ex}")