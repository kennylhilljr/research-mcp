from typing import Annotated

import pytest
from pydantic import Field

from research_mcp.core.budget import Budget, decode_cursor, encode_cursor, fit
from research_mcp.core.envelope import SourceStatus, ToolResult, Untrusted
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.models import FederatedResult, Work


def test_budget():
    """AT-PLAT-31: Trim list tails and text by bytes while preserving cursors."""
    original = ToolResult[list[int]](data=list(range(100)), next_cursor="opaque")
    result = fit(original, 150)
    assert result.truncated and result.next_cursor == "opaque"
    assert result.data == original.data[: len(result.data)]
    assert 0 < len(result.data) < 100
    assert len(result.model_dump_json().encode()) <= 150
    assert not original.truncated and len(original.data) == 100
    text = ToolResult(data=Untrusted(source="arxiv", content="研究" * 100))
    trimmed = Budget.fit(text, 180)
    assert trimmed.data.content == "[truncated]"
    assert trimmed.data.untrusted and trimmed.data.source == "arxiv"
    assert len(trimmed.model_dump_json().encode()) <= 180
    assert not fit(original, 1000).truncated


def test_statuses_are_mandatory():
    """AT-PLAT-31: Both source-status locations survive trimming and cannot be dropped."""
    statuses = [SourceStatus(source="arxiv", state="ok", count=1)]
    work = Work(
        ids=[],
        title="x" * 1000,
        authors=[],
        year=None,
        venue=None,
        work_type="article",
        abstract=None,
        oa_locations=[],
        found_in=["arxiv"],
    )
    original = ToolResult(
        data=FederatedResult(works=[work], statuses=statuses, next_cursor="inner"),
        source_status=statuses,
        next_cursor="outer",
    )
    result = fit(original, 500)
    assert result.data.statuses == statuses and result.source_status == statuses
    assert result.data.next_cursor == "inner" and result.next_cursor == "outer"
    with pytest.raises(ToolError) as exc:
        fit(original, 10)
    assert exc.value.code == ErrorCode.TOO_LARGE


def test_invalid_prefix_is_not_a_size_result():
    """AT-PLAT-31: Invalid short prefixes cannot masquerade as fitting results."""
    result = ToolResult[Annotated[list[str], Field(min_length=2)]](data=["a" * 500] * 3)
    trimmed = fit(result, 180)
    assert len(trimmed.data) == 2 and trimmed.truncated
    assert len(trimmed.model_dump_json().encode()) <= 180
    with pytest.raises(ToolError):
        fit(result, 50)


def test_cursors():
    """AT-PLAT-34: Signed cursors reject tampering, foreign keys and malformed input."""
    key = b"test-only-key"
    payload = {"offset": 4, "source": "arxiv"}
    cursor = encode_cursor(payload, key)
    assert decode_cursor(cursor, key) == payload
    for value, supplied_key in [
        (cursor, b"foreign"),
        ("A" + cursor[1:], key),
        ("!", key),
        ("", key),
        ("研究", key),
    ]:
        with pytest.raises(ToolError) as exc:
            decode_cursor(value, supplied_key)
        assert exc.value.code == ErrorCode.INVALID_ARGUMENT
