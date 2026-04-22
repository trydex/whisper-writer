import threading
from collections import deque
from datetime import datetime


class TranscriptionHistory:
    def __init__(self, maxlen=10):
        self._items = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, text):
        if not text or not text.strip():
            return
        with self._lock:
            self._items.append((datetime.now(), text))

    def snapshot(self):
        with self._lock:
            return list(self._items)

    def last(self):
        with self._lock:
            if not self._items:
                return None
            return self._items[-1][1]

    def clear(self):
        with self._lock:
            self._items.clear()

    def __len__(self):
        with self._lock:
            return len(self._items)
