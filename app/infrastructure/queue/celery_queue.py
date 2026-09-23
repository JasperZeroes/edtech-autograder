from __future__ import annotations

from typing import Protocol


GRADING_TASK_NAME = "grading.grade_submission"


class CelerySender(Protocol):
    def send_task(
        self,
        name: str,
        args: list[int] | None = None,
        kwargs: dict | None = None,
        **options,
    ):
        ...


class CeleryGradingQueue:
    """Real grading queue adapter backed by Celery."""

    def __init__(
        self,
        celery_app: CelerySender,
        *,
        task_name: str = GRADING_TASK_NAME,
    ) -> None:
        self._celery_app = celery_app
        self._task_name = task_name

    def enqueue(self, submission_id: int) -> None:
        if submission_id <= 0:
            raise ValueError("Submission id must be positive.")

        self._celery_app.send_task(
            self._task_name,
            args=[submission_id],
        )
