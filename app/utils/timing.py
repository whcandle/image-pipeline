from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def timed():
    start = time.perf_counter()
    yield lambda: int((time.perf_counter() - start) * 1000)
