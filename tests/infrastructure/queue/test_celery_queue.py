from app.infrastructure.queue.celery_queue import (
    GRADING_TASK_NAME,
    CeleryGradingQueue,
)


class FakeCeleryApp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[int] | None]] = []

    def send_task(
        self,
        name: str,
        args: list[int] | None = None,
        kwargs=None,
        **options,
    ):
        self.calls.append((name, args))


def test_celery_queue_dispatches_submission_id_by_task_name() -> None:
    app = FakeCeleryApp()
    queue = CeleryGradingQueue(app)

    queue.enqueue(42)

    assert app.calls == [(GRADING_TASK_NAME, [42])]


def test_celery_queue_rejects_invalid_submission_id() -> None:
    app = FakeCeleryApp()
    queue = CeleryGradingQueue(app)

    try:
        queue.enqueue(0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
