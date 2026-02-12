from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.external.mips_download import (
    REQUIRED_FILENAMES,
    download_sources,
    load_sources_csv,
    write_manifest,
    write_sources_template,
)


def test_write_and_load_sources_template(tmp_path: Path) -> None:
    path = tmp_path / "mips_sources.csv"
    write_sources_template(path)
    loaded = load_sources_csv(path)
    # template has blank URLs, so loader should return empty mapping
    assert loaded == {}


def test_download_sources_dry_run(tmp_path: Path) -> None:
    mapping = {fn: f"https://example.com/{fn}" for fn in REQUIRED_FILENAMES}
    out = download_sources(tmp_path, mapping, dry_run=True)
    assert len(out) == len(REQUIRED_FILENAMES)
    assert all(r.status == "dry_run" for r in out)


def test_write_manifest(tmp_path: Path) -> None:
    results = download_sources(tmp_path, {"ec_public_reporting.csv": None}, dry_run=True)
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest, 2023, results)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["year"] == 2023
    assert "results" in payload
