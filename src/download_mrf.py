#!/usr/bin/env python3
"""Download public hospital machine-readable price transparency files.

Hospitals are required by CMS to publish machine-readable files (MRFs)
containing their standard charges.  This script fetches the files for the
Bellingham-to-Seattle corridor hospitals used in this project.

Usage:
    python src/download_mrf.py                    # download all
    python src/download_mrf.py --list             # show sources without downloading
    python src/download_mrf.py --only peacehealth # download one hospital

After downloading, run the benchmark pipeline:
    python src/benchmark.py \\
      --input data/raw \\
      --hospitals config/hospitals.csv \\
      --procedures config/surgical_procedures.csv \\
      --focus-hospital "PeaceHealth St. Joseph Medical Center" \\
      --output data/processed
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


# ── Hospital MRF sources ───────────────────────────────────────────
#
# Each entry: (short_key, hospital_name, url, output_filename)
#
# URL notes:
#   - PeaceHealth publishes a ZIP containing a wide-format CSV.
#   - Providence/Swedish publish JSON files following the CMS schema.
#   - Some hospitals use Cloudflare/WAF protection; those are marked
#     "blocked" and must be downloaded manually via a browser.
#
# To add a hospital, append to this list and (if needed) add a
# parser rule in benchmark.py:_infer_hospital_name_from_source().

SOURCES: list[tuple[str, str, str, str]] = [
    # ── PeaceHealth (Craneware ZIP → wide-format CSV) ──────────────
    (
        "peacehealth",
        "PeaceHealth St Joseph Medical Center",
        "https://apim.services.craneware.com/api-pricing-transparency/"
        "api/public/c2b5051ecb723f5355be61d1a3eb6c28/charges/mrf",
        "peacehealth_st_joseph_mrf.zip",
    ),
    (
        "peacehealth_united_general",
        "PeaceHealth United General Hospital",
        "https://apim.services.craneware.com/api-pricing-transparency/"
        "api/public/51492878d96ce15d3ad32eec16ccc830/charges/mrf",
        "peacehealth_united_general_mrf.zip",
    ),
    # ── Providence / Swedish (CMS-schema JSON) ─────────────────────
    (
        "providence_everett",
        "Providence Regional Medical Center Everett",
        "https://pricetransparency.providence.org/wamt/live/"
        "352346161_providence-regional-medical-center-everett_standardcharges.json",
        "providence_everett_standardcharges.json",
    ),
    (
        "swedish_seattle",
        "Swedish Medical Center (Seattle / First Hill)",
        "https://pricetransparency.providence.org/swedish/live/"
        "910433740_swedish-medical-center_standardcharges.json",
        "910433740_swedish-medical-center_standardcharges.json",
    ),
    (
        "swedish_cherry_hill",
        "Swedish Medical Center Cherry Hill",
        "https://pricetransparency.providence.org/swedish/live/"
        "910373400_swedish-medical-center-cherry-hill_standardcharges.json",
        "910373400_swedish-medical-center-cherry-hill_standardcharges.json",
    ),
    (
        "swedish_edmonds",
        "Swedish Edmonds",
        "https://pricetransparency.providence.org/swedish/live/"
        "272305304_swedish-edmonds-hospital_standardcharges.json",
        "swedish_edmonds_standardcharges.json",
    ),
    (
        "swedish_issaquah",
        "Swedish Medical Center Issaquah",
        "https://pricetransparency.providence.org/swedish/live/"
        "910433740_swedish-medical-center-issaquah_standardcharges.json",
        "910433740_swedish-medical-center-issaquah_standardcharges.json",
    ),
    # ── UW Medicine (CMS-schema JSON) ──────────────────────────────
    (
        "uw_medical_center",
        "UW Medical Center",
        "https://www.uwmedicine.org/sites/stevie/files/mrf/"
        "916001537_university-of-washington-medical-center_standardcharges.json",
        "uw_medical_center_standardcharges.json",
    ),
    (
        "harborview",
        "Harborview Medical Center",
        "https://www.uwmedicine.org/sites/stevie/files/mrf/"
        "911631806_harborview-medical-center_standardcharges.json",
        "harborview_standardcharges.json",
    ),
    # ── Skagit Regional (CSV — may bypass Cloudflare WAF) ─────────
    (
        "skagit_valley",
        "Skagit Valley Hospital",
        "https://www.skagitregionalhealth.org/docs/default-source/"
        "finance-and-billing/chargemasters/"
        "562392010_skagit-valley-hospital_standardcharges.csv",
        "skagit_valley_standardcharges.csv",
    ),
    (
        "cascade_valley",
        "Cascade Valley Hospital",
        "https://www.skagitregionalhealth.org/docs/default-source/"
        "finance-and-billing/chargemasters/"
        "562392010_cascade-valley-hospital_standardcharges.csv",
        "cascade_valley_standardcharges.csv",
    ),
    # ── Eastside / Seattle ─────────────────────────────────────────
    (
        "overlake",
        "Overlake Medical Center",
        "https://hospitalpricedisclosure.com/Download.aspx?"
        "pxi=jFpZaWS9NVsNmAQiukfKew*-*&f=iFd*_*cEPwhQHJy3lVvHy9uQ*-*",
        "overlake_standardcharges.csv",
    ),
    (
        "evergreenhealth",
        "EvergreenHealth Medical Center",
        "https://stmlevergreenncus001.blob.core.windows.net/public/"
        "910844563_KING-COUNTY-PUBLIC-HOSPITAL-DISTRICT-NO2_standardcharges.csv",
        "evergreenhealth_standardcharges.csv",
    ),
]


# ── Helpers ─────────────────────────────────────────────────────────

USER_AGENT = (
    "SurgeryCostBenchmark/1.0 "
    "(open-source research; https://github.com/rccorley/surgery-cost-benchmarking)"
)

MAX_RETRIES = 3
BACKOFF_SECS = [2, 4, 8]


def _download(url: str, dest: Path) -> bool:
    """Download a URL to a local file with retries."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Downloading {url}")
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            size_mb = len(data) / (1024 * 1024)
            print(f"  -> Saved {dest.name} ({size_mb:.1f} MB)")
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECS[attempt]
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {exc}")
                time.sleep(wait)
            else:
                print(f"  FAILED after {MAX_RETRIES} attempts: {exc}")
                return False
    return False


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download hospital price transparency files"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sources without downloading",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Download only this hospital (use short key, e.g. 'peacehealth')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "raw",
        help="Directory to save downloaded files (default: data/raw)",
    )
    args = parser.parse_args()

    sources = SOURCES
    if args.only:
        sources = [s for s in sources if s[0] == args.only]
        if not sources:
            valid = ", ".join(s[0] for s in SOURCES)
            print(f"Unknown hospital key '{args.only}'. Valid keys: {valid}")
            sys.exit(1)

    if args.list:
        print("Available hospital MRF sources:\n")
        for key, name, url, filename in sources:
            print(f"  [{key}]")
            print(f"    Hospital: {name}")
            print(f"    URL:      {url}")
            print(f"    File:     {filename}")
            print()
        return

    print(f"Downloading {len(sources)} hospital MRF file(s) to {args.output_dir}\n")

    succeeded = 0
    failed = 0
    for key, name, url, filename in sources:
        dest = args.output_dir / filename
        if dest.exists():
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"[{key}] {name} -- already exists ({size_mb:.1f} MB), skipping")
            succeeded += 1
            continue

        print(f"[{key}] {name}")
        if _download(url, dest):
            succeeded += 1
        else:
            failed += 1

    print(f"\nDone: {succeeded} succeeded, {failed} failed")

    if failed:
        print(
            "\nSome downloads failed. This is often due to WAF/Cloudflare "
            "protection. Try downloading manually in a browser and placing "
            "the file in data/raw/."
        )
        sys.exit(1)

    if succeeded:
        print(
            "\nNext step: run the benchmark pipeline:\n"
            "  python src/benchmark.py \\\n"
            "    --input data/raw \\\n"
            "    --hospitals config/hospitals.csv \\\n"
            "    --procedures config/surgical_procedures.csv \\\n"
            '    --focus-hospital "PeaceHealth St. Joseph Medical Center" \\\n'
            "    --output data/processed"
        )


if __name__ == "__main__":
    main()
