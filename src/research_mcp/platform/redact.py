"""Redaction of secret values and credential patterns (LLD-platform-v2 4.3; SEC-INV-4).

``Redactor`` masks every secret value registered with it and the credential patterns of
PLAT-FR-13. ``RedactingFilter`` applies it to log records and is attached to handlers by
``configure_logging``. ``RedactingStream`` applies it to the daemon's raw stderr.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import IO, Any

from research_mcp.platform.secrets import Secret

MASK = "[REDACTED]"

# PLAT-FR-13: `key=`, `api_key=`, `token=` (any name ending in key or token, so also
# `access_token=`), the three credential headers in header, dict and JSON forms, and the
# Google and GitHub key prefixes.
_ASSIGNMENT = re.compile(r"(?i)((?:key|token)=)[^\s&\"',;]+")
_HEADER = re.compile(
    r"(?i)((?:authorization|x-subscription-token|x-goog-api-key)[\"']?\s*[:=]\s*[\"']?"
    r"(?:(?:bearer|basic|token)\s+)?)[^\s\"',;&}]+"
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
_PLAIN = (int, float, bool, type(None))


class Redactor:
    """Masks registered secret values and credential patterns in text.

    Values are kept for the life of the process, so a rotated-out key stays masked.
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
        with self._lock:
            if value in self._values:
                return
            self._values.add(value)
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
            if key in STANDARD_ATTRS or isinstance(value, _PLAIN):
                continue
            setattr(record, key, redact(value if isinstance(value, str) else repr(value)))
        return True


class RedactingStream:
    """A text stream that masks each complete line before passing it on (SEC-INV-4).

    ``daemon.py`` replaces ``sys.stderr`` with it, so tracebacks and library prints that
    never pass a logging handler are masked too. Text is held until a newline or ``flush``,
    so a value written in pieces is masked whole.
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

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._stream.write(self._redactor.redact(self._pending))
                self._pending = ""
            self._stream.flush()

    def writable(self) -> bool:
        return True

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)
