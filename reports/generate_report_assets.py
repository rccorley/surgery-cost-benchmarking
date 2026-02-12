from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
PLOTS = ROOT / "reports" / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

normalized = pd.read_csv(PROCESSED / "normalized_prices.csv")
procedure = pd.read_csv(PROCESSED / "procedure_benchmark.csv")
hospital = pd.read_csv(PROCESSED / "hospital_benchmark.csv")
focus_rank = pd.read_csv(PROCESSED / "focus_hospital_rank.csv")
payer_disp = pd.read_csv(PROCESSED / "payer_dispersion.csv")


def draw_bar_chart(labels, values, out_file, title, y_fmt="{value:,.0f}", color="#2a9d8f"):
    w, h = 1280, 760
    margin = 100
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)

    d.text((margin, 24), title, fill="black")
    d.line((margin, h - margin, w - margin, h - margin), fill="black", width=2)
    d.line((margin, margin, margin, h - margin), fill="black", width=2)

    if not values:
        d.text((margin, h // 2), "No data", fill="black")
        img.save(out_file)
        return

    vmax = max(values) if max(values) > 0 else 1
    n = len(values)
    plot_w = w - 2 * margin
    bar_w = max(18, int(plot_w / (n * 1.75)))
    gap = bar_w // 2

    x = margin + gap
    for label, value in zip(labels, values):
        bar_h = int((value / vmax) * (h - 2 * margin - 50))
        y0 = h - margin - bar_h
        d.rectangle((x, y0, x + bar_w, h - margin), fill=color, outline="black")
        d.text((x, h - margin + 8), str(label)[:14], fill="black")
        d.text((x, y0 - 18), y_fmt.format(value=value), fill="black")
        x += bar_w + gap

    img.save(out_file)


if not hospital.empty:
    h = hospital.sort_values("median_price")
    labels = [
        name.replace("Providence Health And Services - Washington", "Providence")
        .replace("PeaceHealth St Joseph Medical Center", "PeaceHealth")
        for name in h["hospital_name"].tolist()
    ]
    draw_bar_chart(
        labels=labels,
        values=h["median_price"].tolist(),
        out_file=PLOTS / "hospital_median_price.png",
        title="Hospital Comparison: Median Effective Price",
        y_fmt="${value:,.0f}",
        color="#287271",
    )

if not normalized.empty:
    p = normalized.groupby("code", dropna=False)["effective_price"].median().reset_index().sort_values("effective_price")
    draw_bar_chart(
        labels=p["code"].astype(str).tolist(),
        values=p["effective_price"].tolist(),
        out_file=PLOTS / "procedure_median_price.png",
        title="Procedure Comparison: Median Effective Price",
        y_fmt="${value:,.0f}",
        color="#2a9d8f",
    )

if not procedure.empty:
    q = procedure.sort_values("p90_p10_ratio")
    draw_bar_chart(
        labels=q["code"].astype(str).tolist(),
        values=q["p90_p10_ratio"].tolist(),
        out_file=PLOTS / "procedure_dispersion_ratio.png",
        title="Procedure Dispersion: p90/p10 Ratio",
        y_fmt="{value:.2f}x",
        color="#264653",
    )

if not focus_rank.empty:
    f = focus_rank.sort_values("rank_low_to_high")
    draw_bar_chart(
        labels=f["code"].astype(str).tolist(),
        values=f["rank_low_to_high"].tolist(),
        out_file=PLOTS / "focus_hospital_rank.png",
        title="PeaceHealth Rank vs Corridor Peers (Lower is Better)",
        y_fmt="#{value:.0f}",
        color="#e76f51",
    )

if not payer_disp.empty:
    ph = payer_disp[payer_disp["hospital_name"].astype(str).str.contains("PeaceHealth", case=False, na=False)]
    if not ph.empty:
        ph = ph.sort_values("p90_p10_ratio", ascending=False)
        draw_bar_chart(
            labels=ph["code"].astype(str).tolist(),
            values=ph["p90_p10_ratio"].tolist(),
            out_file=PLOTS / "peacehealth_payer_dispersion.png",
            title="PeaceHealth Payer Dispersion by Procedure (p90/p10)",
            y_fmt="{value:.2f}x",
            color="#f4a261",
        )

print("Generated plot assets in", PLOTS)
