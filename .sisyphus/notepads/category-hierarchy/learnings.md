# Research: Category Hierarchy Implementation Patterns

## 1. SQLAlchemy 2.x Self-Referential Relationships

### Best Practice: Adjacency List Pattern
The adjacency list is the recommended pattern for hierarchical data in SQLAlchemy 2.x. It's simpler than nested sets or materialized path, offers better concurrency, and has sufficient performance when subtrees can be fully loaded into application space.

### Implementation Checklist
- [ ] Use `MappedAsDataclass` for modern SQLAlchemy 2.0 style
- [ ] Define `parent_id` as nullable ForeignKey to same table
- [ ] Configure bidirectional relationship with `back_populates`
- [ ] Use `remote_side=[id]` on the parent side for many-to-one direction
- [ ] Add `join_depth` parameter for eager loading (default 0, increase as needed)
- [ ] Consider `cascade="all, delete-orphan"` for automatic cleanup
- [ ] Use `collection_class=attribute_keyed_dict("name")` for dict-like access

### Code Pattern
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship, remote_side
from typing import Optional, Dict

class TreeNode(Base):
    __tablename__ = "tree_node"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tree_node.id"), nullable=True
    )
    name: Mapped[str]
    
    # Bidirectional relationship
    children: Mapped[Dict[str, "TreeNode"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="parent",
        collection_class=attribute_keyed_dict("name"),
    )
    parent: Mapped[Optional["TreeNode"]] = relationship(
        back_populates="children", 
        remote_side=[id]
    )
    
    @property
    def is_leaf(self) -> bool:
        """True if node has no children."""
        return not self.children
```

### Query Patterns
- **Get root nodes**: `select(Node).where(Node.parent_id.is_(None))`
- **Join to parent**: Use `aliased()` for self-joins
- **Eager loading**: Set `join_depth` or use `joinedload()` with depth

---

## 2. SQLite Self-Referential Foreign Key Behavior

### Key Behaviors
1. **Foreign keys disabled by default** - Must enable with `PRAGMA foreign_keys = ON`
2. **Deferred constraints** - Use `PRAGMA defer_foreign_keys = ON` to delay FK checks until COMMIT
3. **Import order matters** - Parent rows must exist before child rows unless using deferred constraints

### Implementation Strategy
```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    """Enable FK enforcement on every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

# For bulk imports, defer constraints
def bulk_import_with_deferred_fks(session, nodes):
    """Import nodes with cyclic/self-referential FKs safely."""
    session.execute(text("PRAGMA defer_foreign_keys = ON"))
    try:
        session.add_all(nodes)
        session.commit()  # FKs checked here
    except IntegrityError:
        session.rollback()
        raise
```

### Critical Rules
- Always enable `PRAGMA foreign_keys` on connection (not per-transaction)
- Deferred FKs only work inside explicit transactions (BEGIN...COMMIT)
- Deferred FKs reset at transaction boundaries
- Cannot mix deferred FKs with connection pooling without careful handling

---

## 3. Flet Two-Column Responsive Layout

### Recommended Pattern: ResponsiveRow
Use `ResponsiveRow` with breakpoint-based column spans for responsive two-column layouts.

### Breakpoint Strategy
- **xs**: 12 columns (full width, stacked vertically)
- **md**: 6 columns each (two columns side by side)
- **lg**: 6 columns each (maintains two columns)

### Code Pattern
```python
import flet as ft

def build_two_column_layout(left_content, right_content):
    """Build responsive two-column layout."""
    return ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=left_content,
                col={
                    ft.ResponsiveRowBreakpoint.XS: 12,
                    ft.ResponsiveRowBreakpoint.MD: 6,
                },
                padding=10,
            ),
            ft.Container(
                content=right_content,
                col={
                    ft.ResponsiveRowBreakpoint.XS: 12,
                    ft.ResponsiveRowBreakpoint.MD: 6,
                },
                padding=10,
            ),
        ],
        spacing=20,
    )
```

### For Category List Grouping
Use nested `Column` within `ResponsiveRow` cells:
```python
def build_category_list_grouped(categories_by_parent):
    """Display categories grouped by parent."""
    rows = []
    for parent_name, children in categories_by_parent.items():
        group = ft.Column(
            controls=[
                ft.Text(parent_name, weight=ft.FontWeight.BOLD, size=16),
                ft.Column([
                    ft.ListTile(title=ft.Text(child.name))
                    for child in children
                ]),
            ],
            spacing=8,
        )
        rows.append(group)
    
    return ft.ResponsiveRow(
        controls=[
            ft.Container(content=group, col={"xs": 12, "md": 6})
            for group in rows
        ],
        run_spacing=20,
    )
```

---

## 4. Leaf-Only Category Selection Pattern

### Backend Validation Strategy
```python
from pydantic import validator, BaseModel
from typing import Optional

class TransactionCreate(BaseModel):
    category_id: Optional[str]
    
    @validator('category_id')
    def validate_leaf_category(cls, v):
        if v is None:
            return v
        # Check category exists and has no children
        category = get_category(v)
        if category and category.children:
            raise ValueError("Only leaf categories can be assigned to transactions")
        return v
```

### Service Layer Validation
```python
class CategoryService:
    def is_leaf_category(self, category_id: str) -> bool:
        """Check if category has no children."""
        category = self.get_by_id(category_id)
        return category is not None and not category.children
    
    def validate_transaction_category(self, category_id: Optional[str]) -> None:
        """Raise if category is not a valid leaf node."""
        if category_id and not self.is_leaf_category(category_id):
            raise CategoryValidationError(
                "Transaction must use a leaf category"
            )
```

### UI Filtering Pattern
```python
def build_category_dropdown(categories, leaf_only=True):
    """Build dropdown with optional leaf-only filtering."""
    if leaf_only:
        options = [
            ft.dropdown.Option(cat.id, cat.name)
            for cat in categories
            if not cat.children  # Leaf check
        ]
    else:
        options = [
            ft.dropdown.Option(cat.id, cat.name)
            for cat in categories
        ]
    
    return ft.Dropdown(
        label="Category",
        options=options,
        hint_text="Select a category" if leaf_only else "Select a category (any)",
    )
```

### Tree Display with Leaf Indicators
```python
def build_category_tree_item(category, level=0):
    """Build tree view item with visual leaf indicators."""
    indent = "  " * level
    is_leaf = not category.children
    
    return ft.ListTile(
        leading=ft.Icon(
            ft.Icons.CHECK_CIRCLE if is_leaf else ft.Icons.FOLDER,
            color=ft.Colors.GREEN if is_leaf else ft.Colors.ORANGE,
        ),
        title=ft.Text(f"{indent}{category.name}"),
        subtitle=ft.Text("Leaf category" if is_leaf else f"{len(category.children)} subcategories"),
        on_click=lambda e: select_category(category) if is_leaf else toggle_expand(category),
    )
```

---

## Summary: Project-Specific Checklist

### For finance-tracker-flet Category Implementation:

1. **Model Layer**
   - [ ] CategoryDB with parent_id FK to self
   - [ ] Bidirectional children/parent relationships
   - [ ] is_leaf property for quick checks
   - [ ] depth validation (max 1 level for MVP)

2. **Database Layer**
   - [ ] Enable FKs on SQLite connection
   - [ ] Deferred FKs for seeding/import
   - [ ] Index on parent_id for performance

3. **Service Layer**
   - [ ] get_leaf_categories() for dropdowns
   - [ ] validate_leaf_only() for transactions
   - [ ] get_categories_grouped() for tree view

4. **UI Layer**
   - [ ] ResponsiveRow for two-column layout
   - [ ] Filtered dropdown (leaf-only option)
   - [ ] Tree view with expand/collapse
   - [ ] Visual leaf indicators

5. **Validation Layer**
   - [ ] Pydantic validator for leaf-only
   - [ ] Service-layer guard rails
   - [ ] UI filtering to prevent invalid selection
