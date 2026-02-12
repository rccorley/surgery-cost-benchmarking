#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.benchmark import ingest, filter_scope, _normalize_code, _normalize_code_type  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit procedure coverage across hospitals.")
    p.add_argument("--input", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--hospitals", type=Path, default=ROOT / "config" / "hospitals.csv")
    p.add_argument("--procedures", type=Path, default=ROOT / "config" / "surgical_procedures.csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    prices = ingest(args.input)
    if prices.empty:
        print("No rows ingested.")
        return 1

    priced = prices[prices["effective_price"].notna() & (prices["effective_price"] > 0)].copy()
    scoped = filter_scope(prices, args.hospitals, args.procedures)
    proc = pd.read_csv(args.procedures)
    proc["code"] = _normalize_code(proc["code"])
    proc["code_type"] = _normalize_code_type(proc["code_type"])

    print("== Overall ==")
    print(f"Ingested rows (priced): {len(priced):,}")
    print(f"Scoped rows: {len(scoped):,}")
    print(f"Hospitals in scoped set: {scoped['hospital_name'].nunique():,}")
    print(f"Procedures in config: {proc[['code','code_type']].drop_duplicates().shape[0]:,}")

    pre = priced.groupby("hospital_name", dropna=False).size().rename("priced_rows")
    post = scoped.groupby("hospital_name", dropna=False).size().rename("scoped_rows")
    hosp = pre.to_frame().join(post, how="left").fillna(0)
    hosp["retention_pct"] = (100.0 * hosp["scoped_rows"] / hosp["priced_rows"]).round(2)
    hosp = hosp.sort_values("retention_pct")
    print("\n== Row retention by hospital ==")
    print(hosp.to_string())

    proc_by_hospital = (
        scoped.groupby("hospital_name", dropna=False)[["code", "code_type"]]
        .apply(lambda d: d.drop_duplicates().shape[0])
        .rename("distinct_procedures")
        .sort_values(ascending=False)
    )
    print("\n== Distinct scoped procedures by hospital ==")
    print(proc_by_hospital.to_string())

    non_core = priced[~priced["code_type"].astype(str).isin(["CPT", "DRG"])].copy()
    if not non_core.empty:
        top_non_core = (
            non_core.groupby(["hospital_name", "code_type"], dropna=False)
            .size()
            .rename("rows")
            .reset_index()
            .sort_values("rows", ascending=False)
            .head(40)
        )
        print("\n== Top non-CPT/DRG code types (may hide procedure coverage) ==")
        print(top_non_core.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
