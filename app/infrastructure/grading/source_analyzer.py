from __future__ import annotations

import ast

from radon.complexity import cc_visit

from app.application.grading import SourceAnalysisReport
from app.domain.assessment import StaticAnalysisRules


class PythonSourceAnalyzer:
    """Static Python inspection without executing submitted source code."""

    def analyze(
        self,
        *,
        source_code: str,
        rules: StaticAnalysisRules,
    ) -> SourceAnalysisReport:
        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            return SourceAnalysisReport(
                syntax_valid=False,
                missing_required_functions=rules.required_functions,
                forbidden_imports_found=(),
                observed_max_cyclomatic_complexity=None,
                max_cyclomatic_complexity_allowed=(
                    rules.max_cyclomatic_complexity
                ),
                syntax_error=self._format_syntax_error(exc),
            )

        function_names = self._function_names(tree)
        imported_modules = self._imported_modules(tree)

        missing_functions = tuple(
            name
            for name in rules.required_functions
            if name not in function_names
        )

        forbidden_found = tuple(
            name
            for name in rules.forbidden_imports
            if self._matches_import(name, imported_modules)
        )

        observed_complexity = self._max_complexity(source_code)

        return SourceAnalysisReport(
            syntax_valid=True,
            missing_required_functions=missing_functions,
            forbidden_imports_found=forbidden_found,
            observed_max_cyclomatic_complexity=observed_complexity,
            max_cyclomatic_complexity_allowed=(
                rules.max_cyclomatic_complexity
            ),
        )

    @staticmethod
    def _function_names(tree: ast.AST) -> set[str]:
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        }

    @staticmethod
    def _imported_modules(tree: ast.AST) -> set[str]:
        modules: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module)

        return modules

    @staticmethod
    def _matches_import(
        forbidden: str,
        imported_modules: set[str],
    ) -> bool:
        return any(
            module == forbidden
            or module.startswith(f"{forbidden}.")
            for module in imported_modules
        )

    @staticmethod
    def _max_complexity(source_code: str) -> int:
        blocks = cc_visit(source_code)
        if not blocks:
            return 0
        return max(block.complexity for block in blocks)

    @staticmethod
    def _format_syntax_error(exc: SyntaxError) -> str:
        location = (
            f"line {exc.lineno}"
            if exc.lineno is not None
            else "unknown line"
        )
        message = exc.msg or "invalid syntax"
        return f"{message} ({location})"
