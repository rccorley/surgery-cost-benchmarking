from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import json
import re
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlretrieve


CKAN_SEARCH_URL = "https://data.cms.gov/api/3/action/package_search"
DEFAULT_TIMEOUT_SECONDS = 45

REQUIRED_FILENAMES = [
    "ec_public_reporting.csv",
    "ec_score_file.csv",
    "grp_public_reporting.csv",
    "Facility_Affiliation.csv",
]


@dataclass
class DownloadResult:
    filename: str
    url: str | None
    status: str
    detail: str = ""


def _http_get_json(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    with urlopen(url, timeout=timeout) as r:
        payload = r.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def _score_resource(filename: str, year: int, resource: dict) -> int:
    score = 0
    name = str(resource.get("name", "")).lower()
    url = str(resource.get("url", "")).lower()
    target = filename.lower()
    if target in name:
        score += 80
    if target in url:
        score += 80
    if str(year) in name:
        score += 20
    if str(year) in url:
        score += 20
    if "qpp" in name or "qpp" in url:
        score += 10
    if "mips" in name or "mips" in url:
        score += 10
    if url.endswith(".csv"):
        score += 5
    return score


def discover_source_for_filename(filename: str, year: int) -> str | None:
    """Best-effort discovery from CMS CKAN package search."""
    query = f"{filename} {year} qpp mips"
    search_url = f"{CKAN_SEARCH_URL}?q={query.replace(' ', '+')}&rows=50"
    try:
        payload = _http_get_json(search_url)
    except Exception:
        return None
    if not payload.get("success"):
        return None

    results = payload.get("result", {}).get("results", [])
    best_url = None
    best_score = -1
    for pkg in results:
        for res in pkg.get("resources", []) or []:
            url = str(res.get("url", "")).strip()
            if not url:
                continue
            score = _score_resource(filename, year, res)
            if score > best_score:
                best_score = score
                best_url = url
    return best_url


def discover_sources(year: int, filenames: Iterable[str]) -> dict[str, str | None]:
    return {fn: discover_source_for_filename(fn, year) for fn in filenames}


def load_sources_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = str(row.get("filename", "")).strip()
            url = str(row.get("url", "")).strip()
            if fn and url:
                out[fn] = url
    return out


def write_sources_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "url"])
        writer.writeheader()
        for fn in REQUIRED_FILENAMES:
            writer.writerow({"filename": fn, "url": ""})


def download_sources(
    out_dir: Path,
    filename_to_url: dict[str, str | None],
    dry_run: bool = False,
) -> list[DownloadResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[DownloadResult] = []
    for filename, url in filename_to_url.items():
        if not url:
            results.append(DownloadResult(filename=filename, url=None, status="missing_url"))
            continue
        if dry_run:
            results.append(DownloadResult(filename=filename, url=url, status="dry_run"))
            continue

        target = out_dir / filename
        try:
            urlretrieve(url, target)
            results.append(DownloadResult(filename=filename, url=url, status="downloaded"))
        except HTTPError as e:
            results.append(DownloadResult(filename=filename, url=url, status="http_error", detail=str(e.code)))
        except URLError as e:
            results.append(DownloadResult(filename=filename, url=url, status="url_error", detail=str(e.reason)))
        except Exception as e:  # pragma: no cover - defensive
            results.append(DownloadResult(filename=filename, url=url, status="error", detail=repr(e)))
    return results


def write_manifest(path: Path, year: int, results: list[DownloadResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "year": year,
        "results": [asdict(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
