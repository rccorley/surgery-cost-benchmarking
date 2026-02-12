#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import zipfile


REQUIRED = {
    "ec_public_reporting.csv": "ec_public_reporting.csv",
    "grp_public_reporting.csv": "grp_public_reporting.csv",
}
OPTIONAL = {
    "ec_score_file.csv": "ec_score_file.csv",
    "facility_affiliation.csv": "Facility_Affiliation.csv",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract required MIPS CSVs from a CMS ZIP bundle.")
    p.add_argument("--zip", type=Path, required=True, help="Path to downloaded CMS ZIP file.")
    p.add_argument("--year", type=int, default=2023, help="Target year folder under data/external/mips.")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/external/mips"),
        help="Base output dir; files are written to <out-dir>/<year>/.",
    )
    return p.parse_args()


def _normalized_name(member: str) -> str:
    return Path(member).name.strip().lower()


def main() -> int:
    args = parse_args()
    out_year = args.out_dir / str(args.year)
    out_year.mkdir(parents=True, exist_ok=True)

    if not args.zip.exists():
        print(f"ERROR: ZIP not found: {args.zip}")
        return 1

    found: dict[str, str] = {}
    with zipfile.ZipFile(args.zip, "r") as zf:
        for member in zf.namelist():
            n = _normalized_name(member)
            if n in REQUIRED and REQUIRED[n] not in found:
                found[REQUIRED[n]] = member
            if n in OPTIONAL and OPTIONAL[n] not in found:
                found[OPTIONAL[n]] = member

        missing_required = [target for target in REQUIRED.values() if target not in found]
        if missing_required:
            print("ERROR: Required files not found in ZIP:")
            for m in missing_required:
                print(f"  - {m}")
            print("Tip: confirm this ZIP is the Doctors & Clinicians public reporting bundle for the selected year.")
            return 2

        for out_name, member in found.items():
            out_path = out_year / out_name
            with zf.open(member, "r") as src, out_path.open("wb") as dst:
                dst.write(src.read())
            print(f"Extracted: {out_path}")

    print("\nNext step:")
    print(f"  .venv/bin/python scripts/build_outcomes_features.py --year {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
