"""Tests for the HDI dashboard build."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_dashboard import OUT, build_figures, hover, load, render  # noqa: E402


@pytest.fixture(scope="module")
def df():
    return load()


def test_load_cleans_numerics(df):
    assert len(df) > 180
    assert df["HDI Value"].between(0, 1).all()
    assert df["Country"].is_unique
    # thousands separators must be handled, not silently NaN-ed
    assert df["GNI per Capita"].notna().mean() > 0.95
    assert df["GNI per Capita"].max() > 50000


def test_hover_handles_missing_gni(df):
    sample = df.head(3).copy()
    sample.loc[sample.index[0], "GNI per Capita"] = float("nan")
    text = hover(sample)
    assert "n/a" in text.iloc[0]
    assert "$" in text.iloc[1]


def test_four_figures_built(df):
    figs = build_figures(df)
    assert len(figs) == 4


def test_render_is_selfcontained_html(df):
    html = render(build_figures(df), df)
    assert html.startswith("<!DOCTYPE html>")
    assert html.count('class="card') == 4
    assert "plotly" in html.lower()
    # CDN script included exactly once (charts 2-4 reuse it)
    assert html.count("cdn.plot.ly") == 1


def test_build_writes_output(df, tmp_path, monkeypatch):
    import build_dashboard
    out = tmp_path / "index.html"
    monkeypatch.setattr(build_dashboard, "OUT", out)
    build_dashboard.main()
    assert out.exists() and out.stat().st_size > 50_000
