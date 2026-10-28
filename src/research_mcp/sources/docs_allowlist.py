"""Host and path matching for docs sites (LLD-sources-v3 5.11; SRC-FR-15, SRC-INV-3).

v1 matched its crawl filters as URL substrings. Here the parsed host must equal an allowed
host exactly and the cleaned path must start with a prefix at a segment boundary, so
``docs.example.com.evil``, ``evil.com/docs.example.com``, userinfo and ``..`` segments
never pass. The query and fragment never count.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit

# Characters a path keeps unescaped when the cleaned path is written back out (RFC 3986).
_PATH_SAFE = "/!$&'()*+,;=:@"
_ENCODED_SEPARATORS = ("%2f", "%5c")


def _ascii_host(hostname: str | None) -> str | None:
    """The host, lowercased, without one trailing dot, in its ASCII (IDNA) form."""
    if not hostname:
        return None
    host = hostname.lower().removesuffix(".")
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return None


def _has_separator(path: str) -> bool:
    lowered = path.lower()
    return "\\" in path or any(sep in lowered for sep in _ENCODED_SEPARATORS)


def _remove_dot_segments(path: str) -> str:
    segments = path.split("/")[1:]
    kept: list[str] = []
    for segment in segments:
        if segment == "..":
            if kept:
                kept.pop()
        elif segment != ".":
            kept.append(segment)
    if segments and segments[-1] in (".", ".."):
        kept.append("")
    return "/" + "/".join(kept)


def _clean_path(raw: str) -> str | None:
    """The path after one percent-decode and dot-segment removal; None if it hides a
    separator (an encoded slash or a backslash) or is not UTF-8."""
    if _has_separator(raw):
        return None
    try:
        decoded = unquote(raw, errors="strict")
    except UnicodeDecodeError:
        return None
    if _has_separator(decoded):
        return None
    return _remove_dot_segments(decoded or "/")


def _under(path: str, prefix: str) -> bool:
    """``/docs/`` matches ``/docs`` and ``/docs/x``, never ``/docsx``."""
    base = prefix.rstrip("/")
    return path == base or path.startswith(base + "/")


# @spec SRC-23
@dataclass(frozen=True)
class DocsSiteAllowlist:
    """The hosts and path prefixes a docs-site instance may fetch."""

    allowed_hosts: frozenset[str]
    path_prefixes: tuple[str, ...]

    def allows(self, url: str) -> bool:
        return self.canonical(url) is not None

    def canonical(self, url: str) -> str | None:
        """The URL as it is fetched (cleaned path, no fragment), or None when not allowed.

        Callers fetch this form, so ``robots.txt`` is checked against the path the server
        will actually serve.
        """
        if any(ord(char) <= 0x20 or ord(char) == 0x7F for char in url):
            # urlsplit drops tabs and newlines silently; a URL carrying them is refused.
            return None
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError:
            return None
        if parts.scheme != "https" or "@" in parts.netloc or port not in (None, 443):
            return None
        host = _ascii_host(parts.hostname)
        if host is None or host not in self.allowed_hosts:
            return None
        path = _clean_path(parts.path)
        if path is None or not any(_under(path, prefix) for prefix in self.path_prefixes):
            return None
        query = f"?{parts.query}" if parts.query else ""
        return f"https://{host}{quote(path, safe=_PATH_SAFE)}{query}"
