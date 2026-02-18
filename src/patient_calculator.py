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
    st.markdown("#### Where does this data come from?")
    st.markdown(
        "All pricing data shown in this app comes from **hospital machine-readable files (MRFs)** "
        "that hospitals are legally required to publish under the "
        "**CMS Hospital Price Transparency Rule** (45 CFR Parts 180)."
    )
    st.markdown(
        "This rule was finalized in November 2019 and took effect on **January 1, 2021**. "
        "It requires every hospital in the United States to publish their negotiated rates "
        "with every insurance company in a standardized, machine-readable format. "
        "As of January 2025, hospitals must follow the **CMS v2.2 or v3.0 data dictionary** "
        "and face penalties of up to **$2 million/year** for non-compliance."
    )

    st.markdown("#### What data is included?")
    n_hospitals = df["hospital_name"].nunique()
    n_procedures = df["code"].nunique()
    n_records = len(df)
    n_payers = df["payer_name"].nunique()
    n_groups = df["payer_group"].nunique() if "payer_group" in df.columns else 0
    st.markdown(
        f"This app covers **{n_hospitals} hospitals** in the North Puget Sound / I-5 corridor, "
        f"**{n_procedures} common surgical procedures** (CPT and DRG codes), "
        f"and **{n_records:,} price records** across **{n_payers} insurance plans** "
        f"({n_groups} insurer groups)."
    )

    st.markdown("#### Hospitals included")
    hosp_counts = (
        df.groupby("hospital_name")
        .agg(procedures=("code", "nunique"), records=("code", "count"))
        .sort_values("procedures", ascending=False)
        .reset_index()
    )
    hosp_counts.columns = ["Hospital", "Procedures Covered", "Total Price Records"]
    st.dataframe(hosp_counts, use_container_width=True, hide_index=True)

    st.markdown("#### Data sources")
    st.markdown(
        "- **Hospital MRFs**: Downloaded directly from each hospital's price transparency page "
        "or via the CMS TPAFS index\n"
        "- **CMS Hospital Price Transparency GitHub**: "
        "[github.com/CMSgov/hospital-price-transparency](https://github.com/CMSgov/hospital-price-transparency) "
        "— official data dictionary, schemas, and validator\n"
        "- **CMS Physician Fee Schedule**: Used to estimate surgeon and anesthesia fees "
        "when hospitals only publish facility fees\n"
        "- **CMS MIPS Quality Data** (optional): Clinician and group performance scores "
        "for surgeon market intelligence\n"
    )

    st.markdown("#### How are costs estimated?")
    st.markdown(
        "- **Facility fee**: This is the actual hospital negotiated rate from their published MRF data\n"
        "- **Surgeon fee**: Estimated from the CMS Physician Fee Schedule (national average)\n"
        "- **Anesthesia fee**: Estimated from CMS anesthesia conversion factors\n"
        "- **Patient out-of-pocket**: Calculated using your deductible, coinsurance, "
        "and out-of-pocket maximum inputs\n"
    )

    st.markdown("#### Data quality notes")
    st.markdown(
        "- Rates are deduplicated per hospital, procedure, payer, and care setting\n"
        "- Statistical outliers are flagged (3x IQR outside p10-p90 range)\n"
        "- Payer names are normalized across hospitals for cross-hospital comparison\n"
        "- Some hospitals publish more complete data than others — "
        "the confidence badge on each procedure indicates data coverage\n"
        "- **EvergreenHealth** only publishes 4 of our 25 surgical CPT codes "
        "and zero DRG-level inpatient pricing\n"
        "- **Skagit Valley** and **Cascade Valley** hospitals have MRF files published "
        "but their download URLs are intermittently blocked by Cloudflare, "
        "making the data unreliably accessible\n"
    )

    st.markdown("#### Run this for your area")
    st.markdown(
        "This project is **open source** and designed to be re-run for any geography in the US. "
        "Every hospital in the country is required to publish the same data. To analyze your local hospitals:"
    )
    st.markdown(
        "1. **Find your hospitals' MRF files** — search the "
        "[CMS TPAFS index](https://github.com/CMSgov/hospital-price-transparency) "
        "or each hospital's price transparency page\n"
        "2. **Download the files** into `data/raw/`\n"
        "3. **Update `config/hospitals.csv`** with your hospital names\n"
        "4. **Run the pipeline**: `python -m benchmark --input data/raw ...`\n"
        "5. **Launch the app**: `streamlit run src/patient_calculator.py`\n"
    )
    st.markdown(
        "The pipeline automatically handles CMS v2.x JSON, v3.0 CSV (tall and wide formats), "
        "ZIP files, and Providence/Swedish-style nested JSON. "
        "Payer names are normalized automatically for cross-hospital comparison."
    )

    st.divider()
    st.caption(
        "Data sourced from hospital machine-readable files as required by 45 CFR Parts 180. "
        "Prices reflect what hospitals have published and may not match your actual bill. "
        "Always verify with your hospital and insurance company."
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
