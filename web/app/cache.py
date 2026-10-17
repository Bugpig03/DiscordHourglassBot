"""Small in-memory TTL cache shared by the threads of a Gunicorn worker.

Used for data that is identical for every visitor (rankings, public chart series). Never store anything that
depends on who is viewing (private sessions, presence): callers add those fields after reading the cache.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Hashable


class TTLCache:
    def __init__(self, max_entries: int = 512):
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def get_or_set(self, key: Hashable, ttl_seconds: float, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(key)
            if hit and now - hit[0] < ttl_seconds:
                self._data.move_to_end(key)
                return hit[1]
        # Computed outside the lock: a slow query must not block other cache keys
        value = factory()
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            self._data.move_to_end(key)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)
        return value


cache = TTLCache()
