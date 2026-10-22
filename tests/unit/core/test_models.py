from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from research_mcp.core.ids import Identifier
from research_mcp.core.models import CallRecord, SearchFilters, WorkRecord
from research_mcp.core.specs import AuthSpec, RateSpec, SourcePolicy
from research_mcp.core.timeutil import SystemClock
from research_mcp.testing.clock import FakeClock, FakeSleeper


async def test_models_and_clock():
    """AT-PLAT-06: Policy/data types validate and fake time advances deterministically."""
    auth = AuthSpec(("API_KEY",), True, "header", "x-api-key", ("https://example.org",), "")
    policy = SourcePolicy("example", frozenset({"example.org"}), auth, RateSpec(1), 5, 1000)
    assert policy.rate.burst == 1 and policy.auth == auth
    with pytest.raises(FrozenInstanceError):
        policy.source = "changed"
    for origin in [
        "https://example.org/path",
        "https://user@example.org",
        "file://host",
        "host",
        "https://example.org?",
        "https://example.org:bad",
        "https://exa\nmple.org",
    ]:
        with pytest.raises(ValueError):
            AuthSpec((), True, "header", "key", (origin,), "")
    for bounds in [{"year_from": 1799}, {"year_to": 2101}, {"year_from": 2025, "year_to": 2020}]:
        with pytest.raises(ValidationError):
            SearchFilters(**bounds)
    assert SearchFilters(year_from=1800, year_to=2100).oa_only is False
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(1.5)
    sleeper = FakeSleeper(clock)
    await sleeper.sleep(2)
    assert sleeper.sleeps == [2]
    assert (clock.now() - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds() == 3.5
    assert SystemClock().now().tzinfo is UTC
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 1, 1))
    record = WorkRecord(
        ids=[Identifier("doi", "10.1234/test")],
        title="Study",
        provenance={
            "source": "arxiv",
            "upstream_id": "1",
            "adapter_version": "1",
            "retrieved_at": clock.now(),
        },
        extra={"nested": [True, None, {"number": 1}]},
    )
    assert WorkRecord.model_validate_json(record.model_dump_json()) == record
    call = CallRecord(
        ts=clock.now(),
        source="arxiv",
        op="search",
        status=200,
        error_code=None,
        latency_ms=1,
        bytes=100,
        rl_remaining=None,
        rl_reset=None,
        cred_expires_at=None,
        correlation_id=None,
        attempt=1,
    )
    assert CallRecord.model_validate_json(call.model_dump_json()) == call
    with pytest.raises(ValidationError):
        CallRecord.model_validate({"ts": "invalid"})
