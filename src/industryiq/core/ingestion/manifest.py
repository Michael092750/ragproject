"""Provenance metadata from a category's ``manifest.csv``.

The report collector drops a ``manifest.csv`` next to the PDFs in each category
folder (see the ``report-library`` layout). Its columns
``status,url,filename,domain,detected_year,size_bytes,sha256,error`` record where
each file came from. This module turns those rows into the document-level chunk
metadata the manifest can supply:

* ``publisher``       <- ``domain`` (the registrable host, ``www.`` stripped)
* ``published_date``  <- ``detected_year`` (a year; ISO-sortable as the stores want)
* ``source_type``     <- ``domain``, via the heuristic :func:`classify_source_type`

Files with no manifest row (or no manifest at all) simply get none of these --
absent provenance is left unset, never guessed.

Older collector runs wrote the same fields under different names, so reads are
tolerant of a few aliases: ``source_domain`` for ``domain``, ``year_score`` for
``detected_year``, and a ``filename`` that is a full (possibly foreign) path
rather than a bare name -- the join is always by base name.
"""

import csv
import re
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.csv"

# A four-digit 19xx/20xx year, used to keep only plausible years (and reject a
# "0" / blank "unknown" sentinel some manifests use).
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# Per-scan memo of parsed manifests, keyed by manifest path -> (filename -> meta).
ManifestCache = dict[Path, dict[str, dict[str, Any]]]

# Heuristic domain -> source_type table. Deliberately small and explicit: it is
# the obvious starting point, easy to extend, and any unrecognised domain is left
# unclassified rather than mislabeled. Match is on the second-level domain (e.g.
# "mckinsey" in "www.mckinsey.com").
_CONSULTANCIES = frozenset(
    {
        "mckinsey",
        "bcg",
        "bain",
        "deloitte",
        "pwc",
        "kpmg",
        "ey",
        "accenture",
        "gartner",
        "forrester",
        "idc",
        "oliverwyman",
        "rolandberger",
        "kearney",
        "strategyand",
        "capgemini",
    }
)
# Inter-governmental / multilateral bodies (treated as government for filtering;
# the project's source preference flags these as *not* industry analysis).
_IGO = frozenset(
    {"worldbank", "imf", "oecd", "un", "wto", "weforum", "europa", "iea", "who", "unctad"}
)


def classify_source_type(domain: str) -> str:
    """Best-effort publisher *type* for a host, or ``""`` when unrecognised.

    Returns one of ``consultancy`` / ``government`` / ``academic`` /
    ``association`` / ``company``. The classification is intentionally coarse and
    heuristic -- enough to facet retrieval by who published a report -- and errs
    toward ``""`` (unset) over a wrong label for hosts it doesn't recognise.
    """
    labels = domain.lower().strip().removeprefix("www.").split(".")
    labels = [label for label in labels if label]
    if not labels:
        return ""
    tld = labels[-1]
    sld = labels[-2] if len(labels) >= 2 else labels[0]
    if sld in _CONSULTANCIES:
        return "consultancy"
    if sld in _IGO or tld in {"gov", "mil", "int"}:
        return "government"
    if tld == "edu" or "ac" in labels:
        return "academic"
    if tld == "org":
        return "association"
    if tld in {"com", "net", "io", "ai", "co", "biz"}:
        return "company"
    return ""


def _row_year(row: dict[str, str]) -> str:
    """A four-digit publication year from the row, or ``""``.

    Reads ``detected_year`` (canonical) or ``year_score`` (an older collector's
    name for the field) and keeps only a plausible 19xx/20xx year -- so an
    "unknown" sentinel like ``"0"`` is treated as absent, not stamped as year 0.
    """
    raw = (row.get("detected_year") or row.get("year_score") or "").strip()
    match = _YEAR_RE.search(raw)
    return match.group(0) if match else ""


def _basename(filename: str) -> str:
    """Last path segment of ``filename``, tolerating either separator.

    Some collector runs stored an absolute path (often from another machine)
    instead of a bare name; the join to PDFs is by base name, so normalise here.
    """
    return filename.replace("\\", "/").rsplit("/", 1)[-1]


def _row_metadata(row: dict[str, str]) -> dict[str, Any]:
    """Map one manifest row to the doc-level metadata keys it can supply."""
    meta: dict[str, Any] = {}
    domain = (row.get("domain") or row.get("source_domain") or "").strip()
    if domain:
        publisher = domain.lower().removeprefix("www.")
        if publisher:
            meta["publisher"] = publisher
        source_type = classify_source_type(domain)
        if source_type:
            meta["source_type"] = source_type
    year = _row_year(row)
    if year:
        meta["published_date"] = year
    return meta


def load_manifest(manifest_path: Path) -> dict[str, dict[str, Any]]:
    """Read ``manifest_path``, returning ``filename -> doc-level metadata``.

    Unreadable or malformed manifests yield ``{}`` -- a missing manifest must
    never abort an ingest, only leave provenance unset.
    """
    try:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeDecodeError, csv.Error):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        filename = _basename((row.get("filename") or "").strip())
        if filename:
            result[filename] = _row_metadata(row)
    return result


def manifest_metadata(file_path: Path, cache: ManifestCache) -> dict[str, Any]:
    """Doc-level metadata for ``file_path`` from its sibling ``manifest.csv``.

    ``cache`` memoizes each manifest by path across a scan, so a category's
    manifest is parsed once however many files it lists. Returns ``{}`` when the
    file has no manifest or no row in it.
    """
    manifest_path = file_path.parent / MANIFEST_NAME
    if manifest_path not in cache:
        cache[manifest_path] = load_manifest(manifest_path) if manifest_path.is_file() else {}
    return dict(cache[manifest_path].get(file_path.name, {}))
