from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.application.grading import (
    CodeExecutionProtocolError,
    CodeExecutionRequest,
    CodeExecutionUnavailableError,
)
from app.domain.grading import EvaluationStatus, ExecutionOutcome


class JsonTransport(Protocol):
    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        ...


class UrllibJsonTransport:
    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        body = json.dumps(dict(payload)).encode("utf-8")
        request = Request(
            url=url,
            data=body,
            headers={
                "Content-Type": "application/json",
                **dict(headers),
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise CodeExecutionUnavailableError(
                "Judge0 execution service is unavailable."
            ) from exc

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CodeExecutionProtocolError(
                "Judge0 returned a non-JSON response."
            ) from exc

        if not isinstance(decoded, dict):
            raise CodeExecutionProtocolError(
                "Judge0 returned an unexpected response shape."
            )

        return decoded


@dataclass(frozen=True, slots=True)
class _Judge0Status:
    id: int
    description: str


class Judge0CodeExecutionGateway:
    """Synchronous Judge0 adapter for isolated untrusted-code execution."""

    def __init__(
        self,
        *,
        base_url: str,
        python_language_id: int,
        transport: JsonTransport | None = None,
        headers: Mapping[str, str] | None = None,
        request_timeout_seconds: float = 20.0,
    ) -> None:
        normalized = base_url.rstrip("/")
        if not normalized:
            raise ValueError("Judge0 base URL must not be blank.")
        if python_language_id <= 0:
            raise ValueError("Judge0 Python language id must be positive.")
        if request_timeout_seconds <= 0:
            raise ValueError("Judge0 request timeout must be positive.")

        self._base_url = normalized
        self._python_language_id = python_language_id
        self._transport = transport or UrllibJsonTransport()
        self._headers = dict(headers or {})
        self._request_timeout_seconds = request_timeout_seconds

    def execute(self, request: CodeExecutionRequest) -> ExecutionOutcome:
        runtime_seconds = request.execution_limits.max_runtime_ms / 1000
        wall_seconds = max(runtime_seconds * 2, runtime_seconds + 1)

        payload: dict[str, Any] = {
            "source_code": request.source_code,
            "language_id": self._python_language_id,
            "cpu_time_limit": runtime_seconds,
            "wall_time_limit": wall_seconds,
            "memory_limit": request.execution_limits.max_memory_kb,
        }
        if request.stdin is not None:
            payload["stdin"] = request.stdin

        response = self._transport.post_json(
            url=(
                f"{self._base_url}/submissions"
                "?base64_encoded=false&wait=true"
            ),
            payload=payload,
            headers=self._headers,
            timeout_seconds=self._request_timeout_seconds,
        )

        status = self._parse_status(response)
        evaluation_status = self._map_status(status)

        stderr = self._combine_error_fields(response)
        runtime_ms = self._parse_runtime_ms(response.get("time"))

        return ExecutionOutcome(
            status=evaluation_status,
            stdout=self._text(response.get("stdout")),
            stderr=stderr,
            runtime_ms=runtime_ms,
        )

    @staticmethod
    def _parse_status(response: Mapping[str, Any]) -> _Judge0Status:
        raw_status = response.get("status")
        if not isinstance(raw_status, Mapping):
            raise CodeExecutionProtocolError(
                "Judge0 response is missing status information."
            )

        status_id = raw_status.get("id")
        description = raw_status.get("description")

        if not isinstance(status_id, int):
            raise CodeExecutionProtocolError(
                "Judge0 status id is invalid."
            )
        if not isinstance(description, str):
            description = ""

        return _Judge0Status(
            id=status_id,
            description=description,
        )

    @staticmethod
    def _map_status(status: _Judge0Status) -> EvaluationStatus:
        if status.id == 3:
            return EvaluationStatus.PASSED

        if status.id == 5:
            return EvaluationStatus.TIMEOUT

        # With wait=true, queue/processing statuses should not be terminal.
        if status.id in {1, 2}:
            raise CodeExecutionProtocolError(
                "Judge0 returned a non-terminal status while wait=true."
            )

        # Compilation, runtime, internal and execution-format errors are
        # normalized as deterministic execution errors.
        if status.id >= 6:
            return EvaluationStatus.ERROR

        # Wrong Answer can occur on Judge0 when expected_output is supplied.
        # This gateway does not supply it, but normalize defensively.
        if status.id == 4:
            return EvaluationStatus.FAILED

        raise CodeExecutionProtocolError(
            f"Judge0 returned unknown status id {status.id}."
        )

    @staticmethod
    def _combine_error_fields(response: Mapping[str, Any]) -> str:
        parts = [
            Judge0CodeExecutionGateway._text(
                response.get("compile_output")
            ).strip(),
            Judge0CodeExecutionGateway._text(
                response.get("stderr")
            ).strip(),
            Judge0CodeExecutionGateway._text(
                response.get("message")
            ).strip(),
        ]
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _parse_runtime_ms(value: Any) -> int | None:
        if value is None or value == "":
            return None

        try:
            seconds = float(value)
        except (TypeError, ValueError) as exc:
            raise CodeExecutionProtocolError(
                "Judge0 returned an invalid execution time."
            ) from exc

        if seconds < 0:
            raise CodeExecutionProtocolError(
                "Judge0 returned a negative execution time."
            )

        return round(seconds * 1000)

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        return str(value)
