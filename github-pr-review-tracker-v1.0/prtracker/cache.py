from collections import OrderedDict
from typing import Any

# ============================================================
# CACHE
# ============================================================

class SimpleCache:
    def clear(self) -> None:
        self._store.clear()
    
    def __init__(self, max_entries: int = 5) -> None:
        self.max_entries = max_entries
        self._store: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None

        value = self._store.pop(key)
        self._store[key] = value
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.pop(key)

        self._store[key] = value

        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)