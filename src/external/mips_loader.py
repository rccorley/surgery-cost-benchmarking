from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {str(c).lower(): str(c) for c in df.columns}
    for cand in candidates:
        key = cand.lower()
        if key in lowered:
            return lowered[key]
    return None


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype="string")
    except Exception:
        return pd.DataFrame()


def _coerce_rate_to_float(series: pd.Series) -> pd.Series:
    if series.empty:
        return pd.Series(dtype="float64")
    cleaned = (
        series.astype("string")
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.extract(r"([-+]?\d*\.?\d+)")[0]
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _extract_domain(measure_title: str) -> str:
    t = (measure_title or "").lower()
    if "readmission" in t:
        return "READMISSION"
    if "complication" in t:
        return "COMPLICATION"
    if "mortality" in t:
        return "MORTALITY"
    if "infection" in t:
        return "INFECTION"
    if "patient experience" in t or "cahps" in t:
        return "PATIENT_EXPERIENCE"
    if "outcome" in t:
        return "OUTCOME_OTHER"
    return "OTHER"


def _infer_directionality(measure_title: str) -> str:
    t = (measure_title or "").lower()
    lower_better_keywords = [
        "readmission",
        "complication",
        "infection",
        "mortality",
        "adverse",
        "hospitalization",
        "er visit",
    ]
    for k in lower_better_keywords:
        if k in t:
            return "lower_better"
    return "higher_better"


def _canonicalize_reporting(
    src: pd.DataFrame,
    entity_type: str,
    entity_id_col_candidates: list[str],
) -> pd.DataFrame:
    if src.empty:
        return pd.DataFrame()

    measure_cd_col = _find_col(src, ["measure_cd", "measure id", "measure_id", "quality_measure_id"])
    measure_title_col = _find_col(src, ["measure_title", "measure title", "title", "measure_name"])
    rate_col = _find_col(src, ["prf_rate", "performance_rate", "rate", "measure_rate", "performance rate"])
    denom_col = _find_col(
        src,
        ["patient_count", "denominator", "denom", "case_count", "eligible_patients", "sample_size"],
    )
    entity_col = _find_col(src, entity_id_col_candidates)

    required = [measure_cd_col, measure_title_col, rate_col, entity_col]
    if any(c is None for c in required):
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "entity_type": entity_type,
            "entity_id": src[entity_col].astype("string"),
            "measure_cd": src[measure_cd_col].astype("string"),
            "measure_title": src[measure_title_col].astype("string"),
            "raw_rate": _coerce_rate_to_float(src[rate_col]),
        }
    )
    if denom_col is not None:
        out["patient_count"] = pd.to_numeric(src[denom_col], errors="coerce").fillna(0).astype("float64")
    else:
        out["patient_count"] = 0.0

    out = out[out["measure_cd"].notna() & out["entity_id"].notna() & out["raw_rate"].notna()].copy()
    out["measure_domain"] = out["measure_title"].fillna("").map(_extract_domain).astype("string")
    out["directionality"] = out["measure_title"].fillna("").map(_infer_directionality).astype("string")
    return out


def load_mips_public_reporting(mips_raw_dir: Path, year: int | str) -> pd.DataFrame:
    """Load clinician/group MIPS reporting files and normalize to a canonical long shape."""
    year_dir = mips_raw_dir / str(year)
    ec = _read_csv_if_exists(year_dir / "ec_public_reporting.csv")
    grp = _read_csv_if_exists(year_dir / "grp_public_reporting.csv")

    ec_out = _canonicalize_reporting(
        ec,
        entity_type="clinician",
        entity_id_col_candidates=["npi", "clinician_npi", "provider_npi"],
    )
    grp_out = _canonicalize_reporting(
        grp,
        entity_type="group",
        entity_id_col_candidates=["org_pac_id", "group_id", "tin"],
    )
    out = pd.concat([ec_out, grp_out], ignore_index=True)
    if out.empty:
        return out

    out["year"] = int(year)
    out["measure_cd"] = out["measure_cd"].astype("string").str.strip()
    out["entity_id"] = out["entity_id"].astype("string").str.strip()
    out["measure_title"] = out["measure_title"].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    return out
