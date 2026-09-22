import pytest

from app.domain.submission import SourceCode, SubmissionValidationError


def test_source_code_preserves_content_and_exposes_metadata() -> None:
    source = SourceCode("print('hello')\nprint('world')\n")

    assert source.content == "print('hello')\nprint('world')\n"
    assert source.line_count == 2
    assert source.byte_size == len(source.content.encode("utf-8"))
    assert len(source.checksum) == 64


def test_source_code_checksum_is_deterministic() -> None:
    first = SourceCode("print('hello')")
    second = SourceCode("print('hello')")

    assert first.checksum == second.checksum


@pytest.mark.parametrize("content", ["", "   ", "\n\t\n"])
def test_blank_source_code_is_rejected(content: str) -> None:
    with pytest.raises(SubmissionValidationError):
        SourceCode(content)
