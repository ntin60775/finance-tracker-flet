# Decisions

## 2026-02-12 18:06
- Ограничение one-level зафиксировано на model/contracts уровне через SQLAlchemy validators и DB check constraints, без service-логики.
- Инициализация baseline/system категорий оставлена строго root-level через явный `parent_id=None` в `init_default_categories`.

## 2026-02-12 19:02
- В `update_category` выбран back-compatible режим: при вызове без `parent_id` текущий parent сохраняется, чтобы существующие call-site не "развязывали" child-категории в root.
- Удаление категории дополнительно блокируется при наличии дочерних категорий до проверок на связанные транзакции/планы/платежи.

## 2026-02-12 20:34
- Leaf-only правило закреплено на двух уровнях: UI-фильтрация в модалках + backend guard в сервисах create/update, чтобы защититься от обхода UI.
- Текст ошибки backend унифицирован как "конечные категории (без подкатегорий)" для transaction/planned/pending сервисов.
- Для проверки backend guard добавлен отдельный фокусный тестовый модуль `test_category_leaf_guards_services.py` вместо распыления по нескольким несвязанным файлам.

## 2026-02-12 22:10
- Для UX и тестируемости split UI выбран подход без табов: одновременный показ INCOME и EXPENSE секций.
- Parent selector в `CategoryDialog` намеренно показывает и root, и child элементы: second-level nesting блокируется на UI (сообщение об ошибке), а не только backend-валидацией.
- Для выбора root используется sentinel `__root__`, который при сохранении транслируется в пустую строку (нормализуется сервисом в `None`).
