"""Streamlit page: Surgery Cost Intelligence Explorer.

Multi-stakeholder surgery pricing app combining transparency data with
patient benefit design and market benchmarking views.

Run:
    streamlit run src/patient_calculator.py
"""

from __future__ import annotations

from pathlib import Path
import logging

import pandas as pd
import streamlit as st

from patient_estimator import (
    BenefitDesign,
    estimate_patient_cost,
    load_normalized_prices,
)
from tab_patient_view import render_patient_tab
from tab_hospital_view import build_hospital_growth_scorecard, render_hospital_tab
from tab_surgeon_view import render_surgeon_tab

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
MIPS_EXTERNAL = ROOT / "data" / "external" / "mips" / "2023"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "patient_calculator_errors.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
_logger = logging.getLogger("patient_calculator")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    _logger.addHandler(_handler)
    _logger.propagate = False

@st.cache_data
def load_data() -> pd.DataFrame:
    return load_normalized_prices(PROCESSED)


def fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def log_tab_exception(tab_name: str, exc: Exception) -> None:
    """Persist tab crashes with streamlit state hints for debugging."""
    keys = sorted(str(k) for k in st.session_state.keys())
    _logger.exception(
        "tab_crash tab=%s session_keys=%s error=%s",
        tab_name,
        keys,
        repr(exc),
    )


@st.cache_data
def load_procedure_confidence() -> pd.DataFrame:
    path = PROCESSED / "procedure_confidence.csv"
    if not path.exists():
        return pd.DataFrame()
    out = pd.read_csv(path)
    if out.empty:
        return out
    out["code"] = out["code"].astype("string")
    out["code_type"] = out["code_type"].astype("string")
    out["confidence"] = out["confidence"].astype("string")
    return out


@st.cache_data
def load_mips_outcomes_features() -> pd.DataFrame:
    path = PROCESSED / "mips_outcomes_features.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        out = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if out.empty:
        return out
    for col in ["entity_type", "entity_id", "measure_cd", "measure_title", "measure_domain", "outcomes_confidence"]:
        if col in out.columns:
            out[col] = out[col].astype("string")
    return out


def _render_about_tab(df: pd.DataFrame) -> None:
    """Render the About This Data page."""

    # ── Legal basis ──────────────────────────────────────────────────
    st.markdown("#### Legal basis")
    st.markdown(
        "All pricing data shown in this app comes from **hospital machine-readable files (MRFs)** "
        "that hospitals are legally required to publish under the "
        "**CMS Hospital Price Transparency Rule** "
        "([45 CFR Parts 180](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-E/part-180))."
    )
    st.markdown(
        "This rule was finalized in November 2019 and took effect on **January 1, 2021**. "
        "It requires every hospital in the United States to publish their payer-specific negotiated rates "
        "in a standardized, machine-readable format. "
        "As of January 2025, hospitals must follow the "
        "[CMS v2.2 or v3.0 data dictionary](https://github.com/CMSgov/hospital-price-transparency) "
        "and face penalties of up to **$2 million/year** for non-compliance. "
        "As of early 2025, only about "
        "[15% of US hospitals](https://www.patientrightsadvocate.org/interim-semi-annual-hospital-price-transparency-report) "
        "had sufficient dollar-and-cents pricing disclosure, down from "
        "[21.1% in November 2024](https://www.patientrightsadvocate.org/seventh-semi-annual-hospital-price-transparency-report-november-2024)."
    )

    # ── Coverage summary ─────────────────────────────────────────────
    st.markdown("#### Coverage")
    n_hospitals = df["hospital_name"].nunique()
    n_procedures = df["code"].nunique()
    n_records = len(df)
    n_payers = df["payer_name"].nunique()
    n_groups = df["payer_group"].nunique() if "payer_group" in df.columns else 0
    st.markdown(
        f"This app covers **{n_hospitals} hospitals** in the North Puget Sound / I-5 corridor "
        f"(Bellingham to Seattle), "
        f"**{n_procedures} surgical procedures** (CPT and DRG codes), "
        f"and **{n_records:,} price records** across **{n_payers} insurance plans** "
        f"({n_groups} insurer groups)."
    )

    hosp_counts = (
        df.groupby("hospital_name")
        .agg(procedures=("code", "nunique"), records=("code", "count"))
        .sort_values("procedures", ascending=False)
        .reset_index()
    )
    hosp_counts.columns = ["Hospital", "Procedures", "Price Records"]
    st.dataframe(hosp_counts, use_container_width=True, hide_index=True)

    # ── Methodology ──────────────────────────────────────────────────
    st.markdown("#### Methodology")
    st.markdown("##### Facility fees (actual data)")
    st.markdown(
        "The **facility fee** shown for each hospital-procedure-payer combination is the "
        "actual negotiated rate extracted directly from the hospital's published MRF. "
        "These are the same rates hospitals report to CMS and that your insurer uses to "
        "process claims. Where a hospital publishes a percentage-based or algorithm-based rate "
        "instead of a flat dollar amount, we use the CMS-required `estimated_amount` field."
    )
    st.markdown("##### Professional fees (estimated)")
    st.markdown(
        "Surgeon, anesthesia, pathology, and imaging fees are **estimated** because most "
        "hospitals only publish facility fees in their MRFs. Professional fees are billed "
        "separately by physicians and are not included in the hospital transparency file. "
        "Our estimates use procedure-specific multipliers derived from:"
    )
    st.markdown(
        "- **CMS Physician Fee Schedule (PFS) 2024\u20132025** "
        "([cms.gov/medicare/payment/fee-schedules](https://www.cms.gov/medicare/payment/fee-schedules)) "
        "\u2014 national average Medicare rates for surgeon professional services, used as a "
        "baseline ratio against facility fees\n"
        "- **CMS Anesthesia Base Units & Conversion Factors** "
        "([cms.gov/medicare/payment/fee-schedules](https://www.cms.gov/medicare/payment/fee-schedules)) "
        "\u2014 procedure-specific base units multiplied by the national conversion factor\n"
        "- **Published cost analyses** \u2014 AAHKS total joint replacement cost breakdowns, "
        "JAMA Surgery operating-room cost studies, and spinal-implant utilization data "
        "used to calibrate multipliers for specific procedure categories"
    )
    st.markdown(
        "These multipliers express each professional fee as a percentage of the facility fee "
        "(e.g., surgeon = 40% of facility fee for major joint replacement). "
        "The actual professional fees you receive may differ based on your surgeon's contracts."
    )
    st.markdown("##### Patient out-of-pocket")
    st.markdown(
        "Your estimated cost is calculated by applying your insurance benefit design "
        "(deductible remaining, coinsurance percentage, out-of-pocket maximum remaining) "
        "to the total estimated cost. This follows standard insurance cost-sharing logic: "
        "deductible first, then coinsurance on the remainder, capped at the OOP maximum."
    )

    # ── Data sources ─────────────────────────────────────────────────
    st.markdown("#### Data sources")
    st.markdown(
        "| Source | Description | Link |\n"
        "|--------|-------------|------|\n"
        "| Hospital MRFs | Payer-specific negotiated rates downloaded directly from each hospital | "
        "Each hospital's price transparency page |\n"
        "| CMS Hospital Price Transparency | Official data dictionary, schemas, and validator | "
        "[github.com/CMSgov/hospital-price-transparency](https://github.com/CMSgov/hospital-price-transparency) |\n"
        "| CMS Physician Fee Schedule | National average Medicare professional fee rates (2024\u20132025) | "
        "[cms.gov/medicare/payment/fee-schedules](https://www.cms.gov/medicare/payment/fee-schedules) |\n"
        "| CMS Anesthesia Fee Schedule | Base units and conversion factors for anesthesia estimates | "
        "[cms.gov/medicare/payment/fee-schedules](https://www.cms.gov/medicare/payment/fee-schedules) |\n"
        "| Hospital Price Transparency Archive | Git-scraped archive of 5,000+ hospitals across 50 states with historical snapshots | "
        "[github.com/nathansutton/hospital-price-transparency](https://github.com/nathansutton/hospital-price-transparency) |\n"
        "| CMS MIPS Quality Data | Clinician and group performance scores for surgeon market intelligence | "
        "[qpp.cms.gov/about/resource-library](https://qpp.cms.gov/about/resource-library) |"
    )

    # ── Data quality ─────────────────────────────────────────────────
    st.markdown("#### Data quality")
    st.markdown(
        "- Rates are deduplicated per hospital, procedure, payer, and care setting\n"
        "- Statistical outliers are flagged using 3\u00d7 IQR outside the p10\u2013p90 range per procedure\n"
        "- Payer names are normalized from {n_raw} raw strings into {n_groups} canonical insurer groups "
        "for cross-hospital comparison\n"
        "- Confidence badges on each procedure indicate data depth (number of hospitals and payers)\n"
        "- **EvergreenHealth** publishes only 4 of our 25 surgical CPT codes "
        "and zero DRG-level inpatient pricing\n"
        "- **Skagit Valley** and **Cascade Valley** hospitals have MRF URLs that "
        "return 404 errors \u2014 they are not currently meeting CMS transparency requirements"
    .format(
            n_raw=df["payer_name"].nunique(),
            n_groups=n_groups,
        )
    )

    # ── Limitations ──────────────────────────────────────────────────
    st.markdown("#### Limitations")
    st.markdown(
        "- **Not a bill.** Actual charges depend on clinical complexity, length of stay, "
        "and complications. These are estimates based on published negotiated rates.\n"
        "- **Professional fees are estimates.** Only the facility fee comes from actual hospital data. "
        "Surgeon, anesthesia, and other professional fees are modeled from CMS benchmarks.\n"
        "- **Post-acute care not included.** Rehabilitation, home health, and follow-up visits "
        "can add 15\u201340% for major inpatient procedures.\n"
        "- **Hospital compliance varies.** Some hospitals publish more complete data than others. "
        "Missing procedures or payers usually indicate the hospital has not published that data, "
        "not that they don't offer the service.\n"
        "- **Rates may be outdated.** CMS requires quarterly updates, but not all hospitals comply. "
        "Verify with your hospital and insurer before making decisions."
    )

    # ── Open source ──────────────────────────────────────────────────
    st.markdown("#### Run this for your area")
    st.markdown(
        "This project is **open source** and designed to be re-run for any geography in the US. "
        "Every hospital in the country is required to publish the same data."
    )
    st.markdown(
        "1. **Find your hospitals' MRF files** \u2014 search the "
        "[TPAFS community index](https://github.com/TPAFS/transparency-data) "
        "or look for `cms-hpt.txt` at each hospital's website root\n"
        "2. **Download the files** into `data/raw/`\n"
        "3. **Update `config/hospitals.csv`** with your hospital names and regions\n"
        "4. **Run the pipeline**: `python src/benchmark.py --input data/raw ...`\n"
        "5. **Launch the app**: `streamlit run src/patient_calculator.py`"
    )
    st.markdown(
        "The pipeline auto-detects CMS v2.x JSON, wide-format CSV (Craneware), "
        "flat CSV, and ZIP archives. Payer names are normalized automatically."
    )

    # ── Footer ───────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "Data sourced from hospital machine-readable files as required by "
        "[45 CFR Parts 180](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-E/part-180). "
        "Prices reflect what hospitals have published and may not match your actual bill. "
        "Always verify with your hospital and insurance company before making healthcare decisions."
    )


def main() -> None:
    st.set_page_config(
        page_title="Surgery Cost Intelligence Explorer",
        page_icon="\U0001fa7a",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        /* Best-effort for native Streamlit dataframes */
        div[data-testid="stDataFrame"] [role="columnheader"],
        div[data-testid="stDataFrame"] [role="gridcell"] {
            white-space: normal !important;
            word-break: break-word;
            line-height: 1.25;
        }
        /* Wrapped HTML table renderer */
        .wrapped-table-scroll {
            overflow: auto;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 0.5rem;
            max-width: 100%;
        }
        .wrapped-table {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: 0.86rem;
        }
        .wrapped-table th,
        .wrapped-table td {
            white-space: normal !important;
            word-break: break-word;
            vertical-align: top;
            padding: 6px 8px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.25);
            text-align: left;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Surgery Cost Intelligence Explorer")
    st.markdown(
        "Compare surgery pricing from multiple perspectives: **patient out-of-pocket**, "
        "**hospital growth and contracting**, and **independent surgeon market intelligence**."
    )

    df = load_data()
    if df.empty:
        st.error(
            "No processed pricing data found. "
            "Run the benchmark pipeline first to generate data."
        )
        return

    # ── Session state for extracted values ─────────────────────────
    for key in ("extracted_deductible", "extracted_coinsurance", "extracted_oop_max"):
        if key not in st.session_state:
            st.session_state[key] = None

    conf_df = load_procedure_confidence()
    mips_df = load_mips_outcomes_features()

    views = [
        "How Much Should My Surgery Cost Me?",
        "Hospital Growth & Contracting",
        "Independent Surgeon Market Intelligence",
        "About This Data",
    ]
    selected_view = st.segmented_control(
        "Navigation",
        options=views,
        selection_mode="single",
        default=views[0],
        key="main_view_selector_v1",
        label_visibility="collapsed",
    )

    if selected_view == views[0]:
        controls_col, _ = st.columns([1, 5], gap="large")
        with controls_col:
            if hasattr(st, "popover"):
                panel = st.popover("Enter Your Insurance Details", use_container_width=True)
            else:
                panel = st.expander("Enter Your Insurance Details", expanded=False)

            with panel:
                st.caption("Set your deductible, coinsurance, and out-of-pocket max to get personalized cost estimates.")

                st.markdown("**Your Insurance Details**")
                st.caption(
                    "Enter your plan's cost-sharing parameters. "
                    "You can find these on your Summary of Benefits (SBC) document from your insurer."
                )
                default_ded = st.session_state.extracted_deductible
                default_coins = st.session_state.extracted_coinsurance
                default_oop = st.session_state.extracted_oop_max

                deductible_remaining = st.number_input(
                    "Remaining annual deductible ($)",
                    min_value=0,
                    max_value=50_000,
                    value=int(default_ded) if default_ded is not None else 2_000,
                    step=250,
                    help="How much of your annual deductible you still need to meet.",
                )
                coinsurance_pct = st.slider(
                    "Your coinsurance (%)",
                    min_value=0,
                    max_value=100,
                    value=default_coins if default_coins is not None else 20,
                    step=5,
                    help="The percentage YOU pay after meeting your deductible. "
                    "For example, 20% means your plan pays 80%.",
                )
                oop_max_remaining = st.number_input(
                    "Remaining out-of-pocket maximum ($)",
                    min_value=0,
                    max_value=100_000,
                    value=int(default_oop) if default_oop is not None else 6_000,
                    step=500,
                    help="Your plan's cap on what you pay in a year. "
                    "Once you hit this, the plan covers 100%.",
                )

        m1, m2, m3, _ = st.columns([1, 1, 1, 3])
        m1.metric("Plan assumption: Deductible", f"${deductible_remaining:,}")
        m2.metric("Plan assumption: Coinsurance", f"{coinsurance_pct}%")
        m3.metric("Plan assumption: OOP max", f"${oop_max_remaining:,}")

        benefit = BenefitDesign(
            deductible_remaining=float(deductible_remaining),
            coinsurance_pct=coinsurance_pct / 100.0,
            oop_max_remaining=float(oop_max_remaining),
        )

        render_patient_tab(
            df=df,
            coinsurance_pct=coinsurance_pct,
            benefit=benefit,
            conf_df=conf_df,
        )

    elif selected_view == views[1]:
        try:
            render_hospital_tab(
                df=df,
                conf_df=conf_df,
            )
        except Exception as exc:
            log_tab_exception("hospital", exc)
            st.error("Hospital tab encountered an error. Please adjust filters and retry.")
            st.caption(f"Error details logged to: `{LOG_FILE}`")
            st.exception(exc)

    elif selected_view == views[2]:
        try:
            render_surgeon_tab(
                df=df,
                conf_df=conf_df,
                mips_df=mips_df,
            )
        except Exception as exc:
            log_tab_exception("surgeon", exc)
            st.error("Surgeon tab encountered an error. Please adjust filters and retry.")
            st.caption(f"Error details logged to: `{LOG_FILE}`")
            st.exception(exc)

    elif selected_view == views[3]:
        _render_about_tab(df)


if __name__ == "__main__":
    try:
        _logger.info("app_start path=%s", __file__)
        main()
    except Exception as exc:
        _logger.exception("fatal_unhandled_exception error=%s", repr(exc))
        raise
