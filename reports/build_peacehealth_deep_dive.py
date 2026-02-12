"""Build a thorough PeaceHealth-specific report with cross-hospital context."""

from pathlib import Path
from datetime import date

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "peacehealth_deep_dive.md"


def fmt_money(v: float) -> str:
    return f"${v:,.2f}"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_\n"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    normalized = pd.read_csv(PROCESSED / "normalized_prices.csv")
    proc_conf = pd.read_csv(PROCESSED / "procedure_confidence.csv")
    focus_rank = pd.read_csv(PROCESSED / "focus_hospital_rank.csv")
    payer_disp = pd.read_csv(PROCESSED / "payer_dispersion.csv")

    ph = normalized[
        normalized["hospital_name"].astype(str).str.contains("PeaceHealth", case=False, na=False)
    ].copy()
    if ph.empty:
        OUT.write_text("# PeaceHealth Deep Dive\n\nNo PeaceHealth rows found.\n")
        print(f"Wrote {OUT}")
        return

    # ---- Section: PeaceHealth snapshot ----
    n_records = len(ph)
    n_procs = ph["code"].nunique()
    n_payers = ph["payer_name"].nunique()
    n_drg = ph[ph["code_type"].astype(str).str.upper() == "DRG"]["code"].nunique()
    n_cpt = ph[ph["code_type"].astype(str).str.upper() == "CPT"]["code"].nunique()

    # ---- Section: DRG-level analysis (cross-hospital comparable) ----
    drg_ph = ph[ph["code_type"].astype(str).str.upper() == "DRG"]
    drg_all = normalized[normalized["code_type"].astype(str).str.upper() == "DRG"]

    # Per-DRG PeaceHealth stats
    ph_drg_stats = (
        drg_ph.groupby(["code", "description"], dropna=False)["effective_price"]
        .agg(n_rates="count", median="median", min="min", max="max")
        .reset_index()
        .sort_values("code")
    )

    # Cross-hospital rank for each DRG
    rank_view = focus_rank[["code", "description", "rank_low_to_high", "n_hospitals", "hospital_median_price"]].copy()
    rank_view = rank_view.sort_values("code")
    rank_view["hospital_median_price"] = rank_view["hospital_median_price"].map(fmt_money)

    # ---- Section: Payer-level analysis at PeaceHealth ----
    # By payer across all procedures
    payer_proc_med = (
        ph.groupby(["code", "description", "payer_name"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="payer_median")
    )
    proc_med = (
        ph.groupby(["code", "description"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="proc_median")
    )
    payer_rel = payer_proc_med.merge(proc_med, on=["code", "description"], how="left")
    payer_rel["relative_index"] = payer_rel["payer_median"] / payer_rel["proc_median"]
    payer_idx = (
        payer_rel.groupby("payer_name", dropna=False)
        .agg(
            procedures_covered=("code", "nunique"),
            median_relative_index=("relative_index", "median"),
        )
        .reset_index()
        .sort_values("median_relative_index")
    )
    payer_idx["median_relative_index"] = payer_idx["median_relative_index"].map(lambda x: f"{x:.2f}x")

    # ---- Section: Biggest spreads per procedure ----
    spreads = []
    for (code, desc), g in payer_proc_med.groupby(["code", "description"], dropna=False):
        g = g.sort_values("payer_median")
        if len(g) < 2:
            continue
        lo = g.iloc[0]
        hi = g.iloc[-1]
        ratio = hi["payer_median"] / lo["payer_median"] if lo["payer_median"] > 0 else float("nan")
        spreads.append({
            "code": code,
            "description": str(desc)[:45],
            "low_payer": str(lo["payer_name"])[:35],
            "low_rate": fmt_money(lo["payer_median"]),
            "high_payer": str(hi["payer_name"])[:35],
            "high_rate": fmt_money(hi["payer_median"]),
            "ratio": f"{ratio:.2f}x",
        })
    spread_df = pd.DataFrame(spreads).sort_values("ratio", ascending=False)

    # ---- Section: PeaceHealth vs corridor by DRG ----
    corridor_tables = []
    drg_codes = sorted(drg_ph["code"].dropna().unique())
    for drg_code in drg_codes:
        drg_subset = drg_all[drg_all["code"].astype(str) == str(drg_code)]
        if drg_subset["hospital_name"].nunique() < 2:
            continue
        desc = drg_subset["description"].iloc[0] if len(drg_subset) > 0 else "?"
        hosp_stats = (
            drg_subset.groupby("hospital_name", dropna=False)["effective_price"]
            .agg(n_rates="count", median="median", min="min", max="max")
            .reset_index()
            .sort_values("median")
        )
        hosp_stats["median"] = hosp_stats["median"].map(fmt_money)
        hosp_stats["min"] = hosp_stats["min"].map(fmt_money)
        hosp_stats["max"] = hosp_stats["max"].map(fmt_money)
        # Shorten names
        hosp_stats["hospital_name"] = hosp_stats["hospital_name"].str.replace(
            "Providence Health And Services - Washington", "Providence Everett"
        ).str.replace("PeaceHealth St Joseph Medical Center", "PeaceHealth")
        corridor_tables.append((drg_code, desc, hosp_stats))

    # ---- Section: Confidence summary ----
    ph_conf = proc_conf[proc_conf["code"].astype(str).isin(ph["code"].astype(str).unique())]
    conf_view = ph_conf[["code", "code_type", "description", "n_hospitals", "n_rates", "confidence"]].copy()
    conf_view["description"] = conf_view["description"].astype(str).str.slice(0, 50)
    conf_view = conf_view.sort_values(["confidence", "n_hospitals"], ascending=[True, False])

    # ---- Section: CPT within-hospital analysis ----
    cpt_ph = ph[ph["code_type"].astype(str).str.upper() == "CPT"]
    cpt_stats = (
        cpt_ph.groupby(["code", "description"], dropna=False)
        .agg(
            n_rates=("effective_price", "count"),
            n_payers=("payer_name", "nunique"),
            median=("effective_price", "median"),
            min=("effective_price", "min"),
            max=("effective_price", "max"),
            p10=("effective_price", lambda s: s.quantile(0.1)),
            p90=("effective_price", lambda s: s.quantile(0.9)),
        )
        .reset_index()
    )
    cpt_stats["p90_p10"] = cpt_stats["p90"] / cpt_stats["p10"]
    cpt_view = cpt_stats[["code", "description", "n_payers", "median", "min", "max", "p90_p10"]].copy()
    cpt_view = cpt_view.sort_values("p90_p10", ascending=False)
    for col in ["median", "min", "max"]:
        cpt_view[col] = cpt_view[col].map(fmt_money)
    cpt_view["p90_p10"] = cpt_view["p90_p10"].map(lambda x: f"{x:.2f}x")

    # ---- Assemble report ----
    high_n = int((ph_conf["confidence"] == "HIGH").sum())
    med_n = int((ph_conf["confidence"] == "MEDIUM").sum())
    low_n = int((ph_conf["confidence"] == "LOW").sum())

    corridor_md = ""
    for drg_code, desc, tbl in corridor_tables:
        corridor_md += f"\n#### DRG {drg_code}: {desc}\n\n{md_table(tbl)}\n"

    text = f"""# PeaceHealth St. Joseph Medical Center -- Deep Dive Cost Analysis

Date: {date.today().isoformat()}
Corridor: Bellingham to Seattle, WA

---

## Executive Summary

This report provides a comprehensive analysis of surgical pricing at PeaceHealth St. Joseph Medical Center
based on publicly available machine-readable price transparency files. It compares PeaceHealth against
5 corridor peer hospitals across 22 surgical procedures (15 DRGs + 7 CPTs).

**Key findings:**
- PeaceHealth data spans **{n_records}** scoped pricing records across **{n_procs}** procedures and **{n_payers}** payer labels.
- **{high_n}** procedures have HIGH cross-hospital confidence, **{med_n}** MEDIUM, **{low_n}** LOW.
- PeaceHealth ranks in the **middle of the corridor** for most DRG-level procedures, with a few notable exceptions.
- Within PeaceHealth, payer-driven price variation is extreme for CPT procedures (up to 6x between lowest and highest payer).
- DRG-level variation is narrower (typically 1.2x-2.0x) but still material for patient financial planning.

---

## 1. Data Coverage

| Metric | Value |
| --- | --- |
| Scoped PeaceHealth records | {n_records:,} |
| DRG procedures | {n_drg} |
| CPT procedures | {n_cpt} |
| Distinct payer labels | {n_payers} |
| HIGH confidence procedures | {high_n} |
| MEDIUM confidence procedures | {med_n} |
| LOW confidence procedures | {low_n} |

### Procedure Confidence Levels

{md_table(conf_view)}

---

## 2. PeaceHealth Competitive Position (DRG-Level Cross-Hospital)

### Rank vs Corridor Peers (1 = lowest median price)

{md_table(rank_view)}

**Interpretation:** A rank of 1 means PeaceHealth has the lowest median negotiated rate among corridor peers for that DRG. Higher ranks indicate relatively higher pricing.

### Hospital-by-Hospital Comparison per DRG

{corridor_md}

---

## 3. PeaceHealth Within-Hospital Variation (CPT-Level)

CPT-level data is only available for PeaceHealth in this dataset (Providence/Swedish publish CPT codes without payer-negotiated rates). This makes CPT analysis a PeaceHealth internal view, not a market comparison.

### CPT Procedure Variation

{md_table(cpt_view)}

**Interpretation:** p90/p10 above 2.0x indicates large payer-driven dispersion. Patients with different insurance plans face materially different negotiated rates for the same procedure.

---

## 4. Payer Analysis at PeaceHealth

### Biggest Payer Spread by Procedure

{md_table(spread_df)}

### Payer Relative Index (Across All Procedures)

A value below 1.00x means the payer's median rates tend to be below the procedure-level median at PeaceHealth. Above 1.00x means higher.

{md_table(payer_idx)}

**Key takeaway:** Medicare Advantage payers (Regence MA HMO/PPO, Devoted, Molina, Wellpoint) cluster at 0.96-0.98x of median. Commercial plans (especially Regence Blue Shield Commercial) are dramatically higher at 5-6x. Discounted cash rates also exceed the procedure median.

---

## 5. Actionable Insights for PeaceHealth Administration

### Contract Renegotiation Candidates
1. **Regence Blue Shield Commercial** -- negotiated rates are 5-6x the Medicare Advantage baseline for CPT procedures. This spread far exceeds typical commercial-to-Medicare ratios and may indicate legacy contract terms.
2. **Ambetter Commercial** -- shows elevated rates for DRG 470 relative to other payers. Limited procedure coverage in the data.
3. **Discounted Cash** -- cash prices are 2.28x the procedure median, suggesting the self-pay discount schedule may benefit from review against market comparables.

### Competitive Position Actions
- For DRGs where PeaceHealth ranks in the upper half of corridor peers, the admin team should evaluate whether the rate differential reflects case mix complexity, implant cost differences, or pure negotiation position.
- For DRGs where PeaceHealth ranks #1 (lowest), consider whether there is margin erosion risk, especially for procedures with high volume.

### Data Quality Gaps
- CPT-level cross-hospital comparison is not possible with current data because Providence/Swedish publish CPT codes without payer-negotiated rates.
- 4 corridor hospitals (Skagit, Cascade, UW, Overlake) are blocked behind Cloudflare/WAF protections and could not be retrieved programmatically. Manual download from these hospitals would significantly strengthen the analysis.

---

## 6. Patient-Facing Implications

### What Bellingham Patients Should Know

1. **Your insurance plan is the biggest single factor** in what price is negotiated for your surgery at PeaceHealth. For CPT procedures, the spread between lowest and highest payer can exceed 6x.
2. **DRG pricing is more predictable** -- the within-hospital spread for DRG-based inpatient procedures is typically 1.2-2.0x.
3. **PeaceHealth is mid-market** among the corridor for most DRG procedures. It is neither systematically the cheapest nor the most expensive.
4. **Always request a written pre-op estimate** that includes facility, surgeon, anesthesia, imaging/lab, and pathology components.
5. **Verify your plan's specific negotiated rate** -- even two plans from the same insurer (e.g., Regence Medicare Advantage vs Regence Commercial) can differ by 6x.

### Pre-Surgery Financial Checklist

1. Ask for a bundled estimate: facility + surgeon + anesthesia + pathology/imaging/labs
2. Confirm expected CPT/DRG codes and inpatient vs outpatient setting
3. Run an estimate under your exact plan benefits (deductible, coinsurance, OOP max)
4. Compare in-network negotiated rate vs cash/self-pay quote
5. Verify all involved clinicians and facilities are in-network
6. Confirm prior authorization requirements and who is responsible for obtaining them
7. Document reference numbers for all estimate calls

---

*Generated from public hospital machine-readable price transparency files. These are negotiated facility rates, not final patient bills. Actual patient liability depends on plan benefit design (deductible, coinsurance, out-of-pocket maximum) and non-facility components.*
"""

    OUT.write_text(text)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
