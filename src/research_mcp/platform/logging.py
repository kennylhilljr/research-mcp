"""Structured logging, query hashing and stderr log rotation (LLD-platform-v2 4.3, 5.10, 8).

``configure_logging`` is called only by ``daemon.py`` and ``cli.py``. Importing this module
configures nothing.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import logging.handlers
import os
import shutil
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from research_mcp.core.context import correlation_id
from research_mcp.platform.redact import STANDARD_ATTRS, RedactingFilter, Redactor

if TYPE_CHECKING:
    from research_mcp.settings import Settings

MB = 1024 * 1024
LOG_FILE = "research-mcp.jsonl"
MAX_BYTES = 10 * MB
# PLAT-FR-40 keeps 5 files: the live file plus 4 rotated ones (decision 4 of section 10).
BACKUP_COUNT = 4
QUIET_LOGGERS = ("httpx", "httpcore", "uvicorn.access", "mcp")

# PLAT-FR-41, in order; every line carries each of them, null when not set.
LOG_FIELDS = (
    "time",
    "level",
    "event",
    "correlation_id",
    "tool",
    "source",
    "operation",
    "status",
    "error_code",
    "latency_ms",
    "bytes",
    "job_id",
    "attempt",
)
_RECORD_FIELDS = LOG_FIELDS[4:]
_OWN = "_research_mcp_handler"

_log = logging.getLogger(__name__)


def query_hash(text: str) -> str:
    """First 16 hex characters of sha256 over the NFC-normalized, casefolded text."""
    normalized = unicodedata.normalize("NFC", text).casefold()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class _QueryFilter(logging.Filter):
    """Replaces a record's ``query`` with ``query_hash`` and ``query_len`` unless debug is on.

    It runs before ``RedactingFilter``, so the hash is of the text as searched and matches
    ``searches.query_hash``.
    """

    def __init__(self, debug: bool) -> None:
        super().__init__()
        self.debug = debug

    # @spec PLAT-42
    def filter(self, record: logging.LogRecord) -> bool:
        if not self.debug and "query" in vars(record):
            text = str(vars(record).pop("query"))
            record.query_hash = query_hash(text)
            record.query_len = len(unicodedata.normalize("NFC", text))
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line with the PLAT-FR-41 fields first."""

    # @spec PLAT-41
    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or correlation_id.get(),
        }
        for field in _RECORD_FIELDS:
            line[field] = getattr(record, field, None)
        line["logger"] = record.name
        for key, value in vars(record).items():
            if key not in STANDARD_ATTRS and key not in line:
                line[key] = value
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            line["exc"] = record.exc_text
        if record.stack_info:
            line["stack"] = record.stack_info
        return json.dumps(line, default=str, ensure_ascii=False)


class _OwnerOnlyFileHandler(logging.handlers.RotatingFileHandler):
    """A rotating file handler whose live file is mode 0600 and never a followed symlink.

    Rotated files are renames of the live file, so they keep its mode.
    """

    def _open(self) -> io.TextIOWrapper:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW
        fd = os.open(self.baseFilename, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            return open(fd, "a", encoding=self.encoding, errors=self.errors)  # noqa: SIM115
        except BaseException:
            os.close(fd)
            raise


def _all_handlers() -> list[logging.Handler]:
    """Handlers on the root, on every named logger (some do not propagate) and lastResort."""
    named = logging.Logger.manager.loggerDict.values()
    loggers = [logging.getLogger(), *(item for item in named if isinstance(item, logging.Logger))]
    handlers = [handler for logger in loggers for handler in logger.handlers]
    if logging.lastResort is not None:
        handlers.append(logging.lastResort)
    return list(dict.fromkeys(handlers))


def _attach(handler: logging.Handler, redactor: Redactor, debug: bool) -> None:
    handler.filters[:] = [
        f for f in handler.filters if not isinstance(f, RedactingFilter | _QueryFilter)
    ]
    handler.addFilter(_QueryFilter(debug))
    handler.addFilter(RedactingFilter(redactor))


# @spec SEC-5, SEC-14, PLAT-40
def configure_logging(settings: Settings, *, redactor: Redactor | None = None) -> Redactor:
    """Install the JSON file and stderr handlers on the root logger; return the redactor.

    The redacting filter goes on every root handler, so records propagated from child and
    third-party loggers are covered, and on the handlers of every other logger that exists
    at the call and on ``logging.lastResort``. A handler added later is not covered, so
    the daemon configures uvicorn without its own logging (``log_config=None``).
    Calling it again replaces the handlers it installed.
    """
    redactor = redactor if redactor is not None else Redactor()
    debug = settings.logging.debug
    root = logging.getLogger()
    for handler in root.handlers[:]:
        if getattr(handler, _OWN, False):
            root.removeHandler(handler)
            handler.close()

    log_dir = Path(settings.paths.log_dir)
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    formatter = JsonFormatter()
    file_handler = _OwnerOnlyFileHandler(
        log_dir / LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    for handler in (file_handler, stderr_handler):
        handler.setFormatter(formatter)
        setattr(handler, _OWN, True)
        root.addHandler(handler)
    for handler in _all_handlers():
        _attach(handler, redactor, debug)

    logging.getLogger("research_mcp").setLevel(logging.DEBUG if debug else logging.INFO)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    return redactor


def _copy_owner_only(source: Path, target: Path) -> None:
    with source.open("rb") as reader:
        # A fresh file, never an existing one: a symlink planted at the target is removed,
        # not followed.
        target.unlink(missing_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as writer:
            os.fchmod(writer.fileno(), 0o600)
            shutil.copyfileobj(reader, writer)


# @spec PLAT-40
def rotate_stderr_log(path: Path, max_bytes: int = MAX_BYTES, keep: int = 5) -> bool:
    """Rotate ``daemon.err.log`` by copy then truncate; return whether it rotated.

    launchd keeps the file open, so the live file is never renamed. ``keep`` counts the
    live file, so ``keep=5`` leaves ``.1`` to ``.4``. Failures are a warning, never raised.
    """
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return False  # nothing written to stderr yet
    except OSError:
        size = max_bytes  # let the rotation below fail and warn
    if size < max_bytes:
        return False
    try:
        for index in range(keep - 2, 0, -1):
            older = path.with_name(f"{path.name}.{index}")
            if older.exists():
                os.replace(older, path.with_name(f"{path.name}.{index + 1}"))
        _copy_owner_only(path, path.with_name(f"{path.name}.1"))
        os.truncate(path, 0)
    except OSError:
        # No exception text: a path or library message is not needed to retry.
        _log.warning("log_rotate.failed", extra={"operation": "log_rotate"})
        return False
    return True
