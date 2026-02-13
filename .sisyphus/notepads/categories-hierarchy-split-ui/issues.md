# Issues

## 2026-02-12 18:06
- В окружении отсутствовал глобальный `pytest`; локальный запуск потребовал `.venv` и вызов через `.venv/bin/python -m pytest`.

## 2026-02-12 18:11 (retry)
- В retry сохранен файловый скоуп: изменения внесены только в `models.py`, `test_category_hierarchy_model.py` и append-only notepads.

## 2026-02-12 19:02
- LSP для SQLAlchemy ORM в `category_service.py` выдавал ложные type-ошибки на instance attributes (`CategoryDB.*`), пришлось использовать явные `cast(...)` в сервисе для стабилизации диагностики.

## 2026-02-12 20:34
- Часть существующих тестов модалки транзакций продолжала патчить старый символ `get_all_categories`; для обратной совместимости добавлен alias в `transaction_modal` на новый helper.

## 2026-02-12 21:17
- UI-тесты ожидали наличие `CategoriesView.open_create_dialog` и создание `CategoryDialog(category=None)` без обязательных параметров; потребовался совместимый shim без отката split-layout.

## 2026-02-12 22:10
- `flet.Control.update()` падает, если control не добавлен на страницу; это всплыло в unit-тесте для `CategoryDialog` и потребовало safe-update guard.
- `ft.padding.only(...)` в 0.80.x дает DeprecationWarning; в `CategoriesView` заменено на `ft.Padding.only(...)`.

## 2026-02-12 23:02
- Локальный хук отклонил новые docstring в тестах Task 5; пришлось убрать их и оставить самодокументируемые имена тестов без дополнительных комментариев.

## 2026-02-12 19:37 EET
- Сбоев в Task 7 matrix не зафиксировано; минимальные фиксы не потребовались.
- Набор `pytest tests/ -k "reject_grandchild or reject_parent_category_for_transaction or reject_non_leaf_category" -v` отработал как `1004 deselected / 0 selected` с успешным завершением (exit code 0).
