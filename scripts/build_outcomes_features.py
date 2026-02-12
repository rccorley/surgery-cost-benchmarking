#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.external.mips_loader import load_mips_public_reporting
from src.external.provider_bridge import build_provider_hospital_bridge
from src.features.outcomes_scoring import MIPS_FEATURE_COLUMNS, build_mips_outcomes_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build outcomes feature files from external MIPS data.")
    parser.add_argument("--year", type=int, default=2023, help="Performance year folder under data/external/mips.")
    parser.add_argument(
        "--mips-dir",
        type=Path,
        default=ROOT / "data" / "external" / "mips",
        help="Base folder containing year subfolders for MIPS files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "mips_outcomes_features.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--bridge-output",
        type=Path,
        default=ROOT / "data" / "processed" / "provider_hospital_bridge.csv",
        help="Output path for provider-hospital bridge CSV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = load_mips_public_reporting(args.mips_dir, args.year)
    bridge = build_provider_hospital_bridge(args.mips_dir, args.year)
    if raw.empty:
        print(
            f"[build_outcomes_features] No MIPS rows found under: {args.mips_dir / str(args.year)} "
            "(expected ec_public_reporting.csv and/or grp_public_reporting.csv)"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=MIPS_FEATURE_COLUMNS).to_csv(args.output, index=False)
        print(f"[build_outcomes_features] Wrote empty file: {args.output}")
        args.bridge_output.parent.mkdir(parents=True, exist_ok=True)
        bridge.to_csv(args.bridge_output, index=False)
        print(f"[build_outcomes_features] Bridge rows: {len(bridge):,}")
        print(f"[build_outcomes_features] Wrote bridge file: {args.bridge_output}")
        return 0

    features = build_mips_outcomes_features(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(args.output, index=False)
    args.bridge_output.parent.mkdir(parents=True, exist_ok=True)
    bridge.to_csv(args.bridge_output, index=False)
    print(f"[build_outcomes_features] Rows: {len(features):,}")
    print(f"[build_outcomes_features] Entities: {features[['entity_type','entity_id']].drop_duplicates().shape[0]:,}")
    print(f"[build_outcomes_features] Wrote: {args.output}")
    print(f"[build_outcomes_features] Bridge rows: {len(bridge):,}")
    print(f"[build_outcomes_features] Wrote bridge file: {args.bridge_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
