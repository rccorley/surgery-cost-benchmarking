from __future__ import annotations

import pandas as pd
import streamlit as st


def render_wrapped_table(df: pd.DataFrame, height: int | None = 340) -> None:
    """Render a dataframe with wrapped text and bounded height + scrolling."""
    if df.empty:
        st.info("No rows to display.")
        return

    style_attr = f"max-height: {height}px;" if height is not None else "max-height: 340px;"
    html = df.to_html(index=False, escape=True, classes=["wrapped-table"])
    st.markdown(
        f"<div class='wrapped-table-scroll' style='{style_attr}'>{html}</div>",
        unsafe_allow_html=True,
    )
