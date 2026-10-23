"""Redactor, RedactingFilter and RedactingStream (LLD-platform-v2 4.3)."""

from __future__ import annotations

import io
import logging
import sys

import pytest

from research_mcp.platform.redact import MASK, RedactingFilter, RedactingStream, Redactor
from research_mcp.platform.secrets import Secret, SecretRef

# Generated for these tests; not real credentials.
VALUE = "tv-9c2e41f7d0-k3y"
OTHER = "tv-0aa7c3e5b1-tok"


def secret(name: str, value: str) -> Secret:
    return Secret(SecretRef.parse(f"keychain:research-mcp/{name}"), value)


def make_record(msg: object, *args: object, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("research_mcp.test", logging.INFO, __file__, 1, msg, args, None)
    record.__dict__.update(extra)
    return record


def test_registered_values_are_masked_in_text() -> None:
    """@spec SEC-5: Registered secret values are masked wherever they appear in text."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    redactor.register(None)  # a missing credential registers nothing
    assert redactor.redact(f"calling with {VALUE} and again{VALUE}.") == (
        f"calling with {MASK} and again{MASK}."
    )
    assert VALUE not in redactor.redact(f"prefix{VALUE}suffix")


def test_rotated_out_value_stays_masked() -> None:
    """@spec SEC-5: A value replaced by a reload stays masked for the life of the process."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    redactor.register(secret("CORE_API_KEY", OTHER))
    text = redactor.redact(f"old {VALUE} new {OTHER}")
    assert VALUE not in text
    assert OTHER not in text


def test_filter_masks_message_args_and_exception_text() -> None:
    """@spec SEC-5: The filter rewrites the message, its args and the exception text."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    try:
        raise RuntimeError(f"upstream refused {VALUE}")
    except RuntimeError:
        exc_info = sys.exc_info()
    record = make_record("sent %s to %r", VALUE, {"secret": VALUE}, url=f"https://h/?q={VALUE}")
    record.exc_info = exc_info
    record.stack_info = f"stack with {VALUE}"

    assert RedactingFilter(redactor).filter(record)

    formatted = logging.Formatter().format(record)
    assert VALUE not in formatted
    assert "upstream refused" in formatted
    assert record.getMessage() == f"sent {MASK} to {{'secret': '{MASK}'}}"
    assert VALUE not in str(record.__dict__)


def test_filter_masks_values_split_across_args() -> None:
    """@spec SEC-5: A value assembled from several args is masked after formatting."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    record = make_record("%s%s", VALUE[:6], VALUE[6:])
    RedactingFilter(redactor).filter(record)
    assert record.getMessage() == MASK


def test_filter_masks_non_text_extra_fields() -> None:
    """@spec SEC-5: Extra fields that are not text are rendered and masked."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    record = make_record("request", headers={"X-Key": VALUE}, attempt=2)
    RedactingFilter(redactor).filter(record)
    assert VALUE not in str(record.__dict__["headers"])
    assert record.__dict__["attempt"] == 2


def test_filter_survives_a_broken_format_string() -> None:
    """@spec SEC-5: A message whose args do not fit is still masked, not dropped."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    record = make_record(f"bad %d {VALUE}", "not a number")
    assert RedactingFilter(redactor).filter(record)
    assert VALUE not in record.getMessage()


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("GET https://api.core.ac.uk/v3/search?q=x&key=abc123SECRET&page=2", "page=2"),
        ("GET https://api.openalex.org/works?api_key=abc123SECRET", "openalex"),
        ("url https://h.example/cb?access_token=abc123SECRET done", "done"),
        ("form token=abc123SECRET&x=1", "x=1"),
        ("Authorization: Bearer abc123SECRET", "Authorization"),
        ("{'authorization': 'token abc123SECRET'}", "authorization"),
        ('{"Authorization": "Basic abc123SECRET"}', "Authorization"),
        ("X-Subscription-Token: abc123SECRET", "X-Subscription-Token"),
        ("headers={'x-goog-api-key': 'abc123SECRET'}", "x-goog-api-key"),
        ("key AIzaSyabc123SECRET_-xyz in text", "in text"),
        ("ghp_abc123SECRETabc123SECRETabc123SE pushed", "pushed"),
        ("github_pat_11ABC_abc123SECRET then", "then"),
    ],
)
def test_credential_patterns_are_masked(text: str, kept: str) -> None:
    """@spec SEC-6: The credential patterns of PLAT-FR-13 are masked without registration."""
    redacted = Redactor().redact(text)
    assert "abc123SECRET" not in redacted
    assert MASK in redacted
    assert kept in redacted


def test_text_without_credentials_is_unchanged() -> None:
    """@spec SEC-6: Text with no credential pattern passes through unchanged."""
    text = "search q=graph neural networks sources=arxiv,crossref status=200"
    assert Redactor().redact(text) == text


def test_redacting_stream_masks_complete_lines() -> None:
    """@spec SEC-5: Text written to the replaced stderr is masked, even when split mid-value."""
    redactor = Redactor()
    redactor.register(secret("CORE_API_KEY", VALUE))
    target = io.StringIO()
    stream = RedactingStream(target, redactor)
    for char in f"Traceback: {VALUE}\n":
        stream.write(char)
    stream.write(f"tail {VALUE[:4]}")
    stream.write(f"{VALUE[4:]} end")
    assert target.getvalue() == f"Traceback: {MASK}\n"
    stream.flush()
    assert target.getvalue() == f"Traceback: {MASK}\ntail {MASK} end"
    assert stream.writable()
