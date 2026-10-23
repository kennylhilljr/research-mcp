"""configure_logging, query_hash and rotate_stderr_log (LLD-platform-v2 4.3, 5.10, 8)."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import logging.handlers
import os
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pytest

from research_mcp.core.context import correlation_id
from research_mcp.platform.logging import (
    LOG_FIELDS,
    configure_logging,
    query_hash,
    rotate_stderr_log,
)
from research_mcp.platform.redact import MASK, RedactingFilter, Redactor
from research_mcp.platform.secrets import Secret, SecretRef
from research_mcp.settings import Settings

# Generated for these tests; not a real credential.
VALUE = "tv-51be0c94aa-k3y"
MB = 1024 * 1024


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """An isolated home, and the logging state put back after each test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in os.environ:
        if name.startswith("RESEARCH_MCP_"):
            monkeypatch.delenv(name)
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_filters = {id(h): h.filters[:] for h in saved_handlers}
    names = ("research_mcp", "httpx", "httpcore", "uvicorn.access", "mcp")
    saved_levels = {name: logging.getLogger(name).level for name in names}
    saved_root = root.level
    last_resort = logging.lastResort
    saved_last_resort = last_resort.filters[:] if last_resort else []
    yield
    if last_resort:
        last_resort.filters[:] = saved_last_resort
    for handler in root.handlers[:]:
        if handler not in saved_handlers:
            root.removeHandler(handler)
            handler.close()
    for handler in saved_handlers:
        handler.filters[:] = saved_filters[id(handler)]
    root.setLevel(saved_root)
    for name, level in saved_levels.items():
        logging.getLogger(name).setLevel(level)


def settings(tmp_path: Path, *, debug: bool = False) -> Settings:
    return Settings(paths={"log_dir": tmp_path / "logs"}, logging={"debug": debug})


def lines(tmp_path: Path) -> list[dict[str, object]]:
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = (tmp_path / "logs" / "research-mcp.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines()]


def file_handler() -> logging.handlers.RotatingFileHandler:
    found = [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(found) == 1
    return found[0]


def test_rotating_file_is_5_files_of_10mb(tmp_path: Path) -> None:
    """@spec PLAT-40: JSON lines go to research-mcp.jsonl, rotated at 10 MB, 5 files in all."""
    configure_logging(settings(tmp_path))
    handler = file_handler()
    assert Path(handler.baseFilename) == (tmp_path / "logs" / "research-mcp.jsonl").resolve()
    assert handler.maxBytes == 10 * MB
    assert handler.backupCount == 4

    logging.getLogger("research_mcp.test").info("search.done", extra={"status": "ok"})
    [line] = lines(tmp_path)
    assert line["event"] == "search.done"
    assert line["level"] == "INFO"

    handler.maxBytes = 200  # rotate quickly; the count of files is what is checked
    for n in range(100):
        logging.getLogger("research_mcp.test").info("filler %d", n)
    files = sorted(p.name for p in (tmp_path / "logs").iterdir())
    assert files == ["research-mcp.jsonl", *(f"research-mcp.jsonl.{i}" for i in range(1, 5))]


def test_stderr_warnings_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@spec PLAT-40: stderr receives warnings and errors only, never info or debug."""
    stderr = io.StringIO()
    monkeypatch.setattr("sys.stderr", stderr)
    configure_logging(settings(tmp_path, debug=True))
    log = logging.getLogger("research_mcp.test")
    log.debug("debug.line")
    log.info("info.line")
    log.warning("warning.line")
    log.error("error.line")
    text = stderr.getvalue()
    assert "warning.line" in text
    assert "error.line" in text
    assert "info.line" not in text
    assert "debug.line" not in text
    events = [line["event"] for line in lines(tmp_path)]
    assert events == ["debug.line", "info.line", "warning.line", "error.line"]


def test_configure_logging_twice_keeps_one_set_of_handlers(tmp_path: Path) -> None:
    """@spec PLAT-40: A second configuration replaces the handlers instead of adding more."""
    configure_logging(settings(tmp_path))
    configure_logging(settings(tmp_path))
    logging.getLogger("research_mcp.test").info("once")
    assert [line["event"] for line in lines(tmp_path)] == ["once"]


def test_rotate_stderr_log(tmp_path: Path) -> None:
    """@spec PLAT-40: daemon.err.log is copied then truncated at 10 MB, 5 files kept, mode 0600."""
    path = tmp_path / "daemon.err.log"
    path.write_bytes(b"small\n")
    assert rotate_stderr_log(path) is False
    assert path.read_bytes() == b"small\n"

    for generation in range(6):
        path.write_bytes(bytes([65 + generation]) * 64)
        assert rotate_stderr_log(path, max_bytes=64, keep=5) is True
        assert path.stat().st_size == 0

    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["daemon.err.log", *(f"daemon.err.log.{i}" for i in range(1, 5))]
    # Newest first: generation 5 is .1, generation 2 is .4; generations 0 and 1 are gone.
    for index, generation in zip(range(1, 5), range(5, 1, -1), strict=True):
        rotated = tmp_path / f"daemon.err.log.{index}"
        assert rotated.read_bytes() == bytes([65 + generation]) * 64
        assert rotated.stat().st_mode & 0o777 == 0o600


def test_rotate_stderr_log_never_raises(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """@spec PLAT-40: A rotation failure is a warning without exception text, never a raise."""
    missing = tmp_path / "absent" / "daemon.err.log"
    assert rotate_stderr_log(missing) is False

    path = tmp_path / "daemon.err.log"
    path.write_bytes(b"x" * 64)
    path.chmod(0o200)  # the live file cannot be read, so the copy fails
    try:
        with caplog.at_level(logging.WARNING):
            assert rotate_stderr_log(path, max_bytes=64) is False
    finally:
        path.chmod(0o600)
    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    assert caplog.records[0].exc_info is None
    assert path.read_bytes() == b"x" * 64


def test_records_carry_fields_and_correlation_id(tmp_path: Path) -> None:
    """@spec PLAT-41: Every line has correlation_id and the PLAT-FR-41 fields."""
    configure_logging(settings(tmp_path))
    log = logging.getLogger("research_mcp.test")
    token = correlation_id.set("01JCORRELATION")
    try:
        log.info(
            "http.call",
            extra={
                "tool": "search",
                "source": "arxiv",
                "operation": "search",
                "status": 200,
                "error_code": None,
                "latency_ms": 41,
                "bytes": 2048,
                "job_id": None,
                "attempt": 1,
            },
        )
    finally:
        correlation_id.reset(token)
    log.warning("bare.event")

    first, second = lines(tmp_path)
    assert set(LOG_FIELDS) == {
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
    }
    for line in (first, second):
        assert set(LOG_FIELDS) <= set(line)
    assert first["correlation_id"] == "01JCORRELATION"
    assert first["source"] == "arxiv"
    assert first["latency_ms"] == 41
    assert first["attempt"] == 1
    assert str(first["time"]).endswith("Z")
    assert second["event"] == "bare.event"
    assert second["level"] == "WARNING"
    assert second["correlation_id"] is None
    assert second["tool"] is None


def test_exception_text_reaches_the_log_masked(tmp_path: Path) -> None:
    """@spec SEC-5: A traceback logged by the daemon is in the line, with the secret masked."""
    redactor = configure_logging(settings(tmp_path))
    redactor.register(Secret(SecretRef.parse("keychain:research-mcp/CORE_API_KEY"), VALUE))
    try:
        raise ValueError(f"bad response for {VALUE}")
    except ValueError:
        logging.getLogger("research_mcp.test").exception("tool.internal")
    [line] = lines(tmp_path)
    assert "bad response for" in str(line["exc"])
    assert VALUE not in json.dumps(line)


def test_query_text_is_hash_and_length(tmp_path: Path) -> None:
    """@spec PLAT-42: With debug off, query text is logged only as query_hash and query_len."""
    configure_logging(settings(tmp_path))
    query = "Graph Neural Networks for molecules"
    logging.getLogger("research_mcp.test").info("search.start", extra={"query": query})
    [line] = lines(tmp_path)
    assert "query" not in line
    assert line["query_hash"] == query_hash(query)
    assert line["query_len"] == len(query)
    assert "Graph" not in json.dumps(line)


def test_debug_logs_query_text_through_redactor(tmp_path: Path) -> None:
    """@spec PLAT-42: With debug on, query text is logged in clear, still through the redactor."""
    redactor = configure_logging(settings(tmp_path, debug=True))
    redactor.register(Secret(SecretRef.parse("keychain:research-mcp/CORE_API_KEY"), VALUE))
    log = logging.getLogger("research_mcp.test")
    assert log.getEffectiveLevel() == logging.DEBUG
    log.debug("search.start", extra={"query": f"graphs {VALUE}"})
    [line] = lines(tmp_path)
    assert line["query"] == f"graphs {MASK}"
    assert "query_hash" not in line


def test_debug_off_sets_info_level(tmp_path: Path) -> None:
    """@spec PLAT-42: With debug off, the research_mcp logger runs at INFO."""
    configure_logging(settings(tmp_path))
    assert logging.getLogger("research_mcp").level == logging.INFO


def test_query_hash_is_nfc_casefold_stable() -> None:
    """@spec PLAT-42: query_hash is sha256 of the NFC, casefolded text, first 16 hex chars."""
    composed = "Café STRASSE"
    decomposed = unicodedata.normalize("NFD", "café straße")
    assert query_hash(composed) == query_hash(decomposed)
    expected = hashlib.sha256(unicodedata.normalize("NFC", composed).casefold().encode())
    assert query_hash(composed) == expected.hexdigest()[:16]
    assert len(query_hash("x")) == 16
    assert query_hash("x") != query_hash("y")


def test_filter_is_on_every_handler(tmp_path: Path) -> None:
    """@spec SEC-5: The redacting filter sits on every root handler, including existing ones."""
    existing = logging.StreamHandler(io.StringIO())
    logging.getLogger().addHandler(existing)
    configure_logging(settings(tmp_path))
    handlers = logging.getLogger().handlers
    assert existing in handlers
    for handler in handlers:
        assert any(isinstance(f, RedactingFilter) for f in handler.filters)


def test_filter_is_on_handlers_of_non_propagating_loggers(tmp_path: Path) -> None:
    """@spec SEC-5: Handlers on non-propagating loggers, such as uvicorn's, are masked too."""
    stream = io.StringIO()
    own = logging.StreamHandler(stream)
    uvicorn = logging.getLogger("uvicorn.error")
    saved = (uvicorn.handlers[:], uvicorn.propagate)
    uvicorn.addHandler(own)
    uvicorn.propagate = False
    try:
        redactor = configure_logging(settings(tmp_path))
        redactor.register(Secret(SecretRef.parse("keychain:research-mcp/CORE_API_KEY"), VALUE))
        uvicorn.error("startup saw %s", VALUE)
        assert stream.getvalue() == f"startup saw {MASK}\n"
        assert any(isinstance(f, RedactingFilter) for f in logging.lastResort.filters)
    finally:
        uvicorn.handlers[:], uvicorn.propagate = saved


def test_log_files_are_owner_only(tmp_path: Path) -> None:
    """@spec PLAT-40: research-mcp.jsonl and its rotated files are created mode 0600."""
    old = os.umask(0o022)
    try:
        configure_logging(settings(tmp_path))
        handler = file_handler()
        handler.maxBytes = 200
        for n in range(20):
            logging.getLogger("research_mcp.test").info("filler %d", n)
    finally:
        os.umask(old)
    files = list((tmp_path / "logs").iterdir())
    assert len(files) > 1
    for path in files:
        assert path.stat().st_mode & 0o777 == 0o600, path.name


def test_rotate_stderr_log_does_not_follow_a_planted_symlink(tmp_path: Path) -> None:
    """@spec PLAT-40: A symlink planted at daemon.err.log.1 is not written through."""
    path = tmp_path / "daemon.err.log"
    path.write_bytes(b"x" * 64)
    victim = tmp_path / "victim"
    victim.write_bytes(b"keep")
    rotated = tmp_path / "daemon.err.log.1"
    rotated.symlink_to(victim)
    assert rotate_stderr_log(path, max_bytes=64, keep=2) is True
    assert victim.read_bytes() == b"keep"
    assert not rotated.is_symlink()
    assert rotated.read_bytes() == b"x" * 64
    assert rotated.stat().st_mode & 0o777 == 0o600


def test_child_and_third_party_records_are_masked(tmp_path: Path) -> None:
    """@spec SEC-5: Records propagated from child and third-party loggers are masked."""
    redactor = configure_logging(settings(tmp_path))
    redactor.register(Secret(SecretRef.parse("keychain:research-mcp/CORE_API_KEY"), VALUE))
    logging.getLogger("research_mcp.sources.core.deep").info("child %s", VALUE)
    logging.getLogger("some_library.client").warning("library saw %s", VALUE)
    events = [line["event"] for line in lines(tmp_path)]
    assert events == [f"child {MASK}", f"library saw {MASK}"]


def test_noisy_loggers_run_at_warning(tmp_path: Path) -> None:
    """@spec SEC-14: httpx, httpcore, uvicorn.access and mcp run at WARNING."""
    configure_logging(settings(tmp_path))
    for name in ("httpx", "httpcore", "uvicorn.access", "mcp"):
        assert logging.getLogger(name).level == logging.WARNING


def test_info_httpx_url_with_api_key_never_reaches_a_handler(tmp_path: Path) -> None:
    """@spec SEC-14: An INFO httpx record with api_key in the URL reaches no handler."""
    logging.getLogger().setLevel(logging.DEBUG)  # the quiet levels must not rely on the root
    configure_logging(settings(tmp_path))
    seen: list[logging.LogRecord] = []

    class Recorder(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            seen.append(record)

    logging.getLogger().addHandler(Recorder())
    url = "https://api.openalex.org/works?api_key=abc123SECRET"
    logging.getLogger("httpx").info('HTTP Request: GET %s "HTTP/1.1 200 OK"', url)
    logging.getLogger("mcp.server.lowlevel").info("request %s", url)
    assert seen == []
    logging.getLogger("httpx").warning("HTTP Request: GET %s failed", url)
    [line] = lines(tmp_path)
    assert "abc123SECRET" not in json.dumps(line)
    assert MASK in str(line["event"])


def test_configure_logging_uses_the_given_redactor(tmp_path: Path) -> None:
    """@spec SEC-5: The composition root's redactor is the one the handlers use."""
    redactor = Redactor()
    assert configure_logging(settings(tmp_path), redactor=redactor) is redactor
    redactor.register(Secret(SecretRef.parse("keychain:research-mcp/CORE_API_KEY"), VALUE))
    logging.getLogger("research_mcp.test").info("value %s", VALUE)
    assert lines(tmp_path)[0]["event"] == f"value {MASK}"
