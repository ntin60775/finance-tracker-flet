# Issues

## Analysis: Implementation Risks (2026-02-12)

### HIGH RISK: Test Failures

#### 1. test_separator_creation_stability (CRITICAL - WILL FAIL)
**File:** tests/test_calendar_legend_error_handling.py:356-365
```python
def test_separator_creation_stability(self):
    """Тест стабильности создания разделителей между группами."""
    legend = CalendarLegend()
    separator = legend._create_group_separator()
    
    self.assertIsInstance(separator, ft.Container)
    self.assertEqual(separator.width, 1)
    self.assertEqual(separator.height, 16)
```
**Why it will fail:** Directly calls `_create_group_separator()` which we're removing.
**Mitigation:** Either keep method returning None with deprecation warning, or update test.

### MEDIUM RISK: Structural Assumptions

#### 2. Control Count Assertions
**File:** tests/test_calendar_legend_integration.py:293-303
```python
full_content = legend._build_full_legend()
self.assertIsInstance(full_content, ft.Row)
self.assertGreater(len(full_content.controls), 0, "Полная легенда должна содержать элементы")
```
**Risk:** Control count changes from (indicators + separators) to (indicators only).
**Current count:** 7 indicators + 2 separators = 9 controls
**After change:** 7 indicators = 7 controls
**Mitigation:** Tests use `> 0` so they pass, but any exact count assertions would fail.

### LOW RISK: Visual Regression

#### 3. Layout Mode Detection
**File:** src/finance_tracker/components/calendar_legend.py:164-214
- `_should_show_full_legend()` uses width calculations
- If multiline always fits, compact mode may become unused
- **Impact:** Button "Подробнее..." may never appear in practice

#### 4. WidthCalculator Integration
**File:** src/finance_tracker/components/calendar_legend.py:111-162
- `_calculate_required_width()` may over-estimate if separators removed
- Used in `_should_show_full_legend()` and `_get_priority_indicators_for_width()`
- **Risk:** False positives for compact mode trigger

### IMPLEMENTATION SAFE-ZONES

#### Safe to Remove Without Side Effects:
1. **Lines 461-473** - `_create_group_separator()` method
2. **Lines 348-350** - Separator insertion logic in `_build_full_legend()`

#### Must Preserve:
1. **Lines 411-459** - `_group_indicators_visually()` - used for organization
2. **Lines 319-362** - `_build_full_legend()` structure - just modify return type
3. **Lines 364-409** - `_build_compact_legend()` - compact mode unchanged

### MIGRATION PATH RECOMMENDATION

1. **Phase 1:** Remove separator insertion (lines 348-350) - keeps method for compatibility
2. **Phase 2:** Change Row to Wrap or Column in _build_full_legend()
3. **Phase 3:** Update or remove `test_separator_creation_stability`
4. **Phase 4:** Verify control counts in integration tests

### DEPRECATED CODE CONSIDERATIONS

The following are marked as deprecated but still used:
- `_safe_get_page()` (line 702-716) - redirects to PageAccessManager
- `_build_full_legend_content()` (line 801-809) - marked obsolete but present
- `_open_dlg()` / `_close_dlg()` (lines 811-828) - backward compatibility

These should NOT be touched as part of multiline migration.

## Research: External Risks and Compatibility Notes

### Flet Version Compatibility

**Current project constraint**: `flet~=0.80.5`

All documented `Row.wrap` properties are confirmed available in this version:
- `wrap` ✓
- `spacing` ✓  
- `run_spacing` ✓
- `run_alignment` ✓
- `vertical_alignment` ✓

**Risk Level**: LOW - All features are stable core API.

### Potential Issues with Multiline Legend

#### 1. Height Calculation Changes
**Risk**: MEDIUM
- Single-line Row has predictable height
- Multiline Row height varies with number of wrapped rows
- May affect parent container sizing calculations

**Mitigation**: 
- Use `intrinsic_height=True` on parent containers
- Test with extreme legend item counts (min/max)
- Consider max-height constraints if needed

#### 2. Compact Mode Impact
**Risk**: LOW
- The task specifies: "Compact mode with 'Подробнее...' must remain unchanged"
- Wrap property only affects full-mode legend
- Ensure conditional logic correctly applies wrap only to full-mode

**Mitigation**:
- Explicit conditional: `wrap=True if is_full_mode else False`
- Add regression test for compact mode behavior

#### 3. Responsive Width Handling
**Risk**: MEDIUM
- Wrapping behavior depends on available width
- Window resize may cause layout shifts
- Test edge cases: very narrow, very wide windows

**Mitigation**:
- Ensure parent container has `expand=True` or explicit width
- Test at multiple window widths
- Consider `ft.ResponsiveRow` if complex responsive behavior needed

#### 4. Divider Removal
**Risk**: LOW
- Task: "убрать разделители" (remove separators)
- Current implementation may use `ft.Divider` or `ft.VerticalDivider`
- Simply removing may affect visual grouping

**Mitigation**:
- Use `spacing` property to create visual separation
- Consider `bgcolor` on Chip or Container for visual grouping
- Test visual hierarchy without separators

#### 5. Test Assertion Updates
**Risk**: MEDIUM
- Existing tests may assert on control structure
- Changing from flat list to wrapped Row shouldn't break logic
- But test assertions may need updates

**Mitigation**:
- Review existing legend tests before implementation
- Update assertions to check wrap/spacing properties
- Ensure both full-mode and compact-mode tested

### No Deprecated APIs Used

All recommended approaches use current Flet APIs:
- ✓ `ft.Row.wrap` - Current API
- ✓ `ft.Chip` - Current API (if used)
- ✓ `spacing`/`run_spacing` - Current API
- ✗ No deprecated `page.dialog = ...` patterns
- ✗ No deprecated `dialog.open = True/False` patterns

### Platform Considerations

**Desktop (Primary target)**:
- Full wrap support
- Resize handling works correctly

**Web (If applicable)**:
- Same wrap behavior
- Consider touch targets if legend items clickable

### Dependencies

No new dependencies required:
- All features in base `flet` package
- No additional packages to install

---
*Research completed: 2026-02-12*
*Task: Calendar legend multiline layout preparation*

## Implementation Run: Verification blockers (2026-02-12)
- Команда `pytest tests/test_calendar_legend_ui.py -k "details_button_visibility_based_on_width" -v` не выполнилась: `pytest: команда не найдена`.
- Повторные попытки через `python -m pytest` и `python3 -m pytest` также не дали валидного прогона (отсутствуют `python`/модуль `pytest` в текущем окружении).

## Retry: noise diff resolved (2026-02-12)
- Изначально после правки возник шумовой форматный diff по всему `calendar_legend.py`, не соответствующий границам Task 1.
- Проблема устранена через восстановление файла из `HEAD` и повторное внесение только целевого изменения в `_build_full_legend`.

## Task 2: Verification blocker (2026-02-12)
- Таргетный запуск `python3 -m pytest tests/test_calendar_legend_ui.py -k "separator and full_legend or details_button_visibility_based_on_width" -v` завершился блокером окружения: `/usr/bin/python3: No module named pytest`.
- Из-за отсутствия модуля `pytest` выполнить runtime-подтверждение новых тестов в текущем окружении невозможно.
- Повторный запуск той же команды после обновления тестов дал тот же результат: модуль `pytest` отсутствует.

## Final verification status (2026-02-12)
- Блокер окружения закрыт: все требуемые проверки выполнены через `.venv/bin/python`, падений и новых проблем не зафиксировано.
- Коммит с финальным результатом: `90a91ae`.
