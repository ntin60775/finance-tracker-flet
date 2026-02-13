# References: Category Hierarchy Implementation

## SQLAlchemy 2.x Self-Referential Relationships

### Official Documentation

1. **Adjacency List Relationships - SQLAlchemy 2.0**
   - URL: https://docs.sqlalchemy.org/en/20/orm/self_referential.html
   - Key topics: Basic adjacency list, bidirectional relationships, eager loading
   - Notes: Primary reference for self-referential FK implementation

2. **Relationship Configuration - SQLAlchemy 2.0**
   - URL: https://docs.sqlalchemy.org/en/20/orm/relationships.html
   - Key topics: All relationship patterns, cascade options
   - Notes: Comprehensive relationship guide

3. **Working Example - Adjacency List**
   - URL: https://docs.sqlalchemy.org/en/20/_modules/examples/adjacency_list/adjacency_list.html
   - Key topics: Working code example with TreeNode class
   - Notes: Shows `MappedAsDataclass` pattern, dict-based children

4. **Self-Referential Many-to-Many**
   - URL: https://docs.sqlalchemy.org/en/20/orm/join_conditions.html#self-referential-many-to-many-relationship
   - Key topics: Association table pattern for complex hierarchies
   - Notes: Not needed for simple parent-child, but good reference

### Community Discussions

5. **Eager Loading Self-Referential FK - GitHub Discussion #10138**
   - URL: https://github.com/sqlalchemy/sqlalchemy/discussions/10138
   - Key topics: `join_depth` parameter, selectinload for both directions
   - Notes: Explains why both parent and children need join_depth for eager loading

6. **Self-Referential Mapping - Stack Overflow**
   - URL: https://stackoverflow.com/questions/2638217/sqlalchemy-mapping-self-referential-relationship-as-one-to-many-declarative-f
   - Key topics: `remote_side` parameter usage
   - Notes: Classic explanation of directionality in self-referential relationships

---

## SQLite Foreign Key Behavior

### Official Documentation

7. **SQLite Foreign Key Support**
   - URL: https://www.sqlite.org/foreignkeys.html
   - Key topics: Enabling FKs, deferred constraints, ON DELETE/UPDATE
   - Notes: Section 4.2 covers deferred FKs extensively

8. **SQLite PRAGMA Reference**
   - URL: https://www.sqlite.org/pragma.html
   - Key topics: `foreign_keys`, `defer_foreign_keys`, `foreign_key_check`
   - Notes: Complete PRAGMA documentation

### Real-World Issues

9. **Self-Referencing FK Issues - DBA StackExchange**
   - URL: https://dba.stackexchange.com/questions/343664/issues-with-self-referencing-foreign-key-in-sqlite
   - Key topics: Import order problems with self-referential tables
   - Notes: Shows practical solutions for seeding data

10. **Deferred FKs Not Working - SQLAlchemy Discussion #6123**
    - URL: https://github.com/sqlalchemy/sqlalchemy/discussions/6123
    - Key topics: File vs memory database differences, NullPool issues
    - Notes: Critical insight into connection pooling behavior with deferred FKs

11. **Cloudflare D1 Foreign Key Documentation**
    - URL: https://developers.cloudflare.com/d1/sql-api/foreign-keys/
    - Key topics: Production SQLite FK usage patterns
    - Notes: Good practical examples of defer_foreign_keys usage

---

## Flet Layout Patterns

### Official Documentation

12. **ResponsiveRow - Flet Docs**
    - URL: https://docs.flet.dev/controls/responsiverow
    - Key topics: Breakpoints, column spans, responsive layouts
    - Notes: Shows col={"xs": 12, "md": 6} pattern

13. **Column - Flet Docs**
    - URL: https://docs.flet.dev/controls/column
    - Key topics: Vertical layouts, alignment, spacing
    - Notes: Use for grouping within ResponsiveRow cells

14. **Row - Flet Docs**
    - URL: https://docs.flet.dev/controls/row
    - Key topics: Horizontal layouts, expand property
    - Notes: expand=True makes children fill available space

15. **Flet Examples - Responsive Layout**
    - URL: https://github.com/flet-dev/examples/blob/main/python/controls/layout/responsive-row/responsive-layout.py
    - Key topics: Complete working example
    - Notes: Shows page_resize handling

### Tutorials

16. **Building a Responsive Dashboard with Flet**
    - URL: https://fletbuilder.com/flet-blog/building-a-responsive-dashboard-with-flet-and-python
    - Key topics: Dashboard layout patterns
    - Notes: Good for two-column finance app layouts

17. **Flet ToDo Tutorial**
    - URL: https://docs.flet.dev/tutorials/todo/
    - Key topics: Complete app structure, list handling
    - Notes: Best practices for list-based UIs

---

## Finance App Category Patterns

### UI Design Patterns

18. **PatternFly Tree View Guidelines**
    - URL: https://patternfly.org/components/tree-view/design-guidelines
    - Key topics: Tree view elements (expand/collapse, parent node, leaf node)
    - Notes: Professional UI pattern for hierarchical data

19. **Carbon Design System - Tree View**
    - URL: https://carbondesignsystem.com/components/tree-view/usage
    - Key topics: Tree view usage, accessibility
    - Notes: IBM's design system - good for leaf-only selection UX

20. **SAP Fiori Tree Guidelines**
    - URL: https://experience.sap.com/fiori-design-web/tree/
    - Key topics: When to use trees vs lists
    - Notes: Enterprise finance app perspective

### Implementation Examples

21. **Maybe Finance - Category Selection Issue #526**
    - URL: https://github.com/maybe-finance/maybe/issues/526
    - Key topics: Inline category selection, dropdown UX
    - Notes: Real finance app implementing category selection

22. **Recursive CTE for Category Trees - GitHub**
    - URL: https://github.com/databrainhq/dataneuron/blob/main/tests/core/test_sql_query_filter.py#L244
    - Key topics: SQL recursive CTE pattern for trees
    - Notes: Shows SQL pattern for hierarchical queries

---

## Quick Reference Table

| Topic | Primary Reference | Code Example |
|-------|------------------|--------------|
| SQLAlchemy Self-Ref | Doc #1 | Doc #3 |
| SQLite FKs | Doc #7 | Doc #9 |
| Deferred FKs | Doc #7 (4.2) | Doc #10 |
| Flet Responsive | Doc #12 | Doc #15 |
| Tree UI Pattern | Doc #18 | Doc #21 |
| Leaf Validation | Doc #18 | Doc #22 |

---

## Recommended Reading Order

1. Start with SQLAlchemy Doc #1 and #3 for model implementation
2. Read SQLite Doc #7 section 4.2 for FK behavior
3. Review Flet Doc #12 and #15 for UI layout
4. Check PatternFly Doc #18 for UX design guidance
5. Reference GitHub examples (#15, #21) for real implementations
