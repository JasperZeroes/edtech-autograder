from __future__ import annotations

from typing import Protocol

from app.domain.assessment import AssignmentRepository, StaticAnalysisRules
from app.domain.grading import ExecutionOutcome, GradingResultRepository
from app.domain.submission import SubmissionRepository

from .requests import CodeExecutionRequest, SourceAnalysisReport


class CodeExecutionGateway(Protocol):
    """Runs untrusted code only through an isolated execution boundary."""

    def execute(self, request: CodeExecutionRequest) -> ExecutionOutcome:
        ...


class SourceAnalyzer(Protocol):
    """Performs non-executing static inspection of submitted Python code."""

    def analyze(
        self,
        *,
        source_code: str,
        rules: StaticAnalysisRules,
    ) -> SourceAnalysisReport:
        ...


class GradingUnitOfWork(Protocol):
    assignments: AssignmentRepository
    submissions: SubmissionRepository
    grading_results: GradingResultRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
