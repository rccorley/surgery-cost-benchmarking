from pathlib import Path
from datetime import date
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "config"
REPORT = ROOT / "reports" / "report.md"

normalized = pd.read_csv(PROCESSED / "normalized_prices.csv")
procedure = pd.read_csv(PROCESSED / "procedure_benchmark.csv")
hospital = pd.read_csv(PROCESSED / "hospital_benchmark.csv")
focus = pd.read_csv(PROCESSED / "focus_hospital_rank.csv")
payer_disp = pd.read_csv(PROCESSED / "payer_dispersion.csv")
proc_conf = pd.read_csv(PROCESSED / "procedure_confidence.csv") if (PROCESSED / "procedure_confidence.csv").exists() else pd.DataFrame()
source_df = pd.read_csv(CONFIG / "hospital_sources.csv") if (CONFIG / "hospital_sources.csv").exists() else pd.DataFrame()
hospital_catalog = pd.read_csv(CONFIG / "hospitals.csv") if (CONFIG / "hospitals.csv").exists() else pd.DataFrame()


def fmt_money(v):
    return f"${v:,.2f}"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, r in df.iterrows():
        vals = [str(r[c]) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def canon(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)


n_records = len(normalized)
obs_hospitals = normalized["hospital_name"].dropna().nunique()
obs_codes = normalized["code"].dropna().nunique()
obs_payers = normalized["payer_name"].fillna("UNKNOWN").nunique()
price_min = float(normalized["effective_price"].min()) if n_records else float("nan")
price_max = float(normalized["effective_price"].max()) if n_records else float("nan")

# Coverage table: catalog hospitals vs observed hospitals
coverage_tbl = pd.DataFrame()
if not hospital_catalog.empty:
    c = hospital_catalog[["hospital_name", "city"]].drop_duplicates().copy()
    c["catalog_key"] = canon(c["hospital_name"])
    observed_keys = set(canon(normalized["hospital_name"].dropna()))
    c["in_scoped_output"] = c["catalog_key"].isin(observed_keys)
    coverage_tbl = c[["hospital_name", "city", "in_scoped_output"]].sort_values(["in_scoped_output", "hospital_name"], ascending=[False, True])

# Readiness scoring
if not proc_conf.empty and (proc_conf["confidence"] == "HIGH").any():
    readiness = "HIGH"
elif obs_hospitals >= 3:
    readiness = "MODERATE"
elif obs_hospitals == 2:
    readiness = "LOW"
else:
    readiness = "VERY LOW"

# Hospital benchmark view
hospital_view = hospital[["hospital_name", "n_rates", "median_price", "p90", "cv"]].copy() if not hospital.empty else pd.DataFrame()
if not hospital_view.empty:
    hospital_view["median_price"] = hospital_view["median_price"].map(fmt_money)
    hospital_view["p90"] = hospital_view["p90"].map(fmt_money)
    hospital_view["cv"] = hospital_view["cv"].map(lambda x: f"{x:.2f}")

# Cross-hospital rows with at least 2 hospitals
cross = pd.DataFrame()
if not proc_conf.empty:
    cross_codes = set(proc_conf[proc_conf["n_hospitals"] >= 2]["code"].astype(str))
    if not procedure.empty:
        p = procedure.copy()
        p["code"] = p["code"].astype(str)
        cross = p[p["code"].isin(cross_codes)][["code", "code_type", "description", "n_rates", "median_price", "p90_p10_ratio", "cv"]]
        cross = cross.sort_values("p90_p10_ratio", ascending=False)
        if not cross.empty:
            cross["description"] = cross["description"].astype(str).str.slice(0, 70)
            cross["median_price"] = cross["median_price"].map(fmt_money)
            cross["p90_p10_ratio"] = cross["p90_p10_ratio"].map(lambda x: f"{x:.2f}x")
            cross["cv"] = cross["cv"].map(lambda x: f"{x:.2f}")

# PeaceHealth payer dispersion
ph_disp = payer_disp[payer_disp["hospital_name"].astype(str).str.contains("PeaceHealth", case=False, na=False)].copy()
if not ph_disp.empty:
    ph_disp = ph_disp.sort_values("p90_p10_ratio", ascending=False)
    ph_disp_view = ph_disp[["code", "description", "n_unique_payers", "median_price", "p90_p10_ratio", "cv"]].head(8)
    ph_disp_view["description"] = ph_disp_view["description"].astype(str).str.slice(0, 70)
    ph_disp_view["median_price"] = ph_disp_view["median_price"].map(fmt_money)
    ph_disp_view["p90_p10_ratio"] = ph_disp_view["p90_p10_ratio"].map(lambda x: f"{x:.2f}x")
    ph_disp_view["cv"] = ph_disp_view["cv"].map(lambda x: f"{x:.2f}")
else:
    ph_disp_view = pd.DataFrame()

focus_view = focus[["code", "rank_low_to_high", "n_hospitals", "hospital_median_price"]].copy() if not focus.empty else pd.DataFrame()
if not focus_view.empty:
    focus_view["hospital_median_price"] = focus_view["hospital_median_price"].map(fmt_money)

source_status = pd.DataFrame()
if not source_df.empty and "download_status" in source_df.columns:
    source_status = source_df.groupby("download_status", dropna=False).size().reset_index(name="count")

conf_view = pd.DataFrame()
if not proc_conf.empty:
    conf_view = proc_conf[["code", "code_type", "description", "n_hospitals", "n_unique_payers", "n_rates", "p90_p10_ratio", "confidence"]].copy()
    conf_view["description"] = conf_view["description"].astype(str).str.slice(0, 70)
    conf_view["p90_p10_ratio"] = conf_view["p90_p10_ratio"].map(lambda x: f"{x:.2f}x")
    conf_order = pd.Categorical(conf_view["confidence"], categories=["HIGH", "MEDIUM", "LOW"], ordered=True)
    conf_view = conf_view.assign(_conf_order=conf_order).sort_values(["_conf_order", "n_hospitals", "n_rates"], ascending=[True, False, False]).drop(columns=["_conf_order"])

high_conf = proc_conf[proc_conf["confidence"] == "HIGH"] if not proc_conf.empty else pd.DataFrame()
med_conf = proc_conf[proc_conf["confidence"] == "MEDIUM"] if not proc_conf.empty else pd.DataFrame()

report = f"""# Surgery Cost Benchmarking Report

Date: {date.today().isoformat()}
Project: `{ROOT}`

## Project Proposal (Approved and Shared)

This report operationalizes the approved proposal in `{ROOT / 'proposal.md'}`.

## Executive Readiness Assessment

**Current comparative confidence: {readiness}**

Why confidence should still be interpreted carefully:
- Comparable scoped output currently includes **{obs_hospitals} hospital(s)**.
- Cross-hospital conclusions require at least 2-3 hospitals with same code+code_type coverage.
- Confidence is now explicitly gated per procedure (`HIGH/MEDIUM/LOW`) in `procedure_confidence.csv`.

## Methods (Updated for Defensibility)

1. Parse heterogeneous MRF structures (`.json`, `.csv`, `.zip`).
2. Dedicated PeaceHealth parser unpivots wide payer columns (`standard_charge|...|negotiated_dollar`).
3. Normalize code and code_type (`MS-DRG -> DRG`).
4. **Strict scope filter** requires matching both `code` and `code_type` to the surgical catalog.
5. Compute outputs:
- Hospital benchmark
- Procedure benchmark
- Focus-hospital rank
- Payer dispersion by hospital/procedure

## Data Coverage and Sufficiency

- Scoped records: **{n_records:,}**
- Observed hospitals in scoped output: **{obs_hospitals}**
- Procedure codes in scoped output: **{obs_codes}**
- Payer labels in scoped output: **{obs_payers}**
- Effective price range: **{fmt_money(price_min)} to {fmt_money(price_max)}**

### Hospital Coverage vs Target Catalog

{md_table(coverage_tbl)}

### Source Retrieval Status

{md_table(source_status)}

## Findings We Can Defend Now

### 1) Hospital-Level Summary (Observed Data)

{md_table(hospital_view)}

### 2) PeaceHealth Focus-Hospital Rank

{md_table(focus_view)}

Note: when `n_hospitals = 1`, rank is not a comparative market signal.

### 3) PeaceHealth Payer-Level Dispersion

{md_table(ph_disp_view)}

### 4) Cross-Hospital Comparable Rows (n_hospitals >= 2)

{md_table(cross)}

### 5) Procedure Confidence Gates

{md_table(conf_view)}

## Stronger Conclusion (Evidence-Tiered)

- **High-confidence procedures:** {len(high_conf)}  
- **Medium-confidence procedures:** {len(med_conf)}

What we can state with strongest confidence:
- Where procedures are `HIGH` or `MEDIUM`, observed dispersion and median differences are supported by multi-hospital and multi-payer evidence.
- Where procedures are `LOW`, results should be treated as directional only, not definitive market comparisons.

## Patient Implications

What this means for patients in practical terms:
- The same surgery can map to very different negotiated rates by payer at the same hospital, so insurance plan details materially affect financial exposure.
- Posted transparency rates are not final out-of-pocket bills; patients still face benefit design effects (deductible/coinsurance) and non-facility components.
- For many procedures in this dataset, cross-hospital confidence is limited, so patient-facing comparisons should be presented as directional unless confidence is `HIGH` or `MEDIUM`.

### Pre-Op Financial Checklist (Patient-Facing)

1. Ask the hospital for a bundled pre-op estimate:
- Facility fee
- Surgeon professional fee
- Anesthesia
- Pathology/imaging/labs
2. Ask your insurer for expected patient responsibility under your exact plan:
- Remaining deductible
- Coinsurance/copay
- Out-of-pocket max status
3. Confirm coding assumptions:
- Planned CPT/DRG
- Inpatient vs outpatient setting
- Any likely add-on codes
4. Request both allowed-amount and self-pay comparisons:
- Negotiated rate estimate (in-network)
- Cash/self-pay quote
- Prompt-pay or financial-assistance options
5. Before scheduling:
- Verify prior authorization requirements
- Confirm all key clinicians/facilities are in network
- Document reference numbers for all estimate calls

## What We Should NOT Claim Yet

- We should not claim robust Seattle↔Bellingham market-wide pricing dispersion.
- We should not infer competitive position for most procedures where peer coverage is absent.
- We should not interpret single-hospital ranks as market benchmarks.

## Required Next Iteration (Data Acquisition + Parsing)

1. Add direct downloadable MRF sources for at least 2 additional corridor hospitals (UW/Overlake/Skagit/Cascade).
2. Implement hospital-specific parsing for Providence/Swedish payer-negotiated fields (not only discounted cash).
3. Re-run with minimum comparability gates:
- At least 2 hospitals per procedure for cross-hospital claims.
- At least 5 payer observations per hospital-procedure for payer-dispersion claims.
4. Regenerate report and keep a QA section listing included/excluded rows by reason.

## Plots

### Hospital Comparison: Median Effective Price

![Hospital median price](plots/hospital_median_price.png)

### Procedure Comparison: Median Effective Price

![Procedure median price](plots/procedure_median_price.png)

### Cross-Hospital Procedure Dispersion (p90/p10)

![Procedure dispersion](plots/procedure_dispersion_ratio.png)

### PeaceHealth Rank vs Corridor Peers

![Focus hospital rank](plots/focus_hospital_rank.png)

### PeaceHealth Payer Dispersion by Procedure

![PeaceHealth payer dispersion](plots/peacehealth_payer_dispersion.png)
"""

REPORT.write_text(report)
print(f"Wrote {REPORT}")
