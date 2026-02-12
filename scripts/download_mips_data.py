#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.external.mips_download import (
    REQUIRED_FILENAMES,
    discover_sources,
    download_sources,
    load_sources_csv,
    write_manifest,
    write_sources_template,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover and download MIPS source files.")
    parser.add_argument("--year", type=int, default=2023, help="MIPS performance year.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "external" / "mips",
        help="Base output directory. Files are placed under <out-dir>/<year>/",
    )
    parser.add_argument(
        "--sources-csv",
        type=Path,
        default=ROOT / "config" / "mips_sources.csv",
        help="Optional override CSV with columns: filename,url",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover and report without downloading.")
    parser.add_argument(
        "--write-template",
        action="store_true",
        help="Write an editable template sources CSV and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.write_template:
        write_sources_template(args.sources_csv)
        print(f"Wrote template: {args.sources_csv}")
        return 0

    year_dir = args.out_dir / str(args.year)
    manual_sources = load_sources_csv(args.sources_csv)
    discovered = discover_sources(args.year, REQUIRED_FILENAMES)
    filename_to_url = {fn: manual_sources.get(fn) or discovered.get(fn) for fn in REQUIRED_FILENAMES}

    print(f"Target folder: {year_dir}")
    for fn in REQUIRED_FILENAMES:
        source = filename_to_url.get(fn)
        print(f"- {fn}: {'found' if source else 'missing'}")
    if any(not filename_to_url.get(fn) for fn in REQUIRED_FILENAMES):
        print(
            "Tip: populate missing URLs in "
            f"{args.sources_csv} (columns: filename,url), then rerun this command."
        )

    results = download_sources(year_dir, filename_to_url, dry_run=args.dry_run)
    manifest_path = year_dir / "download_manifest.json"
    write_manifest(manifest_path, args.year, results)

    downloaded = sum(1 for r in results if r.status == "downloaded")
    dry = sum(1 for r in results if r.status == "dry_run")
    missing = sum(1 for r in results if r.status == "missing_url")
    failed = len(results) - downloaded - dry - missing
    print(f"Summary: downloaded={downloaded} dry_run={dry} missing_url={missing} failed={failed}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
