# Learnings

## Analysis: Full-Mode Multiline Migration (2026-02-12)

### Source File Structure Map
**File:** `src/finance_tracker/components/calendar_legend.py`

#### Control Tree - Full Mode (Current Implementation)
```
CalendarLegend (ft.Container)
  └─ content: ft.Row (from _build_full_legend, line 319)
      ├─ LegendItem (ft.Row) - Group: dots
      │   ├─ ft.Container (dot visual)
      │   └─ ft.Text (label)
      ├─ LegendItem (ft.Row) - Group: dots
      │   ├─ ft.Container (dot visual)
      │   └─ ft.Text (label)
      ├─ SEPARATOR (ft.Container) - Line 349 insertion point
      │   ├─ width=1, height=16
      │   ├─ bgcolor=ft.Colors.OUTLINE_VARIANT
      │   └─ margin=ft.Margin.symmetric(horizontal=5)
      ├─ LegendItem (ft.Row) - Group: symbols
      │   ├─ ft.Text (symbol visual)
      │   └─ ft.Text (label)
      ├─ LegendItem (ft.Row) - Group: symbols
      │   ├─ ft.Text (symbol visual)
      │   └─ ft.Text (label)
      ├─ SEPARATOR (ft.Container) - Line 349 insertion point
      ├─ LegendItem (ft.Row) - Group: backgrounds
      │   ├─ ft.Container (background visual)
      │   └─ ft.Text (label)
      └─ LegendItem (ft.Row) - Group: backgrounds
          ├─ ft.Container (background visual)
          └─ ft.Text (label)
```

#### Control Tree - Compact Mode (Unchanged)
```
CalendarLegend (ft.Container)
  └─ content: ft.Row (from _build_compact_legend, line 364)
      ├─ LegendItem (ft.Row) - Priority 1-3
      ├─ LegendItem (ft.Row) - Priority 1-3
      ├─ LegendItem (ft.Row) - Priority 1-3
      └─ ft.TextButton ("Подробнее...")
```

### Key Functions Reference

#### Separator Creation (REMOVAL TARGET)
- **Location:** Lines 461-473
- **Function:** `_create_group_separator(self) -> ft.Container`
- **Implementation:**
  ```python
  return ft.Container(
      width=1,
      height=16,
      bgcolor=ft.Colors.OUTLINE_VARIANT,
      margin=ft.Margin.symmetric(horizontal=5)
  )
  ```

#### Separator Insertion Points (REMOVAL TARGETS)
- **Location:** Lines 348-350 in `_build_full_legend()`
- **Code:**
  ```python
  # Добавляем визуальный разделитель между группами (кроме последней)
  if group_name != list(grouped_indicators.keys())[-1] and len(indicators) > 0:
      separator = self._create_group_separator()
      controls.append(separator)
  ```

#### Grouping Logic (PRESERVE - drives layout)
- **Location:** Lines 411-459
- **Function:** `_group_indicators_visually()`
- **Groups:** "dots" (income/expense), "symbols" (planned/pending/loans), "backgrounds" (gaps/overdue)

### Multiline Implementation Strategy

#### Option A: Wrap Within Single Row (Minimal Change)
```python
# In _build_full_legend():
return ft.Row(
    controls=controls,
    alignment=ft.MainAxisAlignment.CENTER,
    spacing=20,
    vertical_alignment=ft.CrossAxisAlignment.CENTER,
    wrap=True  # <-- CHANGE: False -> True
)
```

#### Option B: Column with Grouped Rows (Structured Multiline)
```python
# New approach - groups become separate rows:
return ft.Column([
    ft.Row(dots_group, alignment=ft.MainAxisAlignment.CENTER),
    ft.Row(symbols_group, alignment=ft.MainAxisAlignment.CENTER),
    ft.Row(backgrounds_group, alignment=ft.MainAxisAlignment.CENTER),
], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
```

#### Option C: Responsive Grid (Most Flexible)
```python
# Use Wrap with RunAlignment for natural flow
return ft.Wrap(
    controls=controls_without_separators,  # No separators
    alignment=ft.WrapAlignment.CENTER,
    run_alignment=ft.WrapAlignment.CENTER,
    spacing=20,
    run_spacing=10,
)
```

### Test Impact Analysis

#### Tests That Verify Separator Existence (WILL FAIL)
1. **test_calendar_legend_error_handling.py:356-365**
   - `test_separator_creation_stability()`
   - Directly tests `_create_group_separator()` returns ft.Container with width=1
   - **Failure:** Method may be removed or return None

#### Tests That Verify Control Count (MAY FAIL)
1. **test_calendar_legend_ui.py:324-341**
   - `test_ui_component_structure()` checks `len(full_legend.controls)` implicitly via structure
   - **Failure:** Control count changes when separators removed

2. **test_calendar_legend_integration.py:293-303, 359-369**
   - Checks `len(full_content.controls) > 0`
   - **Status:** Should pass (indicators remain), but count assertions may need update

#### Tests That Iterate Controls (LIKELY PASS)
1. **test_calendar_legend_ui.py:109-114**
   - `test_details_button_visibility_based_on_width()` iterates controls looking for button text
   - **Status:** Pass - doesn't depend on separator count

### Width Calculation Considerations
- **Current:** `_calculate_required_width()` (line 111) includes separator widths
- **After Change:** May need adjustment if separators removed
- **Location:** WidthCalculator usage in lines 126-162

### Modal Window (UNAFFECTED)
- `ModalManager.create_modal()` builds separate structure
- No separator usage in modal
- Tested in: test_calendar_legend_ui.py:116-158

## Research: Flet Row multiline layout for calendar legend

### Official Documentation
**Source**: https://docs.flet.dev/controls/row/

#### Key Properties for Multiline Layout

1. **`wrap` (bool)** - Enables multiline behavior
   - Default: `False` (single-line row)
   - Set `wrap=True` to allow child controls to flow into additional rows when they don't fit
   - **Critical**: Without this, Row remains single-line regardless of available space

2. **`spacing` (Number)** - Spacing between child controls
   - Default: `10`
   - Applies to both horizontal and vertical gaps when wrap is enabled

3. **`run_spacing` (Number)** - Spacing between runs (rows)
   - Default: `10`
   - **Only effective when `wrap=True`**
   - Controls vertical gap between wrapped rows

4. **`run_alignment` (MainAxisAlignment)** - How wrapped rows are aligned vertically
   - Options: `START`, `CENTER`, `END`, `SPACE_BETWEEN`, `SPACE_AROUND`, `SPACE_EVENLY`
   - Default: `START`

5. **`alignment` (MainAxisAlignment)** - Horizontal alignment within each row
   - Same options as run_alignment
   - Default: `START`

6. **`vertical_alignment` (CrossAxisAlignment)** - Vertical alignment of controls within each row
   - Options: `START`, `CENTER`, `END`
   - Default: `START`

### Official Example: Wrapping Children
**Source**: https://docs.flet.dev/controls/row/#wrapping-children

```python
row = ft.Row(
    wrap=True,
    spacing=10,
    run_spacing=10,
    controls=generate_items(30),
    width=page.window.width,
)
```

**Key insight**: To trigger wrapping, Row needs either:
- Explicit `width` constraint, OR
- Parent container with constrained width

### Chip Control for Icon+Label Pattern
**Source**: https://docs.flet.dev/controls/chip/

Chips are perfect for legend items with icon+label:
```python
ft.Chip(
    label="Category Name",
    leading=ft.Icon(ft.Icons.CIRCLE, color=color),
    bgcolor=ft.Colors.TRANSPARENT,  # For clean legend look
    padding=ft.padding.symmetric(horizontal=8, vertical=4),
)
```

**Relevant Chip properties**:
- `leading`: Icon/avatar on the left (perfect for colored indicator)
- `label`: Primary text
- `bgcolor`: Background color (use transparent for minimal look)
- `padding`: Internal padding
- `on_click`: Optional interactivity

### Real-World Pattern from GitHub
**Source**: https://github.com/LineIndent/flet_projects/blob/main/responsive-form-ft/form/main.py

```python
self.tags = ft.Row(self.render_tags(), wrap=True)
```

Simple and effective - just pass `wrap=True` to existing Row.

### Do/Don't Recommendations for This Codebase

#### ✅ DO
1. **Use `wrap=True` explicitly** - This is the primary toggle for multiline behavior
2. **Set both `spacing` and `run_spacing`** - For consistent gaps horizontally and vertically
3. **Consider Chip controls** - Clean built-in icon+label pattern with proper padding
4. **Test with varying legend item counts** - Ensure wrapping works with 2-20+ items
5. **Use `alignment=ft.MainAxisAlignment.START`** - Natural left-to-right reading flow

#### ❌ DON'T
1. **Don't rely on default wrap=False** - Explicit is better for clarity
2. **Don't mix scroll and wrap** - `scroll` mode conflicts with wrapping behavior
3. **Don't forget width constraints** - Row needs bounded width to trigger wrapping
4. **Don't use deprecated `ft.Divider` between legend items** - Use spacing properties instead

### Testing Implications

When switching from single-line to multiline:
- Assertions checking `row.controls` length remain valid
- Assertions checking exact positioning may need adjustment
- Mock `page.update()` calls should still capture control updates
- Consider adding tests for:
  - Row.wrap property value
  - Spacing values (spacing, run_spacing)
  - Number of visible rows at different widths

### Compatibility Notes

- Flet version: All properties available in flet~=0.80.x
- No additional dependencies required
- Works across desktop and web platforms
- Responsive behavior automatic with parent width changes

---
*Research completed: 2026-02-12*
*Task: Calendar legend multiline layout preparation*

## Implementation: Full-mode multiline update (2026-02-12)
- В `_build_full_legend()` сохранена исходная группировка через `_group_indicators_visually()`, но в `controls` добавляются только элементы индикаторов по группам без вставки разделителей.
- Для full-mode `ft.Row` включен перенос: `wrap=True`, добавлен `run_spacing=20` в согласовании с текущим `spacing=20`.
- Compact-mode (`_build_compact_legend`) и кнопка `Подробнее...` не изменялись.

## Retry: diff cleanliness restored (2026-02-12)
- `calendar_legend.py` восстановлен из `HEAD`, затем повторно внесена только целевая правка в `_build_full_legend`.
- Финальный `git diff -- src/finance_tracker/components/calendar_legend.py` ограничен целевым блоком функции без шумового рефакторинга по файлу.

## Task 2: Тесты full-mode и resize-regression (2026-02-12)
- В `tests/test_calendar_legend_ui.py` добавлен `test_full_legend_has_wrap_and_no_separator_profile`: проверяет `full_legend.wrap == True` и отсутствие в full-mode `ft.Container` c профилем `width=1`, `height=16`, `bgcolor=ft.Colors.OUTLINE_VARIANT`.
- В `tests/test_calendar_legend_ui.py` добавлен `test_update_calendar_width_preserves_compact_details_button_contract`: проверяет переходы `full -> compact -> full -> compact` через `update_calendar_width()` и сохранение кнопки `Подробнее...` в compact-path.
- Подтверждено через grep наличие новых assert-ов на `wrap`, профиль separator и контракт compact-кнопки.

## Task 2 Retry: Clean diff only (2026-02-12)
- Шумовой форматный diff в `tests/test_calendar_legend_ui.py` устранен: файл пересобран от `HEAD` и повторно внесены только два целевых теста.
- Финальный `git diff -- tests/test_calendar_legend_ui.py` содержит только добавление тестов без нецелевых style/import churn.

## Final verification + commit (2026-02-12)
- Прогонены через `.venv/bin/python`: `tests/test_calendar_legend_ui.py -v` (17 passed), `tests/test_calendar_legend_integration.py -v` (6 passed), `tests/test_calendar_legend_error_handling.py -v` (20 passed).
- Выполнен `compileall` через `.venv/bin/python -m compileall src/finance_tracker/components/calendar_legend.py` без ошибок.
- Создан коммит `90a91ae` с сообщением `feat(calendar-legend): render full legend as multiline without separators`.

## Plan Sync: Checkboxes updated to executed evidence (2026-02-12)
- Все чекбоксы в .sisyphus/plans/calendar-legend-multiline.md синхронизированы с фактически выполненной работой:
  - Definition of Done (3/3): full-mode wrap, compact-mode сохранен, тесты пройдены
  - TODO Tasks (3/3): Task 1 (multiline), Task 2 (тесты), Task 3 (верификация и коммит)
  - Acceptance Criteria Task 1 (3/3): wrap=True, без separators, compact-mode не изменен
  - Acceptance Criteria Task 2 (3/3): тест на отсутствие separators, тест на кнопку Подробнее, тест на width-переходы
  - Acceptance Criteria Task 3 (5/5): 3 test suites passed, compileall success, commit создан
  - Final Checklist (5/5): все критерии подтверждены
- Итого: 22 чекбокса отмечены как выполненные ([x]).

