# Architectural Decisions: Category Hierarchy

## Decision 1: Adjacency List Pattern (Chosen)

**Status**: Accepted

**Context**: Need to store hierarchical categories (e.g., Food > Groceries > Produce). Options:
1. Adjacency List (parent_id FK) - Simple, good for limited depth
2. Nested Sets - Fast reads, terrible writes
3. Materialized Path - Flexible, complex string handling
4. Closure Table - Most flexible, requires extra table

**Decision**: Use Adjacency List pattern with parent_id self-referential FK.

**Rationale**:
- Simplest to implement and understand
- Sufficient for 1-2 level depth (MVP requirement)
- SQLAlchemy has excellent support
- Easy to add depth constraint if needed
- Good concurrency (unlike nested sets)

**Consequences**:
- (+) Simple model, simple queries
- (+) Native SQLAlchemy support
- (-) Deep tree traversal requires recursive queries
- (-) Harder to get full path in single query (need CTE)

**Mitigation**: Limit to single-level depth for MVP; add constraint.

---

## Decision 2: Single-Level Depth Constraint (MVP)

**Status**: Proposed

**Context**: Unlimited tree depth adds complexity for UI, validation, and queries.

**Decision**: Restrict categories to single level (parent -> children only, no grandchildren).

**Rationale**:
- Covers 95% of personal finance use cases
- Simplifies UI (no deep tree navigation)
- Simplifies leaf-only validation
- Prevents infinite recursion bugs
- Can relax later if needed

**Implementation**:
```python
# Database-level check constraint
CheckConstraint(
    "parent_id IS NULL OR parent_id IN (SELECT id FROM category WHERE parent_id IS NULL)",
    name="single_level_depth"
)

# Or application-level validation
@validates('parent_id')
def validate_single_level(self, key, parent_id):
    if parent_id:
        parent = session.get(Category, parent_id)
        if parent and parent.parent_id:
            raise ValueError("Cannot nest deeper than 1 level")
    return parent_id
```

**Consequences**:
- (+) Simpler UI (no accordion trees)
- (+) Faster queries
- (+) Clearer mental model
- (-) May need migration if users request deeper nesting

---

## Decision 3: Leaf-Only Transaction Categories

**Status**: Accepted

**Context**: Should transactions be allowed to use parent categories or only leaves?

**Decision**: Transactions MUST use leaf categories only.

**Rationale**:
- Prevents ambiguity (is "Food" a real expense or just a container?)
- Enforces proper categorization
- Better reporting accuracy
- Standard pattern in finance apps

**Implementation Strategy**:
1. **Backend**: Pydantic validator + service-layer check
2. **Frontend**: Filter dropdown to show only leaves
3. **UI**: Visual indicator (checkmark) for selectable categories

**Validation Points**:
- Model validation (Pydantic)
- Service layer (explicit check)
- Database (FK constraint - optional)

**Consequences**:
- (+) Data consistency
- (+) Clear reporting
- (-) Slightly more complex UI (need leaf filtering)
- (-) User must create leaf categories before use

---

## Decision 4: Deferred FKs for Seeding

**Status**: Accepted

**Context**: Initial data seeding may create parent/child relationships.

**Decision**: Use `PRAGMA defer_foreign_keys = ON` during seeding/import operations.

**Implementation**:
```python
def seed_categories(session, categories):
    """Seed with deferred FKs to allow any insertion order."""
    session.execute(text("PRAGMA defer_foreign_keys = ON"))
    
    for cat_data in categories:
        session.add(Category(**cat_data))
    
    session.commit()  # FKs validated here
```

**Rationale**:
- Allows flexible JSON/CSV import order
- Avoids complex topological sorting
- Single transaction for atomic seeding

**Consequences**:
- (+) Simple import code
- (+) Can import from unsorted data
- (-) Must remember to enable per-transaction
- (-) Errors only caught at commit time

---

## Decision 5: Two-Column Responsive Layout

**Status**: Accepted

**Context**: Category management UI needs to show tree on left, details on right.

**Decision**: Use Flet `ResponsiveRow` with two-column layout.

**Breakpoints**:
- xs (< 600px): Single column (12 cols each, stacked)
- md (≥ 600px): Two columns (6 cols each, side by side)

**Implementation**:
```python
ft.ResponsiveRow(
    controls=[
        ft.Container(
            content=category_tree_view,
            col={"xs": 12, "md": 6},
        ),
        ft.Container(
            content=category_detail_view,
            col={"xs": 12, "md": 6},
        ),
    ],
    spacing=20,
)
```

**Rationale**:
- Responsive without CSS/media queries
- Mobile-friendly (stacks on small screens)
- Native Flet support

**Consequences**:
- (+) Clean responsive behavior
- (+) No custom CSS needed
- (-) Requires Container wrapper with col property

---

## Decision 6: Eager Loading Strategy

**Status**: Proposed

**Context**: Loading category trees efficiently.

**Decision**: Use `selectinload` for tree queries, `join_depth=1` for individual lookups.

**Model Configuration**:
```python
class Category(Base):
    # ... fields ...
    
    children: Mapped[List["Category"]] = relationship(
        lazy="selectin",  # Batch load children
        join_depth=1,     # Eager load 1 level
        # ...
    )
```

**Query Patterns**:
```python
# For tree view - eager load children
stmt = select(Category).where(Category.parent_id.is_(None))
roots = session.scalars(stmt).all()  # Children loaded

# For dropdown - only need leaf check
stmt = select(Category).options(selectinload(Category.children))
categories = session.scalars(stmt).all()
```

**Rationale**:
- `selectinload` is most efficient for collections
- `join_depth=1` handles single-level constraint
- Avoids N+1 query problem

**Consequences**:
- (+) Efficient tree loading
- (+) No manual batch loading needed
- (-) May load more data than needed in some cases

---

## Decision 7: UUID String IDs (Consistent with Project)

**Status**: Accepted (consistent with existing pattern)

**Context**: Project uses UUID strings for all IDs.

**Decision**: Continue using UUID string IDs for categories.

**Implementation**:
```python
class Category(Base):
    __tablename__ = "category"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("category.id"),
        nullable=True
    )
```

**Rationale**:
- Consistency with existing models
- No int sequence to manage
- Safe for distributed scenarios

---

## Decision 8: Soft Delete vs Hard Delete

**Status**: Proposed

**Context**: What happens when deleting a category with transactions?

**Decision**: Prevent deletion of categories with transactions (hard delete only for unused).

**Implementation**:
```python
def delete_category(self, category_id: str) -> None:
    category = self.get_by_id(category_id)
    
    # Check for transactions
    if category.transactions:
        raise CategoryInUseError(
            f"Cannot delete '{category.name}' - has {len(category.transactions)} transactions"
        )
    
    # Check for children
    if category.children:
        raise CategoryHasChildrenError(
            f"Cannot delete '{category.name}' - has subcategories"
        )
    
    self.session.delete(category)
```

**Alternative Considered**: Soft delete with "archived" flag.
- Rejected: Adds complexity, FK constraints become messy

**Rationale**:
- Data integrity (no orphaned FKs)
- Clear user feedback
- Simpler implementation

**Consequences**:
- (+) Data integrity
- (+) Clear UX (error explains why)
- (-) Cannot delete categories with history

---

## Summary Table

| Decision | Status | Impact |
|----------|--------|--------|
| Adjacency List | Accepted | High - affects all queries |
| Single-Level Depth | Proposed | Medium - limits flexibility |
| Leaf-Only Transactions | Accepted | High - affects UX |
| Deferred FKs for Seeding | Accepted | Low - internal only |
| Two-Column Layout | Accepted | Medium - UI structure |
| Eager Loading Strategy | Proposed | Medium - performance |
| UUID IDs | Accepted | Low - consistency |
| Hard Delete Only | Proposed | Medium - data lifecycle |
