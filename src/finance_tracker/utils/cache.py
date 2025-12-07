"""
Модуль кэширования данных приложения.
Обеспечивает хранение часто используемых данных в памяти для ускорения доступа.
"""

import logging
from typing import Dict, List, Optional, Any, TypeVar, Generic
from threading import Lock

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheStore(Generic[T]):
    """Хранилище кэша для определенного типа данных."""
    
    def __init__(self, name: str):
        self.name = name
        self._cache: Dict[Any, T] = {}
        self._list_cache: Optional[List[T]] = None
        self._lock = Lock()
        
    def get(self, key: Any) -> Optional[T]:
        """Получение элемента по ключу."""
        with self._lock:
            return self._cache.get(key)
            
    def set(self, key: Any, value: T):
        """Сохранение элемента."""
        with self._lock:
            self._cache[key] = value
            # При изменении отдельного элемента сбрасываем кэш списка,
            # так как порядок или состав мог измениться (хотя это грубая стратегия)
            self._list_cache = None
            
    def get_all(self) -> Optional[List[T]]:
        """Получение всех элементов (если они закэшированы списком)."""
        with self._lock:
            return self._list_cache
            
    def set_all(self, items: List[T], key_extractor: callable):
        """Сохранение списка элементов."""
        with self._lock:
            self._list_cache = list(items)
            self._cache.clear()
            for item in items:
                self._cache[key_extractor(item)] = item
                
    def invalidate(self):
        """Полная очистка кэша."""
        with self._lock:
            self._cache.clear()
            self._list_cache = None
            logger.debug(f"Кэш '{self.name}' сброшен")

class AppCache:
    """Глобальный менеджер кэша приложения."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppCache, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Инициализация хранилищ
        self.categories = CacheStore("categories")
        self.lenders = CacheStore("lenders")
        
    def clear_all(self):
        """Очистка всех кэшей."""
        self.categories.invalidate()
        self.lenders.invalidate()

# Глобальный экземпляр
cache = AppCache()
