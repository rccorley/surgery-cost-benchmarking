from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable
import zipfile
import re

import pandas as pd


COLUMN_ALIASES = {
    "hospital_name": ["hospital_name", "hospital", "facility_name", "provider_name", "organization"],
    "payer_name": ["payer_name", "payer", "plan_name", "insurance", "insurance_plan"],
    "code": ["code", "billing_code", "procedure_code", "cpt", "drg", "service_code"],
    "code_type": ["code_type", "billing_code_type", "type", "code_system"],
    "description": ["description", "service_description", "item_description", "procedure_description"],
    "negotiated_rate": ["negotiated_rate", "price", "negotiated_price", "allowed_amount", "rate"],
    "cash_price": ["cash_price", "discounted_cash_price", "cash", "self_pay_price"],
    "setting": ["setting"],
    "gross_charge": ["gross_charge", "standard_charge|gross"],
    "charge_min": ["charge_min", "standard_charge|min"],
    "charge_max": ["charge_max", "standard_charge|max"],
}


def _infer_hospital_name_from_source(source_file: str, current_name: str | pd._libs.missing.NAType) -> str | pd._libs.missing.NAType:
    s = source_file.lower()
    # Swedish (order matters — most-specific first)
    if "swedish-medical-center-cherry-hill" in s:
        return "Swedish Medical Center Cherry Hill"
    if "swedish-medical-center-issaquah" in s:
        return "Swedish Medical Center Issaquah"
    if "swedish-medical-center_standardcharges" in s:
        return "Swedish Medical Center"
    if "swedish-edmonds" in s:
        return "Swedish Edmonds"
    # Providence
    if "providence-regional-medical-center-everett" in s or "providence_everett" in s:
        return "Providence Regional Medical Center Everett"
    # UW Medicine
    if "university-of-washington-medical-center" in s or "uw_medical_center" in s:
        return "UW Medical Center"
    if "harborview-medical-center" in s or "harborview_standardcharges" in s:
        return "Harborview Medical Center"
    # PeaceHealth (order matters — united_general before generic peacehealth)
    if "peacehealth_united_general" in s or "united-general" in s:
        return "PeaceHealth United General Hospital"
    if "peacehealth" in s:
        return "PeaceHealth St Joseph Medical Center"
    # Skagit Regional
    if "skagit-valley-hospital" in s or "skagit_valley" in s:
        return "Skagit Valley Hospital"
    if "cascade-valley-hospital" in s or "cascade_valley" in s:
        return "Cascade Valley Hospital"
    # Eastside
    if "overlake" in s:
        return "Overlake Medical Center"
    if "king-county-public-hospital-district" in s or "evergreenhealth" in s:
        return "EvergreenHealth Medical Center"
    return current_name


def _normalize_code(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    # Common hospital encodings like "MS-DRG 470" or "CPT 27447".
    s = s.str.replace(r"(?i)^(?:MS[- ]?DRG|APR[- ]?DRG|DRG)\s*[-: ]*([0-9]{3})$", r"\1", regex=True)
    s = s.str.replace(r"(?i)^CPT\s*[-: ]*([0-9]{5})$", r"\1", regex=True)
    return s.str.replace(r"\.0+$", "", regex=True)


def _normalize_code_type(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.upper().str.strip()
    # Collapse the common variants into the core code families used for scope
    # matching so cross-hospital coverage is less sensitive to source labeling.
    s = (
        s.str.replace(r"^MS-DRG$", "DRG", regex=True)
        .str.replace(r"^APR-DRG$", "DRG", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )
    is_drg = s.str.contains(r"\bDRG\b", na=False)
    is_cpt_or_hcpcs = s.str.contains(r"\bCPT\b|\bHCPCS\b|\bCPT/HCPCS\b|\bHCPCS/CPT\b", na=False)
    s = s.mask(is_drg, "DRG")
    s = s.mask(is_cpt_or_hcpcs, "CPT")
    return s


def _canonical_name(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "", regex=True)
    )


def flatten_peacehealth_wide(df: pd.DataFrame) -> pd.DataFrame:
    if "description" not in df.columns or not any(c.startswith("standard_charge|") for c in df.columns):
        return df

    code_cols = [c for c in ["code|1", "code|2", "code|3"] if c in df.columns]
    code_type_cols = [c for c in ["code|1|type", "code|2|type", "code|3|type"] if c in df.columns]
    if code_cols:
        df["code"] = df[code_cols].astype("string").bfill(axis=1).iloc[:, 0]
    else:
        df["code"] = pd.NA
    if code_type_cols:
        df["code_type"] = df[code_type_cols].astype("string").bfill(axis=1).iloc[:, 0]
    else:
        df["code_type"] = pd.NA

    df["hospital_name"] = "PeaceHealth St Joseph Medical Center"
    # Extract gross/min/max if available
    has_gross = "standard_charge|gross" in df.columns
    has_min = "standard_charge|min" in df.columns
    has_max = "standard_charge|max" in df.columns
    has_setting = "setting" in df.columns
    base_cols = ["hospital_name", "description", "code", "code_type"]
    records: list[dict] = []

    def _extra_fields(row: pd.Series) -> dict:
        extra: dict = {}
        if has_gross:
            extra["gross_charge"] = row.get("standard_charge|gross")
        if has_min:
            extra["charge_min"] = row.get("standard_charge|min")
        if has_max:
            extra["charge_max"] = row.get("standard_charge|max")
        if has_setting:
            extra["setting"] = row.get("setting")
        return extra

    if "standard_charge|discounted_cash" in df.columns:
        cash_df = df[base_cols + ["standard_charge|discounted_cash"]].copy()
        for _, r in cash_df.iterrows():
            rec = {
                "hospital_name": r["hospital_name"],
                "description": r["description"],
                "code": r["code"],
                "code_type": r["code_type"],
                "payer_name": "DISCOUNTED_CASH",
                "negotiated_rate": pd.NA,
                "cash_price": r["standard_charge|discounted_cash"],
            }
            rec.update(_extra_fields(r))
            records.append(rec)

    payer_cols = [c for c in df.columns if c.startswith("standard_charge|") and c.endswith("|negotiated_dollar")]
    if payer_cols:
        melt_id = base_cols[:]
        for extra_col in ["standard_charge|gross", "standard_charge|min", "standard_charge|max", "setting"]:
            if extra_col in df.columns:
                melt_id.append(extra_col)
        payer_df = df[melt_id + payer_cols].melt(
            id_vars=melt_id,
            value_vars=payer_cols,
            var_name="payer_key",
            value_name="negotiated_rate",
        )
        payer_df = payer_df[payer_df["negotiated_rate"].notna()]
        payer_df = payer_df[payer_df["negotiated_rate"].astype("string").str.strip() != ""]
        for _, r in payer_df.iterrows():
            payer_name = (
                str(r["payer_key"])
                .replace("standard_charge|", "")
                .replace("|negotiated_dollar", "")
                .replace("|", " - ")
            )
            rec = {
                "hospital_name": r["hospital_name"],
                "description": r["description"],
                "code": r["code"],
                "code_type": r["code_type"],
                "payer_name": payer_name,
                "negotiated_rate": r["negotiated_rate"],
                "cash_price": pd.NA,
            }
            rec.update(_extra_fields(r))
            records.append(rec)

    # Fallback: use estimated_amount for payers that only publish percentage or
    # algorithm-based rates.  The estimated_amount is the hospital's own dollar
    # calculation for those payers and is the CMS-required field when a flat
    # negotiated dollar amount is not available.
    seen_payer_codes = set()
    for rec in records:
        seen_payer_codes.add((rec["payer_name"], rec["code"]))

    est_cols = [c for c in df.columns if c.startswith("estimated_amount|")]
    if est_cols:
        est_melt_id = base_cols[:]
        for extra_col in ["standard_charge|gross", "standard_charge|min", "standard_charge|max", "setting"]:
            if extra_col in df.columns:
                est_melt_id.append(extra_col)
        est_df = df[est_melt_id + est_cols].melt(
            id_vars=est_melt_id,
            value_vars=est_cols,
            var_name="payer_key",
            value_name="estimated_amount",
        )
        est_df = est_df[est_df["estimated_amount"].notna()]
        est_df = est_df[est_df["estimated_amount"].astype("string").str.strip() != ""]
        for _, r in est_df.iterrows():
            payer_name = (
                str(r["payer_key"])
                .replace("estimated_amount|", "")
                .replace("|", " - ")
            )
            if (payer_name, r["code"]) in seen_payer_codes:
                continue
            rec = {
                "hospital_name": r["hospital_name"],
                "description": r["description"],
                "code": r["code"],
                "code_type": r["code_type"],
                "payer_name": payer_name,
                "negotiated_rate": r["estimated_amount"],
                "cash_price": pd.NA,
            }
            rec.update(_extra_fields(r))
            records.append(rec)

    out = pd.DataFrame(records)
    if out.empty:
        return pd.DataFrame(columns=["hospital_name", "description", "code", "code_type", "payer_name", "negotiated_rate", "cash_price"])
    out["description"] = out["description"].astype("string")
    return out


def flatten_standard_charge_information(payload: dict) -> pd.DataFrame:
    records = []
    hospital_name = payload.get("hospital_name")
    for item in payload.get("standard_charge_information", []):
        description = item.get("description")
        code_info = item.get("code_information") or [{}]
        charges = item.get("standard_charges") or [{}]

        for code_obj in code_info:
            code = code_obj.get("code")
            code_type = code_obj.get("type")
            for charge in charges:
                discounted_cash = charge.get("discounted_cash")
                if discounted_cash is not None and str(discounted_cash).strip() != "":
                    records.append(
                        {
                            "hospital_name": hospital_name,
                            "payer_name": "DISCOUNTED_CASH",
                            "code": code,
                            "code_type": code_type,
                            "description": description,
                            "negotiated_rate": pd.NA,
                            "cash_price": discounted_cash,
                        }
                    )

                payers_info = charge.get("payers_information")
                if isinstance(payers_info, list) and payers_info:
                    for p in payers_info:
                        payer_label = " - ".join(
                            [x for x in [p.get("payer_name"), p.get("plan_name")] if x]
                        )
                        negotiated = (
                            p.get("negotiated_dollar")
                            or p.get("negotiated_rate")
                            or p.get("estimated_amount")
                            or p.get("standard_charge_dollar")
                        )
                        records.append(
                            {
                                "hospital_name": hospital_name,
                                "payer_name": payer_label if payer_label else "UNKNOWN_PAYER",
                                "code": code,
                                "code_type": code_type,
                                "description": description,
                                "negotiated_rate": negotiated,
                                "cash_price": pd.NA,
                            }
                        )
                elif charge.get("payer_name") or charge.get("payer"):
                    records.append(
                        {
                            "hospital_name": hospital_name,
                            "payer_name": charge.get("payer_name") or charge.get("payer"),
                            "code": code,
                            "code_type": code_type,
                            "description": description,
                            "negotiated_rate": charge.get("negotiated_dollar")
                            or charge.get("negotiated_rate")
                            or charge.get("price"),
                            "cash_price": pd.NA,
                        }
                    )
    return pd.DataFrame(records)


def _first_matching_column(columns: Iterable[str], candidates: list[str]) -> str | None:
    lookup = {c.lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapped = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        source = _first_matching_column(df.columns, aliases)
        mapped[canonical] = df[source] if source else pd.NA

    out = pd.DataFrame(mapped)
    out["code"] = _normalize_code(out["code"])
    out["code_type"] = _normalize_code_type(out["code_type"])
    out["hospital_name"] = out["hospital_name"].astype("string")
    out["payer_name"] = out["payer_name"].astype("string")
    out["description"] = out["description"].astype("string")
    out["negotiated_rate"] = pd.to_numeric(out["negotiated_rate"], errors="coerce")
    out["cash_price"] = pd.to_numeric(out["cash_price"], errors="coerce")
    out["effective_price"] = out["negotiated_rate"].fillna(out["cash_price"])
    # Normalize optional columns
    if "setting" in out.columns:
        out["setting"] = out["setting"].astype("string").str.lower().str.strip()
    for col in ["gross_charge", "charge_min", "charge_max"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _flatten_cms_v3_flat(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten CMS v3.0 flat-format CSV (one row per hospital/procedure/payer).

    This format has ``code|1``, ``standard_charge|negotiated_dollar``, and
    ``payer_name`` as regular columns — unlike the PeaceHealth wide format
    where payer names are embedded in column names.
    """
    code_cols = [c for c in ["code|1", "code|2", "code|3"] if c in df.columns]
    code_type_cols = [c for c in ["code|1|type", "code|2|type", "code|3|type"] if c in df.columns]
    if code_cols:
        df["code"] = df[code_cols].astype("string").bfill(axis=1).iloc[:, 0]
    if code_type_cols:
        df["code_type"] = df[code_type_cols].astype("string").bfill(axis=1).iloc[:, 0]

    # Build payer_name from payer_name + plan_name
    if "payer_name" in df.columns and "plan_name" in df.columns:
        df["payer_name"] = (
            df["payer_name"].astype("string").fillna("")
            + " - "
            + df["plan_name"].astype("string").fillna("")
        ).str.strip(" -")
    elif "payer_name" not in df.columns:
        df["payer_name"] = "UNKNOWN"

    # Extract negotiated rate (prefer negotiated_dollar, then estimated_amount)
    if "standard_charge|negotiated_dollar" in df.columns:
        df["negotiated_rate"] = pd.to_numeric(df["standard_charge|negotiated_dollar"], errors="coerce")
    else:
        df["negotiated_rate"] = pd.NA
    if "estimated_amount" in df.columns:
        est = pd.to_numeric(df["estimated_amount"], errors="coerce")
        df["negotiated_rate"] = df["negotiated_rate"].fillna(est)

    # Extract cash price
    if "standard_charge|discounted_cash" in df.columns:
        df["cash_price"] = pd.to_numeric(df["standard_charge|discounted_cash"], errors="coerce")
    else:
        df["cash_price"] = pd.NA

    # Extract setting, gross, min, max for richer data
    if "setting" not in df.columns:
        df["setting"] = pd.NA
    if "standard_charge|gross" in df.columns:
        df["gross_charge"] = pd.to_numeric(df["standard_charge|gross"], errors="coerce")
    if "standard_charge|min" in df.columns:
        df["charge_min"] = pd.to_numeric(df["standard_charge|min"], errors="coerce")
    if "standard_charge|max" in df.columns:
        df["charge_max"] = pd.to_numeric(df["standard_charge|max"], errors="coerce")

    keep = ["description", "code", "code_type", "payer_name", "negotiated_rate", "cash_price",
            "setting", "gross_charge", "charge_min", "charge_max"]
    keep = [c for c in keep if c in df.columns]
    return df[keep]


def load_any(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            df = pd.read_csv(path, low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, low_memory=False, encoding="latin-1")
        # Some standard charge CSVs include 2 metadata rows before the real header.
        if "description" not in df.columns and any(c.startswith("Unnamed:") for c in df.columns):
            try:
                df = pd.read_csv(path, skiprows=2, low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(path, skiprows=2, low_memory=False, encoding="latin-1")
            except Exception:
                return df
        if any(c.startswith("standard_charge|") for c in df.columns) and "code|1" in df.columns:
            # Distinguish PeaceHealth wide format (payer names in column headers)
            # from CMS v3.0 flat format (payer_name as a regular column)
            if "payer_name" in df.columns:
                return _flatten_cms_v3_flat(df)
            return flatten_peacehealth_wide(df)
        return df

    if suffix == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not members:
                raise ValueError(f"No CSV found inside ZIP: {path}")

            def _score_candidate(df: pd.DataFrame) -> int:
                cols = set(map(str, df.columns))
                score = 0
                if any(c.startswith("standard_charge|") for c in cols):
                    score += 4
                if "code|1" in cols:
                    score += 4
                if "payer_name" in cols:
                    score += 2
                if "description" in cols:
                    score += 2
                score += min(len(df) // 1000, 20)
                return score

            best_df: pd.DataFrame | None = None
            best_score = -1
            for member in members:
                with zf.open(member, "r") as csv_file:
                    try:
                        cand = pd.read_csv(csv_file, low_memory=False)
                    except UnicodeDecodeError:
                        continue
                    except Exception:
                        continue
                if "description" not in cand.columns and any(c.startswith("Unnamed:") for c in cand.columns):
                    with zf.open(member, "r") as csv_file:
                        try:
                            cand = pd.read_csv(csv_file, skiprows=2, low_memory=False)
                        except Exception:
                            pass
                score = _score_candidate(cand)
                if score > best_score:
                    best_score = score
                    best_df = cand

            if best_df is None:
                raise ValueError(f"No readable CSV candidate inside ZIP: {path}")
            if any(c.startswith("standard_charge|") for c in best_df.columns) and "code|1" in best_df.columns:
                if "payer_name" in best_df.columns:
                    return _flatten_cms_v3_flat(best_df)
                return flatten_peacehealth_wide(best_df)
            return best_df

    if suffix in {".json", ".jsonl", ".ndjson"}:
        if suffix in {".jsonl", ".ndjson"}:
            return pd.read_json(path, lines=True)

        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, list):
            return pd.DataFrame(payload)

        if isinstance(payload, dict):
            if "standard_charge_information" in payload and isinstance(payload["standard_charge_information"], list):
                return flatten_standard_charge_information(payload)
            for value in payload.values():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return pd.DataFrame(value)
            return pd.DataFrame([payload])

    raise ValueError(f"Unsupported input format: {path}")


def ingest(input_dir: Path) -> pd.DataFrame:
    all_files = [
        p for p in input_dir.rglob("*") if p.suffix.lower() in {".csv", ".json", ".jsonl", ".ndjson", ".zip"}
    ]
    files = []
    for p in all_files:
        if p.suffix.lower() == ".zip":
            extracted = p.parent / f"{p.stem}_unzipped"
            if extracted.exists():
                continue
        files.append(p)

    frames: list[pd.DataFrame] = []
    for f in files:
        try:
            frame = normalize_columns(load_any(f))
            frame["source_file"] = str(f)
            frame["hospital_name"] = frame["hospital_name"].map(lambda x: _infer_hospital_name_from_source(str(f), x))
            frames.append(frame)
        except Exception:
            continue

    if not frames:
        columns = list(COLUMN_ALIASES.keys()) + ["effective_price", "source_file"]
        return pd.DataFrame(columns=columns)

    return pd.concat(frames, ignore_index=True)


def filter_scope(prices: pd.DataFrame, hospitals_csv: Path, procedures_csv: Path) -> pd.DataFrame:
    hospitals = pd.read_csv(hospitals_csv)["hospital_name"].astype(str)
    proc_df = pd.read_csv(procedures_csv)
    proc_df["code"] = _normalize_code(proc_df["code"])
    proc_df["code_type"] = _normalize_code_type(proc_df["code_type"])
    if "description" not in proc_df.columns:
        proc_df["description"] = pd.NA
    proc_lookup = proc_df[["code", "code_type", "description"]].rename(columns={"description": "catalog_description"})
    procedure_pairs = set(zip(proc_df["code"].astype(str), proc_df["code_type"].astype(str)))

    scoped = prices.copy()
    scoped["_hospital_key"] = _canonical_name(scoped["hospital_name"])
    hospital_key_set = set(_canonical_name(hospitals))
    scoped = scoped[scoped["_hospital_key"].isin(hospital_key_set)]
    cpt_codes = set(proc_df.loc[proc_df["code_type"].astype(str) == "CPT", "code"].astype(str))
    drg_codes = set(proc_df.loc[proc_df["code_type"].astype(str) == "DRG", "code"].astype(str))

    inferred_type = scoped["code_type"].astype("string")
    original_type = inferred_type.str.upper().str.strip()
    infer_eligible = (
        original_type.isna()
        | (original_type == "")
        | original_type.str.contains(r"HCPCS|CPT|DRG", na=False)
    )
    code_str = scoped["code"].astype("string")
    code_5 = code_str.str.extract(r"([0-9]{5})", expand=False)
    code_3 = code_str.str.extract(r"([0-9]{3})", expand=False)
    inferred_type = inferred_type.mask(
        infer_eligible & (~inferred_type.isin(["CPT", "DRG"])) & code_5.isin(cpt_codes),
        "CPT",
    )
    inferred_type = inferred_type.mask(
        infer_eligible & (~inferred_type.isin(["CPT", "DRG"])) & code_3.isin(drg_codes),
        "DRG",
    )
    normalized_code = code_str.mask(inferred_type == "CPT", code_5).mask(inferred_type == "DRG", code_3)
    scoped["_code_pair"] = list(zip(normalized_code.astype(str), inferred_type.astype(str)))
    scoped["code"] = normalized_code.fillna(scoped["code"])
    scoped["code_type"] = inferred_type.fillna(scoped["code_type"])
    scoped = scoped[scoped["_code_pair"].isin(procedure_pairs)]
    scoped = scoped.merge(proc_lookup, on=["code", "code_type"], how="left")
    if "description" not in scoped.columns:
        scoped["description"] = pd.NA
    scoped["description"] = scoped["catalog_description"].fillna(scoped["description"])
    scoped = scoped[scoped["effective_price"].notna() & (scoped["effective_price"] > 0)]
    scoped = scoped.drop(columns=["_hospital_key", "_code_pair", "catalog_description"])

    # ── Deduplication ─────────────────────────────────────────────────
    # PeaceHealth wide format can produce duplicate rows for the same
    # hospital+code+payer (from multiple matching columns). When prices
    # differ, they usually represent inpatient vs outpatient — keep both
    # with different settings. When prices are identical, drop duplicates.
    dedup_cols = [c for c in ["hospital_name", "code", "payer_name", "effective_price", "setting"]
                  if c in scoped.columns]
    if dedup_cols:
        scoped = scoped.drop_duplicates(subset=dedup_cols, keep="first")

    # ── Outlier flagging ──────────────────────────────────────────────
    # Flag rates that are statistical outliers within each procedure.
    # This helps users understand when a rate may be unreliable.
    if len(scoped) > 0:
        outlier_flags = []
        for _, group in scoped.groupby("code"):
            p = group["effective_price"]
            q1 = p.quantile(0.10)
            q3 = p.quantile(0.90)
            iqr = q3 - q1
            lower = max(q1 - 3 * iqr, 0)
            upper = q3 + 3 * iqr
            outlier_flags.append((p < lower) | (p > upper))
        scoped["is_outlier"] = pd.concat(outlier_flags)
    else:
        scoped["is_outlier"] = False

    return scoped


def with_hospital_rank(scoped: pd.DataFrame, focus_hospital: str) -> pd.DataFrame:
    g = (
        scoped.groupby(["hospital_name", "code", "description"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="hospital_median_price")
    )
    g["rank_low_to_high"] = g.groupby("code")["hospital_median_price"].rank(method="min", ascending=True)
    g["n_hospitals"] = g.groupby("code")["hospital_name"].transform("nunique")
    focus_key = _canonical_name(pd.Series([focus_hospital])).iloc[0]
    return g[_canonical_name(g["hospital_name"]) == focus_key].sort_values(["code", "rank_low_to_high"])


def procedure_benchmark(scoped: pd.DataFrame) -> pd.DataFrame:
    if scoped.empty:
        return pd.DataFrame(
            columns=[
                "code",
                "code_type",
                "description",
                "n_rates",
                "median_price",
                "mean_price",
                "min_price",
                "max_price",
                "p10",
                "p90",
                "iqr",
                "p90_p10_ratio",
                "cv",
            ]
        )

    grouped = scoped.groupby(["code", "code_type", "description"], dropna=False)["effective_price"]
    out = grouped.agg(n_rates="count", median_price="median", mean_price="mean", min_price="min", max_price="max").reset_index()
    q = grouped.quantile([0.1, 0.25, 0.75, 0.9]).unstack(level=-1).reset_index()
    q = q.rename(columns={0.1: "p10", 0.25: "q1", 0.75: "q3", 0.9: "p90"})
    cv = (grouped.std(ddof=0) / grouped.mean()).reset_index(name="cv")
    out = out.merge(q, on=["code", "code_type", "description"], how="left")
    out = out.merge(cv, on=["code", "code_type", "description"], how="left")
    out["iqr"] = out["q3"] - out["q1"]
    out["p90_p10_ratio"] = out["p90"] / out["p10"]
    return out.drop(columns=["q1", "q3"])


def hospital_benchmark(scoped: pd.DataFrame) -> pd.DataFrame:
    if scoped.empty:
        return pd.DataFrame(
            columns=[
                "hospital_name",
                "n_rates",
                "median_price",
                "mean_price",
                "p10",
                "p90",
                "iqr",
                "cv",
            ]
        )

    grouped = scoped.groupby("hospital_name", dropna=False)["effective_price"]
    out = grouped.agg(n_rates="count", median_price="median", mean_price="mean").reset_index()
    q = grouped.quantile([0.1, 0.25, 0.75, 0.9]).unstack(level=-1).reset_index()
    q = q.rename(columns={0.1: "p10", 0.25: "q1", 0.75: "q3", 0.9: "p90"})
    out = out.merge(q, on="hospital_name", how="left")
    out["iqr"] = out["q3"] - out["q1"]
    out["cv"] = grouped.std(ddof=0).values / grouped.mean().values
    return out.drop(columns=["q1", "q3"])


def payer_dispersion(scoped: pd.DataFrame) -> pd.DataFrame:
    if scoped.empty:
        return pd.DataFrame(
            columns=[
                "hospital_name",
                "code",
                "description",
                "n_rates",
                "n_unique_payers",
                "median_price",
                "min_price",
                "max_price",
                "p10",
                "p90",
                "iqr",
                "p90_p10_ratio",
                "cv",
            ]
        )

    s = scoped.copy()
    s["payer_name"] = s["payer_name"].fillna("UNKNOWN")
    g = s.groupby(["hospital_name", "code", "description"], dropna=False)["effective_price"]
    out = g.agg(n_rates="count", median_price="median", min_price="min", max_price="max").reset_index()
    q = g.quantile([0.1, 0.25, 0.75, 0.9]).unstack(level=-1).reset_index()
    q = q.rename(columns={0.1: "p10", 0.25: "q1", 0.75: "q3", 0.9: "p90"})
    n_payers = (
        s.groupby(["hospital_name", "code", "description"], dropna=False)["payer_name"]
        .nunique()
        .reset_index(name="n_unique_payers")
    )

    def _cv(x: pd.Series) -> float:
        mean = x.mean()
        if mean == 0 or pd.isna(mean):
            return float("nan")
        return float(x.std(ddof=0) / mean)

    cv_df = g.apply(_cv).reset_index(name="cv")
    out = out.merge(q, on=["hospital_name", "code", "description"], how="left")
    out = out.merge(n_payers, on=["hospital_name", "code", "description"], how="left")
    out = out.merge(cv_df, on=["hospital_name", "code", "description"], how="left")
    out["iqr"] = out["q3"] - out["q1"]
    out["p90_p10_ratio"] = out["p90"] / out["p10"]
    return out.drop(columns=["q1", "q3"])


def procedure_confidence(scoped: pd.DataFrame) -> pd.DataFrame:
    if scoped.empty:
        return pd.DataFrame(
            columns=[
                "code",
                "code_type",
                "description",
                "n_rates",
                "n_hospitals",
                "n_unique_payers",
                "median_price",
                "p90_p10_ratio",
                "confidence",
                "confidence_reason",
            ]
        )

    g = scoped.groupby(["code", "code_type", "description"], dropna=False)
    out = g["effective_price"].agg(n_rates="count", median_price="median").reset_index()
    out["n_hospitals"] = g["hospital_name"].nunique().values
    out["n_unique_payers"] = (
        scoped.assign(payer_name=scoped["payer_name"].fillna("UNKNOWN"))
        .groupby(["code", "code_type", "description"], dropna=False)["payer_name"]
        .nunique()
        .values
    )
    q = g["effective_price"].quantile([0.1, 0.9]).unstack(level=-1).reset_index().rename(columns={0.1: "p10", 0.9: "p90"})
    out = out.merge(q, on=["code", "code_type", "description"], how="left")
    out["p90_p10_ratio"] = out["p90"] / out["p10"]

    def classify(row: pd.Series) -> tuple[str, str]:
        if row["n_hospitals"] >= 4 and row["n_rates"] >= 30 and row["n_unique_payers"] >= 12:
            return "HIGH", "Broad hospital + payer coverage"
        if row["n_hospitals"] >= 2 and row["n_rates"] >= 12 and row["n_unique_payers"] >= 5:
            return "MEDIUM", "Some cross-hospital comparability"
        return "LOW", "Insufficient cross-hospital and/or payer coverage"

    labels = out.apply(classify, axis=1)
    out["confidence"] = labels.map(lambda x: x[0])
    out["confidence_reason"] = labels.map(lambda x: x[1])
    return out.drop(columns=["p10", "p90"]).sort_values(["confidence", "n_hospitals", "n_rates"], ascending=[True, False, False])


def run(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=True)

    prices = ingest(args.input)
    scoped = filter_scope(prices, args.hospitals, args.procedures)

    # Add canonical payer columns for cross-hospital comparisons
    try:
        from payer_normalizer import normalize_payer_names
        scoped = normalize_payer_names(scoped)
    except ImportError:
        pass

    scoped.to_csv(args.output / "normalized_prices.csv", index=False)
    procedure_benchmark(scoped).to_csv(args.output / "procedure_benchmark.csv", index=False)
    hospital_benchmark(scoped).to_csv(args.output / "hospital_benchmark.csv", index=False)
    with_hospital_rank(scoped, args.focus_hospital).to_csv(args.output / "focus_hospital_rank.csv", index=False)
    payer_dispersion(scoped).to_csv(args.output / "payer_dispersion.csv", index=False)
    procedure_confidence(scoped).to_csv(args.output / "procedure_confidence.csv", index=False)

    print("Generated outputs in", args.output)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Surgery cost benchmark pipeline")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--hospitals", type=Path, required=True)
    p.add_argument("--procedures", type=Path, required=True)
    p.add_argument("--focus-hospital", type=str, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p


if __name__ == "__main__":
    run(parser().parse_args())
