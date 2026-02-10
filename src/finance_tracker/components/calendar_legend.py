from typing import Optional, List, Dict
import logging

import flet as ft

from .calendar_legend_types import (
    DisplayMode, 
    LegendIndicator, 
    INDICATOR_CONFIGS
)
from .modal_manager import ModalManager
from .width_calculator import WidthCalculator
from .page_access_manager import PageAccessManager

logger = logging.getLogger(__name__)


class CalendarLegend(ft.Container):
    """
    Улучшенная легенда календаря с адаптивным отображением и исправленными оценками ширины.
    
    Показывает все доступные индикаторы календаря в одну строку при достаточной ширине,
    или отображает приоритетные индикаторы с кнопкой "Подробнее" при ограниченном пространстве.
    
    Ключевые исправления в этой версии:
    - Скорректированы завышенные оценки ширины индикаторов (с ~670px до ~525px)
    - Исправлена неработающая кнопка "Подробнее" через улучшенный доступ к page
    - Добавлен WidthCalculator для точных вычислений ширины
    - Интегрирован PageAccessManager для надёжного доступа к page объекту
    - Улучшен ModalManager для стабильной работы модального окна
    
    Поддерживает:
    - Автоматическое определение доступной ширины календаря
    - Приоритизацию индикаторов при ограниченном пространстве (1-7 по важности)
    - Безопасную работу с модальным окном через множественные стратегии доступа к page
    - Адаптивное поведение при изменении размеров (порог 525px для полной легенды)
    - Визуальную группировку индикаторов (точки, символы, фон)
    - Подробное логирование для диагностики проблем
    
    Режимы отображения:
    - Полная легенда: все 7 индикаторов в одну строку (при ширине >= 525px)
    - Сокращённая легенда: приоритетные индикаторы + кнопка "Подробнее" (при ширине < 525px)
    - Модальное окно: все индикаторы с описаниями, сгруппированные по типам
    """

    def __init__(self, calendar_width: Optional[int] = None):
        """
        Инициализация улучшенной календарной легенды.
        
        Args:
            calendar_width: Ширина календаря для адаптивности (опционально)
        """
        super().__init__()
        
        try:
            # Настройки компонента
            self.calendar_width = calendar_width
            self.display_mode = DisplayMode.AUTO
            
            # Получаем все доступные индикаторы из конфигурации
            self.all_indicators = self._get_all_indicators()
            
            # Создаём менеджер модального окна
            self.modal_manager = ModalManager(self)
            
            # Создаём менеджер доступа к page объекту
            self.page_access_manager = PageAccessManager(self)
            
            # Инициализируем UI
            self._initialize_ui()
            
            logger.debug(
                f"CalendarLegend инициализирован успешно: "
                f"ширина календаря={calendar_width}px, "
                f"индикаторов загружено={len(self.all_indicators)}, "
                f"режим отображения={self.display_mode.value}"
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка при инициализации CalendarLegend: {e}")
            # Инициализируем fallback состояние
            self.calendar_width = calendar_width
            self.display_mode = DisplayMode.AUTO
            self.all_indicators = []
            self.modal_manager = ModalManager(self)
            self.page_access_manager = PageAccessManager(self)
            self._build_fallback_ui()

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
            
            logger.debug(
                f"Загружено {len(indicators)} индикаторов календарной легенды: "
                f"{[ind.type.value for ind in indicators]}"
            )
            return indicators
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке индикаторов: {e}")
            return []

    def _calculate_required_width(self) -> int:
        """
        Вычисляет необходимую ширину для отображения всех индикаторов.
        
        Использует WidthCalculator для точного вычисления ширины с учётом
        длины текста и размеров визуальных элементов.
        
        Returns:
            Необходимая ширина в пикселях
        """
        try:
            if not self.all_indicators:
                logger.debug("Нет индикаторов для вычисления ширины, возвращаем минимальную ширину")
                return 100  # Минимальная ширина
            
            # Используем WidthCalculator для точного вычисления
            result = WidthCalculator.calculate_width_with_fallback(self.all_indicators)
            
            # Логируем детали вычисления для отладки исправлений ширины
            logger.debug(
                f"Вычисление ширины легенды завершено: "
                f"общая_ширина={result.total_width}px, "
                f"точность={'высокая' if result.is_accurate else 'fallback'}, "
                f"индикаторов={len(self.all_indicators)}, "
                f"ширина_индикаторов={sum(result.individual_widths.values()) if result.individual_widths else 'N/A'}px, "
                f"отступы_между_элементами={result.spacing_width}px, "
                f"padding_контейнера={result.padding_width}px"
            )
            
            # Дополнительное логирование индивидуальных ширин для отладки
            if result.individual_widths:
                for indicator_type, width in result.individual_widths.items():
                    logger.debug(f"  Ширина индикатора {indicator_type.value}: {width}px")
            
            # Логируем сравнение с предыдущими значениями для контроля исправлений
            if result.total_width <= 525:
                logger.debug(
                    f"✓ Исправление ширины успешно: {result.total_width}px <= 525px (цель достигнута)"
                )
            else:
                logger.warning(
                    f"⚠ Ширина всё ещё высокая: {result.total_width}px > 525px (требует дополнительной оптимизации)"
                )
            
            return result.total_width
            
        except Exception as e:
            logger.error(f"Ошибка при вычислении ширины легенды: {e}")
            # Fallback к безопасному значению
            fallback_width = 525  # Новое ожидаемое значение после исправлений
            logger.warning(f"Использован fallback для ширины легенды: {fallback_width}px")
            return fallback_width

    def _should_show_full_legend(self) -> bool:
        """
        Определяет, показывать ли полную легенду или сокращённую с кнопкой.
        
        Использует порог в 525px для определения режима отображения.
        Если ширина календаря >= требуемой ширины, показывается полная легенда.
        
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
            
            # Подробное логирование для отладки режима отображения
            logger.debug(
                f"Определение режима отображения легенды: "
                f"ширина_календаря={self.calendar_width}px, "
                f"требуемая_ширина={required_width}px, "
                f"помещается={'ДА' if can_fit_all else 'НЕТ'}, "
                f"выбранный_режим={'полная легенда' if can_fit_all else 'сокращённая с кнопкой'}"
            )
            
            # Логируем пересечение критического порога 525px
            if self.calendar_width is not None:
                if self.calendar_width >= 525:
                    logger.debug(
                        f"✓ Ширина календаря ({self.calendar_width}px) >= 525px (порог для полной легенды)"
                    )
                else:
                    logger.debug(
                        f"⚠ Ширина календаря ({self.calendar_width}px) < 525px (показываем сокращённую легенду)"
                    )
            
            # Логируем эффект исправлений
            if can_fit_all and self.calendar_width and self.calendar_width < 670:
                logger.info(
                    f"🎉 Исправление работает! Полная легенда показана при ширине {self.calendar_width}px "
                    f"(раньше требовалось ~670px)"
                )
            
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
                    logger.debug(
                        f"✓ Добавлен приоритетный индикатор {indicator.type.value}: "
                        f"ширина={needed_width}px, "
                        f"приоритет={indicator.priority}, "
                        f"текущая_общая_ширина={current_width}px"
                    )
                else:
                    logger.debug(
                        f"✗ Индикатор {indicator.type.value} не помещается: "
                        f"нужно={current_width + needed_width}px, "
                        f"доступно={usable_width}px, "
                        f"приоритет={indicator.priority} (пропущен)"
                    )
                    break
            
            logger.debug(
                f"Выбор приоритетных индикаторов завершён: "
                f"выбрано={len(selected_indicators)} из {len(self.all_indicators)}, "
                f"доступная_ширина={available_width}px, "
                f"использовано_ширины={current_width}px, "
                f"выбранные_индикаторы={[ind.type.value for ind in selected_indicators]}"
            )
            
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
                logger.debug(
                    f"Построена полная легенда: "
                    f"все {len(self.all_indicators)} индикаторов с визуальной группировкой"
                )
            else:
                content = self._build_compact_legend()
                logger.debug(
                    "Построена сокращённая легенда: "
                    "приоритетные индикаторы + кнопка 'Подробнее'"
                )
            
            # Настраиваем контейнер с улучшенным стилем
            self.padding = ft.Padding.symmetric(horizontal=10, vertical=5)
            self.margin = ft.Margin.symmetric(vertical=2)
            self.bgcolor = None  # Прозрачный фон для интеграции с календарём
            self.border_radius = 4
            self.content = content
            
            logger.debug(
                f"UI календарной легенды успешно инициализирован: "
                f"режим={'полный' if self._should_show_full_legend() else 'сокращённый'}, "
                f"модальное_окно={'создано' if self.modal_manager.dialog else 'не создано'}"
            )
            
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
            
            logger.debug(
                f"Визуальная группировка индикаторов завершена: "
                f"групп={len(result)}, "
                f"распределение={[(group, len(indicators)) for group, indicators in result.items()]}"
            )
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
            margin=ft.Margin.symmetric(horizontal=5)
        )

    def _create_details_button(self) -> ft.TextButton:
        """
        Создаёт стилизованную кнопку "Подробнее" с правильным дизайном.
        
        Returns:
            Кнопка "Подробнее" с консистентным стилем
        """
        return ft.TextButton(
            content="Подробнее...",
            on_click=self._open_modal_safe,
            height=30,
            style=ft.ButtonStyle(
                color=ft.Colors.PRIMARY,
                text_style=ft.TextStyle(
                    size=12,
                    weight=ft.FontWeight.NORMAL
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
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
            self.padding = ft.Padding.symmetric(horizontal=10, vertical=5)
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
                text or "Элемент",  # Fallback для пустого текста
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
            return self._create_fallback_legend_item(text or "Элемент")

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
            # Минимальный fallback - создаём простейший Row с текстом
            try:
                return ft.Row(
                    controls=[ft.Text("•", size=12), ft.Text(text or "?", size=12)],
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            except Exception as critical_error:
                logger.error(f"Критическая ошибка даже в минимальном fallback: {critical_error}")
                # Последний fallback - возвращаем хотя бы Text
                return ft.Text(f"• {text or '?'}", size=12)

    def _open_modal_safe(self, e):
        """
        Безопасное открытие модального окна с обработкой ошибок.
        
        Использует улучшенный ModalManager с PageAccessManager для надёжного доступа к page.
        
        Args:
            e: Событие от кнопки "Подробнее"
        """
        try:
            # Создаём модальное окно если оно ещё не создано
            if not self.modal_manager.dialog:
                self.modal_manager.create_modal(self.all_indicators)
            
            # Открываем модальное окно через улучшенный ModalManager
            # ModalManager сам использует PageAccessManager для получения page
            success = self.modal_manager.open_modal(event_or_control=e)
            
            if success:
                logger.info(
                    "✓ Модальное окно календарной легенды успешно открыто: "
                    "использован_улучшенный_ModalManager=True, "
                    "PageAccessManager_стратегии=множественные"
                )
            else:
                logger.warning(
                    f"✗ Не удалось открыть модальное окно календарной легенды: "
                    f"проверьте доступность page объекта, "
                    f"событие_типа={type(e).__name__ if e else 'None'}"
                )
                
        except Exception as ex:
            logger.error(
                f"Критическая ошибка при открытии модального окна календарной легенды: {ex}, "
                f"тип_события={type(e).__name__ if e else 'None'}, "
                f"модальное_окно_создано={self.modal_manager.dialog is not None}, "
                f"PageAccessManager_доступен={self.page_access_manager is not None}"
            )

    def _safe_get_page(self, event_or_control) -> Optional[ft.Page]:
        """
        Безопасное получение page объекта из события или контрола.
        
        УСТАРЕЛО: Используйте PageAccessManager.get_page() вместо этого метода.
        Оставлено для обратной совместимости.
        
        Args:
            event_or_control: Событие или контрол от которого нужно получить page
            
        Returns:
            Page объект или None если не удалось получить
        """
        logger.debug("Использован устаревший метод _safe_get_page, перенаправляем на PageAccessManager")
        return self.page_access_manager.get_page(event_or_control)

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
                logger.info(
                    f"🔄 Режим отображения легенды изменился: "
                    f"{old_mode.value} → {new_mode.value}, "
                    f"ширина_календаря: {old_width}px → {new_width}px, "
                    f"требуемая_ширина={self._calculate_required_width()}px"
                )
                self._rebuild_ui()
            else:
                logger.debug(
                    f"Режим отображения не изменился: {new_mode.value}, "
                    f"ширина_календаря: {old_width}px → {new_width}px"
                )
                
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении ширины календарной легенды: {e}, "
                f"старая_ширина={getattr(self, 'calendar_width', None)}px, "
                f"новая_ширина={new_width}px, "
                f"требуемая_ширина_для_полной_легенды=~525px"
            )
            # Fallback - устанавливаем новую ширину без перестройки UI
            self.calendar_width = new_width

    def _rebuild_ui(self):
        """
        Перестраивает UI легенды при изменении режима отображения с сохранением стиля.
        """
        try:
            # Определяем новый режим и перестраиваем контент
            if self._should_show_full_legend():
                self.content = self._build_full_legend()
                logger.info(
                    f"🔄 UI легенды перестроен в полный режим: "
                    f"все {len(self.all_indicators)} индикаторов с группировкой"
                )
            else:
                self.content = self._build_compact_legend()
                logger.info(
                    "🔄 UI легенды перестроен в сокращённый режим: "
                    "приоритетные индикаторы + кнопка 'Подробнее'"
                )
            
            # Обновляем стиль контейнера
            self.padding = ft.Padding.symmetric(horizontal=10, vertical=5)
            self.margin = ft.Margin.symmetric(vertical=2)
                
            # Обновляем отображение если есть доступ к page
            if hasattr(self, 'page') and self.page:
                self.page.update()
                logger.debug("UI календарной легенды обновлён на странице")
            else:
                logger.debug("Page недоступен для обновления UI легенды")
                
        except Exception as e:
            logger.error(f"Ошибка при перестройке UI: {e}")
            # Fallback к безопасному состоянию
            try:
                self._build_fallback_ui()
                logger.info(
                    "Использован fallback UI после ошибки перестройки календарной легенды"
                )
            except Exception as fallback_error:
                logger.error(f"Критическая ошибка даже в fallback UI: {fallback_error}")
                # Минимальный fallback
                self.content = ft.Text("Легенда недоступна", size=12, color=ft.Colors.ERROR)

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
                logger.debug("Диалог закрыт через метод обратной совместимости")
            else:
                logger.warning("Не удалось закрыть диалог: page недоступен")
        except Exception as ex:
            logger.error(f"Ошибка при закрытии диалога: {ex}, "
                        f"событие: {type(e).__name__ if e else 'None'}")