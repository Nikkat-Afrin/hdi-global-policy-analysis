"""Build a self-contained interactive HDI dashboard (docs/index.html).

Four linked interactive views over the UNDP HDR 2021-22 table:

  1. World choropleth of HDI values (hover for components)
  2. GNI per capita (log) vs HDI — the classic development-economics scatter,
     with marker size = life expectancy
  3. Top / bottom 15 countries by HDI
  4. Education gap: expected vs mean years of schooling for the largest gaps

The output is a single static HTML file that renders anywhere (GitHub Pages
serves it from /docs) — no server, no build step, plotly.js from CDN.

Run from the repo root:
    python src/build_dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "index.html"

NUMERIC = ["HDI rank", "HDI Value", "Life expectancy at birth",
           "Expected years of schooling", "Mean years of schooling",
           "GNI per Capita"]


def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "HDR21-22_HDI.csv")
    for c in NUMERIC:
        # values like "64,660" carry thousands separators in the raw export
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False),
                              errors="coerce")
    df = df.dropna(subset=["HDI Value", "Country"]).copy()
    df["Country"] = df["Country"].str.strip()
    return df


def hover(df: pd.DataFrame) -> pd.Series:
    gni = df["GNI per Capita"].map(
        lambda v: f"${v:,.0f}" if pd.notna(v) else "n/a")
    life = df["Life expectancy at birth"].map(
        lambda v: f"{v:.1f}" if pd.notna(v) else "n/a")
    return ("<b>" + df["Country"] + "</b>"
            + "<br>HDI: " + df["HDI Value"].round(3).astype(str)
            + "<br>Life expectancy: " + life
            + "<br>GNI/capita: " + gni)


def build_figures(df: pd.DataFrame) -> list[go.Figure]:
    figs = []

    # 1 — choropleth
    fig = go.Figure(go.Choropleth(
        locations=df["Country"], locationmode="country names",
        z=df["HDI Value"], colorscale="Viridis",
        colorbar_title="HDI", text=hover(df), hoverinfo="text+z"))
    fig.update_layout(title="Human Development Index (HDR 2021-22)",
                      geo=dict(showframe=False, projection_type="natural earth"),
                      margin=dict(l=10, r=10, t=50, b=10))
    figs.append(fig)

    # 2 — GNI vs HDI scatter
    fig = go.Figure(go.Scatter(
        x=df["GNI per Capita"], y=df["HDI Value"], mode="markers",
        marker=dict(size=((df["Life expectancy at birth"].fillna(60) - 45) / 2.2).clip(lower=3),
                    color=df["HDI Value"], colorscale="Viridis", opacity=0.75,
                    line=dict(width=0.5, color="white")),
        text=hover(df), hoverinfo="text"))
    fig.update_layout(title="Income vs Human Development (marker size = life expectancy)",
                      xaxis=dict(title="GNI per capita (log scale)", type="log"),
                      yaxis_title="HDI value",
                      margin=dict(l=60, r=20, t=50, b=50))
    figs.append(fig)

    # 3 — top/bottom 15
    ranked = df.sort_values("HDI Value")
    ends = pd.concat([ranked.head(15), ranked.tail(15)])
    fig = go.Figure(go.Bar(
        x=ends["HDI Value"], y=ends["Country"], orientation="h",
        marker=dict(color=ends["HDI Value"], colorscale="Viridis"),
        text=ends["HDI Value"].round(3), textposition="outside"))
    fig.update_layout(title="Top & bottom 15 countries by HDI",
                      xaxis_title="HDI value", height=700,
                      margin=dict(l=160, r=40, t=50, b=40))
    figs.append(fig)

    # 4 — education gap
    edu = df.copy()
    edu["gap"] = edu["Expected years of schooling"] - edu["Mean years of schooling"]
    top_gap = edu.nlargest(20, "gap").sort_values("gap")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=top_gap["Mean years of schooling"], y=top_gap["Country"],
                         orientation="h", name="Mean years (attained)"))
    fig.add_trace(go.Bar(x=top_gap["gap"], y=top_gap["Country"], orientation="h",
                         name="Gap to expected years",
                         hovertext=("expected: " +
                                    top_gap["Expected years of schooling"].round(1).astype(str))))
    fig.update_layout(barmode="stack", height=650,
                      title="Largest education gaps: expected vs attained schooling",
                      xaxis_title="Years of schooling",
                      margin=dict(l=160, r=40, t=50, b=40))
    figs.append(fig)
    return figs


CSS = """
 body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
        background: #f4f6f9; color: #1c2733; }
 header { padding: 26px 34px 6px; }
 h1 { margin: 0 0 4px; font-size: 25px; }
 .sub { color: #5c6b7a; font-size: 14px; max-width: 920px; }
 .kpis { display: flex; gap: 14px; padding: 16px 34px 0; flex-wrap: wrap; }
 .kpi { background: white; border-radius: 10px; padding: 12px 20px;
        box-shadow: 0 1px 4px rgba(20,40,80,.08); min-width: 150px; }
 .kpi .v { font-size: 22px; font-weight: 700; color: #0b5fff; }
 .kpi .l { font-size: 12px; color: #5c6b7a; }
 .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(470px, 1fr));
         gap: 18px; padding: 18px 34px 36px; }
 .card { background: white; border-radius: 10px; padding: 6px;
         box-shadow: 0 1px 4px rgba(20,40,80,.08); }
 .wide { grid-column: 1 / -1; }
 footer { padding: 0 34px 26px; color: #8595a5; font-size: 13px; }
"""


def render(figs: list[go.Figure], df: pd.DataFrame) -> str:
    top = df.loc[df["HDI Value"].idxmax()]
    bottom = df.loc[df["HDI Value"].idxmin()]
    gap = df["Expected years of schooling"] - df["Mean years of schooling"]
    kpis = [
        (f"{len(df)}", "countries covered"),
        (f"{df['HDI Value'].median():.3f}", "median HDI"),
        (f"{top['Country']} ({top['HDI Value']:.3f})", "highest HDI"),
        (f"{bottom['Country']} ({bottom['HDI Value']:.3f})", "lowest HDI"),
        (f"{gap.mean():.1f} yrs", "avg expected-vs-attained schooling gap"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>'
        for v, l in kpis)
    charts = []
    for i, fig in enumerate(figs):
        cls = "card wide" if i == 0 else "card"
        inner = fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False,
                            div_id=f"chart-{i}", default_height="520px" if i == 0 else "460px")
        charts.append(f'<div class="{cls}">{inner}</div>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Global HDI Dashboard</title><style>{CSS}</style></head><body>
<header><h1>Global Human Development Dashboard</h1>
<div class="sub">UNDP Human Development Report 2021&ndash;22 &middot; interactive
(hover, zoom, pan). The choropleth maps the composite index; the scatter shows the
income-development relationship the HDI was designed to look beyond.</div>
</header>
<div class="kpis">{kpi_html}</div>
<div class="grid">{''.join(charts)}</div>
<footer>Built with Plotly from <code>data/HDR21-22_HDI.csv</code> &middot;
regenerate with <code>python src/build_dashboard.py</code></footer>
</body></html>"""


def main() -> None:
    df = load()
    html = render(build_figures(df), df)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard: {len(df)} countries, 4 charts -> {OUT} "
          f"({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
