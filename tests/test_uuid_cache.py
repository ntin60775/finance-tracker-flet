
from finance_tracker.utils.cache import CacheStore
from hypothesis import given, strategies as st
import uuid

@given(st.uuids())
def test_cache_store_with_uuid_keys(uuid_key):
    """
    **Feature: uuid-migration, Property 11: Кэширование UUID**
    """
    store = CacheStore("test")
    key = str(uuid_key)
    value = {"data": "test"}
    
    store.set(key, value)
    assert store.get(key) == value

def test_cache_set_all_with_uuid_extractor():
    """Test set_all using UUIDs."""
    store = CacheStore("test")
    
    class Item:
        def __init__(self, id, name):
            self.id = id
            self.name = name
            
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    items = [Item(id1, "Item 1"), Item(id2, "Item 2")]
    
    store.set_all(items, key_extractor=lambda x: x.id)
    
    assert store.get(id1).name == "Item 1"
    assert store.get(id2).name == "Item 2"
    assert len(store.get_all()) == 2
