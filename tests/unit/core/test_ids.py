"""Identity contract and regression tests, entirely offline."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest
from hypothesis import given
from hypothesis import strategies as st

from research_mcp.core import ids


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" DOI:10.1145/3649835. ", "10.1145/3649835"),
        ("https://doi.org/10.1000/ABC%2FDEF", "10.1000/abc/def"),
        ("http://dx.doi.org/10.1000/ABC);", "10.1000/abc"),
        ("10.1000/part/subpart/", "10.1000/part/subpart/"),
        ("10.123456789/ABC", "10.123456789/abc"),
        ("10.1000/%252FABC", "10.1000//abc"),
    ],
)
def test_doi(raw: str, expected: str) -> None:
    """AT-SRCH-10: DOI prefixes, escapes, punctuation and suffix slashes."""
    assert ids.normalize_doi(raw) == expected
    assert ids.normalize_doi(expected) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "10.123/x",
        "10.1234567890/x",
        "10.1000/",
        "10.1000/a b",
        "10.1000/%FF",
        "10.1000/%C3%28",
        "10.1000/%xy",
    ],
)
def test_bad_doi(raw: str) -> None:
    """AT-SRCH-10: Invalid DOI forms and invalid UTF-8 are refused."""
    with pytest.raises(ids.IdentifierError):
        ids.normalize_doi(raw)


@pytest.mark.parametrize(
    ("raw", "value", "version"),
    [
        ("2410.18291v1", "2410.18291", 1),
        ("2410.18291", "2410.18291", None),
        ("arXiv:2410.18291v2", "2410.18291", 2),
        ("https://arxiv.org/abs/2410.18291v1", "2410.18291", 1),
        ("https://arxiv.org/pdf/2410.18291v1.pdf", "2410.18291", 1),
        ("ARXIV:HEP-TH/9901001v3", "hep-th/9901001", 3),
        ("math.ag/0301001", "math.AG/0301001", None),
    ],
)
def test_arxiv(raw: str, value: str, version: int | None) -> None:
    """AT-SRCH-11: arXiv version is separate from modern and legacy identities."""
    assert ids.normalize_arxiv(raw) == (value, version)
    assert ids.parse_any(raw) == ids.Identifier("arxiv", value, version)


@pytest.mark.parametrize(
    ("normalizer", "raw", "expected"),
    [
        (ids.normalize_pmid, "PMID:12345", "12345"),
        (ids.normalize_pmid, "https://pubmed.ncbi.nlm.nih.gov/12345/", "12345"),
        (ids.normalize_pmcid, "pmcid:pmc123", "PMC123"),
        (ids.normalize_pmcid, "123", "PMC123"),
        (ids.normalize_openalex, "https://api.openalex.org/works/w123", "W123"),
        (ids.normalize_openalex, "https://openalex.org/W123", "W123"),
        (ids.normalize_s2, "s2:" + "AB" * 20, "ab" * 20),
        (ids.normalize_s2, "https://www.semanticscholar.org/paper/title/" + "AB" * 20, "ab" * 20),
        (ids.normalize_core, "https://core.ac.uk/outputs/123", "123"),
        (ids.normalize_nct, "https://clinicaltrials.gov/study/nct01234567", "NCT01234567"),
        (ids.normalize_rfc, "https://www.rfc-editor.org/rfc/rfc09110.txt", "9110"),
        (ids.normalize_handle, "https://hdl.handle.net/123.45/AbC/nested/", "123.45/AbC/nested/"),
        (
            ids.normalize_dspace_uuid,
            "UUID:ABCDEF12-1234-5678-90AB-123456789ABC",
            "abcdef12-1234-5678-90ab-123456789abc",
        ),
    ],
)
def test_canonical_forms(normalizer: Callable[[str], str], raw: str, expected: str) -> None:
    """AT-SRCH-12: All non-DOI scholarly schemes have canonical forms."""
    assert normalizer(raw) == expected
    assert normalizer(expected) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "HTTPS://Example.ORG:443/Case/Path?utm_source=x&keep=Yes&fbclid=x#frag",
            "https://example.org/Case/Path?keep=Yes",
        ),
        ("http://EXAMPLE.org:80/?gclid=x&empty=&a=1&a=2", "http://example.org/?empty=&a=1&a=2"),
        ("https://example.org:8443/A%2Fb", "https://example.org:8443/A%2Fb"),
        ("http://[::1]:80/", "http://[::1]/"),
    ],
)
def test_url(raw: str, expected: str) -> None:
    """AT-SRCH-13: URL normalization preserves path case and meaningful query values."""
    assert ids.normalize_url(raw) == expected
    assert ids.normalize_url(expected) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.org/%FF",
        "https://example.org/?x=%FF",
        "https://[broken",
        "https://example.org:bad",
        "relative/path",
    ],
)
def test_invalid_url(raw: str) -> None:
    """AT-SRCH-13: Malformed URLs and invalid UTF-8 fail with IdentifierError."""
    with pytest.raises(ids.IdentifierError):
        ids.normalize_url(raw)


@pytest.mark.parametrize(
    ("raw", "scheme", "value"),
    [
        ("doi:10.1000/ABC", "doi", "10.1000/abc"),
        ("https://doi.org/10.1000/ABC", "doi", "10.1000/abc"),
        ("PMC123", "pmcid", "PMC123"),
        ("123", "pmid", "123"),
        ("core:123", "core", "123"),
        ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123/", "pmcid", "PMC123"),
        ("W123", "openalex", "W123"),
        ("NCT01234567", "nct", "NCT01234567"),
        ("RFC 9110", "rfc", "9110"),
        ("a" * 40, "s2", "a" * 40),
        ("123.45/Case/", "handle", "123.45/Case/"),
        (
            "abcdef12-1234-5678-90ab-123456789abc",
            "dspace_uuid",
            "abcdef12-1234-5678-90ab-123456789abc",
        ),
        ("github:Owner/Repo.git.git", "github", "owner/repo"),
        ("https://GitHub.com/Owner/Repo.git", "github", "owner/repo"),
        ("https://example.org/Doc.pdf", "url", "https://example.org/Doc.pdf"),
    ],
)
def test_detect(raw: str, scheme: str, value: str) -> None:
    """AT-SRCH-14: Explicit prefixes, recognized hosts and bare shapes select schemes."""
    assert ids.parse_any(raw) == ids.Identifier(scheme, value)


@pytest.mark.parametrize(
    "raw",
    [
        "doi_10.1145_3649835",
        "core_123",
        "paper.pdf",
        "arxiv:2410.18291.pdf",
        "unknown:123",
        "words",
        "",
        "x\x00y",
    ],
)
def test_reject_unknown(raw: str) -> None:
    """AT-SRCH-14: Unknown input and filename shapes never become identifiers."""
    with pytest.raises(ids.IdentifierError):
        ids.parse_any(raw)


@given(
    number=st.integers(min_value=1, max_value=99999999),
    upper=st.booleans(),
    padding=st.sampled_from(["", " ", "\t", "\n "]),
)
def test_normalizer_properties(number: int, upper: bool, padding: str) -> None:
    """AT-SRCH-15: Normalizers are idempotent and stable under valid case and whitespace changes."""
    cases = [
        (ids.normalize_doi, f"doi:10.1000/item{number}"),
        (ids.normalize_pmid, f"pmid:{number}"),
        (ids.normalize_pmcid, f"pmc{number}"),
        (ids.normalize_openalex, f"w{number}"),
        (ids.normalize_s2, f"{number:040x}"),
        (ids.normalize_core, f"core:{number}"),
        (ids.normalize_nct, f"nct{number:08d}"),
        (ids.normalize_rfc, f"rfc:{number:09d}"),
        (ids.normalize_handle, f"{number}/123/nested/"),
        (ids.normalize_dspace_uuid, f"abcdef12-1234-5678-90ab-{number:012x}"),
        (ids.normalize_github, f"github:owner/repo{number}.git.git"),
        (ids.normalize_url, f"https://example.org/{number}?utm_source=x"),
    ]
    for normalizer, raw in cases:
        expected = normalizer(raw)
        # Handle suffixes and URL paths/queries are case sensitive.
        variant = (
            raw.upper()
            if upper and normalizer not in {ids.normalize_handle, ids.normalize_url}
            else raw
        )
        assert normalizer(padding + variant + padding) == expected
        assert normalizer(expected) == expected
    raw_arxiv = f"math.AG/0301001v{number}"
    value, version = ids.normalize_arxiv(
        padding + (raw_arxiv.upper() if upper else raw_arxiv) + padding
    )
    assert ids.normalize_arxiv(value) == (value, None)
    assert ids.normalize_arxiv(f"{value}v{version}") == (value, version)
    assert ids.title_key(ids.title_key("The Ａrt of Science!")) == ids.title_key(
        "The Ａrt of Science!"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  The Ｓｔｕｄｙ of SCIENCE: a review! ", "study science review"),
        ("Straße and STRASSE", "strasse strasse"),
        ("Cafe\u0301, with café", "café café"),
        ("Graph-based\tmethods\nfor research", "graph based methods research"),
        ("the and of", ""),
    ],
)
def test_title(raw: str, expected: str) -> None:
    """AT-SRCH-16: NFKC, casefold, punctuation, stop words and whitespace normalize titles."""
    assert ids.title_key(raw) == expected


def test_identifier_frozen() -> None:
    """AT-SRCH-14: Parsed identifiers are immutable dataclass values."""
    ident = ids.parse_any("pmid:123")
    with pytest.raises(FrozenInstanceError):
        ident.value = "456"


@pytest.mark.parametrize(
    ("normalizer", "raw"),
    [
        (ids.normalize_arxiv, "2410.123"),
        (ids.normalize_pmid, "12x"),
        (ids.normalize_pmcid, "PMC"),
        (ids.normalize_openalex, "A123"),
        (ids.normalize_s2, "abc"),
        (ids.normalize_core, "core_123"),
        (ids.normalize_nct, "NCT123"),
        (ids.normalize_rfc, "RFC-1"),
        (ids.normalize_handle, "123/"),
        (ids.normalize_dspace_uuid, "not-a-uuid"),
        (ids.normalize_github, "github:owner/.."),
        (ids.normalize_github, "https://example.org/owner/repo"),
    ],
)
def test_invalid_scheme_forms(normalizer: Callable[[str], object], raw: str) -> None:
    """AT-SRCH-12: Scheme normalizers refuse malformed values and unexpected URL hosts."""
    with pytest.raises(ids.IdentifierError):
        normalizer(raw)


@pytest.mark.parametrize(
    "normalizer",
    [
        ids.normalize_doi,
        ids.normalize_arxiv,
        ids.normalize_pmid,
        ids.normalize_pmcid,
        ids.normalize_openalex,
        ids.normalize_s2,
        ids.normalize_core,
        ids.normalize_nct,
        ids.normalize_rfc,
        ids.normalize_handle,
        ids.normalize_dspace_uuid,
        ids.normalize_github,
        ids.normalize_url,
    ],
)
@pytest.mark.parametrize("escape", ["%FF", "%C3%28", "%ED%A0%80"])
def test_strict_utf8_decoding(normalizer: Callable[[str], object], escape: str) -> None:
    """AT-SRCH-15: Every identifier normalizer rejects invalid UTF-8 escapes."""
    raw = f"https://example.org/{escape}" if normalizer is ids.normalize_url else escape
    with pytest.raises(ids.IdentifierError, match="Invalid UTF-8 escape"):
        normalizer(raw)
