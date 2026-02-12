from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


@st.cache_data
def load_data() -> pd.DataFrame:
    path = PROCESSED / "normalized_prices.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["hospital_name"] = df["hospital_name"].astype("string")
    df["payer_name"] = df["payer_name"].astype("string").fillna("UNKNOWN")
    df["code"] = df["code"].astype("string")
    df["code_type"] = df["code_type"].astype("string")
    df["description"] = df["description"].astype("string")
    df["effective_price"] = pd.to_numeric(df["effective_price"], errors="coerce")
    return df[df["effective_price"].notna()]


@st.cache_data
def load_procedure_confidence() -> pd.DataFrame:
    path = PROCESSED / "procedure_confidence.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def summarize_procedure(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(["code", "code_type", "description"], dropna=False)["effective_price"]
    out = g.agg(n_rates="count", median_price="median", mean_price="mean", min_price="min", max_price="max").reset_index()
    q = g.quantile([0.1, 0.9]).unstack(level=-1).reset_index().rename(columns={0.1: "p10", 0.9: "p90"})
    out = out.merge(q, on=["code", "code_type", "description"], how="left")
    out["p90_p10_ratio"] = out["p90"] / out["p10"]
    return out.sort_values("median_price", ascending=False)


def summarize_hospital(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("hospital_name", dropna=False)["effective_price"]
    out = g.agg(n_rates="count", median_price="median", mean_price="mean", min_price="min", max_price="max").reset_index()
    out["cv"] = g.std(ddof=0).values / g.mean().values
    return out.sort_values("median_price", ascending=False)


def payer_dispersion(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(["hospital_name", "code", "code_type", "description"], dropna=False)["effective_price"]
    out = g.agg(n_rates="count", median_price="median", min_price="min", max_price="max").reset_index()
    q = g.quantile([0.1, 0.9]).unstack(level=-1).reset_index().rename(columns={0.1: "p10", 0.9: "p90"})
    n_payers = (
        df.groupby(["hospital_name", "code", "code_type", "description"], dropna=False)["payer_name"]
        .nunique()
        .reset_index(name="n_unique_payers")
    )
    out = out.merge(q, on=["hospital_name", "code", "code_type", "description"], how="left")
    out = out.merge(n_payers, on=["hospital_name", "code", "code_type", "description"], how="left")
    out["p90_p10_ratio"] = out["p90"] / out["p10"]
    return out.sort_values("p90_p10_ratio", ascending=False)


def main() -> None:
    st.set_page_config(page_title="Surgery Cost Benchmarking", layout="wide")
    st.title("Surgery Cost Benchmarking Explorer")
    st.caption("Filter by procedure, hospital, and payer. Use readiness indicators to judge confidence before drawing conclusions.")

    df = load_data()
    conf_df = load_procedure_confidence()
    if df.empty:
        st.error("No processed data found. Run the benchmark pipeline first to generate data/processed/normalized_prices.csv.")
        return

    with st.sidebar:
        st.header("Filters")
        hospitals = sorted(df["hospital_name"].dropna().astype(str).unique().tolist())
        code_types = sorted(df["code_type"].dropna().astype(str).unique().tolist())
        procedures = sorted(df["code"].dropna().astype(str).unique().tolist())
        payers = sorted(df["payer_name"].dropna().astype(str).unique().tolist())

        selected_hospitals = st.multiselect("Hospital", hospitals, default=hospitals)
        selected_code_types = st.multiselect("Code Type", code_types, default=code_types)
        selected_procedures = st.multiselect("Procedure Code", procedures, default=procedures)
        selected_payers = st.multiselect("Payer", payers, default=payers)

    filtered = df[
        df["hospital_name"].astype(str).isin(selected_hospitals)
        & df["code_type"].astype(str).isin(selected_code_types)
        & df["code"].astype(str).isin(selected_procedures)
        & df["payer_name"].astype(str).isin(selected_payers)
    ].copy()

    n_records = len(filtered)
    n_hosp = filtered["hospital_name"].nunique(dropna=True)
    n_proc = filtered[["code", "code_type"]].drop_duplicates().shape[0]
    n_pay = filtered["payer_name"].nunique(dropna=True)

    cross_hosp = (
        filtered.groupby(["code", "code_type"], dropna=False)["hospital_name"]
        .nunique()
        .reset_index(name="n_hospitals")
    )
    n_cross = int((cross_hosp["n_hospitals"] >= 2).sum()) if not cross_hosp.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Records", f"{n_records:,}")
    c2.metric("Hospitals", n_hosp)
    c3.metric("Procedure Buckets", n_proc)
    c4.metric("Payers", n_pay)
    c5.metric("Cross-Hospital Comparable Procedures", n_cross)

    if not conf_df.empty:
        conf_counts = conf_df["confidence"].value_counts()
        st.caption(
            "Procedure confidence counts: "
            + ", ".join([f"{k}: {v}" for k, v in conf_counts.items()])
        )

    if n_hosp < 2:
        st.warning("Only one hospital is currently in scope after filters, so cross-hospital conclusions are not reliable.")
    elif n_cross < 2:
        st.warning("Very few procedures have at least 2 hospitals after filters; comparative conclusions are limited.")

    proc_summary = summarize_procedure(filtered)
    hosp_summary = summarize_hospital(filtered)
    pay_disp = payer_dispersion(filtered)

    st.subheader("Hospital Median Price")
    if hosp_summary.empty:
        st.info("No data under current filters.")
    else:
        chart_df = hosp_summary[["hospital_name", "median_price"]].sort_values(
            "median_price", ascending=False
        )
        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "hospital_name:N",
                    sort=alt.SortField(field="median_price", order="descending"),
                    title="Hospital",
                ),
                y=alt.Y("median_price:Q", title="Median Price"),
                tooltip=[
                    alt.Tooltip("hospital_name:N", title="Hospital"),
                    alt.Tooltip("median_price:Q", title="Median Price", format=",.2f"),
                ],
            )
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(hosp_summary, use_container_width=True)

    st.subheader("Procedure Summary")
    if proc_summary.empty:
        st.info("No data under current filters.")
    else:
        st.dataframe(proc_summary, use_container_width=True)

    st.subheader("Procedure Confidence Gates")
    if conf_df.empty:
        st.info("No procedure_confidence.csv found. Re-run benchmark pipeline to generate confidence gates.")
    else:
        conf_filtered = conf_df[
            conf_df["code"].astype(str).isin(selected_procedures)
            & conf_df["code_type"].astype(str).isin(selected_code_types)
        ].copy()
        st.dataframe(conf_filtered, use_container_width=True)

    st.subheader("Payer Dispersion by Hospital and Procedure")
    if pay_disp.empty:
        st.info("No data under current filters.")
    else:
        st.dataframe(pay_disp, use_container_width=True)

    st.subheader("Raw Filtered Records")
    st.dataframe(filtered.sort_values(["hospital_name", "code", "effective_price"], ascending=[True, True, False]), use_container_width=True)


if __name__ == "__main__":
    main()
