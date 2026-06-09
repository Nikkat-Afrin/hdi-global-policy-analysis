"""
Human Development Index — policy insights & component analysis (HDR 2021-22).

Adds analytical depth to the EDA notebook:
  * classify the 195 countries into UNDP development tiers,
  * regress HDI on its three pillars (health / education / income) to quantify
    each pillar's contribution,
  * surface countries that "punch above/below" their income (GNI-rank vs HDI-rank).

Writes reports/hdi_insights.md and reports/figures/*.png.
Run from repo root:  python src/hdi_insights.py
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")


def main():
    df = pd.read_csv(ROOT / "data" / "HDR21-22_HDI.csv")
    for c in ["HDI Value", "Life expectancy at birth", "Expected years of schooling",
              "Mean years of schooling", "GNI per Capita", "GNI per capita rank minus HDI rank"]:
        df[c] = num(df[c])
    df = df.dropna(subset=["HDI Value"]).copy()

    # UNDP development tiers
    df["Tier"] = pd.cut(df["HDI Value"], [0, 0.55, 0.70, 0.80, 1.0],
                        labels=["Low", "Medium", "High", "Very High"])
    tier_counts = df["Tier"].value_counts().reindex(["Very High", "High", "Medium", "Low"])

    # Component-contribution regression (standardized pillars -> comparable betas)
    pillars = ["Life expectancy at birth", "Expected years of schooling",
               "Mean years of schooling", "GNI per Capita"]
    d = df.dropna(subset=pillars + ["HDI Value"])
    Xs = StandardScaler().fit_transform(d[pillars])
    reg = LinearRegression().fit(Xs, d["HDI Value"])
    contrib = pd.Series(reg.coef_, index=pillars).sort_values(ascending=False)
    r2 = reg.score(Xs, d["HDI Value"])

    # Over/under-performers vs income
    over = df.dropna(subset=["GNI per capita rank minus HDI rank"]).sort_values(
        "GNI per capita rank minus HDI rank", ascending=False)

    print("Tiers:", tier_counts.to_dict())
    print(f"\nStandardized pillar contributions to HDI (R^2={r2:.3f}):")
    print(contrib.round(4).to_string())
    print("\nTop 5 'punch above income' (GNI rank - HDI rank):")
    print(over[["Country", "GNI per capita rank minus HDI rank"]].head(5).to_string(index=False))

    # --- figures ---
    plt.figure(figsize=(7, 5)); tier_counts.plot.bar(color="#1565c0")
    plt.title("Countries by UNDP development tier (HDR 2021-22)")
    plt.ylabel("# countries"); plt.tight_layout()
    plt.savefig(FIG / "hdi_tiers.png", dpi=120); plt.close()

    plt.figure(figsize=(7, 6))
    colors = {"Very High": "#1b5e20", "High": "#9e9d24", "Medium": "#ef6c00", "Low": "#b71c1c"}
    for t, g in df.dropna(subset=["GNI per Capita"]).groupby("Tier"):
        plt.scatter(g["GNI per Capita"], g["HDI Value"], s=18, alpha=0.7,
                    label=t, color=colors.get(str(t), "gray"))
    plt.xscale("log"); plt.xlabel("GNI per capita (log, 2017 PPP $)"); plt.ylabel("HDI value")
    plt.title("HDI vs income — diminishing returns above ~$30k"); plt.legend()
    plt.tight_layout(); plt.savefig(FIG / "hdi_vs_gni.png", dpi=120); plt.close()

    plt.figure(figsize=(8, 6))
    contrib.sort_values().plot.barh(color="#00897b")
    plt.title(f"Standardized contribution of each pillar to HDI (R²={r2:.2f})")
    plt.xlabel("Std. regression coefficient"); plt.tight_layout()
    plt.savefig(FIG / "hdi_pillar_contributions.png", dpi=120); plt.close()

    (ROOT / "reports").mkdir(exist_ok=True)
    lines = ["# HDI policy insights", "",
             f"- Countries analyzed: **{len(df)}**",
             f"- Tier distribution: " + ", ".join(f"{k}: {int(v)}" for k, v in tier_counts.items()),
             f"- Component regression R²: **{r2:.3f}**", "",
             "## Standardized pillar contributions to HDI", "",
             "| Pillar | Std. coefficient |", "|---|---|"]
    for k, v in contrib.items():
        lines.append(f"| {k} | {v:.4f} |")
    lines += ["", "## Top 'punch above their income' countries (GNI rank − HDI rank)", ""]
    for _, r in over.head(8).iterrows():
        lines.append(f"- {r['Country']}: +{int(r['GNI per capita rank minus HDI rank'])}")
    (ROOT / "reports" / "hdi_insights.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWritten to {ROOT/'reports'}")


if __name__ == "__main__":
    main()
