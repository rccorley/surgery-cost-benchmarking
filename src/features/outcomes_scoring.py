from __future__ import annotations

import pandas as pd

MIPS_FEATURE_COLUMNS = [
    "year",
    "entity_type",
    "entity_id",
    "measure_cd",
    "measure_title",
    "measure_domain",
    "raw_rate",
    "patient_count",
    "directionality",
    "regional_percentile",
    "reliability_weight",
    "measure_score_norm",
    "outcomes_composite",
    "outcomes_confidence",
    "measures_observed",
]


def reliability_weight(patient_count: float, threshold: float = 50.0) -> float:
    if patient_count <= 0:
        return 0.0
    return float(max(0.0, min(1.0, patient_count / threshold)))


def normalize_measure_score(regional_percentile: float, directionality: str) -> float:
    p = float(max(0.0, min(100.0, regional_percentile)))
    if directionality == "lower_better":
        return 100.0 - p
    return p


def assign_confidence(avg_reliability: float) -> str:
    if avg_reliability >= 0.75:
        return "HIGH"
    if avg_reliability >= 0.40:
        return "MEDIUM"
    return "LOW"


def build_mips_outcomes_features(mips_df: pd.DataFrame) -> pd.DataFrame:
    if mips_df.empty:
        return pd.DataFrame()

    df = mips_df.copy()
    df["raw_rate"] = pd.to_numeric(df["raw_rate"], errors="coerce")
    df["patient_count"] = pd.to_numeric(df.get("patient_count", 0), errors="coerce").fillna(0.0)
    df = df[df["raw_rate"].notna()].copy()
    if df.empty:
        return pd.DataFrame()

    grp_keys = ["year", "entity_type", "measure_cd"]
    df["regional_percentile"] = (
        df.groupby(grp_keys, dropna=False)["raw_rate"].rank(method="average", pct=True) * 100.0
    )
    df["reliability_weight"] = df["patient_count"].map(reliability_weight)
    df["measure_score_norm"] = df.apply(
        lambda r: normalize_measure_score(r["regional_percentile"], str(r.get("directionality", "higher_better"))),
        axis=1,
    )
    df["weighted_score"] = df["measure_score_norm"] * df["reliability_weight"]

    comp = (
        df.groupby(["year", "entity_type", "entity_id"], dropna=False)
        .agg(
            weighted_score_sum=("weighted_score", "sum"),
            reliability_sum=("reliability_weight", "sum"),
            avg_reliability=("reliability_weight", "mean"),
            measures_observed=("measure_cd", "nunique"),
        )
        .reset_index()
    )
    comp["outcomes_composite"] = comp["weighted_score_sum"] / comp["reliability_sum"].where(comp["reliability_sum"] > 0)
    comp["outcomes_composite"] = comp["outcomes_composite"].fillna(0.0)
    comp["outcomes_confidence"] = comp["avg_reliability"].map(assign_confidence)

    out = df.merge(
        comp[
            [
                "year",
                "entity_type",
                "entity_id",
                "outcomes_composite",
                "outcomes_confidence",
                "measures_observed",
            ]
        ],
        on=["year", "entity_type", "entity_id"],
        how="left",
    )

    for c in MIPS_FEATURE_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA
    return out[MIPS_FEATURE_COLUMNS].sort_values(
        ["entity_type", "entity_id", "outcomes_composite", "measure_cd"],
        ascending=[True, True, False, True],
    )
