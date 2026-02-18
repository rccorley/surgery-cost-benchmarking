from __future__ import annotations

import altair as alt
from html import escape
import pandas as pd
import streamlit as st

from patient_estimator import (
    BenefitDesign,
    compare_hospitals,
    compare_hospitals_by_group,
    compare_hospitals_by_insurer,
    compare_payers,
    estimate_episode_cost,
    estimate_patient_cost,
    PatientEstimate,
)
from ui_tables import render_wrapped_table

_SRC_ACTUAL = "Actual hospital data"
_SRC_ESTIMATE = "CMS benchmark estimate"


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


def _render_confidence_badge(conf_row: pd.Series | None) -> None:
    """Show a confidence badge based on procedure data quality."""
    if conf_row is None or conf_row.empty:
        return
    level = str(conf_row.get("confidence", "")).upper()
    n_hosp = int(conf_row.get("n_hospitals", 0))
    n_rates = int(conf_row.get("n_rates", 0))
    n_payers = int(conf_row.get("n_unique_payers", 0))

    if level == "HIGH":
        st.success(
            f"**HIGH confidence** — {n_hosp} hospitals, {n_rates} rates, "
            f"{n_payers} payers report this procedure",
            icon="\u2705",
        )
    elif level == "MEDIUM":
        st.info(
            f"**MEDIUM confidence** — {n_hosp} hospitals, {n_rates} rates. "
            "Cross-hospital comparisons available but limited.",
            icon="\u2139\ufe0f",
        )
    else:
        st.warning(
            f"**LOW confidence** — Only {n_hosp} hospital(s) report this procedure. "
            "Comparisons may be unreliable. Verify with your hospital.",
            icon="\u26a0\ufe0f",
        )


def render_patient_tab(
    df: pd.DataFrame,
    coinsurance_pct: int,
    benefit: BenefitDesign,
    conf_df: pd.DataFrame | None = None,
) -> None:
    st.markdown("#### What will my surgery cost?")

    # ── Hospital selection (first — drives procedure and payer lists) ──
    all_hospitals = _prioritize_st_joes(sorted(df["hospital_name"].unique().tolist()))
    prev_hospital = st.session_state.get("_prev_patient_hospital")

    # Read hospital from session state (or default to first) so we can
    # compute procedure options before rendering all three dropdowns level.
    selected_hospital = st.session_state.get("patient_selected_hospital", all_hospitals[0])
    if selected_hospital not in all_hospitals:
        selected_hospital = all_hospitals[0]

    hospital_changed = selected_hospital != prev_hospital
    if hospital_changed:
        st.session_state["_prev_patient_hospital"] = selected_hospital
        for key in ("patient_selected_code", "patient_selected_payer"):
            if key in st.session_state:
                del st.session_state[key]
        if prev_hospital is not None:
            st.rerun()

    # ── Procedure sort + payer counts ─────────────────────────────────
    hosp_df = df[df["hospital_name"] == selected_hospital]
    payer_counts = (
        hosp_df[hosp_df["negotiated_rate"].notna()]
        .groupby("code")["payer_name"]
        .nunique()
        .rename("n_payers")
    )
    proc_options = (
        hosp_df[["code", "code_type", "description", "procedure_label"]]
        .drop_duplicates(subset=["code"])
        .join(payer_counts, on="code")
    )

    sort_order = st.radio(
        "Sort procedures by",
        options=["Most plans first", "A → Z"],
        horizontal=True,
        key="proc_sort_order",
        label_visibility="collapsed",
    )

    if sort_order == "A → Z":
        proc_options = proc_options.sort_values("procedure_label")
    else:
        proc_options = proc_options.sort_values("n_payers", ascending=False)

    def _proc_label(row: pd.Series) -> str:
        n = int(row["n_payers"]) if pd.notna(row.get("n_payers")) else 0
        return f"{row['procedure_label']}  ({row['code_type']} {row['code']}) — {n} plans"

    proc_display = {row["code"]: _proc_label(row) for _, row in proc_options.iterrows()}
    all_codes = list(proc_display.keys())

    if st.session_state.get("patient_selected_code") not in all_codes:
        st.session_state.pop("patient_selected_code", None)

    # ── Payer options (computed before rendering) ─────────────────────
    selected_code = st.session_state.get("patient_selected_code", all_codes[0] if all_codes else None)
    if selected_code not in all_codes:
        selected_code = all_codes[0] if all_codes else None

    proc_df = df[df["code"] == selected_code] if selected_code else pd.DataFrame()
    hosp_proc_df = proc_df[proc_df["hospital_name"] == selected_hospital] if not proc_df.empty else pd.DataFrame()
    all_payers = sorted(hosp_proc_df["payer_name"].unique().tolist()) if not hosp_proc_df.empty else []

    if st.session_state.get("patient_selected_payer") not in all_payers:
        st.session_state.pop("patient_selected_payer", None)

    # ── All three dropdowns on one level ──────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_hospital = st.selectbox(
            "Hospital",
            options=all_hospitals,
            key="patient_selected_hospital",
            help="Select a hospital to see its procedures and insurance plans.",
        )

    with c2:
        selected_code = st.selectbox(
            "Procedure",
            options=all_codes,
            format_func=lambda c: proc_display.get(c, c),
            key="patient_selected_code",
            help="Type to search. Sorted by number of insurance plans. Each option shows the plan count.",
        )

    with c3:
        selected_payer = st.selectbox(
            "Insurance plan",
            options=all_payers,
            key="patient_selected_payer",
            help="Type to search. Only shows plans with a published negotiated rate for this hospital and procedure.",
        )

    # Recompute filtered frames from actual selectbox values
    hosp_proc_df = df[(df["hospital_name"] == selected_hospital) & (df["code"] == selected_code)]

    # ── Confidence signal ────────────────────────────────────────────
    if conf_df is not None and not conf_df.empty:
        match = conf_df[conf_df["code"].astype(str) == str(selected_code)]
        if not match.empty:
            _render_confidence_badge(match.iloc[0])

    rates = hosp_proc_df[hosp_proc_df["payer_name"] == selected_payer]["effective_price"]
    if rates.empty:
        st.warning("No rate found for this combination.")
        return

    median_rate = rates.median()
    est: PatientEstimate = estimate_patient_cost(median_rate, benefit)

    st.divider()

    st.subheader("Facility Fee — Your Estimated Cost")
    st.markdown(
        ":green[**This is from actual hospital data**] — the negotiated rate "
        "published in the hospital's CMS-mandated price transparency file."
    )

    result_cols = st.columns(3)
    result_cols[0].metric(
        "You Pay (Facility Fee)",
        fmt(est.patient_total),
        help="Your estimated out-of-pocket for the facility fee.",
    )
    result_cols[1].metric("Plan Pays", fmt(est.plan_pays))
    result_cols[2].metric(
        "Negotiated Rate",
        fmt(est.negotiated_rate),
        help="The total facility price your insurer negotiated with this hospital.",
    )

    st.markdown("#### How your facility fee cost breaks down")
    breakdown_data = pd.DataFrame(
        [
            {
                "Step": "1. Deductible",
                "Amount": est.deductible_portion,
                "Explanation": f"You pay the first {fmt(est.deductible_portion)} toward your remaining deductible",
            },
            {
                "Step": "2. Coinsurance",
                "Amount": est.coinsurance_portion,
                "Explanation": f"You pay {coinsurance_pct}% of the remaining {fmt(est.negotiated_rate - est.deductible_portion)}",
            },
            {
                "Step": "3. OOP Max Cap",
                "Amount": est.patient_total,
                "Explanation": "Hit OOP max -- plan covers the rest"
                if est.hit_oop_max
                else "Below your OOP max",
            },
        ]
    )
    breakdown_data["Amount"] = breakdown_data["Amount"].map(fmt)
    render_wrapped_table(breakdown_data)

    if est.hit_oop_max:
        st.info(
            f"Your costs hit your out-of-pocket maximum ({fmt(benefit.oop_max_remaining)}). "
            "Your plan covers 100% beyond this point for the rest of the year."
        )

    st.divider()
    st.subheader("Total Episode Cost — Estimated")
    st.markdown(
        ":orange[**These are estimates, not actual prices.**] Surgeon, anesthesia, "
        "pathology, and imaging fees are estimated using published CMS benchmark "
        "ratios. Only the facility fee comes from real hospital data."
    )

    episode = estimate_episode_cost(median_rate, selected_code)
    ep_cols = st.columns(2)
    with ep_cols[0]:
        st.metric("Facility Fee", fmt(episode.facility_fee))
        st.caption(":green[Actual negotiated rate]")
    with ep_cols[1]:
        st.metric(
            "Estimated Total Episode Cost",
            fmt(episode.total_episode),
            delta=f"+{fmt(episode.total_episode - episode.facility_fee)} estimated other fees",
            delta_color="inverse",
        )
        st.caption(":orange[Includes estimated fees]")

    episode_breakdown = pd.DataFrame(
        [
            {"Component": "Facility Fee", "Estimated Amount": episode.facility_fee, "Source": _SRC_ACTUAL},
            {"Component": "Surgeon Professional Fee", "Estimated Amount": episode.surgeon_fee, "Source": _SRC_ESTIMATE},
            {"Component": "Anesthesia", "Estimated Amount": episode.anesthesia_fee, "Source": _SRC_ESTIMATE},
            {"Component": "Pathology & Lab", "Estimated Amount": episode.pathology_lab_fee, "Source": _SRC_ESTIMATE},
            {"Component": "Imaging", "Estimated Amount": episode.imaging_fee, "Source": _SRC_ESTIMATE},
        ]
    )
    episode_breakdown["Estimated Amount"] = episode_breakdown["Estimated Amount"].map(fmt)
    render_wrapped_table(episode_breakdown)

    st.caption(f"Category: **{episode.category}**")
    if episode.is_default:
        st.warning(
            "This procedure does not have specific CMS benchmark data. "
            "The estimates above use conservative default ratios."
        )

    episode_est = estimate_patient_cost(episode.total_episode, benefit)
    st.markdown("#### Your estimated out-of-pocket on the total episode")
    ep_result_cols = st.columns(3)
    ep_result_cols[0].metric(
        "You Pay (Total Episode)",
        fmt(episode_est.patient_total),
        help="Estimated out-of-pocket if all components apply to your plan.",
    )
    ep_result_cols[1].metric("Plan Pays", fmt(episode_est.plan_pays))
    ep_result_cols[2].metric("Total Episode", fmt(episode_est.negotiated_rate))

    if episode_est.hit_oop_max:
        st.info(
            f"The total episode pushes you to your out-of-pocket maximum "
            f"({fmt(benefit.oop_max_remaining)}). Your plan covers the rest."
        )

    st.divider()
    st.subheader("How Does Your Plan Compare?")
    st.caption(
        "Same procedure, same hospital -- but different plans pay very different rates. "
        "Here's what patients on other plans would pay with the same benefit design."
    )

    payer_comp = compare_payers(df, selected_hospital, selected_code, benefit)
    if not payer_comp.empty:
        st.markdown(f"**{len(payer_comp)} plans** have negotiated rates for this procedure at this hospital.")
        st.markdown("**Visual: Out-of-Pocket by Plan**")
        payer_chart = payer_comp[["payer", "your_estimated_cost"]].head(12).copy()
        _render_sorted_bar(payer_chart, "payer", "your_estimated_cost", "Estimated Out-of-Pocket")
        payer_comp_display = payer_comp.copy()
        for col in ["negotiated_rate", "your_estimated_cost", "plan_pays", "deductible_portion", "coinsurance_portion"]:
            payer_comp_display[col] = payer_comp_display[col].map(fmt)
        row_height = 35
        header_height = 38
        table_height = header_height + row_height * len(payer_comp_display) + 2
        st.markdown("**Plan Comparison Table**")
        render_wrapped_table(payer_comp_display, height=min(table_height, 800))

        cheapest = payer_comp.iloc[0]
        most_expensive = payer_comp.iloc[-1]
        spread = most_expensive["your_estimated_cost"] - cheapest["your_estimated_cost"]
        if spread > 0:
            st.markdown(
                "<p><strong>Payer spread at this hospital:</strong> "
                f"The cheapest plan (<strong>{escape(str(cheapest['payer']))}</strong>) would cost you "
                f"<strong>{fmt(cheapest['your_estimated_cost'])}</strong>, while the most expensive "
                f"(<strong>{escape(str(most_expensive['payer']))}</strong>) would cost "
                f"<strong>{fmt(most_expensive['your_estimated_cost'])}</strong> "
                f"- a difference of <strong>{fmt(spread)}</strong> for the same surgery.</p>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("Same Plan, Different Hospitals")
    st.caption(
        "If your plan is accepted at multiple corridor hospitals, "
        "here's how the cost would differ."
    )

    # Tiered cross-hospital comparison:
    # 1. Exact payer name match
    # 2. payer_canonical (same insurer + plan type, e.g. "Aetna - Commercial")
    # 3. payer_group (same insurer, all plan types, e.g. "Aetna")
    hosp_comp = compare_hospitals(df, selected_payer, selected_code, benefit)
    group_comp = compare_hospitals_by_group(df, selected_payer, selected_code, benefit)
    insurer_comp = compare_hospitals_by_insurer(df, selected_payer, selected_code, benefit)
    canonical_label = group_comp.attrs.get("canonical_label", "") if not group_comp.empty else ""
    insurer_label = insurer_comp.attrs.get("insurer_label", "") if not insurer_comp.empty else ""

    exact_count = len(hosp_comp) if not hosp_comp.empty else 0
    group_count = len(group_comp) if not group_comp.empty else 0
    insurer_count = len(insurer_comp) if not insurer_comp.empty else 0

    # Pick the best tier that shows multi-hospital data
    if group_count > 1 and group_count >= exact_count:
        show_comp = group_comp
        match_tier = "canonical"
    elif exact_count > 1:
        show_comp = hosp_comp
        match_tier = "exact"
    elif insurer_count > 1:
        show_comp = insurer_comp
        match_tier = "insurer"
    else:
        show_comp = pd.DataFrame()
        match_tier = "none"

    if not show_comp.empty and len(show_comp) > 1:
        if match_tier == "canonical" and canonical_label:
            st.markdown(
                f"**{len(show_comp)} hospitals** have **{escape(canonical_label)}** plans "
                f"for this procedure."
            )
        elif match_tier == "insurer" and insurer_label:
            st.markdown(
                f"Your exact plan type is only at one hospital, but **{len(show_comp)} hospitals** "
                f"have **{escape(insurer_label)}** plans (across plan types) for this procedure."
            )
            st.caption(
                "Note: This compares all plan types from the same insurer "
                "(e.g. Commercial, Medicare Advantage, Medicaid). Rates may differ by plan type."
            )
        else:
            st.markdown(f"**{len(show_comp)} hospitals** have this exact plan for this procedure.")
        st.markdown("**Visual: Out-of-Pocket by Hospital**")
        hosp_chart = show_comp[["hospital", "your_estimated_cost"]].copy()
        _render_sorted_bar(hosp_chart, "hospital", "your_estimated_cost", "Estimated Out-of-Pocket")
        show_display = show_comp.copy()
        fmt_cols = ["negotiated_rate", "your_estimated_cost", "plan_pays", "deductible_portion", "coinsurance_portion"]
        for col in fmt_cols:
            if col in show_display.columns:
                show_display[col] = show_display[col].map(fmt)
        row_height = 35
        header_height = 38
        table_height = header_height + row_height * len(show_display) + 2
        st.markdown("**Hospital Comparison Table**")
        render_wrapped_table(show_display, height=min(table_height, 800))

        cheapest_h = show_comp.iloc[0]
        most_expensive_h = show_comp.iloc[-1]
        savings = most_expensive_h["your_estimated_cost"] - cheapest_h["your_estimated_cost"]
        if savings > 0:
            st.markdown(
                "<p><strong>Potential savings by choosing a different hospital:</strong> "
                f"Going to <strong>{escape(str(cheapest_h['hospital']))}</strong> instead of "
                f"<strong>{escape(str(most_expensive_h['hospital']))}</strong> could save you "
                f"<strong>{fmt(savings)}</strong> out-of-pocket.</p>",
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "This plan only has negotiated rates at one hospital "
            "in the corridor for this procedure."
        )

    st.divider()
    st.subheader("Quick Visual Summary")
    v1, v2 = st.columns(2)
    with v1:
        st.markdown("**Episode Cost Component Mix**")
        component_chart = (
            pd.DataFrame(
                [
                    {"component": "Facility", "amount": episode.facility_fee},
                    {"component": "Surgeon", "amount": episode.surgeon_fee},
                    {"component": "Anesthesia", "amount": episode.anesthesia_fee},
                    {"component": "Path/Lab", "amount": episode.pathology_lab_fee},
                    {"component": "Imaging", "amount": episode.imaging_fee},
                ]
            )
            .rename(columns={"component": "label", "amount": "value"})
        )
        _render_sorted_bar(component_chart, "label", "value", "Estimated Amount")
    with v2:
        st.markdown("**Your Cost vs Plan Cost (Total Episode)**")
        share_chart = (
            pd.DataFrame(
                [
                    {"bucket": "You Pay", "amount": episode_est.patient_total},
                    {"bucket": "Plan Pays", "amount": episode_est.plan_pays},
                ]
            )
            .rename(columns={"bucket": "label", "amount": "value"})
        )
        _render_sorted_bar(share_chart, "label", "value", "Amount")

    st.divider()
    st.markdown("#### Data Sources & Disclaimers")
    st.markdown(
        """
**What's real vs. estimated in this tool:**

| Data | Source | Reliability |
|------|--------|-------------|
| Facility fee (negotiated rate) | Hospital CMS transparency file | **Actual data** |
| Surgeon, anesthesia, pathology, imaging fees | CMS benchmark ratios | Approximate estimate |
| Your out-of-pocket calculation | Your inputs above | Depends on accuracy of inputs |

**Important:**
- **Not a bill.** Actual charges depend on clinical complexity, length of stay,
  and complications.
- **Verify with your insurer.** Always call your insurance company and the
  hospital's financial counselor for a formal pre-operative estimate.
- **Post-acute care not included.** Rehabilitation, home health, and follow-up
  visits can add 15-40% for major inpatient procedures.
"""
    )

