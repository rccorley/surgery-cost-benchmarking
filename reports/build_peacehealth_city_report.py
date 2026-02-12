from pathlib import Path
from datetime import date

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "peacehealth_bellingham_city_report.md"


def fmt_money(v: float) -> str:
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
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    normalized = pd.read_csv(PROCESSED / "normalized_prices.csv")
    proc_conf = pd.read_csv(PROCESSED / "procedure_confidence.csv")

    ph = normalized[normalized["hospital_name"].astype(str).str.contains("PeaceHealth", case=False, na=False)].copy()
    if ph.empty:
        OUT.write_text("# PeaceHealth Bellingham Patient Report\n\nNo PeaceHealth rows found in processed data.\n")
        print(f"Wrote {OUT}")
        return

    # Core procedure dispersion for local patient use
    proc = (
        ph.groupby(["code", "code_type", "description"], dropna=False)
        .agg(
            n_rates=("effective_price", "count"),
            n_payers=("payer_name", "nunique"),
            median_price=("effective_price", "median"),
            min_price=("effective_price", "min"),
            max_price=("effective_price", "max"),
            p10=("effective_price", lambda s: s.quantile(0.1)),
            p90=("effective_price", lambda s: s.quantile(0.9)),
        )
        .reset_index()
    )
    proc["p90_p10_ratio"] = proc["p90"] / proc["p10"]
    proc_view = proc[
        [
            "code",
            "code_type",
            "description",
            "n_payers",
            "median_price",
            "p90_p10_ratio",
            "min_price",
            "max_price",
        ]
    ].copy()
    proc_view = proc_view.sort_values("p90_p10_ratio", ascending=False)
    for col in ["median_price", "min_price", "max_price"]:
        proc_view[col] = proc_view[col].map(fmt_money)
    proc_view["p90_p10_ratio"] = proc_view["p90_p10_ratio"].map(lambda x: f"{x:.2f}x")

    # Payer-specific high/low by procedure
    pp = (
        ph.groupby(["code", "description", "payer_name"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="payer_median")
    )
    spreads = []
    for (code, desc), g in pp.groupby(["code", "description"], dropna=False):
        g = g.sort_values("payer_median")
        lo = g.iloc[0]
        hi = g.iloc[-1]
        spreads.append(
            {
                "code": code,
                "description": desc,
                "low_payer": lo["payer_name"],
                "low_median": lo["payer_median"],
                "high_payer": hi["payer_name"],
                "high_median": hi["payer_median"],
                "high_low_ratio": hi["payer_median"] / lo["payer_median"] if lo["payer_median"] else float("nan"),
            }
        )
    spread_view = pd.DataFrame(spreads).sort_values("high_low_ratio", ascending=False)
    if not spread_view.empty:
        spread_view["low_median"] = spread_view["low_median"].map(fmt_money)
        spread_view["high_median"] = spread_view["high_median"].map(fmt_money)
        spread_view["high_low_ratio"] = spread_view["high_low_ratio"].map(lambda x: f"{x:.2f}x")

    # Simple payer index: relative to PeaceHealth procedure medians
    proc_med = (
        ph.groupby(["code", "description"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="proc_median")
    )
    payer_rel = pp.merge(proc_med, on=["code", "description"], how="left")
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

    # Corridor context for DRG 470
    drg = normalized[
        (normalized["code"].astype(str) == "470") & (normalized["code_type"].astype(str).str.upper() == "DRG")
    ].copy()
    drg_hosp = (
        drg.groupby("hospital_name", dropna=False)["effective_price"]
        .agg(n_rates="count", median_price="median", min_price="min", max_price="max")
        .reset_index()
        .sort_values("median_price")
    )
    if not drg_hosp.empty:
        for col in ["median_price", "min_price", "max_price"]:
            drg_hosp[col] = drg_hosp[col].map(fmt_money)

    confidence = proc_conf[
        proc_conf["code"].astype(str).isin(proc["code"].astype(str))
    ][["code", "confidence"]].drop_duplicates()
    high_n = int((confidence["confidence"] == "HIGH").sum())
    low_n = int((confidence["confidence"] == "LOW").sum())

    text = f"""# PeaceHealth St. Joseph (Bellingham) Patient-Focused Cost Report

Date: {date.today().isoformat()}
Project: `{ROOT}`

## Why This Report Is For Bellingham Residents

This report focuses specifically on how surgical prices vary **inside PeaceHealth St. Joseph Medical Center** and what that likely means for local patients planning care.

## PeaceHealth Snapshot

- Scoped PeaceHealth records: **{len(ph):,}**
- Distinct procedures in scope: **{ph['code'].nunique()}**
- Distinct payer labels in scope: **{ph['payer_name'].nunique()}**
- Confidence mix for PeaceHealth-covered procedures: **{high_n} HIGH, {low_n} LOW**

## What A Bellingham Patient Should Know First

1. Your insurance plan can change expected allowed amounts substantially, even at the same hospital.
2. For several procedures, payer spread is multi-x (not small percentage differences).
3. The transparency data are useful for negotiation and planning, but they are not a final bill quote.

## PeaceHealth Procedure Variation (Within-Hospital)

{md_table(proc_view)}

Interpretation:
- `p90/p10` above ~2.0x means large payer-driven spread at this hospital for that procedure.
- `min_price`/`max_price` indicates the observed negotiated range in this dataset, not guaranteed patient liability.

## Biggest Payer Spread By Procedure (PeaceHealth)

{md_table(spread_view)}

Interpretation:
- `high_low_ratio` quantifies how far apart payer medians are for the same procedure at PeaceHealth.
- This is the clearest signal for patients that pre-op benefit checks matter.

## Which Payers Trend Lower vs Higher (PeaceHealth Relative Index)

{md_table(payer_idx)}

Interpretation:
- A value below `1.00x` means that payer tends to be below the PeaceHealth procedure median.
- A value above `1.00x` means that payer tends to be above the PeaceHealth procedure median.

## Corridor Context: DRG 470 (Most Comparable Cross-Hospital Signal)

{md_table(drg_hosp)}

Interpretation:
- DRG 470 is currently the strongest cross-hospital comparison signal in this dataset.
- For most CPT procedures, current cross-hospital evidence is limited, so local patient decisions should emphasize within-PeaceHealth variation + insurer-specific benefits checks.

## What To Ask Before Scheduling Surgery In Bellingham

1. “Can you provide a written pre-op estimate with facility, surgeon, anesthesia, imaging/lab, and pathology components?”
2. “Which exact CPT/DRG codes are expected for my case, and inpatient vs outpatient setting?”
3. “Can you run an estimate under my exact plan benefits (deductible, coinsurance, out-of-pocket max status)?”
4. “Can I see both in-network negotiated estimate and cash/self-pay quote?”
5. “Are all involved clinicians and facilities in-network for my plan?”
6. “What prior authorization is required, and who is responsible for obtaining it?”

## Practical Bottom Line For Local Patients

- Use this report as a **financial planning and question checklist** before surgery.
- Do not rely on one headline number; request a full episode estimate.
- If your procedure is in a high-spread category, compare options and ask for itemized assumptions before committing.
"""

    OUT.write_text(text)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
