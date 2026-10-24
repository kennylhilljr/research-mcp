"""A fake ``LaunchctlPort`` for tests: it records every request and runs no process.

``on_start`` is called on each ``kickstart`` or ``bootstrap``, so a test can bring an
in-process daemon up when the shim asks launchd to start it (PLAT-73, PLAT-77).
"""

from collections.abc import Callable
from pathlib import Path


class FakeLaunchctl:
    def __init__(self, *, loaded: bool = True, on_start: Callable[[], None] | None = None) -> None:
        self.loaded = set[str]()
        self._loaded_by_default = loaded
        self.on_start = on_start
        self.calls: list[tuple[str, ...]] = []

    async def is_loaded(self, label: str) -> bool:
        self.calls.append(("print", label))
        return self._loaded_by_default or label in self.loaded

    async def kickstart(self, label: str) -> None:
        self.calls.append(("kickstart", label))
        self._started()

    async def bootstrap(self, plist: Path) -> None:
        self.calls.append(("bootstrap", str(plist)))
        self.loaded.add(plist.stem)
        self._started()

    async def bootout(self, label: str) -> None:
        self.calls.append(("bootout", label))
        self.loaded.discard(label)

    async def kill(self, signal_name: str, label: str) -> None:
        self.calls.append(("kill", signal_name, label))

    @property
    def starts(self) -> list[tuple[str, ...]]:
        return [call for call in self.calls if call[0] in {"kickstart", "bootstrap"}]

    def _started(self) -> None:
        if self.on_start is not None:
            self.on_start()
