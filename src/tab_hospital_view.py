from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from ui_tables import render_wrapped_table


def fmt(amount: float) -> str:
    return f"${amount:,.2f}"


def _prioritize_st_joes(options: list[str]) -> list[str]:
    preferred = None
    for opt in options:
        low = str(opt).lower()
        if "peacehealth" in low and ("st joe" in low or "st joseph" in low):
            preferred = opt
            break
    if preferred is None:
        return options
    return [preferred] + [o for o in options if o != preferred]


def _safe_selectbox(label: str, options: list[str], key: str, format_func=None) -> str:
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]
    if format_func is None:
        return st.selectbox(label, options=options, key=key)
    return st.selectbox(label, options=options, key=key, format_func=format_func)


def _safe_multiselect(label: str, options: list[str], default: list[str], key: str) -> list[str]:
    if key in st.session_state:
        current = st.session_state[key]
        if not isinstance(current, list) or any(v not in options for v in current):
            del st.session_state[key]
    valid_default = [v for v in default if v in options]
    return st.multiselect(label, options=options, default=valid_default, key=key)


def build_hospital_growth_scorecard(df: pd.DataFrame, hospital_name: str, conf_df: pd.DataFrame) -> pd.DataFrame:
    by_hosp = (
        df.groupby(["hospital_name", "code", "code_type", "procedure_label"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="hospital_median")
    )
    by_hosp["rank_low_to_high"] = by_hosp.groupby(["code", "code_type"])["hospital_median"].rank(
        method="min", ascending=True
    )
    by_hosp["n_hospitals"] = by_hosp.groupby(["code", "code_type"])["hospital_name"].transform("nunique")

    target = by_hosp[by_hosp["hospital_name"] == hospital_name].copy()
    if target.empty:
        return pd.DataFrame()

    hdf = df[df["hospital_name"] == hospital_name].copy()
    payer_stats = (
        hdf.groupby(["code", "code_type", "procedure_label"], dropna=False)["effective_price"]
        .agg(
            n_rates="count",
            n_payers="nunique",
            p10=lambda s: s.quantile(0.1),
            p90=lambda s: s.quantile(0.9),
            cv=lambda s: (s.std(ddof=0) / s.mean()) if s.mean() > 0 else 0,
        )
        .reset_index()
    )
    payer_stats["p90_p10_ratio"] = payer_stats["p90"] / payer_stats["p10"]

    score = target.merge(
        payer_stats[
            ["code", "code_type", "procedure_label", "n_rates", "n_payers", "p90_p10_ratio", "cv"]
        ],
        on=["code", "code_type", "procedure_label"],
        how="left",
    )

    if not conf_df.empty:
        score = score.merge(
            conf_df[["code", "code_type", "confidence"]],
            on=["code", "code_type"],
            how="left",
        )
    else:
        score["confidence"] = "LOW"

    def market_score(row: pd.Series) -> float:
        n_hosp = float(row["n_hospitals"])
        rank = float(row["rank_low_to_high"])
        if n_hosp <= 1:
            return 0.50
        return max(0.0, min(1.0, 1.0 - ((rank - 1.0) / (n_hosp - 1.0))))

    def stability_score(row: pd.Series) -> float:
        ratio = float(row["p90_p10_ratio"]) if pd.notna(row["p90_p10_ratio"]) else 3.0
        return max(0.0, min(1.0, (3.0 - ratio) / 2.0))

    conf_map = {"HIGH": 1.00, "MEDIUM": 0.65, "LOW": 0.30}
    score["confidence"] = score["confidence"].fillna("LOW")
    score["market_position_score"] = score.apply(market_score, axis=1)
    score["payer_stability_score"] = score.apply(stability_score, axis=1)
    score["confidence_score"] = score["confidence"].map(conf_map).fillna(0.30)
    score["coverage_score"] = (score["n_payers"].fillna(0) / 10.0).clip(0, 1)
    score["growth_opportunity_score"] = 100.0 * (
        0.45 * score["market_position_score"]
        + 0.25 * score["payer_stability_score"]
        + 0.20 * score["confidence_score"]
        + 0.10 * score["coverage_score"]
    )

    def action_label(row: pd.Series) -> str:
        if row["confidence"] == "LOW":
            return "Watch (Low Evidence)"
        if row["growth_opportunity_score"] >= 70:
            return "Grow"
        if row["market_position_score"] < 0.35 or row["payer_stability_score"] < 0.35:
            return "Reprice/Contract"
        return "Defend"

    score["recommended_action"] = score.apply(action_label, axis=1)
    return score.sort_values("growth_opportunity_score", ascending=False)


def render_hospital_tab(df: pd.DataFrame, conf_df: pd.DataFrame) -> None:
    st.subheader("Hospital / Periop Perspective")
    st.caption(
        "Procedure-level growth scorecard for service-line and periop leaders. "
        "Use this to identify where to grow volume vs where to focus contracting."
    )

    market_df = df.copy()
    if not conf_df.empty:
        market_df = market_df.merge(
            conf_df[["code", "code_type", "confidence"]],
            on=["code", "code_type"],
            how="left",
        )
    market_df["confidence"] = market_df.get("confidence", "LOW").fillna("LOW")

    top1, top2 = st.columns(2)
    with top1:
        code_type_options = sorted(market_df["code_type"].dropna().astype(str).unique().tolist())
        selected_code_types = _safe_multiselect(
            "Market Scope: Code Types",
            code_type_options,
            code_type_options,
            key="hospital_tab_code_types_v3",
        )
    with top2:
        conf_options = ["HIGH", "MEDIUM", "LOW"]
        selected_conf = _safe_multiselect(
            "Market Scope: Confidence Tiers",
            conf_options,
            conf_options,
            key="hospital_tab_conf_v3",
        )

    scoped_df = market_df[
        market_df["code_type"].astype(str).isin(selected_code_types)
        & market_df["confidence"].astype(str).isin(selected_conf)
    ].copy()
    if scoped_df.empty:
        st.info("No rows remain after current market scope filters.")
        return

    st.markdown("#### Regional Market Snapshot")
    proc_key = scoped_df["code_type"].astype(str) + ":" + scoped_df["code"].astype(str)
    hosp_count = int(scoped_df["hospital_name"].nunique())
    proc_count = int(proc_key.nunique())

    proc_spread = (
        scoped_df.groupby(["code", "code_type", "procedure_label", "hospital_name"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="hospital_proc_median")
    )
    spread_summary = (
        proc_spread.groupby(["code", "code_type", "procedure_label"], dropna=False)["hospital_proc_median"]
        .agg(n_hospitals="nunique", min_rate="min", max_rate="max", median_rate="median")
        .reset_index()
    )
    spread_summary = spread_summary[spread_summary["n_hospitals"] >= 2].copy()
    spread_summary["cross_hospital_ratio"] = spread_summary["max_rate"] / spread_summary["min_rate"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Hospitals in Scope", str(hosp_count))
    c2.metric("Procedures in Scope", str(proc_count))
    if spread_summary.empty:
        c3.metric("Median Cross-Hospital Spread", "n/a")
    else:
        c3.metric("Median Cross-Hospital Spread", f"{spread_summary['cross_hospital_ratio'].median():.2f}x")

    hosp_summary = (
        scoped_df.groupby("hospital_name", dropna=False)["effective_price"]
        .agg(
            median_rate="median",
            n_rates="count",
            n_payers="nunique",
        )
        .reset_index()
        .sort_values("median_rate")
    )
    if not spread_summary.empty:
        ratio_by_hospital = proc_spread.merge(
            spread_summary[["code", "code_type", "cross_hospital_ratio"]],
            on=["code", "code_type"],
            how="left",
        )
        ratio_by_hospital = (
            ratio_by_hospital.groupby("hospital_name", dropna=False)["cross_hospital_ratio"]
            .median()
            .reset_index(name="median_market_spread")
        )
        hosp_summary = hosp_summary.merge(ratio_by_hospital, on="hospital_name", how="left")
    else:
        hosp_summary["median_market_spread"] = float("nan")

    hosp_summary["median_rate"] = hosp_summary["median_rate"].map(fmt)
    hosp_summary["median_market_spread"] = hosp_summary["median_market_spread"].map(
        lambda x: f"{x:.2f}x" if pd.notna(x) else "n/a"
    )
    st.markdown("**Regional Hospital Summary Table**")
    render_wrapped_table(hosp_summary)

    st.markdown("#### Cross-Hospital Benchmark for a Procedure")
    proc_options = (
        scoped_df[["code", "code_type", "procedure_label"]]
        .drop_duplicates()
        .sort_values(["procedure_label", "code_type", "code"])
    )
    proc_options["proc_key"] = proc_options["code_type"].astype(str) + "::" + proc_options["code"].astype(str)
    proc_label_map = {
        row["proc_key"]: f"{row['procedure_label']} ({row['code_type']} {row['code']})"
        for _, row in proc_options.iterrows()
    }
    selected_proc_key = _safe_selectbox(
        "Procedure for Cross-Hospital Comparison",
        proc_options["proc_key"].tolist(),
        key="hospital_tab_market_proc_v3",
        format_func=lambda k: proc_label_map.get(k, k),
    )
    selected_code_type, selected_code = selected_proc_key.split("::", 1)
    proc_benchmark = scoped_df[
        (scoped_df["code"].astype(str) == str(selected_code))
        & (scoped_df["code_type"].astype(str) == str(selected_code_type))
    ].copy()
    proc_hosp = (
        proc_benchmark.groupby("hospital_name", dropna=False)["effective_price"]
        .agg(median_rate="median", n_rates="count", n_payers="nunique")
        .reset_index()
        .sort_values("median_rate")
    )
    if not proc_hosp.empty:
        proc_hosp["rank_low_to_high"] = range(1, len(proc_hosp) + 1)
        proc_hosp["median_rate"] = proc_hosp["median_rate"].map(fmt)
    st.markdown("**Procedure Cross-Hospital Table**")
    render_wrapped_table(proc_hosp)

    st.markdown("#### Hospital Drill-Down")
    hospital_options = _prioritize_st_joes(sorted(scoped_df["hospital_name"].dropna().unique().tolist()))
    selected_hospital = _safe_selectbox(
        "Focus Hospital",
        hospital_options,
        key="hospital_tab_focus_hospital_v3",
    )

    scorecard = build_hospital_growth_scorecard(scoped_df, selected_hospital, conf_df)
    if scorecard.empty:
        st.info("No scorecard data available for this hospital in the selected scope.")
        return

    st.markdown("#### Action Priorities for Selected Hospital")
    grow = scorecard[scorecard["recommended_action"] == "Grow"][
        ["procedure_label", "growth_opportunity_score", "confidence"]
    ].head(5)
    reprice = scorecard[scorecard["recommended_action"] == "Reprice/Contract"][
        ["procedure_label", "growth_opportunity_score", "confidence"]
    ].head(5)
    low_evidence = scorecard[scorecard["recommended_action"] == "Watch (Low Evidence)"][
        ["procedure_label", "growth_opportunity_score", "confidence"]
    ].head(5)

    c_left, c_mid, c_right = st.columns(3)
    with c_left:
        st.markdown("**Top Grow Candidates**")
        render_wrapped_table(grow)
    with c_mid:
        st.markdown("**Reprice / Contract Candidates**")
        render_wrapped_table(reprice)
    with c_right:
        st.markdown("**Watch (Low Evidence) Candidates**")
        render_wrapped_table(low_evidence)

    st.markdown("#### Growth Opportunity Visuals")
    vc = (
        scorecard["recommended_action"]
        .value_counts()
        .rename_axis("action")
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    top_growth = (
        scorecard.sort_values("growth_opportunity_score", ascending=False)
        .head(10)[["procedure_label", "growth_opportunity_score"]]
        .set_index("procedure_label")
    )
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Action Mix**")
        vc_sorted = vc.sort_values("count", ascending=False)
        action_chart = (
            alt.Chart(vc_sorted)
            .mark_bar()
            .encode(
                x=alt.X(
                    "action:N",
                    sort=alt.SortField(field="count", order="descending"),
                    title="Action",
                ),
                y=alt.Y("count:Q", title="Count"),
                tooltip=[
                    alt.Tooltip("action:N", title="Action"),
                    alt.Tooltip("count:Q", title="Count"),
                ],
            )
        )
        st.altair_chart(action_chart, use_container_width=True)
    with p2:
        st.markdown("**Top 10 Opportunity Scores**")
        top_growth_df = (
            top_growth.reset_index()
            .rename(columns={"index": "procedure"})
            .sort_values("growth_opportunity_score", ascending=False)
        )
        chart = (
            alt.Chart(top_growth_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "procedure_label:N",
                    sort=alt.SortField(field="growth_opportunity_score", order="descending"),
                    title="Procedure",
                ),
                y=alt.Y("growth_opportunity_score:Q", title="Growth Opportunity Score"),
                tooltip=[
                    alt.Tooltip("procedure_label:N", title="Procedure"),
                    alt.Tooltip("growth_opportunity_score:Q", title="Score", format=".1f"),
                ],
            )
        )
        st.altair_chart(chart, use_container_width=True)

    detail_codes = sorted(scorecard["code"].astype(str).unique().tolist())
    label_map = (
        scorecard.assign(_code=scorecard["code"].astype(str))[["_code", "procedure_label"]]
        .drop_duplicates("_code")
        .set_index("_code")["procedure_label"]
        .to_dict()
    )
    detail_code = _safe_selectbox(
        "Detail Procedure",
        detail_codes,
        key="hospital_tab_detail_code_v2",
        format_func=lambda c: f"{label_map.get(c, c)} ({c})",
    )

    selected_proc_row = scorecard[scorecard["code"].astype(str) == str(detail_code)].head(1)
    if not selected_proc_row.empty:
        r = selected_proc_row.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Growth Opportunity Score", f"{r['growth_opportunity_score']:.1f}/100")
        c2.metric("Market Rank", f"{int(r['rank_low_to_high'])}/{int(r['n_hospitals'])}")
        c3.metric("Payer Dispersion (p90/p10)", f"{r['p90_p10_ratio']:.2f}x")
        c4.metric("Recommended Action", str(r["recommended_action"]))
        st.caption(
            f"Confidence: **{r['confidence']}** | Payers observed: **{int(r['n_payers'])}** | "
            f"Procedure median at {selected_hospital}: **{fmt(r['hospital_median'])}**"
        )

    view = scorecard[
        [
            "code",
            "code_type",
            "procedure_label",
            "hospital_median",
            "rank_low_to_high",
            "n_hospitals",
            "n_payers",
            "p90_p10_ratio",
            "confidence",
            "growth_opportunity_score",
            "recommended_action",
        ]
    ].copy()
    view = view.rename(columns={"procedure_label": "procedure"})
    view["hospital_median"] = view["hospital_median"].map(fmt)
    view["p90_p10_ratio"] = view["p90_p10_ratio"].map(lambda x: f"{x:.2f}x")
    view["growth_opportunity_score"] = view["growth_opportunity_score"].map(lambda x: f"{x:.1f}")

    st.markdown("#### Procedure Growth Scorecard")
    render_wrapped_table(view, height=500)

    st.caption(
        "Scoring model (MVP): 45% market position, 25% payer stability, "
        "20% confidence gate, 10% payer coverage."
    )
