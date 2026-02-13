# Acceptance Test Patterns: Category Hierarchy

## Test Category 1: Model & Relationship Tests

### Test: Self-Referential Relationship Integrity
```python
def test_category_parent_child_relationship(db_session):
    """Verify bidirectional parent-child relationship works."""
    # Arrange
    parent = Category(name="Food", id="cat-food")
    child = Category(name="Groceries", id="cat-groceries", parent=parent)
    
    # Act
    db_session.add(parent)
    db_session.commit()
    
    # Assert
    assert child.parent == parent
    assert child in parent.children
    assert child.parent_id == parent.id
```

### Test: Leaf Node Detection
```python
def test_category_is_leaf_property(db_session):
    """Verify is_leaf correctly identifies nodes without children."""
    # Arrange
    parent = Category(name="Parent", id="cat-parent")
    child = Category(name="Child", id="cat-child", parent=parent)
    db_session.add_all([parent, child])
    db_session.commit()
    
    # Assert
    assert parent.is_leaf is False
    assert child.is_leaf is True
```

### Test: Circular Reference Prevention
```python
def test_category_circular_reference_blocked(db_session):
    """Verify category cannot be its own ancestor."""
    # Arrange
    parent = Category(name="Parent", id="cat-parent")
    child = Category(name="Child", id="cat-child", parent=parent)
    db_session.add_all([parent, child])
    db_session.commit()
    
    # Act & Assert - Try to make child its own grandparent
    with pytest.raises(IntegrityError):
        parent.parent = child  # Would create cycle
        db_session.commit()
    db_session.rollback()
```

---

## Test Category 2: Foreign Key & Import Tests

### Test: Deferred FKs Allow Out-of-Order Insert
```python
def test_deferred_fks_self_referential_import(db_session):
    """Test PRAGMA defer_foreign_keys allows child-before-parent."""
    # Arrange
    db_session.execute(text("PRAGMA defer_foreign_keys = ON"))
    
    # Act - Insert child before parent (normally invalid)
    child = Category(id="cat-child", name="Child", parent_id="cat-parent")
    parent = Category(id="cat-parent", name="Parent", parent_id=None)
    
    db_session.add(child)
    db_session.add(parent)
    
    # Assert - Should succeed with deferred FKs
    db_session.commit()
    
    # Verify relationship
    assert child.parent == parent
    assert child in parent.children
```

### Test: Immediate FKs Enforce Referential Integrity
```python
def test_immediate_fks_block_invalid_reference(db_session):
    """Test immediate FKs prevent orphan references."""
    # Arrange - Deferred OFF by default after commit
    db_session.execute(text("PRAGMA defer_foreign_keys = OFF"))
    
    # Act & Assert
    child = Category(id="cat-child", name="Child", parent_id="nonexistent")
    db_session.add(child)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
```

### Test: FK Enable on Connection
```python
def test_foreign_keys_enabled_on_connect(engine):
    """Verify FK enforcement is enabled on new connections."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        fk_status = result.scalar()
        assert fk_status == 1, "Foreign keys must be enabled"
```

---

## Test Category 3: Service Layer Tests

### Test: Leaf-Only Validation
```python
def test_service_rejects_non_leaf_category_for_transaction(category_service):
    """Verify transactions cannot use parent categories."""
    # Arrange
    parent = category_service.create(name="Food", id="cat-food")
    category_service.create(name="Groceries", id="cat-groceries", parent_id=parent.id)
    
    # Act & Assert
    with pytest.raises(CategoryValidationError, match="leaf category"):
        category_service.validate_transaction_category(parent.id)
```

### Test: Get Leaf Categories
```python
def test_service_get_leaf_categories(category_service, db_session):
    """Verify only leaf categories are returned."""
    # Arrange
    parent = category_service.create(name="Parent", id="cat-parent")
    child1 = category_service.create(name="Child1", id="cat-child1", parent_id=parent.id)
    child2 = category_service.create(name="Child2", id="cat-child2", parent_id=parent.id)
    
    # Act
    leaves = category_service.get_leaf_categories()
    
    # Assert
    assert len(leaves) == 2
    assert child1 in leaves
    assert child2 in leaves
    assert parent not in leaves
```

### Test: Delete Protection
```python
def test_service_prevents_delete_with_transactions(category_service, db_session):
    """Verify cannot delete category with transaction history."""
    # Arrange
    category = category_service.create(name="Food", id="cat-food")
    
    # Create a transaction using this category
    txn = Transaction(amount=100.0, category_id=category.id)
    db_session.add(txn)
    db_session.commit()
    
    # Act & Assert
    with pytest.raises(CategoryInUseError):
        category_service.delete(category.id)
```

### Test: Delete Protection with Children
```python
def test_service_prevents_delete_with_children(category_service):
    """Verify cannot delete category with subcategories."""
    # Arrange
    parent = category_service.create(name="Parent", id="cat-parent")
    category_service.create(name="Child", id="cat-child", parent_id=parent.id)
    
    # Act & Assert
    with pytest.raises(CategoryHasChildrenError):
        category_service.delete(parent.id)
```

---

## Test Category 4: UI/Layout Tests

### Test: ResponsiveRow Column Assignment
```python
def test_category_list_uses_responsive_layout():
    """Verify category list uses ResponsiveRow with proper column spans."""
    # Arrange
    view = CategoryListView()
    
    # Act
    layout = view.build_layout()
    
    # Assert
    assert isinstance(layout, ft.ResponsiveRow)
    assert len(layout.controls) == 2  # Two columns
    
    for container in layout.controls:
        assert isinstance(container, ft.Container)
        assert "xs" in container.col
        assert "md" in container.col
        assert container.col["xs"] == 12
        assert container.col["md"] == 6
```

### Test: Dropdown Filters to Leaf Only
```python
def test_category_dropdown_shows_only_leaves(category_service):
    """Verify dropdown contains only leaf categories."""
    # Arrange
    parent = category_service.create(name="Parent", id="cat-parent")
    leaf = category_service.create(name="Leaf", id="cat-leaf", parent_id=parent.id)
    
    # Act
    dropdown = build_category_dropdown(leaf_only=True)
    option_values = [opt.key for opt in dropdown.options]
    
    # Assert
    assert leaf.id in option_values
    assert parent.id not in option_values
```

### Test: Tree View Expand/Collapse
```python
def test_category_tree_expand_collapse():
    """Verify tree nodes can expand and collapse."""
    # Arrange
    tree = CategoryTreeView()
    parent = Mock(id="cat-parent", name="Parent", children=[
        Mock(id="cat-child", name="Child", children=[])
    ])
    
    # Act
    tree_item = tree.build_tree_item(parent)
    
    # Assert
    assert tree_item.leading is not None  # Has expand/collapse icon
```

---

## Test Category 5: Integration Tests

### Test: End-to-End Category Creation Flow
```python
def test_create_category_with_parent_integration(client, db_session):
    """Test full flow: create parent, create child, verify tree."""
    # Arrange
    parent_data = {"name": "Food", "type": "expense"}
    
    # Act - Create parent
    response = client.post("/api/categories", json=parent_data)
    assert response.status_code == 201
    parent_id = response.json()["id"]
    
    # Create child
    child_data = {"name": "Groceries", "type": "expense", "parent_id": parent_id}
    response = client.post("/api/categories", json=child_data)
    assert response.status_code == 201
    child_id = response.json()["id"]
    
    # Verify tree structure
    response = client.get("/api/categories/tree")
    tree = response.json()
    assert len(tree) == 1
    assert tree[0]["id"] == parent_id
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["id"] == child_id
```

### Test: Transaction with Leaf Category
```python
def test_create_transaction_with_leaf_category_integration(client, db_session):
    """Test transaction creation validates leaf category."""
    # Arrange - Create hierarchy
    parent = Category(name="Food", id="cat-food")
    child = Category(name="Groceries", id="cat-groceries", parent=parent)
    db_session.add_all([parent, child])
    db_session.commit()
    
    # Act - Try to use parent (should fail)
    txn_data = {
        "amount": 50.00,
        "category_id": parent.id,
        "date": "2024-01-15",
    }
    response = client.post("/api/transactions", json=txn_data)
    
    # Assert
    assert response.status_code == 422
    assert "leaf" in response.json()["detail"].lower()
    
    # Act - Use child (should succeed)
    txn_data["category_id"] = child.id
    response = client.post("/api/transactions", json=txn_data)
    
    # Assert
    assert response.status_code == 201
```

---

## Test Category 6: Property-Based Tests

### Test: Tree Integrity Invariants
```python
from hypothesis import given, strategies as st

def test_tree_parent_child_consistency(db_session):
    """Property: Every child's parent_id matches its parent's id."""
    # Query all categories
    categories = db_session.scalars(select(Category)).all()
    
    for cat in categories:
        if cat.parent_id:
            assert cat.parent is not None
            assert cat.parent.id == cat.parent_id
```

### Test: No Circular References
```python
def test_no_circular_references(db_session):
    """Property: Following parent links never returns to starting node."""
    categories = db_session.scalars(select(Category)).all()
    
    for start in categories:
        visited = set()
        current = start
        while current:
            assert current.id not in visited, f"Cycle detected at {current.id}"
            visited.add(current.id)
            current = current.parent
```

---

## Test Category 7: Edge Cases

### Test: Root Category Without Parent
```python
def test_root_category_has_no_parent(db_session):
    """Verify root category (parent_id=None) is valid."""
    root = Category(name="Root", id="cat-root", parent_id=None)
    db_session.add(root)
    db_session.commit()
    
    assert root.parent is None
    assert root.parent_id is None
    assert root.is_leaf is True  # No children yet
```

### Test: Deep Tree (Constraint Check)
```python
def test_single_level_constraint_enforced(category_service):
    """Verify cannot create grandchild categories."""
    # Arrange
    grandparent = category_service.create(name="Grandparent", id="cat-gp")
    parent = category_service.create(name="Parent", id="cat-parent", parent_id=grandparent.id)
    
    # Act & Assert
    with pytest.raises(CategoryValidationError):
        category_service.create(
            name="Child", 
            id="cat-child", 
            parent_id=parent.id
        )
```

### Test: Unicode Category Names
```python
def test_unicode_category_names(db_session):
    """Verify categories support unicode names."""
    cat = Category(name="食品 🍎", id="cat-unicode")
    db_session.add(cat)
    db_session.commit()
    
    retrieved = db_session.get(Category, cat.id)
    assert retrieved.name == "食品 🍎"
```

---

## Test Execution Order

```bash
# 1. Fast unit tests
pytest tests/test_category_model.py -v

# 2. Service layer tests
pytest tests/test_category_service.py -v

# 3. Integration tests
pytest tests/test_category_integration.py -v

# 4. Property-based tests (longer running)
pytest tests/test_category_properties.py -v --hypothesis-seed=0

# 5. All category tests with coverage
pytest tests/test_category*.py --cov=src/finance_tracker --cov-report=html
```

---

## Test Data Fixtures

```python
@pytest.fixture
def sample_category_hierarchy(db_session):
    """Create sample 2-level category hierarchy."""
    expense = Category(name="Expense", id="cat-expense", type="expense")
    food = Category(name="Food", id="cat-food", type="expense", parent=expense)
    transport = Category(name="Transport", id="cat-transport", type="expense", parent=expense)
    groceries = Category(name="Groceries", id="cat-groceries", type="expense", parent=food)
    
    db_session.add_all([expense, food, transport, groceries])
    db_session.commit()
    
    return {
        "root": expense,
        "parents": [food, transport],
        "leaves": [groceries],
    }

@pytest.fixture
def category_service(db_session):
    """Provide category service with test session."""
    return CategoryService(session=db_session)
```
