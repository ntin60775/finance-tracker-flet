# Многострочная легенда под календарем

## TL;DR

> **Quick Summary**: Перевести полную легенду календаря на многострочный вывод (адаптивный перенос), убрать разделители между группами и сохранить текущий compact-режим с кнопкой `Подробнее...` без изменений.
>
> **Deliverables**:
> - Обновленный рендер полной легенды в `CalendarLegend` (multiline-capable)
> - Обновленные/новые pytest-кейсы для full-mode и регрессий compact-mode
> - Подтверждение через таргетные тестовые команды с артефактами в `.sisyphus/evidence/`
>
> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential
> **Critical Path**: Task 1 -> Task 2 -> Task 3

---

## Context

### Original Request
Сделать вывод легенды под календарем в несколько строк вместо одной строки с разделителем.

### Interview Summary
**Key Discussions**:
- Формат подтвержден: адаптивный многострочный вывод полной легенды.
- Разделители между визуальными группами в полной легенде нужно убрать.
- Compact-режим (узкая ширина, кнопка `Подробнее...`) оставляем без изменений.
- Стратегия тестов: `Tests-after` на существующей инфраструктуре `pytest`.

**Research Findings**:
- Полная легенда сейчас строится в `src/finance_tracker/components/calendar_legend.py::_build_full_legend` и рендерится как `ft.Row(..., wrap=False)`.
- Разделители добавляются в `src/finance_tracker/components/calendar_legend.py::_create_group_separator`.
- Интеграция с HomeView: легенда уже находится под календарем в `src/finance_tracker/views/home_view.py`.
- Тестовое покрытие по легенде уже есть в `tests/test_calendar_legend_ui.py`, `tests/test_calendar_legend_integration.py`, `tests/test_calendar_legend_error_handling.py`.

### Metis Review
**Identified Gaps (addressed)**:
- Gap: при текущем критерии full-mode перенос может проявляться редко на очень широких экранах.
  - Resolution: фиксируем изменение на уровне структуры full-mode (`wrap=True`, `run_spacing`, без разделителей), а регрессию compact-mode покрываем тестами.
- Gap: риск хрупких проверок "разделитель отсутствует".
  - Resolution: тесты должны искать разделитель по конкретному профилю (`width=1`, `height=16`, `bgcolor=OUTLINE_VARIANT`), а не по типу `Container`.
- Gap: риск случайной поломки compact-mode.
  - Resolution: добавить отдельные регрессионные тесты на наличие кнопки `Подробнее...` и сценарии `update_calendar_width()`.

---

## Work Objectives

### Core Objective
Изменить визуальный рендер полной легенды календаря на многострочный формат без разделителей, не меняя поведение compact-режима и модального окна.

### Concrete Deliverables
- Изменения в `src/finance_tracker/components/calendar_legend.py` в зоне full-mode рендера.
- Тесты для проверки `wrap`-поведения full-mode и отсутствия разделителей.
- Регрессионные тесты, подтверждающие неизменность compact-mode.

### Definition of Done
- [x] Полная легенда строится с переносом строк (`wrap=True`) и без group separators.
- [x] Compact-режим по-прежнему показывает кнопку `Подробнее...` в последнем контроле.
- [x] Таргетные тесты проходят: `test_calendar_legend_ui.py`, `test_calendar_legend_integration.py`, `test_calendar_legend_error_handling.py`.

### Must Have
- Многострочная (multiline-capable) полная легенда.
- Отсутствие горизонтальных/вертикальных разделителей групп в full-mode.
- Обратная совместимость существующих сценариев с модальным окном и compact-mode.

### Must NOT Have (Guardrails)
- Не менять бизнес-логику календаря, индикаторов, транзакций.
- Не менять API/контракты `ModalManager`, `PageAccessManager`, `WidthCalculator`.
- Не внедрять deprecated Flet API (`page.dialog = ...`, `dialog.open = ...`).
- Не раздувать scope до рефакторинга всего компонента.
- Не менять порог/критерий переключения full/compact режима (default decision для этого плана).

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> Все проверки выполняет агент: только команды/инструменты. Ручная визуальная проверка пользователем не используется.

### Test Decision
- **Infrastructure exists**: YES (`pytest`, `hypothesis`, UI/integration tests уже есть)
- **Automated tests**: Tests-after
- **Framework**: pytest

### Agent-Executed QA Scenarios (MANDATORY - ALL tasks)

Каждая задача ниже содержит детализированные сценарии с командами и артефактами:
- UI-структура full-mode проверяется через unit/UI pytest.
- Негативный/регрессионный сценарий: compact-mode и width-switch поведение.
- Артефакты: текстовые логи команд в `.sisyphus/evidence/`.

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1 (Start Immediately):
└── Task 1: Обновить full-mode layout на multiline + убрать separators

Wave 2 (After Wave 1):
└── Task 2: Обновить/добавить тесты на новый full-mode и регрессии compact-mode

Wave 3 (After Wave 2):
└── Task 3: Прогон верификации, сбор evidence, фиксация результата

Critical Path: Task 1 -> Task 2 -> Task 3
Parallel Speedup: не применимо (последовательная зависимость)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 2, 3 | None |
| 2 | 1 | 3 | None |
| 3 | 2 | None | None |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|--------------------|
| 1 | 1 | `task(category="quick", load_skills=["frontend-ui-ux"], run_in_background=false)` |
| 2 | 2 | `task(category="quick", load_skills=["frontend-ui-ux"], run_in_background=false)` |
| 3 | 3 | `task(category="quick", load_skills=["git-master"], run_in_background=false)` |

---

## TODOs

- [x] 1. Перевести full-mode легенды на multiline и убрать разделители

  **What to do**:
  - Изменить `src/finance_tracker/components/calendar_legend.py::_build_full_legend` так, чтобы full-mode рендерился как многострочный (`ft.Row` с `wrap=True` и `run_spacing`).
  - Убрать вставку разделителей `_create_group_separator()` из full-mode controls.
  - Сохранить текущую визуальную группировку/порядок индикаторов и выравнивание по центру.
  - Не менять compact-mode (`_build_compact_legend`) и кнопку `Подробнее...`.
  - Оставить безопасное fallback-поведение без деградации error-handling.

  **Must NOT do**:
  - Не менять логику выбора full/compact в `_should_show_full_legend` без явной необходимости.
  - Не менять `ModalManager`, `PageAccessManager`, `WidthCalculator`.
  - Не изменять конфигурации `INDICATOR_CONFIGS`.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: локальное изменение одного UI-компонента без архитектурных миграций.
  - **Skills**: `frontend-ui-ux`
    - `frontend-ui-ux`: нужен для аккуратного layout-решения и сохранения UX-поведения.
  - **Skills Evaluated but Omitted**:
    - `playwright`: Flet desktop UI здесь проверяется существующими pytest UI-тестами, браузерный E2E не обязателен.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 1)
  - **Blocks**: 2, 3
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `src/finance_tracker/components/calendar_legend.py::_build_full_legend` - основная точка изменения full-mode рендера.
  - `src/finance_tracker/components/calendar_legend.py::_group_indicators_visually` - существующий порядок/группировка индикаторов, который важно не сломать.
  - `src/finance_tracker/components/calendar_legend.py::_build_compact_legend` - эталон поведения compact-mode, который нельзя затронуть.

  **API/Type References**:
  - `src/finance_tracker/components/calendar_legend_types.py::LegendIndicator` - контракт индикатора (visual element + label + priority).
  - `src/finance_tracker/components/calendar_legend_types.py::INDICATOR_CONFIGS` - источник набора индикаторов и приоритетов.

  **Test References**:
  - `tests/test_calendar_legend_ui.py::TestCalendarLegendUI::test_ui_component_structure` - текущие ожидания по структуре Row.
  - `tests/test_calendar_legend_ui.py::TestCalendarLegendUI::test_details_button_visibility_based_on_width` - guardrail для compact-mode.
  - `tests/test_calendar_legend_error_handling.py::test_separator_creation_stability` - обратная совместимость метода создания separator.

  **Documentation References**:
  - `AGENTS.md` - правило про modern Flet dialog API и тестовые конвенции.
  - `README.md` (раздел тестов) - рекомендуемые команды pytest для локальной валидации.

  **External References**:
  - Official docs: `https://flet.dev/docs/controls/row` - свойства `wrap`, `spacing`, `run_spacing` для многострочного layout.

  **Acceptance Criteria**:
  - [x] В full-mode возвращается `ft.Row` с включенным переносом (`wrap=True`).
  - [x] В full-mode не добавляются group separators (`width=1`, `height=16`, `bgcolor=OUTLINE_VARIANT`).
  - [x] Compact-mode код и кнопка `Подробнее...` не изменены по контракту.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Full-mode structure supports multiline wrapping
    Tool: Bash (pytest)
    Preconditions: dev dependencies installed, pytest available
    Steps:
      1. Update/add test case in tests/test_calendar_legend_ui.py for full-mode wrap behavior
      2. Run: pytest tests/test_calendar_legend_ui.py -k "full_legend and wrap" -v > .sisyphus/evidence/task-1-full-wrap.txt 2>&1
      3. Assert: exit code 0
      4. Assert: test verifies full_legend.wrap is True
    Expected Result: Full-mode explicitly supports multiline wrapping
    Failure Indicators: pytest non-zero exit or missing wrap assertion
    Evidence: .sisyphus/evidence/task-1-full-wrap.txt

  Scenario: Compact-mode remains unchanged (regression guard)
    Tool: Bash (pytest)
    Preconditions: Task 1 changes applied
    Steps:
      1. Run: pytest tests/test_calendar_legend_ui.py -k "details_button_visibility_based_on_width" -v > .sisyphus/evidence/task-1-compact-regression.txt 2>&1
      2. Assert: exit code 0
      3. Assert: compact legend still includes TextButton with text "Подробнее..."
    Expected Result: Compact behavior preserved
    Failure Indicators: details button missing or assertion failure
    Evidence: .sisyphus/evidence/task-1-compact-regression.txt
  ```

  **Commit**: NO

- [x] 2. Обновить тесты на отсутствие разделителей и стабильность при изменении ширины

  **What to do**:
  - Добавить/обновить тесты в `tests/test_calendar_legend_ui.py` для проверки отсутствия separator-элементов в full-mode.
  - Добавить регрессионный тест на `update_calendar_width()` для переходов между режимами без потери текущего контракта compact-mode.
  - При необходимости уточнить тесты в `tests/test_calendar_legend_integration.py` так, чтобы они не зависели от устаревшего предположения про single-line full-mode.
  - Сохранить устойчивость error-handling тестов (`tests/test_calendar_legend_error_handling.py`).

  **Must NOT do**:
  - Не удалять существующие property/integration тесты легенды.
  - Не ослаблять проверки до формального "тест проходит" без проверки бизнес-требования.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: целевые правки нескольких тест-кейсов вокруг одного компонента.
  - **Skills**: `frontend-ui-ux`
    - `frontend-ui-ux`: помогает корректно формализовать UI-contract assertions.
  - **Skills Evaluated but Omitted**:
    - `playwright`: покрытие делается существующими unit/integration pytest тестами Flet-компонентов.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: 3
  - **Blocked By**: 1

  **References**:

  **Pattern References**:
  - `tests/test_calendar_legend_ui.py::TestCalendarLegendUI` - основной шаблон UI-тестов для этого компонента.
  - `tests/test_calendar_legend_integration.py::TestCalendarLegendIntegration::test_property_13_responsive_stability` - шаблон проверки стабильности при ресайзе.
  - `tests/test_calendar_legend_error_handling.py::test_separator_creation_stability` - показывает допустимость сохранения метода separator для обратной совместимости.

  **API/Type References**:
  - `src/finance_tracker/components/calendar_legend.py::update_calendar_width` - контракт перестройки режима при изменении ширины.
  - `src/finance_tracker/components/calendar_legend.py::_rebuild_ui` - точка обновления content после смены режима.

  **Documentation References**:
  - `AGENTS.md` - требование добавлять/обновлять UI-тесты вместе с UI-изменениями.
  - `.kiro/steering/ui-testing.md` - конвенции по структуре UI-тестов.

  **Acceptance Criteria**:
  - [x] Есть тест, который доказывает отсутствие separators в full-mode по конкретным признакам элемента.
  - [x] Есть тест, подтверждающий, что compact-mode все еще содержит кнопку `Подробнее...`.
  - [x] Есть тест на `update_calendar_width()` с проверкой стабильности переходов режима после изменения layout full-mode.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Full-mode has no legacy separators
    Tool: Bash (pytest)
    Preconditions: Test case for separator absence added
    Steps:
      1. Run: pytest tests/test_calendar_legend_ui.py -k "separator and full_legend" -v > .sisyphus/evidence/task-2-no-separators.txt 2>&1
      2. Assert: exit code 0
      3. Assert: test checks no control with width=1,height=16,bgcolor=OUTLINE_VARIANT in full-mode
    Expected Result: Full-mode contains no group separators
    Failure Indicators: any matched separator-like control in full-mode
    Evidence: .sisyphus/evidence/task-2-no-separators.txt

  Scenario: Width-change regression is stable
    Tool: Bash (pytest)
    Preconditions: update_calendar_width regression test added/updated
    Steps:
      1. Run: pytest tests/test_calendar_legend_integration.py -k "responsive_stability or width" -v > .sisyphus/evidence/task-2-width-regression.txt 2>&1
      2. Assert: exit code 0
      3. Assert: compact-mode path still passes with details button checks
    Expected Result: No regressions in mode switching
    Failure Indicators: mode switch assertion failures, missing details button
    Evidence: .sisyphus/evidence/task-2-width-regression.txt
  ```

  **Commit**: NO

- [x] 3. Выполнить итоговую верификацию и подготовить коммит

  **What to do**:
  - Прогнать целевой набор тестов по легенде/интеграции/устойчивости.
  - Зафиксировать артефакты команд в `.sisyphus/evidence/`.
  - Проверить отсутствие побочных изменений вне целевых файлов.
  - Подготовить один тематический коммит.

  **Must NOT do**:
  - Не запускать нерелевантный тяжелый прогон всей кодовой базы без необходимости.
  - Не включать в коммит несвязанные файлы.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: финальная проверка и аккуратная фиксация небольшого scope.
  - **Skills**: `git-master`
    - `git-master`: нужен для чистой фиксации изменений и проверки состава коммита.
  - **Skills Evaluated but Omitted**:
    - `playwright`: не обязателен для текущего уровня проверки (pytest покрывает требование).

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 3)
  - **Blocks**: None
  - **Blocked By**: 2

  **References**:
  - `tests/test_calendar_legend_ui.py`
  - `tests/test_calendar_legend_integration.py`
  - `tests/test_calendar_legend_error_handling.py`
  - `src/finance_tracker/components/calendar_legend.py`

  **Acceptance Criteria**:
  - [x] `pytest tests/test_calendar_legend_ui.py -v` завершился успешно.
  - [x] `pytest tests/test_calendar_legend_integration.py -v` завершился успешно.
  - [x] `pytest tests/test_calendar_legend_error_handling.py -v` завершился успешно.
  - [x] `python -m compileall src/finance_tracker/components/calendar_legend.py` завершился без ошибок.
  - [x] Подготовлен 1 коммит с тематическим сообщением.

  **Agent-Executed QA Scenarios**:

  ```bash
  Scenario: Targeted legend validation suite passes
    Tool: Bash
    Preconditions: Tasks 1-2 completed
    Steps:
      1. Run: pytest tests/test_calendar_legend_ui.py tests/test_calendar_legend_integration.py tests/test_calendar_legend_error_handling.py -v > .sisyphus/evidence/task-3-targeted-suite.txt 2>&1
      2. Assert: exit code 0
      3. Run: python -m compileall src/finance_tracker/components/calendar_legend.py > .sisyphus/evidence/task-3-compileall.txt 2>&1
      4. Assert: exit code 0
    Expected Result: Изменение стабильно по UI/integration/error и синтаксически корректно
    Failure Indicators: любой non-zero exit code
    Evidence: .sisyphus/evidence/task-3-targeted-suite.txt, .sisyphus/evidence/task-3-compileall.txt

  Scenario: Negative regression guard (compact behavior)
    Tool: Bash
    Preconditions: Targeted suite available
    Steps:
      1. Run: pytest tests/test_calendar_legend_ui.py -k "details_button_visibility_based_on_width" -v > .sisyphus/evidence/task-3-compact-guard.txt 2>&1
      2. Assert: exit code 0
      3. Assert: compact mode still exposes 'Подробнее...' button expectation
    Expected Result: Compact mode contract unchanged
    Failure Indicators: missing button assertion or failed test
    Evidence: .sisyphus/evidence/task-3-compact-guard.txt
  ```

  **Commit**: YES
  - Message: `feat(calendar-legend): render full legend as multiline without separators`
  - Files:
    - `src/finance_tracker/components/calendar_legend.py`
    - `tests/test_calendar_legend_ui.py`
    - `tests/test_calendar_legend_integration.py` (если потребуется)
    - `tests/test_calendar_legend_error_handling.py` (только если потребуется корректировка)
  - Pre-commit: `pytest tests/test_calendar_legend_ui.py tests/test_calendar_legend_integration.py tests/test_calendar_legend_error_handling.py -v`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 3 | `feat(calendar-legend): render full legend as multiline without separators` | `src/finance_tracker/components/calendar_legend.py`, legend-related tests | `pytest tests/test_calendar_legend_ui.py tests/test_calendar_legend_integration.py tests/test_calendar_legend_error_handling.py -v` |

---

## Success Criteria

### Verification Commands
```bash
pytest tests/test_calendar_legend_ui.py -v
pytest tests/test_calendar_legend_integration.py -v
pytest tests/test_calendar_legend_error_handling.py -v
python -m compileall src/finance_tracker/components/calendar_legend.py
```

### Final Checklist
- [x] Full-mode легенды многострочный (структурно подтвержден через `wrap=True`).
- [x] Разделители групп в full-mode отсутствуют.
- [x] Compact-mode и кнопка `Подробнее...` не сломаны.
- [x] Таргетные тесты проходят без ручной проверки.
- [x] Изменения ограничены заявленным scope.
