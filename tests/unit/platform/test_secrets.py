"""Secrets: references, the Secret wrapper, KeychainProvider, FakeProvider and SecretCache."""

from __future__ import annotations

import copy
import hashlib
import logging
import pickle
import subprocess
from datetime import UTC, datetime
from typing import Any

import pytest

from research_mcp.platform.secrets import (
    FakeProvider,
    KeychainProvider,
    Secret,
    SecretCache,
    SecretMeta,
    SecretRef,
    SecretState,
)

# Generated for these tests; not a real credential.
VALUE = "tv-4f1c9a2e7b-k3y"
STDERR = "security: SecKeychainSearchCopyNext: diagnostic text that must stay private"

# Shape of `security find-generic-password -s ... -a ...` output (no -w), values replaced.
METADATA_STDOUT = """keychain: "/Users/tester/Library/Keychains/login.keychain-db"
version: 512
class: "genp"
attributes:
    0x00000007 <blob>="research-mcp/CORE_API_KEY"
    0x00000008 <blob>=<NULL>
    "acct"<blob>="tester"
    "cdat"<timedate>=0x32303236303130313039303030305A00  "20260101090000Z\\000"
    "mdat"<timedate>=0x32303236313031353038333031355A00  "20261015083015Z\\000"
    "svce"<blob>="research-mcp/CORE_API_KEY"
"""


class Recorder:
    """A fake ``subprocess.run`` that records each call and returns a canned result."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        raises: Exception | None = None,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.raises = raises
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(argv), kwargs))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


CORE = SecretRef.parse("keychain:research-mcp/CORE_API_KEY")


# AT-PLAT-12


def test_parse_valid_references() -> None:
    """AT-PLAT-12: keychain:research-mcp/NAME and env:NAME parse into SecretRef."""
    assert SecretRef.parse("keychain:research-mcp/CORE_API_KEY") == SecretRef(
        "keychain", "CORE_API_KEY", "research-mcp/CORE_API_KEY"
    )
    assert SecretRef.parse("env:NCBI_API_KEY") == SecretRef("env", "NCBI_API_KEY", "")
    assert str(CORE) == "keychain:research-mcp/CORE_API_KEY"
    assert str(SecretRef.parse("env:GITHUB_TOKEN")) == "env:GITHUB_TOKEN"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "CORE_API_KEY",
        "keychain:",
        "keychain:CORE_API_KEY",
        "keychain:other/CORE_API_KEY",
        "keychain:research-mcp/",
        "keychain:research-mcp/core_api_key",
        "keychain:research-mcp/CORE/API",
        "keychain:research-mcp/CORE_API_KEY ",
        " keychain:research-mcp/CORE_API_KEY",
        "keychain:research-mcp/CORE\nAPI",
        "keychain:research-mcp/CORE_API_KEY\n",
        "keychain:research-mcp/CORE\x00",
        "Keychain:research-mcp/CORE_API_KEY",
        "env:",
        "env:A-B",
        "env:1ABC",
        "env:ABC\n",
        "vault:research-mcp/CORE_API_KEY",
        "gcloud_adc:GOOGLE_SIGNIN",
        "env:" + "A" * 65,
    ],
)
def test_parse_rejects_malformed_references(text: str) -> None:
    """AT-PLAT-12: malformed references fail with ValueError."""
    with pytest.raises(ValueError):
        SecretRef.parse(text)


@pytest.mark.parametrize(
    ("backend", "name", "service"),
    [
        ("keychain", "CORE_API_KEY", "research-mcp/OTHER_KEY"),
        ("keychain", "CORE_API_KEY", "CORE_API_KEY"),
        ("keychain", "CORE_API_KEY", "research-mcp/CORE_API_KEY\n"),
        ("keychain", "CORE\nKEY", "research-mcp/CORE\nKEY"),
        ("keychain", "core", "research-mcp/core"),
        ("env", "NCBI_API_KEY", "research-mcp/NCBI_API_KEY"),
        ("vault", "CORE_API_KEY", "research-mcp/CORE_API_KEY"),
    ],
)
def test_direct_construction_validates(backend: Any, name: str, service: str) -> None:
    """AT-PLAT-12: SecretRef validates on construction, not only in parse (SPEC 0.6)."""
    with pytest.raises(ValueError):
        SecretRef(backend, name, service)


def test_parse_error_does_not_echo_input() -> None:
    """AT-PLAT-12: a malformed reference (possibly a pasted secret) is not echoed."""
    pasted = "ghp_" + "x9" * 10
    for text in (pasted, "env:" + pasted, "keychain:research-mcp/" + pasted):
        with pytest.raises(ValueError) as caught:
            SecretRef.parse(text)
        assert pasted not in str(caught.value)


# AT-SEC-01


def test_secret_text_forms_hide_value(caplog: pytest.LogCaptureFixture) -> None:
    """AT-SEC-01: repr, str, format and logging never contain the value."""
    secret = Secret(CORE, VALUE)
    fp = hashlib.sha256(VALUE.encode()).hexdigest()[:8]
    assert secret.fingerprint == fp
    expected = f"Secret(name=CORE_API_KEY, fp={fp})"
    assert repr(secret) == expected
    assert str(secret) == expected
    assert f"{secret}" == expected
    assert f"{secret!r}" == expected
    assert f"{secret:>60}".strip() == expected
    assert "%s %r" % (secret, secret) == f"{expected} {expected}"  # noqa: UP031
    assert "{}".format(secret) == expected  # noqa: UP032
    assert repr([secret]) == f"[{expected}]"
    assert VALUE not in repr(ValueError(secret))

    logger = logging.getLogger("test_secrets")
    with caplog.at_level(logging.DEBUG, logger="test_secrets"):
        logger.info("loaded %s", secret)
        logger.info(secret)
        logger.info("%r", {"key": secret})
    assert caplog.records
    assert VALUE not in caplog.text
    for record in caplog.records:
        assert VALUE not in record.getMessage()

    assert secret.reveal() == VALUE


def test_secret_has_no_dict_and_refuses_pickle() -> None:
    """AT-SEC-01: the value is not exposed through __dict__ or serialization."""
    secret = Secret(CORE, VALUE)
    assert not hasattr(secret, "__dict__")
    with pytest.raises(TypeError):
        pickle.dumps(secret)
    with pytest.raises(TypeError):
        secret.__getstate__()
    assert copy.copy(secret) is secret
    assert copy.deepcopy(secret) is secret


# AT-SEC-02


def test_keychain_read_argv_and_timeout() -> None:
    """AT-SEC-02: get runs /usr/bin/security find-generic-password -w with a 5 s timeout."""
    runner = Recorder(stdout=VALUE + "\n")
    state, secret = KeychainProvider("tester", runner=runner).get(CORE)
    assert state is SecretState.OK
    assert secret is not None
    assert secret.reveal() == VALUE
    assert secret.ref == CORE
    [(argv, kwargs)] = runner.calls
    assert argv == [
        "/usr/bin/security",
        "find-generic-password",
        "-s",
        "research-mcp/CORE_API_KEY",
        "-a",
        "tester",
        "-w",
    ]
    assert kwargs["timeout"] == 5
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs.get("shell", False) is False
    assert kwargs.get("input") is None


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected"),
    [
        (44, STDERR, SecretState.MISSING),
        (36, STDERR, SecretState.LOCKED),
        (51, STDERR, SecretState.LOCKED),
        (1, "security: User interaction is not allowed.", SecretState.LOCKED),
        (1, STDERR, SecretState.ERROR),
        (128, STDERR, SecretState.ERROR),
    ],
)
def test_keychain_read_exit_codes(
    returncode: int,
    stderr: str,
    expected: SecretState,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AT-SEC-02: exit 44 is missing, a locked keychain is keychain_locked, stderr is not echoed."""
    runner = Recorder(returncode=returncode, stdout="", stderr=stderr)
    with caplog.at_level(logging.DEBUG):
        state, secret = KeychainProvider("tester", runner=runner).get(CORE)
    assert (state, secret) == (expected, None)
    out = capsys.readouterr()
    for text in (caplog.text, out.out, out.err, repr(state)):
        assert "diagnostic" not in text
        assert "interaction" not in text


@pytest.mark.parametrize(
    "error",
    [
        subprocess.TimeoutExpired(["/usr/bin/security"], 5, stderr=STDERR),
        FileNotFoundError("/usr/bin/security"),
    ],
)
def test_keychain_read_failures_are_error(error: Exception) -> None:
    """AT-SEC-02: a timeout or a missing binary maps to error without raising."""
    runner = Recorder(raises=error)
    assert KeychainProvider("tester", runner=runner).get(CORE) == (SecretState.ERROR, None)


def test_keychain_empty_output_is_error() -> None:
    """AT-SEC-02: exit 0 with no value is an error, not an empty secret."""
    runner = Recorder(stdout="\n")
    assert KeychainProvider("tester", runner=runner).get(CORE) == (SecretState.ERROR, None)


def test_env_reference_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """AT-SEC-02: env references are read from the environment without running security."""
    runner = Recorder()
    provider = KeychainProvider("tester", runner=runner)
    ref = SecretRef.parse("env:RESEARCH_MCP_TEST_SECRET")
    monkeypatch.delenv("RESEARCH_MCP_TEST_SECRET", raising=False)
    assert provider.get(ref) == (SecretState.MISSING, None)
    monkeypatch.setenv("RESEARCH_MCP_TEST_SECRET", VALUE)
    state, secret = provider.get(ref)
    assert state is SecretState.OK
    assert secret is not None
    assert secret.reveal() == VALUE
    assert runner.calls == []


@pytest.mark.parametrize("user", ["", "tes\nter", "tester\x00", "téster"])
def test_keychain_rejects_unsafe_account(user: str) -> None:
    """AT-SEC-02: the account name cannot carry control characters into security."""
    with pytest.raises(ValueError):
        KeychainProvider(user, runner=Recorder())


# AT-SEC-13


def test_keychain_set_writes_through_stdin() -> None:
    """AT-SEC-13: set runs security -i and writes the command on stdin, never in argv."""
    runner = Recorder()
    KeychainProvider("tester", runner=runner).set(CORE, VALUE)
    [(argv, kwargs)] = runner.calls
    assert argv == ["/usr/bin/security", "-i"]
    assert all(VALUE not in part for part in argv)
    assert kwargs["input"] == (
        'add-generic-password -U -s "research-mcp/CORE_API_KEY" -a "tester" -w "' + VALUE + '"\n'
    )
    assert kwargs["input"].count("\n") == 1
    assert kwargs["timeout"] == 5
    assert kwargs.get("shell", False) is False


def test_keychain_set_quotes_value() -> None:
    """AT-SEC-13: quotes and backslashes in a value stay inside one quoted argument."""
    runner = Recorder()
    KeychainProvider("tester", runner=runner).set(CORE, 'a"b\\c d')
    [(_argv, kwargs)] = runner.calls
    assert kwargs["input"].endswith(' -w "a\\"b\\\\c d"\n')


@pytest.mark.parametrize(
    "value",
    ["", VALUE + "\n", VALUE + "\nadd-generic-password -s x", "a\rb", "a\tb", "a\x00b", "kéy"],
)
def test_keychain_set_rejects_unprintable_values(value: str) -> None:
    """AT-SEC-13: no control character reaches the security -i script; nothing runs."""
    runner = Recorder()
    with pytest.raises(ValueError) as caught:
        KeychainProvider("tester", runner=runner).set(CORE, value)
    assert runner.calls == []
    if value:
        assert value not in str(caught.value)


def test_keychain_set_failure_hides_stderr() -> None:
    """AT-SEC-13: a failed write raises without the value or the stderr text."""
    runner = Recorder(returncode=1, stderr=STDERR)
    with pytest.raises(RuntimeError) as caught:
        KeychainProvider("tester", runner=runner).set(CORE, VALUE)
    assert VALUE not in str(caught.value)
    assert "diagnostic" not in str(caught.value)


def test_keychain_set_timeout_does_not_chain_stderr() -> None:
    """AT-SEC-13: a timed-out write raises without chaining the exception that holds stderr."""
    timeout = subprocess.TimeoutExpired(["/usr/bin/security", "-i"], 5, stderr=STDERR)
    runner = Recorder(raises=timeout)
    with pytest.raises(RuntimeError) as caught:
        KeychainProvider("tester", runner=runner).set(CORE, VALUE)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def test_set_refuses_env_reference() -> None:
    """AT-SEC-13: only Keychain items can be written; env references are refused."""
    ref = SecretRef.parse("env:CORE_API_KEY")
    runner = Recorder()
    with pytest.raises(ValueError):
        KeychainProvider("tester", runner=runner).set(ref, VALUE)
    assert runner.calls == []
    with pytest.raises(ValueError):
        FakeProvider().set(ref, VALUE)


def test_fake_provider_set_records_argv_without_value() -> None:
    """AT-SEC-13: FakeProvider records the argv set would use, which never holds the value."""
    fake = FakeProvider(user="tester")
    fake.set(CORE, VALUE)
    state, secret = fake.get(CORE)
    assert state is SecretState.OK
    assert secret is not None
    assert secret.reveal() == VALUE
    assert fake.argv[0] == ["/usr/bin/security", "-i"]
    assert all(VALUE not in part for argv in fake.argv for part in argv)
    with pytest.raises(ValueError):
        fake.set(CORE, "bad\nvalue")


# AT-SEC-03


def test_keychain_metadata_never_passes_w() -> None:
    """AT-SEC-03: metadata runs find-generic-password without -w and returns mdat only."""
    runner = Recorder(stdout=METADATA_STDOUT)
    meta = KeychainProvider("tester", runner=runner).metadata(CORE)
    assert meta == SecretMeta("CORE_API_KEY", datetime(2026, 10, 15, 8, 30, 15, tzinfo=UTC))
    [(argv, kwargs)] = runner.calls
    assert "-w" not in argv
    assert "-g" not in argv
    assert argv == [
        "/usr/bin/security",
        "find-generic-password",
        "-s",
        "research-mcp/CORE_API_KEY",
        "-a",
        "tester",
    ]
    assert kwargs["timeout"] == 5


def test_keychain_metadata_without_mdat_and_failures() -> None:
    """AT-SEC-03: a missing mdat gives no date; a missing or locked item gives no metadata."""
    no_mdat = Recorder(stdout='attributes:\n    "acct"<blob>="tester"\n')
    assert KeychainProvider("tester", runner=no_mdat).metadata(CORE) == SecretMeta(
        "CORE_API_KEY", None
    )
    for code in (44, 36, 51, 1):
        failed = Recorder(returncode=code, stderr=STDERR)
        assert KeychainProvider("tester", runner=failed).metadata(CORE) is None
    timeout = Recorder(raises=subprocess.TimeoutExpired(["/usr/bin/security"], 5))
    assert KeychainProvider("tester", runner=timeout).metadata(CORE) is None


def test_env_reference_has_no_metadata_in_both_providers() -> None:
    """AT-SEC-03: env references have no metadata in KeychainProvider and FakeProvider alike."""
    ref = SecretRef.parse("env:CORE_API_KEY")
    runner = Recorder(stdout=METADATA_STDOUT)
    assert KeychainProvider("tester", runner=runner).metadata(ref) is None
    assert runner.calls == []
    fake = FakeProvider({"CORE_API_KEY": VALUE}, environ={"CORE_API_KEY": VALUE})
    assert fake.metadata(ref) is None
    assert fake.argv == []


def test_fake_provider_metadata_matches_keychain() -> None:
    """AT-SEC-03: FakeProvider.metadata records the no -w argv and returns the date only."""
    when = datetime(2026, 10, 15, 8, 30, 15, tzinfo=UTC)
    fake = FakeProvider({"CORE_API_KEY": VALUE}, modified={"CORE_API_KEY": when})
    assert fake.metadata(CORE) == SecretMeta("CORE_API_KEY", when)
    assert fake.argv == [
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            "research-mcp/CORE_API_KEY",
            "-a",
            "tester",
        ]
    ]
    assert fake.metadata(SecretRef.parse("keychain:research-mcp/NVD_API_KEY")) is None
    fake.states["CORE_API_KEY"] = SecretState.LOCKED
    assert fake.metadata(CORE) is None
    assert fake.get(CORE) == (SecretState.LOCKED, None)


# AT-SEC-04


def test_secret_cache_reload_returns_changed_names() -> None:
    """AT-SEC-04: reload re-reads secrets and returns the names whose fingerprints changed."""
    nvd = SecretRef.parse("keychain:research-mcp/NVD_API_KEY")
    gh = SecretRef.parse("env:GITHUB_TOKEN")
    zen = SecretRef.parse("keychain:research-mcp/ZENODO_TOKEN")
    fake = FakeProvider(
        {"CORE_API_KEY": VALUE, "NVD_API_KEY": "nvd-value-1"}, environ={"GITHUB_TOKEN": "gh-1"}
    )
    cache = SecretCache(
        fake,
        {"CORE_API_KEY": CORE, "NVD_API_KEY": nvd, "GITHUB_TOKEN": gh, "ZENODO_TOKEN": zen},
        sources={"core_ac": "CORE_API_KEY", "github": "GITHUB_TOKEN"},
    )
    assert cache.get("CORE_API_KEY") is None
    assert cache.state("CORE_API_KEY") is SecretState.MISSING
    cache.load()
    core = cache.get("CORE_API_KEY")
    assert core is not None
    assert core.reveal() == VALUE
    assert cache.state("NVD_API_KEY") is SecretState.OK
    assert cache.state("ZENODO_TOKEN") is SecretState.MISSING
    assert cache.get("UNKNOWN") is None
    assert cache.state("UNKNOWN") is SecretState.MISSING
    assert cache.secret_for("core_ac") is core
    assert cache.secret_for("arxiv") is None

    calls = len(fake.argv)
    assert cache.reload() == []
    assert len(fake.argv) > calls

    fake.items["NVD_API_KEY"] = "nvd-value-2"
    fake.environ["GITHUB_TOKEN"] = "gh-2"
    fake.items["ZENODO_TOKEN"] = "zen-1"
    del fake.items["CORE_API_KEY"]
    assert cache.reload() == ["CORE_API_KEY", "NVD_API_KEY", "GITHUB_TOKEN", "ZENODO_TOKEN"]
    nvd_secret = cache.get("NVD_API_KEY")
    assert nvd_secret is not None
    assert nvd_secret.reveal() == "nvd-value-2"
    assert cache.state("CORE_API_KEY") is SecretState.MISSING
    assert cache.secret_for("core_ac") is None

    fake.states["NVD_API_KEY"] = SecretState.LOCKED
    assert cache.reload() == ["NVD_API_KEY"]
    assert cache.state("NVD_API_KEY") is SecretState.LOCKED
    assert cache.reload() == []
