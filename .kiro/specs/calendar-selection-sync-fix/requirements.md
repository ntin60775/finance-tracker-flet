# Requirements Document

## Introduction

При нажатии на карточку плановой транзакции в виджете плановых транзакций на главном экране, дата переключается в панели транзакций (правая колонка), но календарь (центральная колонка) не обновляет визуальное выделение выбранного дня. Это создаёт несоответствие между отображаемыми данными и визуальным состоянием календаря, что сбивает пользователя с толку.

## Glossary

- **Calendar_Widget**: Компонент календаря в центральной колонке главного экрана
- **Planned_Transactions_Widget**: Виджет плановых транзакций в левой колонке главного экрана
- **Transactions_Panel**: Панель транзакций в правой колонке главного экрана
- **HomeView**: Главное представление приложения, координирующее работу всех компонентов
- **HomePresenter**: Presenter, содержащий бизнес-логику главного экрана
- **Selected_Date**: Текущая выбранная дата в календаре

## Requirements

### Requirement 1: Синхронизация выделения календаря при клике на плановую транзакцию

**User Story:** Как пользователь, я хочу, чтобы при нажатии на карточку плановой транзакции календарь визуально выделял соответствующую дату, чтобы я мог видеть согласованность между всеми компонентами интерфейса.

#### Acceptance Criteria

1. WHEN пользователь кликает на карточку плановой транзакции в виджете THEN THE Calendar_Widget SHALL визуально выделить дату вхождения
2. WHEN пользователь кликает на карточку плановой транзакции THEN THE Transactions_Panel SHALL отобразить транзакции для даты вхождения
3. WHEN пользователь кликает на карточку плановой транзакции THEN THE Selected_Date SHALL обновиться на дату вхождения
4. WHEN дата вхождения находится в другом месяце THEN THE Calendar_Widget SHALL переключиться на месяц вхождения
5. WHEN календарь переключается на другой месяц THEN THE Calendar_Widget SHALL загрузить данные для нового месяца

### Requirement 2: Корректная работа метода select_date в Calendar_Widget

**User Story:** Как разработчик, я хочу, чтобы метод `select_date` в Calendar_Widget корректно обновлял визуальное выделение, чтобы синхронизация между компонентами работала надёжно.

#### Acceptance Criteria

1. WHEN вызывается метод `select_date` с датой текущего месяца THEN THE Calendar_Widget SHALL обновить выделение без перезагрузки данных
2. WHEN вызывается метод `select_date` с датой другого месяца THEN THE Calendar_Widget SHALL переключить месяц и обновить выделение
3. WHEN метод `select_date` вызывается программно THEN THE Calendar_Widget SHALL НЕ вызывать callback `on_date_selected`
4. WHEN метод `select_date` обновляет выделение THEN THE Calendar_Widget SHALL перерисовать сетку календаря

### Requirement 3: Правильная последовательность вызовов в HomePresenter

**User Story:** Как разработчик, я хочу, чтобы HomePresenter правильно координировал обновление всех компонентов, чтобы избежать рассинхронизации состояния.

#### Acceptance Criteria

1. WHEN вызывается `on_date_selected` в HomePresenter THEN THE HomePresenter SHALL обновить `selected_date`
2. WHEN HomePresenter обновляет данные транзакций THEN THE HomePresenter SHALL вызвать `update_transactions` callback
3. WHEN HomePresenter обновляет данные транзакций THEN THE HomePresenter SHALL вызвать `update_calendar_selection` callback
4. WHEN `update_calendar_selection` вызывается THEN THE HomeView SHALL делегировать вызов в Calendar_Widget через метод `select_date`
5. WHEN происходит ошибка при обновлении календаря THEN THE HomePresenter SHALL логировать предупреждение без прерывания работы

### Requirement 4: Тестирование синхронизации выделения

**User Story:** Как разработчик, я хочу иметь автоматические тесты для синхронизации выделения календаря, чтобы предотвратить регрессии в будущем.

#### Acceptance Criteria

1. THE System SHALL иметь unit тест для метода `select_date` в Calendar_Widget
2. THE System SHALL иметь unit тест для callback `update_calendar_selection` в HomeView
3. THE System SHALL иметь integration тест для полного сценария клика на плановую транзакцию
4. THE System SHALL иметь property-based тест для синхронизации выделения с любыми датами
5. WHEN тесты запускаются THEN THE System SHALL проверять, что `select_date` вызывается с правильной датой
