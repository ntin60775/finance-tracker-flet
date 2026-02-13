# Pitfalls to Avoid: Category Hierarchy Implementation

## 1. ORM/Object Lifecycle Pitfalls

### Detached Object Errors
**Problem**: Accessing `category.children` after the session closes raises `DetachedInstanceError`.

**Bad**:
```python
def get_category(session, id):
    return session.get(Category, id)  # Returns detached after session closes

# Later...
cat = get_category(session, 1)
for child in cat.children:  # ERROR: DetachedInstanceError
    print(child.name)
```

**Good**:
```python
def get_category_with_children(session, id):
    return session.scalar(
        select(Category)
        .where(Category.id == id)
        .options(joinedload(Category.children))
    )

# Or use join_depth in model
children = relationship("Category", lazy="joined", join_depth=1)
```

### Circular Reference in Serialization
**Problem**: Self-referential relationships cause infinite recursion in JSON serialization.

**Bad**:
```python
class Category(Base):
    children = relationship("Category")  # No lazy strategy
    
cat_dict = cat.__dict__  # May recurse infinitely
```

**Good**:
```python
# Use Pydantic models with explicit exclusion
class CategoryRead(BaseModel):
    id: str
    name: str
    is_leaf: bool
    # Don't include children to avoid recursion
    
    class Config:
        from_attributes = True
```

### N+1 Query Problem
**Problem**: Loading tree nodes one by one causes N+1 queries.

**Bad**:
```python
roots = session.scalars(select(Category).where(Category.parent_id.is_(None)))
for root in roots:
    for child in root.children:  # Each access = new query!
        print(child.name)
```

**Good**:
```python
# Eager load children
roots = session.scalars(
    select(Category)
    .where(Category.parent_id.is_(None))
    .options(selectinload(Category.children))
)
```

---

## 2. SQLite Foreign Key Pitfalls

### FKs Disabled by Default
**Problem**: SQLite doesn't enforce FK constraints unless explicitly enabled.

**Bad**:
```python
engine = create_engine("sqlite:///app.db")
# Foreign keys NOT enforced!
```

**Good**:
```python
@event.listens_for(engine, "connect")
def enable_fks(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys = ON")
```

### Deferred FKs Don't Persist
**Problem**: `PRAGMA defer_foreign_keys` resets at transaction boundaries.

**Bad**:
```python
session.execute(text("PRAGMA defer_foreign_keys = ON"))
# ... do work ...
session.commit()  # FKs checked here
# Next transaction: deferred is OFF again
```

**Good**:
```python
# Set at beginning of each transaction
with session.begin():
    session.execute(text("PRAGMA defer_foreign_keys = ON"))
    # ... bulk insert ...
```

### Import Order Issues
**Problem**: Self-referential FKs fail if child inserted before parent.

**Bad**:
```python
# Trying to seed data
session.add(Category(id="child", parent_id="parent"))  # FAILS
session.add(Category(id="parent", parent_id=None))
session.commit()
```

**Good - Option 1: Deferred FKs**:
```python
session.execute(text("PRAGMA defer_foreign_keys = ON"))
session.add(Category(id="child", parent_id="parent"))  # OK
session.add(Category(id="parent", parent_id=None))
session.commit()  # FKs validated here
```

**Good - Option 2: Ordered Insert**:
```python
# Insert roots first
for root in roots:
    session.add(root)
session.flush()  # Roots now have IDs

# Then children
for child in children:
    session.add(child)
session.commit()
```

### Connection Pooling Issues
**Problem**: Deferred FKs with connection pooling can fail because each checkout gets a fresh connection.

**Bad**:
```python
engine = create_engine("sqlite:///file.db")  # Uses NullPool for SQLite files
# defer_foreign_keys set on connection 1
# But next query uses connection 2 - deferred is OFF
```

**Good**:
```python
# Use SingletonThreadPool for single-threaded apps
from sqlalchemy.pool import SingletonThreadPool
engine = create_engine(
    "sqlite:///file.db",
    poolclass=SingletonThreadPool,
    connect_args={"check_same_thread": False}
)

# Or always set PRAGMAs in connect event
@event.listens_for(engine, "connect")
def setup_connection(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys = ON")
```

---

## 3. Flet Layout Pitfalls

### ResponsiveRow Without col Property
**Problem**: Controls in ResponsiveRow without `col` property don't render correctly.

**Bad**:
```python
ft.ResponsiveRow(
    controls=[
        ft.Text("Column 1"),  # Missing col!
        ft.Text("Column 2"),
    ]
)
```

**Good**:
```python
ft.ResponsiveRow(
    controls=[
        ft.Container(
            content=ft.Text("Column 1"),
            col={"xs": 12, "md": 6},
        ),
        ft.Container(
            content=ft.Text("Column 2"),
            col={"xs": 12, "md": 6},
        ),
    ]
)
```

### Missing expand on Child Controls
**Problem**: Children don't fill available space without expand.

**Bad**:
```python
ft.Row(controls=[ft.Text("A"), ft.Text("B")])  # No expansion
```

**Good**:
```python
ft.Row(
    controls=[
        ft.Container(content=ft.Text("A"), expand=True),
        ft.Container(content=ft.Text("B"), expand=True),
    ]
)
```

### Dialog API Deprecation
**Problem**: Using deprecated dialog patterns.

**Bad**:
```python
page.dialog = my_dialog
my_dialog.open = True
page.update()
```

**Good**:
```python
page.open(my_dialog)   # Modern API
# ... later ...
page.close(my_dialog)  # Modern API
```

---

## 4. Category Tree Logic Pitfalls

### Infinite Recursion in Tree Traversal
**Problem**: Circular parent references cause infinite loops.

**Bad**:
```python
def get_descendants(category):
    result = []
    for child in category.children:
        result.append(child)
        result.extend(get_descendants(child))  # Infinite if cycle!
    return result
```

**Good**:
```python
def get_descendants(category, visited=None):
    if visited is None:
        visited = set()
    if category.id in visited:
        raise ValueError(f"Cycle detected at {category.id}")
    visited.add(category.id)
    
    result = []
    for child in category.children:
        result.append(child)
        result.extend(get_descendants(child, visited))
    return result
```

### Race Condition in Leaf Validation
**Problem**: Category may gain children after leaf check but before transaction commit.

**Bad**:
```python
def create_transaction(session, category_id):
    category = session.get(Category, category_id)
    if not category.children:  # Check 1
        # ... time passes ...
        txn = Transaction(category_id=category_id)  # Check 1 is stale!
        session.add(txn)
        session.commit()
```

**Good**:
```python
def create_transaction(session, category_id):
    # Lock category row
    category = session.scalar(
        select(Category)
        .where(Category.id == category_id)
        .with_for_update()  # Row lock
    )
    
    # Refresh children (may trigger lazy load inside transaction)
    session.refresh(category, ['children'])
    
    if category.children:
        raise ValueError("Not a leaf category")
    
    txn = Transaction(category_id=category_id)
    session.add(txn)
    session.commit()
```

### Missing NULL Check
**Problem**: Not handling NULL parent_id for root categories.

**Bad**:
```python
def get_parent_chain(category):
    chain = [category]
    while category.parent_id:  # Fails if parent_id is NULL
        category = category.parent
        chain.append(category)
    return chain
```

**Good**:
```python
def get_parent_chain(category):
    chain = [category]
    current = category
    while current.parent is not None:  # Check relationship, not FK
        current = current.parent
        chain.append(current)
    return chain
```

---

## 5. Testing Pitfalls

### Mocking SQLAlchemy Relationships
**Problem**: Mocking relationships doesn't test actual FK behavior.

**Bad**:
```python
def test_category_tree():
    parent = Mock()
    parent.children = [Mock(), Mock()]
    # Doesn't test real SQLAlchemy behavior
```

**Good**:
```python
def test_category_tree(db_session):
    parent = Category(name="Parent")
    child = Category(name="Child", parent=parent)
    db_session.add(parent)
    db_session.commit()
    
    assert len(parent.children) == 1
    assert child.parent == parent
```

### Not Testing Deferred FK Behavior
**Problem**: Missing tests for import scenarios with cyclic references.

**Test**:
```python
def test_self_referential_import_order(db_session):
    """Test that deferred FKs allow child-before-parent insertion."""
    db_session.execute(text("PRAGMA defer_foreign_keys = ON"))
    
    # Insert child first (normally fails)
    child = Category(id="child", parent_id="parent")
    db_session.add(child)
    
    # Then insert parent
    parent = Category(id="parent", parent_id=None)
    db_session.add(parent)
    
    # Should succeed with deferred FKs
    db_session.commit()
    
    # Verify hierarchy
    assert child.parent == parent
```
