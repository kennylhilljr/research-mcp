"""Secret references, the Secret wrapper and the Keychain provider (SPEC 3.1).

Secret values never appear in a process argument list, a log record, an error message or
the text form of any object here. Keychain writes go to ``/usr/bin/security -i`` on stdin,
and the stderr of ``security`` is inspected for the locked case but never logged or returned.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, NoReturn, Protocol

_SECURITY = "/usr/bin/security"
_SERVICE_PREFIX = "research-mcp/"
_TIMEOUT_S = 5.0

_NAME = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_BACKENDS = ("keychain", "env")
_EXIT_NOT_FOUND = 44
_EXIT_LOCKED = (36, 51)
_LOCKED_TEXT = "User interaction is not allowed"
_MDAT = re.compile(r'"mdat"<timedate>=(?:0x[0-9A-Fa-f]+\s+)?"(\d{14})Z')

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _printable_ascii(text: str) -> bool:
    return all(" " <= char <= "~" for char in text)


# @spec PLAT-12
@dataclass(frozen=True)
class SecretRef:
    """Where a secret lives: ``keychain:research-mcp/NAME`` or ``env:NAME``.

    An ``env`` reference has no Keychain service, so its ``service`` is empty.
    """

    backend: Literal["keychain", "env"]
    name: str
    service: str

    def __post_init__(self) -> None:
        # Messages never echo the rejected values: a mistyped reference may be a pasted secret.
        if self.backend not in _BACKENDS:
            raise ValueError("secret reference backend must be 'keychain' or 'env'")
        if not isinstance(self.name, str) or _NAME.fullmatch(self.name) is None:
            raise ValueError("secret name must match [A-Z][A-Z0-9_]{0,63}")
        expected = _SERVICE_PREFIX + self.name if self.backend == "keychain" else ""
        if self.service != expected:
            raise ValueError("keychain service must be research-mcp/<NAME>; env has none")

    @classmethod
    def parse(cls, text: str) -> SecretRef:
        backend, sep, rest = text.partition(":")
        if not sep:
            raise ValueError("secret reference must be keychain:research-mcp/<NAME> or env:<NAME>")
        if backend == "keychain":
            if not rest.startswith(_SERVICE_PREFIX):
                raise ValueError("keychain reference must be keychain:research-mcp/<NAME>")
            name = rest.removeprefix(_SERVICE_PREFIX)
            return cls("keychain", name, _SERVICE_PREFIX + name)
        if backend == "env":
            return cls("env", rest, "")
        raise ValueError("secret reference backend must be 'keychain' or 'env'")

    def __str__(self) -> str:
        return f"keychain:{self.service}" if self.backend == "keychain" else f"env:{self.name}"


@dataclass(frozen=True)
class SecretMeta:
    name: str
    modified_at: datetime | None


# @spec SEC-1
class Secret:
    """A secret value whose text form shows only its name and fingerprint."""

    __slots__ = ("_ref", "_value")

    def __init__(self, ref: SecretRef, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("secret value must be a str")
        self._ref = ref
        self._value = value

    @property
    def ref(self) -> SecretRef:
        return self._ref

    def reveal(self) -> str:
        return self._value

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self._value.encode()).hexdigest()[:8]

    def __repr__(self) -> str:
        return f"Secret(name={self.ref.name}, fp={self.fingerprint})"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return format(repr(self), spec)

    def __reduce__(self) -> NoReturn:
        raise TypeError("Secret cannot be pickled")

    def __getstate__(self) -> NoReturn:
        raise TypeError("Secret cannot be pickled")

    def __copy__(self) -> Secret:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Secret:
        return self


class SecretState(StrEnum):
    OK = "ok"
    MISSING = "missing"
    LOCKED = "keychain_locked"
    ERROR = "error"
    INVALID = "invalid"  # returned only by GoogleAdcProvider (M1); never by the providers here


_KEEP_ON_REREAD = (SecretState.LOCKED, SecretState.ERROR)


class SecretProvider(Protocol):
    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]: ...
    def metadata(self, ref: SecretRef) -> SecretMeta | None: ...
    def set(self, ref: SecretRef, value: str) -> None: ...


def _read_argv(ref: SecretRef, user: str, *, value: bool) -> list[str]:
    argv = [_SECURITY, "find-generic-password", "-s", ref.service, "-a", user]
    return [*argv, "-w"] if value else argv


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _write_script(ref: SecretRef, user: str, value: str) -> str:
    """The one-line ``security -i`` script; every part is printable ASCII, so no newline."""
    if not value or not _printable_ascii(value):
        raise ValueError(f"value for {ref.name} must be non-empty printable ASCII")
    return (
        f"add-generic-password -U -s {_quote(ref.service)} -a {_quote(user)} -w {_quote(value)}\n"
    )


def _check_writable(ref: SecretRef) -> None:
    if ref.backend != "keychain":
        raise ValueError(f"{ref.name} is an env reference; only Keychain items can be set")


def _parse_mdat(stdout: str) -> datetime | None:
    match = _MDAT.search(stdout)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


# @spec SEC-2, SEC-3, SEC-13
class KeychainProvider:
    """Reads and writes Keychain generic passwords through ``/usr/bin/security``."""

    def __init__(self, user: str, runner: Runner = subprocess.run) -> None:
        if not user or not _printable_ascii(user):
            raise ValueError("keychain account must be non-empty printable ASCII")
        self._user = user
        self._runner = runner

    def _run(self, argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return self._runner(
            argv, input=stdin, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False
        )

    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]:
        if ref.backend == "env":
            value = os.environ.get(ref.name)
            return (SecretState.OK, Secret(ref, value)) if value else (SecretState.MISSING, None)
        try:
            done = self._run(_read_argv(ref, self._user, value=True))
        except (OSError, subprocess.SubprocessError):
            return SecretState.ERROR, None
        if done.returncode == 0:
            value = (done.stdout or "").removesuffix("\n")
            return (SecretState.OK, Secret(ref, value)) if value else (SecretState.ERROR, None)
        if done.returncode == _EXIT_NOT_FOUND:
            return SecretState.MISSING, None
        if done.returncode in _EXIT_LOCKED or _LOCKED_TEXT in (done.stderr or ""):
            return SecretState.LOCKED, None
        return SecretState.ERROR, None

    def metadata(self, ref: SecretRef) -> SecretMeta | None:
        if ref.backend != "keychain":
            return None
        try:
            done = self._run(_read_argv(ref, self._user, value=False))
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        return SecretMeta(ref.name, _parse_mdat(done.stdout or ""))

    def set(self, ref: SecretRef, value: str) -> None:
        _check_writable(ref)
        script = _write_script(ref, self._user, value)
        # Raised outside the except block so no __context__ carries the captured stderr.
        done: subprocess.CompletedProcess[str] | None = None
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            done = self._run([_SECURITY, "-i"], stdin=script)
        if done is None:
            raise RuntimeError(f"could not run security to store {ref.name}")
        if done.returncode != 0:
            raise RuntimeError(f"security could not store {ref.name} (exit {done.returncode})")


class FakeProvider:
    """In-memory provider for tests; records every argv ``KeychainProvider`` would run.

    ``items`` holds Keychain values by name, ``environ`` the values ``env`` references see,
    and ``states`` forces a state (for example ``keychain_locked``) for a Keychain name.
    """

    def __init__(
        self,
        items: Mapping[str, str] | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        user: str = "tester",
        modified: Mapping[str, datetime] | None = None,
    ) -> None:
        self.items = dict(items or {})
        self.environ = dict(environ or {})
        self.states: dict[str, SecretState] = {}
        self.modified = dict(modified or {})
        self.user = user
        self.argv: list[list[str]] = []

    def get(self, ref: SecretRef) -> tuple[SecretState, Secret | None]:
        if ref.backend == "env":
            value = self.environ.get(ref.name)
            return (SecretState.OK, Secret(ref, value)) if value else (SecretState.MISSING, None)
        self.argv.append(_read_argv(ref, self.user, value=True))
        forced = self.states.get(ref.name)
        if forced is not None and forced is not SecretState.OK:
            return forced, None
        value = self.items.get(ref.name)
        return (SecretState.OK, Secret(ref, value)) if value else (SecretState.MISSING, None)

    def metadata(self, ref: SecretRef) -> SecretMeta | None:
        if ref.backend != "keychain":
            return None
        self.argv.append(_read_argv(ref, self.user, value=False))
        forced = self.states.get(ref.name)
        if ref.name not in self.items or (forced is not None and forced is not SecretState.OK):
            return None
        return SecretMeta(ref.name, self.modified.get(ref.name))

    def set(self, ref: SecretRef, value: str) -> None:
        _check_writable(ref)
        _write_script(ref, self.user, value)
        self.argv.append([_SECURITY, "-i"])
        self.items[ref.name] = value
        self.modified[ref.name] = datetime.now(UTC)


class SecretCache:
    """Secrets read once and kept in memory; ``reload`` re-reads them (PLAT-FR-15).

    ``refs`` maps credential names to references. ``sources`` maps a source id to the
    credential name it uses, which makes the cache a ``CredentialResolver``.
    """

    def __init__(
        self,
        provider: SecretProvider,
        refs: Mapping[str, SecretRef],
        sources: Mapping[str, str] | None = None,
    ) -> None:
        self._provider = provider
        self._refs = dict(refs)
        self._sources = dict(sources or {})
        self._entries: dict[str, tuple[SecretState, Secret | None]] = {}

    def _read(self) -> dict[str, tuple[SecretState, Secret | None]]:
        return {name: self._provider.get(ref) for name, ref in self._refs.items()}

    def load(self) -> None:
        self._entries = self._read()

    def get(self, name: str) -> Secret | None:
        return self._entries.get(name, (SecretState.MISSING, None))[1]

    def state(self, name: str) -> SecretState:
        return self._entries.get(name, (SecretState.MISSING, None))[0]

    # @spec SEC-4
    def reload(self) -> list[str]:
        """Re-read every secret; return the names whose fingerprint changed.

        A ``keychain_locked`` or ``error`` re-read keeps the previous secret and reports the
        new state, so a locked Keychain does not strip working credentials; ``missing`` clears.
        """
        before = {name: self._fingerprint(name) for name in self._refs}
        entries = self._read()
        for name, (state, secret) in entries.items():
            previous = self.get(name)
            if secret is None and state in _KEEP_ON_REREAD and previous is not None:
                entries[name] = (state, previous)
        self._entries = entries
        return [name for name in self._refs if self._fingerprint(name) != before[name]]

    def _fingerprint(self, name: str) -> str | None:
        secret = self.get(name)
        return None if secret is None else secret.fingerprint

    def secret_for(self, source: str) -> Secret | None:
        name = self._sources.get(source)
        return None if name is None else self.get(name)
