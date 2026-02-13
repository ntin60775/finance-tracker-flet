# Learnings

## 2026-02-12 18:06
- CategoryDB получил self-reference `parent_id` + `parent/children` relationship для иерархии категорий.
- Контракты `Category` и `CategoryCreate` теперь валидируют `parent_id` как UUID и запрещают parent для INCOME.
- Для системных категорий добавлено правило root-only: `parent_id=None`.

## 2026-02-12 18:11 (retry)
- Ужесточена нормализация типа категории при `parent`-валидации: INCOME-родитель теперь стабильно отклоняется даже при строковом представлении enum.
- Добавлен отдельный тест на запрет `EXPENSE` дочерней категории с `INCOME` родителем через assignment `parent=...`.

## 2026-02-12 19:02
- В `category_service` добавлены сервисные проверки иерархии для `create_category`/`update_category`: существование parent, тип parent=`EXPENSE`, parent только root, запрет self/cycle, запрет child для `INCOME`.
- Добавлен guard на "used parent": нельзя создавать/назначать дочернюю категорию под parent, который уже используется в `transactions`, `planned_transactions` или `pending_payments`.
- Добавлены helper-операции сервиса: `get_expense_tree` и `get_selectable_leaf_categories`.

## 2026-02-12 20:34
- Модалки `transaction/planned/pending` переключены на `get_selectable_leaf_categories`, поэтому для EXPENSE в dropdown остаются только leaf-категории, а для INCOME сохраняется полный валидный набор.
- Для отображения дочерних категорий в модалках используется формат `Parent / Child` через проверку связки `category.parent`.
- В сервисах `transaction/planned/pending` добавлен единый leaf-guard для EXPENSE: create/update отклоняют parent-категории с `ValueError` и текстом про "конечные категории".

## 2026-02-12 22:10
- `CategoriesView` переделан на split layout без табов: слева отдельный список INCOME, справа дерево EXPENSE (root + children) через `get_expense_tree`.
- Для визуального группирования children используется отступ (wrapper padding) и чуть более легкий стиль заголовка.
- `CategoryDialog` поддерживает выбор родителя для EXPENSE: dropdown включает root и child (label `Parent / Child`) и блокирует попытку создать подкатегорию второго уровня.
- Для unit-тестов добавлен guard на обновление UI: диалог не вызывает `update()` без привязки к `page`.

## 2026-02-12 16:51 UTC
- Перед продолжением задач выполнено refresh метаданных boulder: в `.sisyphus/boulder.json` обновлено только поле `started_at`.

## 2026-02-12 21:17
- Для обратной совместимости UI-тестов добавлен legacy-create режим `CategoryDialog` (создание без `create_mode`) и shim `CategoriesView.open_create_dialog`.
- Split-flow остается основным: явные кнопки создают income / expense root / expense child через `create_mode`.

## 2026-02-12 23:02
- Для Task 5 вынесен общий helper для фильтров категорий: построение label/path (`Parent / Child`) и маппинга aggregate `parent -> {parent + children}` переиспользуется в history и plan-fact.
- В `PlanFactView` parent-aggregate сделан через один сервисный запрос без category-id + локальная фильтрация/пересчет summary по `occurrences[*].category_id`, что сохраняет UUID-safe поток без `int(...)`.

## 2026-02-12 23:47
- В snapshot-экспорте категорий добавлен детерминированный topological parent-first порядок: родители всегда сериализуются раньше дочерних категорий.
- В snapshot-импорте категорий добавлена двухфазная вставка (сначала `parent_id=None`, затем связывание parent), что убирает риск FK-гонок при child-before-parent payload.
- Для импорта добавлена явная валидация `parent_id`: fail-fast на неразрешимые ссылки и циклы до очистки данных, с rollback по стандартному потоку ошибок.

## 2026-02-12 19:37 EET
- Финальный regression Task 7 полностью зеленый: `ruff` + все 5 целевых `pytest` команд прошли без падений.
- Guardrails подтверждены: deprecated Flet dialog API не используется в коде (`page.dialog = ...`, `.open = True/False` отсутствуют как AST-assign; grep-совпадения были только в поясняющих строках).
- Инварианты иерархии сохранены: one-level only и leaf-only подтверждены тестами (`test_category_dialog_prevents_second_level_nesting`, leaf checks в transaction/planned/pending suite) и сервисными проверками (`_validate_parent_constraints`, `_ensure_leaf_expense_category`).
- Split-layout categories без tabs сохранен: `CategoriesView` использует `ft.Row` с `income_section`/`expense_section`, без `Tabs/Tab`.
- 2026-02-13: Финальная доставка выполнена — все текущие изменения закоммичены одним коммитом и отправлены в origin/master.
- 2026-02-13: Попытка push выполнена, но отправка в GitHub заблокирована: отсутствуют учетные данные в текущем окружении (terminal prompts disabled).
