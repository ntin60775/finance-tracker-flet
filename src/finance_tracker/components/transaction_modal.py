import datetime
from typing import Optional, Callable
from decimal import Decimal, InvalidOperation
import flet as ft
from sqlalchemy.orm import Session

from finance_tracker.models import TransactionType, TransactionCreate, TransactionUpdate, TransactionDB
from finance_tracker.services.category_service import get_all_categories
from finance_tracker.utils.error_handler import safe_handler


class TransactionModal:
    """
    Модальное окно для создания и редактирования транзакции.
    
    Позволяет пользователю:
    - Выбрать тип транзакции (Доход/Расход)
    - Выбрать категорию (фильтруется по типу)
    - Ввести сумму и описание
    - Выбрать дату
    """

    def __init__(
        self,
        session: Session,
        on_save: Callable[[TransactionCreate], None],
        on_update: Optional[Callable[[str, TransactionUpdate], None]] = None,
    ):
        """
        Инициализация модального окна.

        Args:
            session: Сессия БД для загрузки категорий.
            on_save: Callback, вызываемый при создании новой транзакции.
                     Принимает объект TransactionCreate.
            on_update: Callback, вызываемый при обновлении существующей транзакции.
                      Принимает id транзакции и объект TransactionUpdate.
        """
        self.session = session
        self.on_save = on_save
        self.on_update = on_update
        self.page: Optional[ft.Page] = None
        self.current_date = datetime.date.today()
        
        # Атрибуты для режима редактирования
        self.edit_mode: bool = False
        self.editing_transaction: Optional[TransactionDB] = None
        
        # UI Controls - заменяем SegmentedButton на простые RadioButton
        self.type_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value=TransactionType.EXPENSE.value, label="Расход"),
                ft.Radio(value=TransactionType.INCOME.value, label="Доход"),
            ]),
            value=TransactionType.EXPENSE.value,
            on_change=self._on_type_change,
        )
        
        self.date_button = ft.ElevatedButton(
            text=self.current_date.strftime("%d.%m.%Y"),
            icon=ft.Icons.CALENDAR_TODAY,
            on_click=self._open_date_picker
        )
        
        self.amount_field = ft.TextField(
            label="Сумма",
            suffix_text="₽",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d{0,2}$", replacement_string=""),
            on_change=self._clear_error
        )
        
        self.category_dropdown = ft.Dropdown(
            label="Категория",
            options=[],
            on_change=self._clear_error
        )
        
        self.description_field = ft.TextField(
            label="Описание (необязательно)",
            multiline=True,
            max_lines=3
        )
        
        self.error_text = ft.Text(color=ft.Colors.ERROR, size=12)

        # Date Picker (будет добавлен в overlay страницы)
        self.date_picker = ft.DatePicker(
            on_change=self._on_date_change,
            first_date=datetime.date(2020, 1, 1),
            last_date=datetime.date(2030, 12, 31),
        )

        # Dialog - заголовок будет обновляться в зависимости от режима
        self.dialog_title = ft.Text("Новая транзакция")
        self.dialog = ft.AlertDialog(
            modal=True,
            title=self.dialog_title,
            content=ft.Column(
                controls=[
                    self.type_radio,
                    self.date_button,
                    self.amount_field,
                    self.category_dropdown,
                    self.description_field,
                    self.error_text,
                ],
                width=400,
                tight=True,
                spacing=15
            ),
            actions=[
                ft.TextButton("Отмена", on_click=self.close),
                ft.ElevatedButton("Сохранить", on_click=self._save),
            ],
        )

    def open(self, page: ft.Page, date: Optional[datetime.date] = None):
        """
        Открытие модального окна в режиме создания новой транзакции.

        Args:
            page: Ссылка на страницу Flet.
            date: Предустановленная дата (по умолчанию сегодня).
        """
        from finance_tracker.utils.logger import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.debug(f"Открытие TransactionModal в режиме создания для даты: {date}")
            
            if not page:
                raise ValueError("Page не может быть None")
                
            self.page = page
            self.current_date = date or datetime.date.today()
            
            # Устанавливаем режим создания
            self.edit_mode = False
            self.editing_transaction = None
            self.dialog_title.value = "Новая транзакция"
            
            # Сбрасываем поля формы
            self._reset_form()
            
            # Загружаем категории для типа по умолчанию
            self._load_categories(TransactionType.EXPENSE)
            
            # Открываем диалог используя overlay
            page.overlay.append(self.dialog)
            self.dialog.open = True
            page.update()
            
            logger.info("TransactionModal успешно открыт в режиме создания")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии TransactionModal: {e}", exc_info=True)
            
            # Показываем пользователю сообщение об ошибке
            if page:
                try:
                    page.open(ft.SnackBar(
                        content=ft.Text(f"Ошибка при открытии формы: {str(e)}"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def open_edit(self, page: ft.Page, transaction: TransactionDB):
        """
        Открытие модального окна в режиме редактирования существующей транзакции.

        Args:
            page: Ссылка на страницу Flet.
            transaction: Редактируемая транзакция.
        """
        from finance_tracker.utils.logger import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.debug(f"Открытие TransactionModal в режиме редактирования для транзакции: {transaction.id}")
            
            if not page:
                raise ValueError("Page не может быть None")
            if not transaction:
                raise ValueError("Transaction не может быть None")
                
            self.page = page
            self.current_date = transaction.transaction_date
            
            # Устанавливаем режим редактирования
            self.edit_mode = True
            self.editing_transaction = transaction
            self.dialog_title.value = "Редактировать транзакцию"
            
            # Предзаполняем поля данными транзакции
            self._prefill_form(transaction)
            
            # Загружаем категории для типа транзакции
            self._load_categories(transaction.type)
            
            # Открываем диалог используя overlay
            page.overlay.append(self.dialog)
            self.dialog.open = True
            page.update()
            
            logger.info("TransactionModal успешно открыт в режиме редактирования")
            
        except Exception as e:
            logger.error(f"Ошибка при открытии TransactionModal в режиме редактирования: {e}", exc_info=True)
            
            # Показываем пользователю сообщение об ошибке
            if page:
                try:
                    page.open(ft.SnackBar(
                        content=ft.Text(f"Ошибка при открытии формы редактирования: {str(e)}"),
                        bgcolor=ft.Colors.ERROR
                    ))
                except Exception as snack_error:
                    logger.error(f"Не удалось показать SnackBar: {snack_error}")

    def close(self, e=None):
        """Закрытие модального окна."""
        if self.dialog and self.page:
            self.dialog.open = False
            self.page.update()

    def _open_date_picker(self, e):
        """Открытие выбора даты."""
        self.date_picker.pick_date()

    def _on_date_change(self, e):
        """Обработка выбора даты."""
        if self.date_picker.value:
            self.current_date = self.date_picker.value.date()
            self.date_button.text = self.current_date.strftime("%d.%m.%Y")
            self.date_button.update()

    def _on_type_change(self, e):
        """Обработка смены типа транзакции."""
        if not self.type_radio.value:
            return
        
        selected_type = self.type_radio.value
        self._load_categories(TransactionType(selected_type))
        if self.page:
            self.page.update()

    def _load_categories(self, t_type: TransactionType):
        """Загрузка категорий выбранного типа."""
        from finance_tracker.utils.logger import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.debug(f"Загрузка категорий типа: {t_type}")
            
            if not self.session:
                raise ValueError("Session не инициализирована")
                
            categories = get_all_categories(self.session, t_type)
            logger.debug(f"Получено {len(categories)} категорий из сервиса")
            
            self.category_dropdown.options = [
                ft.dropdown.Option(key=str(c.id), text=c.name) for c in categories
            ]
            logger.debug(f"Создано {len(self.category_dropdown.options)} опций для dropdown")
            
            # В режиме редактирования сохраняем выбранную категорию, если она подходит по типу
            if self.edit_mode and self.editing_transaction:
                # Проверяем, что категория транзакции есть среди загруженных категорий
                category_ids = [str(c.id) for c in categories]
                if str(self.editing_transaction.category_id) in category_ids:
                    self.category_dropdown.value = str(self.editing_transaction.category_id)
                    logger.debug(f"Установлена категория из редактируемой транзакции: {self.editing_transaction.category_id}")
                else:
                    self.category_dropdown.value = None
                    logger.warning(f"Категория {self.editing_transaction.category_id} не найдена среди категорий типа {t_type}")
            else:
                # В режиме создания сбрасываем выбор
                self.category_dropdown.value = None
            
            self.category_dropdown.error_text = None
            
            logger.debug("Категории успешно загружены в dropdown")
                
        except Exception as e:
            error_msg = f"Ошибка загрузки категорий: {e}"
            self.error_text.value = error_msg
            
            logger.error(f"Ошибка при загрузке категорий в TransactionModal: {e}", exc_info=True)
            
            # Не обновляем page здесь, чтобы не мешать основному процессу открытия

    def _reset_form(self):
        """Сброс полей формы к значениям по умолчанию."""
        self.date_button.text = self.current_date.strftime("%d.%m.%Y")
        self.amount_field.value = ""
        self.amount_field.error_text = None
        self.description_field.value = ""
        self.error_text.value = ""
        self.type_radio.value = TransactionType.EXPENSE.value
        self.category_dropdown.value = None
        self.category_dropdown.error_text = None

    def _prefill_form(self, transaction: TransactionDB):
        """
        Предзаполнение полей формы данными транзакции.
        
        Args:
            transaction: Транзакция для редактирования.
        """
        from finance_tracker.utils.logger import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.debug(f"Предзаполнение формы данными транзакции: {transaction.id}")
            
            # Устанавливаем дату
            self.date_button.text = transaction.transaction_date.strftime("%d.%m.%Y")
            
            # Устанавливаем сумму
            self.amount_field.value = str(transaction.amount)
            self.amount_field.error_text = None
            
            # Устанавливаем описание
            self.description_field.value = transaction.description or ""
            
            # Устанавливаем тип транзакции
            self.type_radio.value = transaction.type.value
            
            # Устанавливаем категорию (будет установлена после загрузки категорий)
            self.category_dropdown.value = str(transaction.category_id)
            self.category_dropdown.error_text = None
            
            # Сбрасываем ошибки
            self.error_text.value = ""
            
            logger.debug("Форма успешно предзаполнена")
            
        except Exception as e:
            logger.error(f"Ошибка при предзаполнении формы: {e}", exc_info=True)
            self.error_text.value = f"Ошибка при загрузке данных транзакции: {str(e)}"

    def _clear_error(self, e):
        """Сброс ошибок при вводе."""
        if isinstance(e.control, ft.TextField):
            e.control.error_text = None
        elif isinstance(e.control, ft.Dropdown):
            e.control.error_text = None
        self.page.update()

    @safe_handler()
    def _save(self, e):
        """Валидация и сохранение транзакции."""
        from finance_tracker.utils.logger import get_logger
        logger = get_logger(__name__)
        
        try:
            logger.debug(f"Сохранение транзакции в режиме: {'редактирование' if self.edit_mode else 'создание'}")
            
            errors = False
            amount = Decimal('0')
            
            # Валидация суммы
            try:
                amount = Decimal(self.amount_field.value or "0")
                if amount <= Decimal('0'):
                    self.amount_field.error_text = "Сумма должна быть больше 0"
                    errors = True
            except (InvalidOperation, TypeError, ValueError):
                self.amount_field.error_text = "Введите корректное число"
                errors = True
                
            # Валидация категории
            if not self.category_dropdown.value:
                self.category_dropdown.error_text = "Выберите категорию"
                errors = True
                
            if errors:
                logger.debug("Обнаружены ошибки валидации")
                if self.page:
                    self.page.update()
                return

            selected_type = self.type_radio.value
            
            if self.edit_mode:
                # Режим редактирования - создаем TransactionUpdate
                if not self.editing_transaction:
                    raise ValueError("editing_transaction не установлена в режиме редактирования")
                if not self.on_update:
                    raise ValueError("on_update callback не установлен для режима редактирования")
                
                transaction_update = TransactionUpdate(
                    amount=amount,
                    type=TransactionType(selected_type),
                    category_id=self.category_dropdown.value,
                    description=self.description_field.value or "",
                    transaction_date=self.current_date
                )
                
                logger.debug(f"Создан объект TransactionUpdate для транзакции {self.editing_transaction.id}")
                
                # Закрываем диалог ПЕРЕД вызовом callback
                self.close()
                
                # Вызываем callback для обновления
                self.on_update(self.editing_transaction.id, transaction_update)
                
            else:
                # Режим создания - создаем TransactionCreate
                if not self.on_save:
                    raise ValueError("on_save callback не установлен для режима создания")
                
                transaction_data = TransactionCreate(
                    amount=amount,
                    type=TransactionType(selected_type),
                    category_id=self.category_dropdown.value,
                    description=self.description_field.value or "",
                    transaction_date=self.current_date
                )
                
                logger.debug("Создан объект TransactionCreate")
                
                # Закрываем диалог ПЕРЕД вызовом callback
                self.close()
                
                # Вызываем callback для создания
                self.on_save(transaction_data)
                
            logger.info(f"Транзакция успешно {'обновлена' if self.edit_mode else 'создана'}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении транзакции: {e}", exc_info=True)
            self.error_text.value = f"Ошибка при сохранении: {str(e)}"
            if self.page:
                self.page.update()
            # Поднимаем исключение дальше для тестов
            raise
