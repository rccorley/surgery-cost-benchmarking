from __future__ import annotations

from pathlib import Path

import pandas as pd


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {str(c).lower(): str(c) for c in df.columns}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def _normalize_hospital_name(name: str) -> str:
    return " ".join(str(name).strip().split()).lower()


def build_provider_hospital_bridge(mips_raw_dir: Path, year: int | str) -> pd.DataFrame:
    """Build a lightweight clinician/group -> hospital bridge from Facility_Affiliation.csv."""
    path = mips_raw_dir / str(year) / "Facility_Affiliation.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        raw = pd.read_csv(path, dtype="string")
    except Exception:
        return pd.DataFrame()
    if raw.empty:
        return pd.DataFrame()

    npi_col = _find_col(raw, ["npi", "clinician_npi", "provider_npi"])
    grp_col = _find_col(raw, ["org_pac_id", "group_id", "tin"])
    hosp_col = _find_col(raw, ["facility_name", "hospital_name", "facility", "organization_name"])

    if hosp_col is None:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    if npi_col is not None:
        c = raw[[npi_col, hosp_col]].copy()
        c.columns = ["entity_id", "hospital_name"]
        c["entity_type"] = "clinician"
        frames.append(c)
    if grp_col is not None:
        g = raw[[grp_col, hosp_col]].copy()
        g.columns = ["entity_id", "hospital_name"]
        g["entity_type"] = "group"
        frames.append(g)
    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out["entity_id"] = out["entity_id"].astype("string").str.strip()
    out["hospital_name"] = out["hospital_name"].astype("string").str.strip()
    out = out[out["entity_id"].notna() & out["hospital_name"].notna()].copy()
    out["hospital_name_std"] = out["hospital_name"].map(_normalize_hospital_name).astype("string")
    out["bridge_strength"] = 1.0
    out["bridge_confidence"] = "HIGH"
    out = out.drop_duplicates(subset=["entity_type", "entity_id", "hospital_name_std"])
    return out[
        [
            "entity_type",
            "entity_id",
            "hospital_name",
            "hospital_name_std",
            "bridge_strength",
            "bridge_confidence",
        ]
    ].sort_values(["entity_type", "entity_id", "hospital_name"])
