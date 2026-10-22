"""Bounded typed output and authenticated opaque cursors."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel, ValidationError

from research_mcp.core.envelope import ToolResult
from research_mcp.core.errors import ErrorCode, ToolError
from research_mcp.core.models import JsonValue

_MARKER = "[truncated]"
_PROTECTED = frozenset({"statuses", "source_status", "next_cursor", "source", "untrusted"})
_TEXT = frozenset({"text", "content", "abstract", "title", "description"})


def _targets(value: Any) -> Iterator[tuple[Any, str | int]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _PROTECTED:
                continue
            if isinstance(child, list) or (key in _TEXT and isinstance(child, str)):
                yield value, key
            yield from _targets(value[key])
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _targets(child)
            if isinstance(child, str):
                yield value, index


def fit[T](result: ToolResult[T], limit_bytes: int) -> ToolResult[T]:
    """Return a validated copy; metadata that cannot fit raises TOO_LARGE."""
    if len(result.model_dump_json().encode("utf-8")) <= limit_bytes:
        return result.model_copy(deep=True)
    payload = result.model_dump(mode="json")
    payload["truncated"] = True
    # Only data is reducible: warnings and envelope metadata remain intact.
    wrapper = {"content": payload["data"]}
    for parent, key in _targets(wrapper):
        original = parent[key]
        valid = original
        prefixes = range(len(original) - 1, -1, -1) if isinstance(original, list) else [0]
        for length in prefixes:
            replacement = original[:length] if isinstance(original, list) else _MARKER
            if len(json.dumps(replacement)) >= len(json.dumps(original)):
                continue
            parent[key] = replacement
            payload["data"] = wrapper["content"]
            try:
                candidate_payload = dict(payload)
                if isinstance(result.data, BaseModel):
                    candidate_payload["data"] = type(result.data).model_validate(payload["data"])
                candidate = type(result).model_validate(candidate_payload)
            except ValidationError:
                # Invalid prefixes are not evidence that a smaller one fits the schema.
                parent[key] = valid
                continue
            valid = replacement
            if len(candidate.model_dump_json().encode("utf-8")) <= limit_bytes:
                return candidate
        # Keep only a validated reduction for the next field.
    raise ToolError(ErrorCode.TOO_LARGE, "Mandatory result metadata exceeds the byte budget")


class Budget:
    fit = staticmethod(fit)


def encode_cursor(payload: dict[str, JsonValue], key: bytes) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
    tag = hmac.digest(key, body, hashlib.sha256)
    return base64.urlsafe_b64encode(body + tag).rstrip(b"=").decode("ascii")


def decode_cursor(cursor: str, key: bytes) -> dict[str, JsonValue]:
    try:
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        body, tag = raw[:-32], raw[-32:]
        if len(tag) != 32 or not hmac.compare_digest(tag, hmac.digest(key, body, hashlib.sha256)):
            raise ValueError("Invalid signature")
        payload: dict[str, JsonValue] = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Expected cursor object")
        return payload
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ToolError(ErrorCode.INVALID_ARGUMENT, "Invalid cursor") from exc
