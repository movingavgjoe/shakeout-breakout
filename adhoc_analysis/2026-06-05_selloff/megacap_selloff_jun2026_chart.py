"""Render the June 3 -> June 5, 2026 mega-cap sell-off chart for the blog.

Reads megacap_selloff_jun2026.csv (produced by megacap_selloff_jun2026.py) and
draws a dual-axis combo chart:
  * bars  = two-day price change (Wed close -> Fri close), red = down, green = up
  * markers = trailing P/E that existed on Wednesday (right axis, labeled)

Outputs a high-resolution PNG suitable for a blog hero image and thumbnail.
This is a standalone visual script; it does not modify the data script.

Usage:
    python make_selloff_chart.py
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
CSV = HERE / "megacap_selloff_jun2026.csv"
OUT_PNG = HERE / "megacap_selloff_jun2026_chart.png"

# --- palette -----------------------------------------------------------------
DOWN = "#E23B3B"     # red bars (price fell)
UP = "#2EA66B"       # green bars (price rose)
PE_COLOR = "#1F2D5A" # deep navy for the P/E markers
INK = "#1A1A1A"
MUTED = "#6B7280"


def load() -> pd.DataFrame:
    df = pd.read_csv(CSV)
    if "error" in df.columns:
        df = df[df["error"].isna() | (df["error"].astype(str).str.strip() == "")]
    df = df.dropna(subset=["pct_change", "trailing_pe_early"])
    return df.sort_values("pct_change").reset_index(drop=True)  # biggest drop first


def make_chart(df: pd.DataFrame) -> Path:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.edgecolor": "#D1D5DB",
        "axes.linewidth": 1.0,
    })

    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = range(len(df))
    tickers = df["ticker"].tolist()
    pct = df["pct_change"].tolist()
    pe = df["trailing_pe_early"].tolist()

    # --- bars: two-day % change ---
    colors = [UP if v >= 0 else DOWN for v in pct]
    bars = ax.bar(x, pct, width=0.62, color=colors, zorder=3)

    ax.axhline(0, color="#6B7280", linewidth=1.4, zorder=2)
    ax.set_ylabel("Two-day price change  (Wed → Fri)", fontsize=12,
                  color=INK, fontweight="bold")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    # Symmetric range about zero so the % zero sits on the vertical center line
    # (and lines up with the P/E zero below). Bars hang beneath the line; the
    # P/E lollipops rise above it, so the two series no longer overlap.
    pbound = max(abs(min(pct)), abs(max(pct))) * 1.15
    ax.set_ylim(-pbound, pbound)
    # Only label the % range the data actually occupies (the upper half is
    # reserved for the P/E lollipops, which read off the right axis).
    lo = int(math.floor(min(pct) / 5.0) * 5)
    hi = int(math.ceil(max(pct) / 5.0) * 5)
    ax.set_yticks(list(range(lo, hi + 1, 5)))
    ax.tick_params(axis="y", labelsize=10, colors=MUTED)
    ax.set_xticks(list(x))
    ax.set_xticklabels(tickers, fontsize=12, fontweight="bold", color=INK)
    ax.grid(axis="y", color="#EEF0F3", linewidth=1, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # bar value labels: drops sit just below the bar (red); risers sit just
    # above the bar (green). For risers the paired P/E label is moved *below*
    # its dot (see below) so the two don't collide in the shared upper zone.
    for xi, v in zip(x, pct):
        if v >= 0:
            ax.annotate(f"{v:+.1f}%", (xi, v), ha="center", va="bottom",
                        xytext=(0, 4), textcoords="offset points",
                        fontsize=10, fontweight="bold", color=UP, zorder=7)
        else:
            ax.annotate(f"{v:+.1f}%", (xi, v), ha="center", va="top",
                        xytext=(0, -4), textcoords="offset points",
                        fontsize=10, fontweight="bold", color=DOWN, zorder=4)

    # --- right axis: Wednesday trailing P/E as lollipops ---
    ax2 = ax.twinx()
    # Symmetric about zero too, so the P/E zero lines up with the % zero on the
    # shared center line. P/E values are all positive -> lollipops sit above it.
    pe_bound = max(pe) * 1.18
    ax2.set_ylim(-pe_bound, pe_bound)
    # stems rise from the center line to each dot
    ax2.vlines(x, 0, pe, color=PE_COLOR, linewidth=2.2, alpha=0.45, zorder=4)
    ax2.plot(x, pe, linestyle="none", marker="o", markersize=13,
             markerfacecolor=PE_COLOR, markeredgecolor="white",
             markeredgewidth=1.7, zorder=6)
    ax2.set_ylabel("Trailing P/E on Wednesday", fontsize=12,
                   color=PE_COLOR, fontweight="bold")
    # only label the populated (positive) half of the P/E axis
    ax2.set_yticks(list(range(0, int(pe_bound) + 1, 100)))
    ax2.tick_params(axis="y", labelsize=10, colors=PE_COLOR)
    for s in ("top", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["right"].set_color("#D1D5DB")

    # P/E value labels: above each marker, except for risers (where the bar sits
    # in the same upper zone) the label goes below the marker to avoid a clash.
    for xi, v, pv in zip(x, pe, pct):
        below = pv >= 0
        ax2.annotate(f"{v:.0f}×", (xi, v), textcoords="offset points",
                     xytext=(0, -14 if below else 12),
                     ha="center", va="top" if below else "bottom",
                     fontsize=9.5, fontweight="bold", color=PE_COLOR, zorder=8)

    # --- titles + legend ---
    ax.set_title("Mega-Cap Tech Sell-Off: June 3 → June 5, 2026",
                 fontsize=18, fontweight="bold", color=INK, pad=34, loc="left")
    ax.annotate("Two-day price drop vs. the P/E multiple each stock carried going in",
                xy=(0, 1.045), xycoords="axes fraction", fontsize=11.5,
                color=MUTED, ha="left")

    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend = [
        Patch(facecolor=DOWN, label="Price fell"),
        Patch(facecolor=UP, label="Price rose"),
        Line2D([0], [0], marker="o", linestyle="none", markersize=10,
               markerfacecolor=PE_COLOR, markeredgecolor="white",
               label="Trailing P/E (Wed)"),
    ]
    ax.legend(handles=legend, loc="lower left", frameon=False, fontsize=10,
              ncol=3, bbox_to_anchor=(0, -0.16))

    fig.text(0.99, 0.01, "Source: SEC EDGAR (fundamentals) + Yahoo Finance (prices)",
             ha="right", va="bottom", fontsize=8, color=MUTED)

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(OUT_PNG, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return OUT_PNG


def main() -> None:
    df = load()
    out = make_chart(df)
    print(f"Saved chart: {out}  ({len(df)} tickers)")


if __name__ == "__main__":
    main()
