from __future__ import annotations

from app.application.grading import GradeSubmission
from app.config import get_database_settings
from app.infrastructure.grading import (
    Judge0CodeExecutionGateway,
    PythonSourceAnalyzer,
)
from app.infrastructure.grading.settings import get_grading_settings
from app.infrastructure.persistence import (
    SqlAlchemyGradingUnitOfWork,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.queue.celery_app import celery_app
from app.infrastructure.queue.celery_queue import GRADING_TASK_NAME


def run_grade_submission(submission_id: int) -> dict[str, int | bool]:
    database_settings = get_database_settings()
    grading_settings = get_grading_settings()

    engine = create_database_engine(database_settings.database_url)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            workflow = GradeSubmission(
                unit_of_work=SqlAlchemyGradingUnitOfWork(session),
                execution_gateway=Judge0CodeExecutionGateway(
                    base_url=grading_settings.judge0_base_url,
                    python_language_id=(
                        grading_settings.judge0_python_language_id
                    ),
                    request_timeout_seconds=(
                        grading_settings.judge0_request_timeout_seconds
                    ),
                ),
                source_analyzer=PythonSourceAnalyzer(),
            )
            outcome = workflow.execute(submission_id=submission_id)

            return {
                "submission_id": submission_id,
                "grading_result_id": outcome.stored_result.id,
                "already_completed": outcome.was_already_completed,
            }
    finally:
        engine.dispose()


@celery_app.task(name=GRADING_TASK_NAME)
def grade_submission_task(
    submission_id: int,
) -> dict[str, int | bool]:
    return run_grade_submission(submission_id)
