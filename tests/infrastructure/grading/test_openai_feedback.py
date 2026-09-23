from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import pytest

from app.application.grading import (
    AIFeedbackProtocolError,
    AIFeedbackRequest,
    AIFeedbackUnavailableError,
)
from app.infrastructure.grading import OpenAIFeedbackGateway


class FakeTransport:
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


def safe_request() -> AIFeedbackRequest:
    return AIFeedbackRequest(
        submission_id=42,
        final_score=Decimal("70.00"),
        io_percentage=Decimal("57.14"),
        unit_percentage=Decimal("100.00"),
        static_percentage=Decimal("100.00"),
        visible_outcomes=(
            "io: visible example: passed; 40/40 points",
        ),
        hidden_total=2,
        hidden_passed=1,
        hidden_failed_or_other=1,
        deterministic_facts=(
            "Passed 1 of 1 visible evaluations.",
            "Passed 1 of 2 hidden evaluations.",
        ),
    )


def test_openai_adapter_uses_responses_api_with_safe_facts() -> None:
    transport = FakeTransport(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "1. Practice edge cases.\n2. Review tests.",
                        }
                    ],
                }
            ]
        }
    )
    gateway = OpenAIFeedbackGateway(
        api_key="test-key",
        model="gpt-5.6-luna",
        transport=transport,
        timeout_seconds=9,
    )

    result = gateway.generate(safe_request())

    assert result.startswith("1. Practice edge cases")
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/responses"
    assert call["payload"]["model"] == "gpt-5.6-luna"
    assert "instructions" in call["payload"]
    assert "input" in call["payload"]
    assert "Authoritative final score: 70.00/100" in call["payload"]["input"]
    assert "hidden edge" not in call["payload"]["input"]
    assert call["headers"] == {
        "Authorization": "Bearer test-key"
    }
    assert call["timeout_seconds"] == 9


def test_adapter_accepts_direct_output_text_when_present() -> None:
    gateway = OpenAIFeedbackGateway(
        api_key="test-key",
        model="gpt-5.6-luna",
        transport=FakeTransport(
            {"output_text": "Focus on boundary conditions."}
        ),
    )

    assert gateway.generate(safe_request()) == (
        "Focus on boundary conditions."
    )


def test_missing_api_key_is_optional_feature_unavailable() -> None:
    gateway = OpenAIFeedbackGateway(
        api_key=None,
        model="gpt-5.6-luna",
        transport=FakeTransport({}),
    )

    with pytest.raises(
        AIFeedbackUnavailableError,
        match="not configured",
    ):
        gateway.generate(safe_request())


def test_response_without_text_is_protocol_error() -> None:
    gateway = OpenAIFeedbackGateway(
        api_key="test-key",
        model="gpt-5.6-luna",
        transport=FakeTransport({"output": []}),
    )

    with pytest.raises(AIFeedbackProtocolError):
        gateway.generate(safe_request())
