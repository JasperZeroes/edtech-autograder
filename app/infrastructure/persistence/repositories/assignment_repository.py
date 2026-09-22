from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.assessment import (
    Assignment,
    AssignmentRepository,
    AssignmentStatus,
    ExecutionLimits,
    GradingPolicy,
    GradingTestVisibility,
    IOTestCase,
    StaticAnalysisRules,
    UnitTestSpecification,
)
from app.infrastructure.persistence.models import (
    AssignmentModel,
    IOTestCaseModel,
    StaticAnalysisRulesModel,
    UnitTestSpecificationModel,
)


class AssignmentPersistenceError(RuntimeError):
    """Raised when persisted assessment state cannot be reconciled."""


class SqlAlchemyAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, assignment_id: int) -> Assignment | None:
        model = self._session.scalar(
            self._base_query().where(AssignmentModel.id == assignment_id)
        )
        return self._to_domain(model) if model is not None else None

    def list_by_instructor(self, instructor_id: int) -> list[Assignment]:
        models = self._session.scalars(
            self._base_query()
            .where(AssignmentModel.instructor_id == instructor_id)
            .order_by(AssignmentModel.id)
        ).all()
        return [self._to_domain(model) for model in models]

    def list_published(self) -> list[Assignment]:
        models = self._session.scalars(
            self._base_query()
            .where(AssignmentModel.status == AssignmentStatus.PUBLISHED.value)
            .order_by(AssignmentModel.id)
        ).all()
        return [self._to_domain(model) for model in models]

    def save(self, assignment: Assignment) -> Assignment:
        if assignment.id is None:
            model = AssignmentModel()
            self._session.add(model)
        else:
            model = self._session.scalar(
                self._base_query().where(
                    AssignmentModel.id == assignment.id
                )
            )
            if model is None:
                raise AssignmentPersistenceError(
                    f"Cannot update assignment {assignment.id}: "
                    "persistence record does not exist."
                )

        self._apply_aggregate(assignment, model)
        self._session.flush()
        self._sync_domain_ids(assignment, model)
        return assignment

    @staticmethod
    def _base_query():
        return select(AssignmentModel).options(
            selectinload(AssignmentModel.io_test_cases),
            selectinload(AssignmentModel.unit_test_spec),
            selectinload(AssignmentModel.static_analysis_rules),
        )

    def _apply_aggregate(
        self,
        assignment: Assignment,
        model: AssignmentModel,
    ) -> None:
        model.instructor_id = assignment.instructor_id
        model.title = assignment.title
        model.description = assignment.description
        model.instructions = assignment.instructions
        model.language = assignment.language
        model.status = assignment.status.value

        model.io_weight = assignment.grading_policy.io_weight
        model.unit_weight = assignment.grading_policy.unit_weight
        model.static_weight = assignment.grading_policy.static_weight

        model.max_runtime_ms = assignment.execution_limits.max_runtime_ms
        model.max_memory_kb = assignment.execution_limits.max_memory_kb

        self._apply_io_tests(assignment, model)
        self._apply_unit_test(assignment, model)
        self._apply_static_rules(assignment, model)

    def _apply_io_tests(
        self,
        assignment: Assignment,
        model: AssignmentModel,
    ) -> None:
        existing_by_id = {
            test.id: test
            for test in model.io_test_cases
            if test.id is not None
        }
        next_models: list[IOTestCaseModel] = []

        for test_case in assignment.io_test_cases:
            if test_case.id is None:
                test_model = IOTestCaseModel()
            else:
                test_model = existing_by_id.get(test_case.id)
                if test_model is None:
                    raise AssignmentPersistenceError(
                        f"IO test case {test_case.id} does not belong "
                        f"to assignment {assignment.id}."
                    )

            test_model.name = test_case.name
            test_model.stdin = test_case.stdin
            test_model.expected_stdout = test_case.expected_stdout
            test_model.points = test_case.points
            test_model.visibility = test_case.visibility.value
            test_model.order_index = test_case.order_index
            next_models.append(test_model)

        model.io_test_cases = next_models

    @staticmethod
    def _apply_unit_test(
        assignment: Assignment,
        model: AssignmentModel,
    ) -> None:
        specification = assignment.unit_test_spec

        if specification is None:
            model.unit_test_spec = None
            return

        existing = model.unit_test_spec
        if specification.id is None:
            unit_model = existing or UnitTestSpecificationModel()
        elif existing is not None and existing.id == specification.id:
            unit_model = existing
        else:
            raise AssignmentPersistenceError(
                f"Unit-test specification {specification.id} does not belong "
                f"to assignment {assignment.id}."
            )

        unit_model.name = specification.name
        unit_model.test_code = specification.test_code
        unit_model.points = specification.points
        unit_model.visibility = specification.visibility.value
        model.unit_test_spec = unit_model

    @staticmethod
    def _apply_static_rules(
        assignment: Assignment,
        model: AssignmentModel,
    ) -> None:
        rules = assignment.static_analysis_rules

        if rules is None:
            model.static_analysis_rules = None
            return

        existing = model.static_analysis_rules
        if rules.id is None:
            static_model = existing or StaticAnalysisRulesModel()
        elif existing is not None and existing.id == rules.id:
            static_model = existing
        else:
            raise AssignmentPersistenceError(
                f"Static-analysis rules {rules.id} do not belong "
                f"to assignment {assignment.id}."
            )

        static_model.required_functions = list(rules.required_functions)
        static_model.forbidden_imports = list(rules.forbidden_imports)
        static_model.max_cyclomatic_complexity = (
            rules.max_cyclomatic_complexity
        )
        static_model.points = rules.points
        model.static_analysis_rules = static_model

    @staticmethod
    def _sync_domain_ids(
        assignment: Assignment,
        model: AssignmentModel,
    ) -> None:
        assignment.id = model.id

        if len(assignment.io_test_cases) != len(model.io_test_cases):
            raise AssignmentPersistenceError(
                "Persisted IO test count does not match the aggregate."
            )

        assignment.io_test_cases = [
            IOTestCase(
                id=persisted.id,
                name=test.name,
                stdin=test.stdin,
                expected_stdout=test.expected_stdout,
                points=test.points,
                visibility=test.visibility,
                order_index=test.order_index,
            )
            for test, persisted in zip(
                assignment.io_test_cases,
                model.io_test_cases,
                strict=True,
            )
        ]

        if assignment.unit_test_spec is not None:
            persisted = model.unit_test_spec
            if persisted is None:
                raise AssignmentPersistenceError(
                    "Unit-test specification was not persisted."
                )
            spec = assignment.unit_test_spec
            assignment.unit_test_spec = UnitTestSpecification(
                id=persisted.id,
                name=spec.name,
                test_code=spec.test_code,
                points=spec.points,
                visibility=spec.visibility,
            )

        if assignment.static_analysis_rules is not None:
            persisted = model.static_analysis_rules
            if persisted is None:
                raise AssignmentPersistenceError(
                    "Static-analysis rules were not persisted."
                )
            rules = assignment.static_analysis_rules
            assignment.static_analysis_rules = StaticAnalysisRules(
                id=persisted.id,
                required_functions=rules.required_functions,
                forbidden_imports=rules.forbidden_imports,
                max_cyclomatic_complexity=rules.max_cyclomatic_complexity,
                points=rules.points,
            )

    @staticmethod
    def _to_domain(model: AssignmentModel) -> Assignment:
        return Assignment(
            id=model.id,
            instructor_id=model.instructor_id,
            title=model.title,
            description=model.description,
            instructions=model.instructions,
            language=model.language,
            status=AssignmentStatus(model.status),
            grading_policy=GradingPolicy(
                io_weight=model.io_weight,
                unit_weight=model.unit_weight,
                static_weight=model.static_weight,
            ),
            execution_limits=ExecutionLimits(
                max_runtime_ms=model.max_runtime_ms,
                max_memory_kb=model.max_memory_kb,
            ),
            io_test_cases=[
                IOTestCase(
                    id=test.id,
                    name=test.name,
                    stdin=test.stdin,
                    expected_stdout=test.expected_stdout,
                    points=test.points,
                    visibility=GradingTestVisibility(test.visibility),
                    order_index=test.order_index,
                )
                for test in model.io_test_cases
            ],
            unit_test_spec=(
                UnitTestSpecification(
                    id=model.unit_test_spec.id,
                    name=model.unit_test_spec.name,
                    test_code=model.unit_test_spec.test_code,
                    points=model.unit_test_spec.points,
                    visibility=GradingTestVisibility(
                        model.unit_test_spec.visibility
                    ),
                )
                if model.unit_test_spec is not None
                else None
            ),
            static_analysis_rules=(
                StaticAnalysisRules(
                    id=model.static_analysis_rules.id,
                    required_functions=tuple(
                        model.static_analysis_rules.required_functions
                    ),
                    forbidden_imports=tuple(
                        model.static_analysis_rules.forbidden_imports
                    ),
                    max_cyclomatic_complexity=(
                        model.static_analysis_rules.max_cyclomatic_complexity
                    ),
                    points=model.static_analysis_rules.points,
                )
                if model.static_analysis_rules is not None
                else None
            ),
        )
