import calendar
import datetime
from typing import Callable, List, Optional

import flet as ft

from finance_tracker.models.enums import TransactionType, PaymentStatus
from finance_tracker.models.models import (
    Transaction,
    PlannedOccurrence,
    PendingPaymentDB,
    LoanPaymentDB,
)
from finance_tracker.utils.logger import get_logger
from finance_tracker.services.balance_forecast_service import detect_cash_gaps
from finance_tracker.services.pending_payment_service import get_all_pending_payments
from finance_tracker.database import get_db

logger = get_logger(__name__)


class CalendarWidget(ft.Container):
    """
    Виджет календаря для отображения дней месяца и индикаторов транзакций.

    Ячейки имеют квадратную форму (aspect_ratio=1), высота подстраивается под ширину.
    Размер шрифта и индикаторов адаптируется под разрешение экрана.
    """

    # Константы для адаптивного расчёта размеров шрифта и индикаторов
    # min_height - минимальная высота окна для применения пресета
    RESOLUTION_PRESETS = {
        # 2K (2560x1440): высота окна ~1340px
        "2k": {"min_height": 1200, "font_size": 16, "indicator_size": 10},
        # Full HD (1920x1080): высота окна ~980px
        "fullhd": {"min_height": 800, "font_size": 14, "indicator_size": 8},
        # Меньшие разрешения
        "default": {"min_height": 0, "font_size": 12, "indicator_size": 6},
    }

    def __init__(
        self,
        on_date_selected: Callable[[datetime.date], None],
        initial_date: Optional[datetime.date] = None,
        page_height: Optional[int] = None,
    ):
        """
        Инициализация виджета календаря.

        Args:
            on_date_selected: Callback функция, вызываемая при выборе даты.
            initial_date: Начальная дата (по умолчанию сегодня).
            page_height: Высота страницы для адаптивного расчёта размеров (опционально).
        """
        super().__init__()
        self.on_date_selected = on_date_selected
        self.current_date = initial_date or datetime.date.today()
        # Устанавливаем selected_date на current_date, чтобы при старте что-то было выбрано
        self.selected_date = self.current_date
        self.calendar = calendar.Calendar(firstweekday=0)  # Понедельник - первый день
        self.transactions: List[Transaction] = []
        self.planned_occurrences: List[PlannedOccurrence] = []
        self.pending_payments: List[PendingPaymentDB] = []
        self.loan_payments: List[LoanPaymentDB] = []
        self.cash_gaps: List[datetime.date] = []

        # Сохраняем начальную высоту страницы
        self._page_height = page_height

        # Вычисляем размеры для текущего разрешения
        self._update_cell_dimensions()

        # UI Components
        self.header_text = ft.Text(
            value="", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
        )
        self.days_grid = ft.Column(spacing=2)

        # Init Layout
        self.padding = 10
        self.border = ft.Border.all(1, "outlineVariant")
        self.border_radius = 10
        self.bgcolor = "surface"

        self.content = ft.Column(
            controls=[
                self._build_header(),
                self._build_weekdays_header(),
                self.days_grid,
            ],
            spacing=10,
        )

    def _update_cell_dimensions(self):
        """
        Вычисляет размеры шрифта и индикаторов на основе высоты экрана.

        Определяет пресет разрешения (2K, Full HD, default) и устанавливает
        соответствующие размеры: размер шрифта, размер индикаторов.
        Высота ячеек определяется через aspect_ratio=1 (квадратные ячейки).
        """
        # Получаем высоту страницы
        page_height = self._page_height
        if page_height is None and self.page:
            page_height = self.page.height

        # Fallback к Full HD если высота неизвестна
        if not page_height:
            page_height = 1080

        # Преобразуем в int для безопасности (в тестах может быть MagicMock)
        try:
            page_height = int(page_height) if page_height else 1080
        except (ValueError, TypeError):
            page_height = 1080

        # Определяем пресет по высоте экрана
        if page_height >= self.RESOLUTION_PRESETS["2k"]["min_height"]:
            preset = self.RESOLUTION_PRESETS["2k"]
            logger.debug(f"Используется пресет 2K для высоты {page_height}px")
        elif page_height >= self.RESOLUTION_PRESETS["fullhd"]["min_height"]:
            preset = self.RESOLUTION_PRESETS["fullhd"]
            logger.debug(f"Используется пресет Full HD для высоты {page_height}px")
        else:
            preset = self.RESOLUTION_PRESETS["default"]
            logger.debug(f"Используется пресет default для высоты {page_height}px")

        # Устанавливаем размеры (высота определяется через aspect_ratio=1)
        self._font_size = preset["font_size"]
        self._indicator_size = preset["indicator_size"]

        logger.info(
            f"Адаптивные размеры календаря: шрифт={self._font_size}px, "
            f"индикаторы={self._indicator_size}px (экран: {page_height}px)"
        )

    def update_for_page_height(self, page_height: int):
        """
        Обновляет размеры ячеек при изменении высоты страницы.

        Args:
            page_height: Новая высота страницы в пикселях
        """
        self._page_height = page_height
        self._update_cell_dimensions()
        self._update_calendar()

    def did_mount(self):
        """Вызывается после монтирования контрола на страницу."""
        # Обновляем размеры на основе реальной высоты страницы
        if self.page and self.page.height:
            self._page_height = self.page.height
            self._update_cell_dimensions()
        self._update_calendar()

    def set_transactions(
        self,
        transactions: List[Transaction],
        planned_occurrences: Optional[List[PlannedOccurrence]] = None,
    ):
        """
        Обновление данных для отображения индикаторов.

        Args:
            transactions: Список транзакций за отображаемый месяц.
            planned_occurrences: Список плановых вхождений за отображаемый месяц.
        """
        self.transactions = transactions
        self.planned_occurrences = planned_occurrences or []

        # Обновляем кассовые разрывы для текущего месяца
        self._update_cash_gaps()

        # Обновляем отложенные платежи для текущего месяца
        self._update_pending_payments()

        # Обновляем платежи по кредитам для текущего месяца
        self._update_loan_payments()

        self._update_calendar()

    def _update_cash_gaps(self):
        """Обновляет список кассовых разрывов для отображаемого месяца."""
        try:
            # Определяем диапазон дат для текущего месяца
            # Находим первый и последний день месяца
            _, days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)
            start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
            end_date = datetime.date(self.current_date.year, self.current_date.month, days_in_month)

            # Используем сервис для обнаружения кассовых разрывов
            with get_db() as session:
                self.cash_gaps = detect_cash_gaps(session, start_date, end_date)

        except Exception as e:
            logger.error(f"Ошибка при обновлении кассовых разрывов: {e}")
            self.cash_gaps = []

    def _update_pending_payments(self):
        """Обновляет список отложенных платежей с плановой датой для отображаемого месяца."""
        try:
            # Загружаем все активные отложенные платежи с плановой датой
            with get_db() as session:
                all_payments = get_all_pending_payments(session, has_planned_date=True)

                # Фильтруем только платежи текущего месяца
                _, days_in_month = calendar.monthrange(
                    self.current_date.year, self.current_date.month
                )
                start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
                end_date = datetime.date(
                    self.current_date.year, self.current_date.month, days_in_month
                )

                self.pending_payments = [
                    p
                    for p in all_payments
                    if p.planned_date and start_date <= p.planned_date <= end_date
                ]

                logger.info(
                    f"Загружено {len(self.pending_payments)} отложенных платежей "
                    f"для месяца {self.current_date.month}/{self.current_date.year}"
                )

        except Exception as e:
            logger.error(f"Ошибка при обновлении отложенных платежей: {e}")
            self.pending_payments = []

    def _update_loan_payments(self):
        """Обновляет список платежей по кредитам для отображаемого месяца."""
        try:
            # Определяем диапазон дат для текущего месяца
            _, days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)
            start_date = datetime.date(self.current_date.year, self.current_date.month, 1)
            end_date = datetime.date(self.current_date.year, self.current_date.month, days_in_month)

            # Загружаем все платежи по кредитам для текущего месяца
            with get_db() as session:
                self.loan_payments = (
                    session.query(LoanPaymentDB)
                    .filter(
                        LoanPaymentDB.scheduled_date >= start_date,
                        LoanPaymentDB.scheduled_date <= end_date,
                    )
                    .all()
                )

                logger.info(
                    f"Загружено {len(self.loan_payments)} платежей по кредитам "
                    f"для месяца {self.current_date.month}/{self.current_date.year}"
                )

        except Exception as e:
            logger.error(f"Ошибка при обновлении платежей по кредитам: {e}")
            self.loan_payments = []

    def _build_header(self):
        """Создание заголовка с навигацией."""
        return ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT,
                    on_click=self._prev_month,
                    tooltip="Предыдущий месяц",
                ),
                ft.Container(content=self.header_text, expand=True, alignment=ft.Alignment.CENTER),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT,
                    on_click=self._next_month,
                    tooltip="Следующий месяц",
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _build_weekdays_header(self):
        """
        Создание заголовка с номерами недель (горизонтально).

        В вертикальном календаре вместо дней недели (Пн-Вс) показываем номера недель (Н1, Н2, ...).
        Первый элемент - пустой контейнер для выравнивания с метками дней недели слева.

        Returns:
            Row с метками недель
        """
        # Определяем количество недель в текущем месяце
        month_matrix = self.calendar.monthdayscalendar(
            self.current_date.year, self.current_date.month
        )
        num_weeks = len(month_matrix)

        return ft.Row(
            controls=[
                # Пустой контейнер для выравнивания с метками дней недели слева
                ft.Container(width=40),
                # Метки недель
                *[
                    ft.Container(
                        content=ft.Text(
                            f"Н{i + 1}",
                            weight=ft.FontWeight.BOLD,
                            color="secondary",
                            text_align=ft.TextAlign.CENTER,
                            size=12,
                        ),
                        expand=True,
                        alignment=ft.Alignment.CENTER,
                    )
                    for i in range(num_weeks)
                ],
            ],
            spacing=2,
        )

    def _prev_month(self, _):
        """Переход к предыдущему месяцу."""
        # Вычисляем первый день предыдущего месяца
        first_day = self.current_date.replace(day=1)
        prev_month = first_day - datetime.timedelta(days=1)
        self.current_date = prev_month.replace(day=1)

        # Обновляем кассовые разрывы, отложенные платежи и платежи по кредитам при смене месяца
        self._update_cash_gaps()
        self._update_pending_payments()
        self._update_loan_payments()
        self._update_calendar()

    def _next_month(self, _):
        """Переход к следующему месяцу."""
        # Вычисляем первый день следующего месяца
        days_in_month = calendar.monthrange(self.current_date.year, self.current_date.month)[1]
        next_month = self.current_date.replace(day=1) + datetime.timedelta(days=days_in_month)
        self.current_date = next_month

        # Обновляем кассовые разрывы, отложенные платежи и платежи по кредитам при смене месяца
        self._update_cash_gaps()
        self._update_pending_payments()
        self._update_loan_payments()
        self._update_calendar()

    def _on_day_click(self, date_obj: datetime.date):
        """Обработка клика по дню."""
        self.selected_date = date_obj
        self._update_calendar()  # Перерисовываем для обновления выделения
        if self.on_date_selected:
            self.on_date_selected(date_obj)

    def select_date(self, date_obj: datetime.date):
        """
        Программный выбор даты (без вызова callback).

        Используется для синхронизации выделения при выборе даты из других компонентов.

        Args:
            date_obj: Дата для выбора
        """
        logger.debug(
            f"select_date вызван с датой: {date_obj}, "
            f"текущая selected_date: {self.selected_date}, "
            f"текущий месяц: {self.current_date}"
        )

        # Проверяем доступность page перед началом обновления
        if not self.page:
            logger.warning(
                f"select_date: self.page недоступен при попытке выбрать дату {date_obj}. "
                f"Обновление selected_date выполнено, но визуальное обновление отложено."
            )
            # Всё равно обновляем selected_date для сохранения состояния
            self.selected_date = date_obj
            return

        self.selected_date = date_obj

        # Если дата в другом месяце, переключаем месяц
        if date_obj.year != self.current_date.year or date_obj.month != self.current_date.month:
            logger.debug(
                f"Дата в другом месяце, переключаем с "
                f"{self.current_date} на {date_obj.replace(day=1)}"
            )
            self.current_date = date_obj.replace(day=1)
            # Обновляем данные для нового месяца
            self._update_cash_gaps()
            self._update_pending_payments()
            self._update_loan_payments()

        logger.debug(
            f"Перед вызовом _update_calendar(), self.page доступен: {self.page is not None}"
        )
        self._update_calendar()  # Перерисовываем для обновления выделения
        logger.debug("select_date завершён успешно")

    def _update_calendar(self):
        """
        Перерисовка сетки календаря (транспонированная вертикальная версия).

        Создаёт 7 строк (по одной для каждого дня недели),
        каждая строка содержит ячейки для всех недель месяца.
        Дни недели отображаются по вертикали (строки), недели - по горизонтали (столбцы).
        """
        logger.debug(
            f"_update_calendar вызван, "
            f"self.page доступен: {self.page is not None}, "
            f"selected_date: {self.selected_date}"
        )

        if not self.page:
            logger.warning(
                f"_update_calendar: self.page недоступен! "
                f"Визуальное обновление календаря невозможно. "
                f"selected_date={self.selected_date}, current_date={self.current_date}"
            )
            return

        # Обновляем заголовок
        months = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь",
        ]
        self.header_text.value = f"{months[self.current_date.month - 1]} {self.current_date.year}"

        # Очищаем сетку
        self.days_grid.controls.clear()

        # Генерируем матрицу дней месяца
        month_matrix = self.calendar.monthdayscalendar(
            self.current_date.year, self.current_date.month
        )

        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        # Для каждого дня недели создаём строку (транспонирование)
        for day_index, weekday in enumerate(weekdays):
            day_row = ft.Row(spacing=2)

            # Добавляем метку дня недели слева
            is_weekend = weekday in ["Сб", "Вс"]
            day_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        weekday,
                        weight=ft.FontWeight.BOLD,
                        color="secondary",
                        size=self._font_size - 2,  # Адаптивный размер шрифта метки
                    ),
                    width=40,
                    alignment=ft.Alignment.CENTER_RIGHT,
                    padding=ft.Padding.only(right=5),
                    # Выделяем выходные светлым фоном
                    bgcolor=ft.Colors.BLUE_50 if is_weekend else None,
                    border_radius=5,
                )
            )

            # Добавляем ячейки для каждой недели (транспонирование)
            for week in month_matrix:
                day = week[day_index]
                if day == 0:
                    # Пустая ячейка - квадратная (aspect_ratio=1)
                    day_row.controls.append(
                        ft.Container(
                            expand=True,
                            aspect_ratio=1,  # Квадратная ячейка
                        )
                    )
                else:
                    # Ячейка с днём
                    current_day_date = datetime.date(
                        self.current_date.year, self.current_date.month, day
                    )
                    day_row.controls.append(self._build_day_cell(current_day_date))

            self.days_grid.controls.append(day_row)

        # Обновляем заголовок с номерами недель (он зависит от количества недель)
        if hasattr(self, "content") and self.content and len(self.content.controls) > 1:
            self.content.controls[1] = self._build_weekdays_header()

        # Проверяем, добавлен ли контрол на страницу (имеет uid)
        # Если нет - пропускаем update, т.к. это вызовет AssertionError
        try:
            if hasattr(self, "_Control__uid") and self._Control__uid is not None:
                logger.debug("Перед вызовом self.update()")
                self.update()
                logger.debug("_update_calendar завершён успешно, self.update() вызван")
            else:
                logger.debug("Пропуск self.update() - контрол ещё не добавлен на страницу")
        except AssertionError as e:
            logger.warning(
                f"AssertionError при update(): {e} - контрол ещё не полностью инициализирован"
            )

    def _build_day_cell(self, date_obj: datetime.date) -> ft.Container:
        """
        Создание ячейки для конкретного дня.

        Args:
            date_obj: Дата для ячейки

        Returns:
            Container с содержимым ячейки
        """
        is_selected = self.selected_date == date_obj
        is_today = date_obj == datetime.date.today()
        is_cash_gap = date_obj in self.cash_gaps
        has_overdue_payment = self._has_overdue_payment(date_obj)

        # Собираем индикаторы для дня
        indicators = self._get_indicators_for_date(date_obj)

        # Стилизация
        if has_overdue_payment:
            bg_color = ft.Colors.RED_100
            text_color = ft.Colors.BLACK
            border = ft.Border.all(2, ft.Colors.RED_700)
        elif is_cash_gap:
            bg_color = ft.Colors.AMBER_100
            text_color = ft.Colors.BLACK
            border = ft.Border.all(2, ft.Colors.AMBER_700)
        elif is_selected:
            bg_color = "primaryContainer"
            text_color = "onPrimaryContainer"
            border = ft.Border.all(2, ft.Colors.GREEN_700)
        elif is_today:
            bg_color = ft.Colors.BLUE_50
            text_color = "primary"
            border = ft.Border.all(2, "primary")
        else:
            bg_color = ft.Colors.SURFACE_CONTAINER_LOW
            text_color = "onSurface"
            border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        # Формируем tooltip
        tooltip_text = None
        if has_overdue_payment:
            tooltip_text = "Просроченный платёж по кредиту!"
        elif is_cash_gap:
            tooltip_text = "Кассовый разрыв!"

        # Разбиваем индикаторы на строки, если их больше 3
        indicator_rows = []
        if len(indicators) <= 3:
            indicator_rows.append(
                ft.Row(
                    controls=indicators,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                )
            )
        else:
            # Разбиваем на строки по 3 индикатора
            for i in range(0, len(indicators), 3):
                indicator_rows.append(
                    ft.Row(
                        controls=indicators[i : i + 3],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=2,
                    )
                )

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        str(date_obj.day),
                        weight=ft.FontWeight.BOLD
                        if is_today or is_selected
                        else ft.FontWeight.NORMAL,
                        color=text_color,
                        size=self._font_size,  # Адаптивный размер шрифта
                    ),
                    ft.Column(
                        controls=indicator_rows,
                        spacing=1,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            aspect_ratio=1,  # Квадратная ячейка (высота = ширина)
            bgcolor=bg_color,
            border_radius=8,
            border=border,
            on_click=lambda _, d=date_obj: self._on_day_click(d),
            ink=True,
            tooltip=tooltip_text,
        )

    def _has_overdue_payment(self, date_obj: datetime.date) -> bool:
        """
        Проверяет наличие просроченных платежей по кредитам для конкретной даты.

        Args:
            date_obj: Дата для проверки

        Returns:
            True, если есть просроченные платежи на эту дату
        """
        for payment in self.loan_payments:
            if payment.scheduled_date == date_obj and payment.status == PaymentStatus.OVERDUE:
                return True
        return False

    def _get_indicators_for_date(self, date_obj: datetime.date) -> List[ft.Control]:
        """Генерация индикаторов для конкретной даты."""
        indicators = []

        has_income = False
        has_expense = False

        # Фильтруем транзакции для этой даты
        for t in self.transactions:
            if t.date == date_obj:
                if t.type == TransactionType.INCOME:
                    has_income = True
                elif t.type == TransactionType.EXPENSE:
                    has_expense = True

        # Проверяем плановые вхождения
        has_planned = False
        for occ in self.planned_occurrences:
            if occ.occurrence_date == date_obj:
                has_planned = True
                break

        # Проверяем отложенные платежи с плановой датой
        has_pending_payment = False
        for payment in self.pending_payments:
            if payment.planned_date == date_obj:
                has_pending_payment = True
                break

        # Проверяем платежи по кредитам (requirements 11.6)
        has_loan_payment = False
        for payment in self.loan_payments:
            if payment.scheduled_date == date_obj:
                has_loan_payment = True
                break

        # Используем адаптивный размер индикаторов
        dot_size = self._indicator_size - 2  # Точки чуть меньше
        icon_size = self._indicator_size

        if has_income:
            indicators.append(
                ft.Container(
                    width=dot_size,
                    height=dot_size,
                    border_radius=dot_size // 2,
                    bgcolor=ft.Colors.GREEN,
                )
            )
        if has_expense:
            indicators.append(
                ft.Container(
                    width=dot_size,
                    height=dot_size,
                    border_radius=dot_size // 2,
                    bgcolor=ft.Colors.RED,
                )
            )
        if has_planned:
            indicators.append(
                ft.Text("◆", size=icon_size, color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD)
            )
        if has_pending_payment:
            indicators.append(ft.Text("📋", size=icon_size, weight=ft.FontWeight.BOLD))
        if has_loan_payment:
            indicators.append(ft.Text("💳", size=icon_size, weight=ft.FontWeight.BOLD))

        return indicators
