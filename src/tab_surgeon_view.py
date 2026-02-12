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


def _render_sorted_bar(df: pd.DataFrame, x_col: str, y_col: str, y_title: str) -> None:
    chart_df = df[[x_col, y_col]].sort_values(y_col, ascending=False)
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{x_col}:N",
                sort=alt.SortField(field=y_col, order="descending"),
                title=x_col.replace("_", " ").title(),
            ),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            tooltip=[alt.Tooltip(f"{x_col}:N", title=x_col.replace("_", " ").title()), alt.Tooltip(f"{y_col}:Q")],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_surgeon_tab(
    df: pd.DataFrame,
    conf_df: pd.DataFrame,
    mips_df: pd.DataFrame,
) -> None:
    st.subheader("Surgeon Market Intelligence Dashboard")
    st.caption(
        "Independent-surgeon view: payer mix, local hospital positioning, and negotiation signals "
        "for alignment or employment discussions."
    )

    with st.expander("MIPS Outcomes Intelligence (Pilot - Optional)", expanded=False):
        if mips_df.empty:
            st.caption(
                "MIPS outcomes module is available but not loaded. Add `ec_public_reporting.csv` and "
                "`grp_public_reporting.csv` to `data/external/mips/2023/`, then run "
                "`python3 scripts/build_outcomes_features.py --year 2023`."
            )
            st.caption("The surgeon market and pricing analysis below still works without this module.")
        else:
            mips_view = mips_df.copy()
            for col in ["outcomes_composite", "measure_score_norm", "regional_percentile", "patient_count"]:
                if col in mips_view.columns:
                    mips_view[col] = pd.to_numeric(mips_view[col], errors="coerce")

            entity_type_options = sorted(mips_view["entity_type"].dropna().astype(str).unique().tolist())
            ent_type = _safe_selectbox(
                "Entity Type",
                entity_type_options,
                key="surgeon_mips_entity_type_v1",
            )
            scoped_mips = mips_view[mips_view["entity_type"].astype(str) == str(ent_type)].copy()

            comp = (
                scoped_mips[["entity_id", "outcomes_composite", "outcomes_confidence", "measures_observed"]]
                .drop_duplicates(subset=["entity_id"])
                .sort_values("outcomes_composite", ascending=False)
            )
            top_entities = comp.head(20).copy()
            top_entities["outcomes_composite"] = top_entities["outcomes_composite"].map(lambda x: f"{x:.1f}")
            st.markdown("**Top Entities by Outcomes Composite**")
            render_wrapped_table(top_entities)

            if not comp.empty:
                selected_entity = _safe_selectbox(
                    "Entity for Measure Detail",
                    comp["entity_id"].astype(str).tolist(),
                    key="surgeon_mips_entity_v1",
                )
                em = scoped_mips[scoped_mips["entity_id"].astype(str) == str(selected_entity)].copy()
                em = em.sort_values("measure_score_norm", ascending=False)
                detail = em[
                    [
                        "measure_cd",
                        "measure_title",
                        "measure_domain",
                        "raw_rate",
                        "patient_count",
                        "regional_percentile",
                        "measure_score_norm",
                    ]
                ].copy()
                for c in ["raw_rate", "patient_count", "regional_percentile", "measure_score_norm"]:
                    detail[c] = pd.to_numeric(detail[c], errors="coerce")
                detail["raw_rate"] = detail["raw_rate"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "n/a")
                detail["patient_count"] = detail["patient_count"].map(lambda x: f"{int(x)}" if pd.notna(x) else "n/a")
                detail["regional_percentile"] = detail["regional_percentile"].map(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "n/a"
                )
                detail["measure_score_norm"] = detail["measure_score_norm"].map(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "n/a"
                )
                st.markdown("**Measure Detail Table**")
                render_wrapped_table(detail, height=320)

    st.markdown("#### Regional Surgeon Market Snapshot")
    scope1, scope2 = st.columns(2)
    with scope1:
        code_type_options = sorted(df["code_type"].dropna().astype(str).unique().tolist())
        selected_code_types = st.multiselect(
            "Market Scope: Code Types",
            options=code_type_options,
            default=code_type_options,
            key="surgeon_market_code_types_v3",
        )
    with scope2:
        conf_options = ["HIGH", "MEDIUM", "LOW"]
        selected_conf = st.multiselect(
            "Market Scope: Confidence Tiers",
            options=conf_options,
            default=conf_options,
            key="surgeon_market_conf_v3",
        )

    scoped_df = df.copy()
    if not conf_df.empty:
        scoped_df = scoped_df.merge(
            conf_df[["code", "code_type", "confidence"]],
            on=["code", "code_type"],
            how="left",
        )
    scoped_df["confidence"] = scoped_df.get("confidence", "LOW").fillna("LOW")
    scoped_df = scoped_df[
        scoped_df["code_type"].astype(str).isin(selected_code_types)
        & scoped_df["confidence"].astype(str).isin(selected_conf)
    ].copy()
    if scoped_df.empty:
        st.info("No rows available for current market scope.")
        return

    hosp_position = (
        scoped_df.groupby("hospital_name", dropna=False)["effective_price"]
        .median()
        .reset_index(name="hospital_median")
        .sort_values("hospital_median")
    )
    proc_summary = (
        scoped_df.groupby(["code", "code_type", "procedure_label"], dropna=False)["effective_price"]
        .agg(min_rate="min", median_rate="median", max_rate="max", n_rates="count")
        .reset_index()
    )
    proc_summary = proc_summary[proc_summary["min_rate"] > 0].copy()
    proc_summary["spread_ratio"] = proc_summary["max_rate"] / proc_summary["min_rate"]

    k1, k2, k3 = st.columns(3)
    k1.metric("Hospitals in Scope", str(int(scoped_df["hospital_name"].nunique())))
    k2.metric("Procedures in Scope", str(int((scoped_df["code_type"].astype(str) + ":" + scoped_df["code"].astype(str)).nunique())))
    if proc_summary.empty:
        k3.metric("Median Procedure Spread", "n/a")
    else:
        k3.metric("Median Procedure Spread", f"{proc_summary['spread_ratio'].median():.2f}x")

    v1, v2 = st.columns(2)
    with v1:
        st.markdown("**Regional Hospital Median Rates**")
        if hosp_position.empty:
            st.info("No hospital-level summary available.")
        else:
            _render_sorted_bar(hosp_position, "hospital_name", "hospital_median", "Median Rate")
    with v2:
        st.markdown("**Top 10 Highest-Spread Procedures**")
        if proc_summary.empty:
            st.info("No procedure spread summary available.")
        else:
            top_spread = proc_summary.sort_values("spread_ratio", ascending=False).head(10)
            _render_sorted_bar(top_spread, "procedure_label", "spread_ratio", "Spread Ratio")

    st.markdown("#### Payer Landscape Across Hospitals")
    payer_hosp = (
        scoped_df.groupby(["payer_name", "hospital_name"], dropna=False)["effective_price"]
        .median()
        .reset_index(name="payer_hospital_median")
    )
    payer_summary = (
        payer_hosp.groupby("payer_name", dropna=False)["payer_hospital_median"]
        .agg(
            hospitals_covered="count",
            payer_market_median="median",
            min_rate="min",
            max_rate="max",
        )
        .reset_index()
        .sort_values(["hospitals_covered", "payer_market_median"], ascending=[False, True])
    )
    payer_summary = payer_summary[payer_summary["min_rate"] > 0].copy()
    if payer_summary.empty:
        st.info("No payer landscape rows available in the selected market scope.")
    else:
        payer_summary["cross_hospital_ratio"] = payer_summary["max_rate"] / payer_summary["min_rate"]
        ps1, ps2, ps3 = st.columns(3)
        ps1.metric("Distinct Payers", str(int(payer_summary["payer_name"].nunique())))
        ps2.metric("Median Payer Hospital Coverage", str(int(payer_summary["hospitals_covered"].median())))
        ps3.metric("Median Payer Spread", f"{payer_summary['cross_hospital_ratio'].median():.2f}x")

        pchart1, pchart2 = st.columns(2)
        with pchart1:
            st.markdown("**Top Payers by Hospital Coverage**")
            coverage_df = payer_summary.head(12).copy()
            _render_sorted_bar(coverage_df, "payer_name", "hospitals_covered", "Hospitals Covered")
        with pchart2:
            st.markdown("**Top Payers by Cross-Hospital Spread**")
            spread_df = payer_summary.sort_values("cross_hospital_ratio", ascending=False).head(12)
            _render_sorted_bar(spread_df, "payer_name", "cross_hospital_ratio", "Cross-Hospital Spread")

        payer_view = payer_summary[
            ["payer_name", "hospitals_covered", "payer_market_median", "cross_hospital_ratio"]
        ].copy()
        payer_view["payer_market_median"] = payer_view["payer_market_median"].map(fmt)
        payer_view["cross_hospital_ratio"] = payer_view["cross_hospital_ratio"].map(lambda x: f"{x:.2f}x")
        st.markdown("**Payer Landscape Table**")
        render_wrapped_table(payer_view)

    st.markdown("#### Procedure & Hospital Drill-Down")
    code_options = sorted(scoped_df["code"].dropna().astype(str).unique().tolist())
    d1, d2, d3 = st.columns(3)
    with d1:
        selected_code = _safe_selectbox(
            "Key Procedure",
            code_options,
            key="surgeon_tab_code_v3",
            format_func=lambda c: str(scoped_df[scoped_df["code"].astype(str) == c]["procedure_label"].iloc[0]),
        )
    proc_all = scoped_df[scoped_df["code"].astype(str) == str(selected_code)].copy()
    code_type_options = sorted(proc_all["code_type"].dropna().astype(str).unique().tolist())
    with d2:
        selected_code_type = _safe_selectbox(
            "Procedure Code Type",
            code_type_options,
            key="surgeon_tab_code_type_v3",
        )
    proc_all = proc_all[proc_all["code_type"].astype(str) == str(selected_code_type)].copy()
    hospital_options = _prioritize_st_joes(sorted(proc_all["hospital_name"].dropna().unique().tolist()))
    with d3:
        selected_hospital = _safe_selectbox(
            "Focus Hospital",
            hospital_options,
            key="surgeon_tab_hospital_v3",
        )

    hosp_proc_df = proc_all[proc_all["hospital_name"] == selected_hospital].copy()
    if proc_all.empty or hosp_proc_df.empty:
        st.info("No rows available for current surgeon-market drill-down filters.")
        return

    hosp_position_proc = (
        proc_all.groupby("hospital_name", dropna=False)["effective_price"]
        .median()
        .reset_index(name="hospital_median")
        .sort_values("hospital_median")
    )
    if not hosp_position_proc.empty:
        hosp_position_proc["rank_low_to_high"] = range(1, len(hosp_position_proc) + 1)
        hosp_position_view = hosp_position_proc.copy()
        hosp_position_view["hospital_median"] = hosp_position_view["hospital_median"].map(fmt)
    else:
        hosp_position_view = hosp_position_proc

    payer_mix = (
        hosp_proc_df.groupby("payer_name", dropna=False)["effective_price"]
        .agg(n_rates="count", median_rate="median")
        .reset_index()
        .sort_values("n_rates", ascending=False)
    )
    if not payer_mix.empty:
        payer_mix["share_of_rows"] = (payer_mix["n_rates"] / payer_mix["n_rates"].sum() * 100.0).round(1)
        payer_mix["median_rate"] = payer_mix["median_rate"].map(fmt)

    st.markdown(f"#### Local Hospital Positioning for Selected Procedure ({selected_code})")
    if hosp_position_view.empty:
        st.info("No cross-hospital positioning data for this procedure.")
    else:
        render_wrapped_table(hosp_position_view)

    st.markdown(f"#### Payer Mix at {selected_hospital} (Selected Procedure)")
    if payer_mix.empty:
        st.info("No payer-mix data for this hospital/procedure.")
    else:
        render_wrapped_table(payer_mix[["payer_name", "n_rates", "share_of_rows", "median_rate"]])

    confidence_label = "LOW"
    if not conf_df.empty:
        c = conf_df[
            (conf_df["code"].astype(str) == str(selected_code))
            & (conf_df["code_type"].astype(str) == str(hosp_proc_df["code_type"].iloc[0]))
        ]
        if not c.empty:
            confidence_label = str(c.iloc[0]["confidence"])

    selected_rank = None
    total_hosp = len(hosp_position_proc)
    if not hosp_position_proc.empty:
        srow = hosp_position_proc[hosp_position_proc["hospital_name"] == selected_hospital]
        if not srow.empty:
            selected_rank = int(srow.iloc[0]["rank_low_to_high"])

    spread_ratio = (
        hosp_proc_df["effective_price"].quantile(0.9) / hosp_proc_df["effective_price"].quantile(0.1)
        if len(hosp_proc_df) >= 3 and hosp_proc_df["effective_price"].quantile(0.1) > 0
        else float("nan")
    )
    align_signal = "Neutral"
    if selected_rank is not None and total_hosp > 1 and confidence_label in {"HIGH", "MEDIUM"}:
        if selected_rank <= max(1, total_hosp // 2):
            align_signal = "Favorable"
        else:
            align_signal = "Caution"

    leverage_signal = "Moderate"
    if pd.notna(spread_ratio):
        if spread_ratio >= 2.5:
            leverage_signal = "High"
        elif spread_ratio < 1.5:
            leverage_signal = "Low"

    c1, c2, c3 = st.columns(3)
    c1.metric("Evidence Confidence", confidence_label)
    c2.metric("Alignment Signal", align_signal)
    c3.metric("Negotiation Leverage", leverage_signal)

    st.markdown("#### Negotiation Support Notes")
    rank_text = f"{selected_rank}/{total_hosp}" if selected_rank is not None and total_hosp else "n/a"
    spread_text = f"{spread_ratio:.2f}x" if pd.notna(spread_ratio) else "n/a"
    st.markdown(
        f"- **Hospital rate position ({selected_code})**: {rank_text} (lower rank means lower median negotiated rate).\n"
        f"- **Payer dispersion at selected hospital**: {spread_text} (higher spread suggests payer-dependent economics).\n"
        f"- **Confidence gate**: {confidence_label} (use LOW as directional only in alignment decisions).\n"
        "- **Use case**: bring these benchmarks into compensation, block-time, and support-resource discussions."
    )
