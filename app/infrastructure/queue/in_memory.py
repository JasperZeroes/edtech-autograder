from __future__ import annotations

from collections import deque
from threading import Lock


class InMemoryGradingQueue:
    """Development-only queue replaced by Celery in the grading worker slice."""

    def __init__(self) -> None:
        self._submission_ids: deque[int] = deque()
        self._lock = Lock()

    def enqueue(self, submission_id: int) -> None:
        if submission_id <= 0:
            raise ValueError("Submission id must be positive.")

        with self._lock:
            self._submission_ids.append(submission_id)

    def pending_ids(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(self._submission_ids)
