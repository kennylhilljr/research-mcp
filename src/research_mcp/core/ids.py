"""Pure canonicalization and detection of research identifiers."""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


class IdentifierError(ValueError):
    """An input cannot be interpreted as a supported identifier."""


@dataclass(frozen=True)
class Identifier:
    scheme: str
    value: str
    version: int | None = None


def _text(s: str) -> str:
    s = s.strip()
    if not s or any(unicodedata.category(c) == "Cc" for c in s):
        raise IdentifierError("Empty identifier or control character")
    return s


def _unquote(s: str) -> str:
    if re.search(r"%(?![0-9a-fA-F]{2})", s):
        raise IdentifierError("Invalid percent escape")
    try:
        return unquote(s, errors="strict")
    except UnicodeError as exc:
        raise IdentifierError("Invalid UTF-8 escape") from exc


def _decode(s: str) -> str:
    # Decode once and keep literal percent signs escaped, so a second call is a no-op.
    return _text(_unquote(s).replace("%", "%25"))


def _is_url(s: str) -> bool:
    return re.match(r"[a-z][a-z0-9+.-]*://", s, flags=re.I) is not None


def _match(s: str, pattern: str) -> str:
    # Unicode mode, so \S also refuses non-ASCII whitespace; digit classes are spelled [0-9].
    if re.fullmatch(pattern, s) is None:
        raise IdentifierError("Invalid identifier form")
    return s


def _payload(s: str, prefixes: tuple[str, ...], hosts: tuple[str, ...] = ()) -> str:
    s = _text(s)
    for prefix in prefixes:
        if s.lower().startswith(prefix + ":"):
            s = s[len(prefix) + 1 :].strip()
            break
    if _is_url(s):
        try:
            url = urlsplit(s)
            if url.scheme.lower() not in {"http", "https"} or url.hostname not in hosts:
                raise IdentifierError("Unexpected identifier host")
            s = url.path.removeprefix("/")
        except ValueError as exc:
            raise IdentifierError("Invalid identifier URL") from exc
    return _decode(s)


# @spec SRCH-10
def normalize_doi(s: str) -> str:
    s = _payload(s, ("doi",), ("doi.org", "dx.doi.org")).lower()
    # Any Unicode punctuation trails off, except the slash some DOI suffixes end with.
    while s and s[-1] != "/" and unicodedata.category(s[-1]).startswith("P"):
        s = s[:-1]
    return _match(s, r"10\.[0-9]{4,9}/\S+")


# @spec SRCH-11
def normalize_arxiv(s: str) -> tuple[str, int | None]:
    s = _payload(s, ("arxiv",), ("arxiv.org", "www.arxiv.org"))
    s = re.sub(r"^(abs|pdf)/", "", s, flags=re.I)
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    version_match = re.search(r"v([0-9]+)$", s, flags=re.I)
    version = int(version_match[1]) if version_match else None
    if version_match:
        s = s[: version_match.start()]
    s = s.lower()
    s = re.sub(r"\.[a-z]{2}/", lambda m: m[0].upper(), s)
    return _match(s, r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})"), version


# @spec SRCH-12
def normalize_pmid(s: str) -> str:
    s = _payload(s, ("pmid",), ("pubmed.ncbi.nlm.nih.gov",))
    return _match(s.rstrip("/"), r"[0-9]+")


# @spec SRCH-12
def normalize_pmcid(s: str) -> str:
    s = _payload(
        s, ("pmcid",), ("pmc.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov")
    )
    s = re.sub(r"^(?:pmc/)?articles/", "", s, flags=re.I).rstrip("/").upper()
    return "PMC" + _match(s.removeprefix("PMC"), r"[0-9]+")


# @spec SRCH-12
def normalize_openalex(s: str) -> str:
    s = _payload(s, ("openalex",), ("openalex.org", "www.openalex.org", "api.openalex.org"))
    s = re.sub(r"^works/", "", s, flags=re.I).rstrip("/")
    return _match(s.upper(), r"W[0-9]+")


# @spec SRCH-12
def normalize_s2(s: str) -> str:
    s = _payload(s, ("s2", "semantic_scholar"), ("semanticscholar.org", "www.semanticscholar.org"))
    if s.lower().startswith("paper/"):
        s = s.rstrip("/").rsplit("/", 1)[-1]
    return _match(s.lower(), r"[0-9a-f]{40}")


# @spec SRCH-12
def normalize_core(s: str) -> str:
    s = _payload(s, ("core",), ("core.ac.uk",))
    s = re.sub(r"^(?:works|outputs)/", "", s, flags=re.I).rstrip("/")
    return _match(s, r"[0-9]+")


# @spec SRCH-12
def normalize_nct(s: str) -> str:
    s = _payload(s, ("nct",), ("clinicaltrials.gov", "www.clinicaltrials.gov"))
    s = re.sub(r"^(?:study|ct2/show)/", "", s, flags=re.I).rstrip("/").upper()
    return "NCT" + _match(s.removeprefix("NCT"), r"[0-9]{8}")


# @spec SRCH-12
def normalize_rfc(s: str) -> str:
    s = _payload(s, ("rfc",), ("rfc-editor.org", "www.rfc-editor.org", "datatracker.ietf.org"))
    s = re.sub(r"^(?:rfc/|doc/html/)", "", s, flags=re.I)
    s = re.sub(r"^rfc\s*", "", s, flags=re.I)
    s = re.sub(r"\.(?:txt|html)$", "", s, flags=re.I)
    return str(int(_match(s, r"[0-9]+")))


# @spec SRCH-12
def normalize_handle(s: str) -> str:
    s = _payload(s, ("handle", "hdl"), ("hdl.handle.net",))
    return _match(s, r"[0-9]+(?:\.[0-9]+)*/\S+")


# @spec SRCH-12
def normalize_dspace_uuid(s: str) -> str:
    s = _payload(s, ("dspace_uuid", "uuid"))
    return _match(s.lower(), r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def normalize_github(s: str) -> str:
    s = _payload(s, ("github",), ("github.com", "www.github.com")).lower().rstrip("/")
    while s.endswith(".git"):
        s = s[:-4]
    s = _match(s, r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?/[a-z0-9_.-]+")
    if s.split("/")[1] in {".", ".."}:
        raise IdentifierError("Invalid repository name")
    return s


# @spec SRCH-13, SRCH-38
def normalize_url(s: str) -> str:
    s = _text(s)
    if any(c.isspace() for c in s):
        # urlsplit strips trailing spaces, so a raw space would not survive a second pass.
        raise IdentifierError("Unencoded whitespace in URL")
    _unquote(s)  # Validate escapes, retaining reserved URL characters in their encoded form.
    try:
        url = urlsplit(s)
        scheme = url.scheme.lower()
        if scheme not in {"http", "https"} or not url.hostname or url.username is not None:
            raise IdentifierError("Expected an absolute HTTP URL without credentials")
        host = url.hostname.lower()
        host = f"[{host}]" if ":" in host else host
        port = url.port
        if port is not None and (scheme, port) not in {("http", 80), ("https", 443)}:
            host += f":{port}"
        query = [
            (k, v)
            for k, v in parse_qsl(url.query, keep_blank_values=True, errors="strict")
            if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
        ]
        path = url.path
        if path == "/":
            path = ""
        elif path.endswith("/"):
            path = path[:-1]
        return urlunsplit((scheme, host, path, urlencode(query), ""))
    except (ValueError, UnicodeError) as exc:
        raise IdentifierError("Invalid URL") from exc


_NORMALIZERS: dict[str, Callable[[str], str]] = {
    "doi": normalize_doi,
    "pmid": normalize_pmid,
    "pmcid": normalize_pmcid,
    "openalex": normalize_openalex,
    "s2": normalize_s2,
    "core": normalize_core,
    "nct": normalize_nct,
    "rfc": normalize_rfc,
    "handle": normalize_handle,
    "dspace_uuid": normalize_dspace_uuid,
    "github": normalize_github,
    "url": normalize_url,
}
_ALIASES = {"hdl": "handle", "uuid": "dspace_uuid", "semantic_scholar": "s2"}
_HOSTS = {
    "doi.org": "doi",
    "dx.doi.org": "doi",
    "arxiv.org": "arxiv",
    "pubmed.ncbi.nlm.nih.gov": "pmid",
    "pmc.ncbi.nlm.nih.gov": "pmcid",
    "ncbi.nlm.nih.gov": "pmcid",
    "openalex.org": "openalex",
    "api.openalex.org": "openalex",
    "semanticscholar.org": "s2",
    "core.ac.uk": "core",
    "clinicaltrials.gov": "nct",
    "rfc-editor.org": "rfc",
    "datatracker.ietf.org": "rfc",
    "hdl.handle.net": "handle",
    "github.com": "github",
}
_SHAPES = (
    (r"10\.\d{4,9}/", "doi"),
    (r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v\d+)?$", "arxiv"),
    (r"PMC\d+$", "pmcid"),
    (r"W\d+$", "openalex"),
    (r"NCT\d{8}$", "nct"),
    (r"RFC\s*\d+$", "rfc"),
    (r"[0-9a-f]{40}$", "s2"),
    (r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$", "dspace_uuid"),
    (r"\d+(?:\.\d+)*/", "handle"),
    (r"\d+$", "pmid"),
)


# @spec SRCH-14, SRCH-15
def parse_any(s: str) -> Identifier:
    s = _text(s)
    prefix, separator, rest = s.partition(":")
    scheme = _ALIASES.get(prefix.lower(), prefix.lower())
    if separator and scheme == "url":
        # The other normalizers strip their own prefix; normalize_url takes a bare URL.
        s = rest.strip()
    # Run after the url: prefix is gone so a prefixed URL ending .pdf is judged as a URL.
    if not _is_url(s) and (s.lower().endswith(".pdf") or re.match(r"(?i)(doi|core)_", s)):
        raise IdentifierError("File names are not identifiers")
    if not (separator and scheme in {*_NORMALIZERS, "arxiv"}):
        if _is_url(s):
            try:
                host = (urlsplit(s).hostname or "").removeprefix("www.")
            except ValueError as exc:
                raise IdentifierError("Invalid URL") from exc
            scheme = _HOSTS.get(host, "url")
        else:
            scheme = next((name for pattern, name in _SHAPES if re.match(pattern, s, re.I)), "")
    if scheme == "arxiv":
        value, version = normalize_arxiv(s)
        return Identifier(scheme, value, version)
    if scheme in _NORMALIZERS:
        return Identifier(scheme, _NORMALIZERS[scheme](s))
    raise IdentifierError("Unknown identifier scheme")


_STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    ]
)


# @spec SRCH-16
def title_key(title: str) -> str:
    text = unicodedata.normalize("NFKC", title).casefold()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return " ".join(word for word in text.split() if word not in _STOP_WORDS)
