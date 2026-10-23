"""Redaction of secret values and credential patterns (LLD-platform-v2 4.3; SEC-INV-4).

``Redactor`` masks every secret value registered with it and the credential patterns of
PLAT-FR-13. ``RedactingFilter`` applies it to log records and is attached to handlers by
``configure_logging``. ``RedactingStream`` applies it to the daemon's raw stderr.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import urllib.parse
from collections.abc import Iterable
from typing import IO

from research_mcp.platform.secrets import Secret

MASK = "[REDACTED]"

# PLAT-FR-13: `key=`, `api_key=`, `token=` (any name ending in key or token, so also
# `access_token=`), the three credential headers, and the Google and GitHub key prefixes.
# A name and its value may be joined as in a query string, a header, a dict or JSON
# (`key = v`, `"api_key": "v"`) or a raw header tuple (`(b'authorization', b'Bearer v')`).
_JOIN = r"[\"']?\s*(?:[:=]\s*(?:b?[\"'])?|,\s*b?[\"'])"
_ASSIGNMENT = re.compile(r"(?i)((?:key|token)" + _JOIN + r")[^\s&\"',;}]+")
_HEADER = re.compile(
    r"(?i)((?:authorization|x-subscription-token|x-goog-api-key)"
    + _JOIN
    + r"(?:(?:bearer|basic|token)\s+)?)[^\s\"',;&}]+"
)
_PREFIXED = re.compile(r"(?:AIza[0-9A-Za-z_\-]+|ghp_[0-9A-Za-z]+|github_pat_[0-9A-Za-z_]+)")

# Attributes every LogRecord has; anything else on a record came from `extra`.
STANDARD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
        "message",
        "asctime",
    }
)
_NUMBER = (int, float)


def _forms(value: str) -> set[str]:
    """The value as it can appear in text: literal, percent-encoded, JSON or repr escaped."""
    forms = {
        value,
        urllib.parse.quote(value, safe=""),
        urllib.parse.quote(value),
        urllib.parse.quote_plus(value),
        json.dumps(value)[1:-1],
        json.dumps(value, ensure_ascii=False)[1:-1],
        repr(value)[1:-1],
        repr(value.encode())[2:-1],
    }
    forms.discard("")
    return forms


class Redactor:
    """Masks registered secret values and credential patterns in text.

    Values are kept for the life of the process, so a rotated-out key stays masked. Each
    value is matched in its literal, percent-encoded and escaped forms.
    """

    def __init__(self) -> None:
        self._values: set[str] = set()
        self._pattern: re.Pattern[str] | None = None
        self._lock = threading.Lock()

    # @spec SEC-5, SEC-7
    def register(self, secret: Secret | None) -> None:
        """Add a loaded or reloaded secret's value; ``None`` (a missing secret) is ignored."""
        if secret is None:
            return
        value = secret.reveal()
        if not value:
            return
        forms = _forms(value)
        with self._lock:
            if forms <= self._values:
                return
            self._values |= forms
            # Longest first, so a value that contains another is masked whole.
            ordered = sorted(self._values, key=len, reverse=True)
            self._pattern = re.compile("|".join(re.escape(v) for v in ordered))

    # @spec SEC-6
    def redact(self, text: str) -> str:
        pattern = self._pattern
        if pattern is not None:
            text = pattern.sub(MASK, text)
        text = _HEADER.sub(lambda m: m.group(1) + MASK, text)
        text = _ASSIGNMENT.sub(lambda m: m.group(1) + MASK, text)
        return _PREFIXED.sub(MASK, text)


class RedactingFilter(logging.Filter):
    """Rewrites a record's message, args, exception text, stack text and extra fields.

    The message is formatted with its args first and the result masked, so a value split
    across several args is still caught; ``args`` is then empty.
    """

    def __init__(self, redactor: Redactor) -> None:
        super().__init__()
        self.redactor = redactor

    # @spec SEC-5
    def filter(self, record: logging.LogRecord) -> bool:
        redact = self.redactor.redact
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            # Arguments that do not fit the format: keep both parts, masked.
            message = f"{record.msg} {record.args!r}"
        record.msg = redact(message)
        record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        record.exc_info = None
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        for key, value in list(vars(record).items()):
            if key in STANDARD_ATTRS or value is None or isinstance(value, bool):
                continue
            if isinstance(value, _NUMBER):
                # A number keeps its type unless its digits hold a registered value.
                text = str(value)
                masked = redact(text)
                if masked != text:
                    setattr(record, key, masked)
                continue
            setattr(record, key, redact(value if isinstance(value, str) else repr(value)))
        return True


class RedactingStream:
    """A text stream that masks each complete line before passing it on (SEC-INV-4).

    ``daemon.py`` replaces ``sys.stderr`` with it, so tracebacks and library prints that
    never pass a logging handler are masked too. Text is held until a newline or ``flush``,
    so a value written in pieces is masked whole.

    Only the members below exist; nothing is forwarded to the wrapped stream, so ``buffer``,
    ``detach`` and ``reconfigure`` are absent rather than a way around the redactor.
    ``fileno`` is kept for ``faulthandler`` and child processes: descriptor 2 is open to the
    whole process anyway, and what goes through it never passed Python text.
    """

    def __init__(self, stream: IO[str], redactor: Redactor) -> None:
        self._stream = stream
        self._redactor = redactor
        self._pending = ""
        self._lock = threading.Lock()

    # @spec SEC-5
    def write(self, text: str) -> int:
        with self._lock:
            self._pending += text
            head, newline, tail = self._pending.rpartition("\n")
            if newline:
                self._stream.write(self._redactor.redact(head + newline))
                self._pending = tail
        return len(text)

    def writelines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._stream.write(self._redactor.redact(self._pending))
                self._pending = ""
            self._stream.flush()

    def close(self) -> None:
        self.flush()

    @property
    def closed(self) -> bool:
        return bool(self._stream.closed)

    @property
    def encoding(self) -> str:
        return getattr(self._stream, "encoding", None) or "utf-8"

    @property
    def errors(self) -> str | None:
        return getattr(self._stream, "errors", None)

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def isatty(self) -> bool:
        return self._stream.isatty()

    def fileno(self) -> int:
        return self._stream.fileno()
