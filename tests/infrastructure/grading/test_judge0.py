from __future__ import annotations

from typing import Any, Mapping

import pytest

from app.application.grading import (
    CodeExecutionProtocolError,
    CodeExecutionRequest,
)
from app.domain.assessment import ExecutionLimits
from app.domain.grading import EvaluationStatus
from app.infrastructure.grading import Judge0CodeExecutionGateway


class FakeJsonTransport:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "url": url,
                "payload": dict(payload),
                "headers": dict(headers),
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


def request() -> CodeExecutionRequest:
    return CodeExecutionRequest(
        source_code="print(input())",
        stdin="hello",
        execution_limits=ExecutionLimits(
            max_runtime_ms=2_000,
            max_memory_kb=128_000,
        ),
    )


def gateway(
    response: Mapping[str, Any],
) -> tuple[Judge0CodeExecutionGateway, FakeJsonTransport]:
    transport = FakeJsonTransport(response)
    return (
        Judge0CodeExecutionGateway(
            base_url="https://judge0.example.test/",
            python_language_id=71,
            transport=transport,
            headers={"X-Test-Key": "secret"},
            request_timeout_seconds=9,
        ),
        transport,
    )


def test_execute_translates_limits_and_python_language_id() -> None:
    adapter, transport = gateway(
        {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": "hello\n",
            "stderr": None,
            "time": "0.125",
        }
    )

    result = adapter.execute(request())

    assert result.status is EvaluationStatus.PASSED
    assert result.stdout == "hello\n"
    assert result.runtime_ms == 125

    call = transport.calls[0]
    assert call["url"] == (
        "https://judge0.example.test/submissions"
        "?base64_encoded=false&wait=true"
    )
    assert call["payload"]["language_id"] == 71
    assert call["payload"]["source_code"] == "print(input())"
    assert call["payload"]["stdin"] == "hello"
    assert call["payload"]["cpu_time_limit"] == 2.0
    assert call["payload"]["wall_time_limit"] == 4.0
    assert call["payload"]["memory_limit"] == 128_000
    assert call["headers"] == {"X-Test-Key": "secret"}
    assert call["timeout_seconds"] == 9


@pytest.mark.parametrize(
    ("status_id", "expected"),
    [
        (3, EvaluationStatus.PASSED),
        (4, EvaluationStatus.FAILED),
        (5, EvaluationStatus.TIMEOUT),
        (6, EvaluationStatus.ERROR),
        (11, EvaluationStatus.ERROR),
        (13, EvaluationStatus.ERROR),
    ],
)
def test_judge0_terminal_statuses_are_normalized(
    status_id: int,
    expected: EvaluationStatus,
) -> None:
    adapter, _ = gateway(
        {
            "status": {"id": status_id, "description": "status"},
            "stdout": "",
            "stderr": "",
            "time": "0.01",
        }
    )

    assert adapter.execute(request()).status is expected


def test_compile_and_runtime_diagnostics_are_combined() -> None:
    adapter, _ = gateway(
        {
            "status": {"id": 6, "description": "Compilation Error"},
            "compile_output": "SyntaxError",
            "stderr": "trace",
            "message": "compiler failed",
            "time": None,
        }
    )

    result = adapter.execute(request())

    assert result.status is EvaluationStatus.ERROR
    assert result.stderr == "SyntaxError\ntrace\ncompiler failed"
    assert result.runtime_ms is None


@pytest.mark.parametrize("status_id", [1, 2])
def test_wait_true_rejects_non_terminal_judge0_status(
    status_id: int,
) -> None:
    adapter, _ = gateway(
        {
            "status": {"id": status_id, "description": "processing"},
        }
    )

    with pytest.raises(
        CodeExecutionProtocolError,
        match="non-terminal",
    ):
        adapter.execute(request())


def test_missing_status_is_protocol_error() -> None:
    adapter, _ = gateway({"stdout": "hello"})

    with pytest.raises(CodeExecutionProtocolError):
        adapter.execute(request())


def test_invalid_runtime_is_protocol_error() -> None:
    adapter, _ = gateway(
        {
            "status": {"id": 3, "description": "Accepted"},
            "time": "not-a-number",
        }
    )

    with pytest.raises(
        CodeExecutionProtocolError,
        match="invalid execution time",
    ):
        adapter.execute(request())


def test_gateway_constructor_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        Judge0CodeExecutionGateway(
            base_url="",
            python_language_id=71,
        )

    with pytest.raises(ValueError):
        Judge0CodeExecutionGateway(
            base_url="https://judge0.example.test",
            python_language_id=0,
        )
