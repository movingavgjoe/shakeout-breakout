"""Mega-cap selloff snapshot: Wed Jun 3, 2026 vs Fri Jun 5, 2026.

For each ticker, computes:
  * % change in closing price (Jun 3 -> Jun 5)
  * Trailing P/E, Forward P/E, and PEG on each date

Data comes from the sibling `valuation_metrics` package (Stooq prices,
SEC EDGAR fundamentals, yfinance forward consensus).

NOTE on interpreting the two-day P/E change: trailing EPS (EDGAR) and forward
consensus (yfinance) do not move over a two-day window with no new filing, so
the day-to-day differences in P/E and PEG here are driven almost entirely by the
price move. That's the point of the comparison for the article.

Setup before running (set your own contact email; never hardcode it):
    export EDGAR_USER_AGENT="shakeout-breakout you@example.com"

Usage:
    python megacap_selloff_jun2026.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

# --- make the valuation_metrics package importable ---------------------------
# This script lives at: shakeout-breakout/adhoc_analysis/2026-06-05_selloff/<file>
# so the repo root is three levels up.
VM_DIR = Path(__file__).resolve().parents[2] / "valuation_metrics"
sys.path.insert(0, str(VM_DIR))

from src import edgar, estimates, metrics, prices  # noqa: E402

TICKERS = ["NVDA", "MSFT", "AVGO", "MU", "META", "GOOGL", "AMZN", "AAPL", "TSLA"]
DATE_EARLY = "2026-06-03"  # Wednesday
DATE_LATE = "2026-06-05"   # Friday
OUT_CSV = Path(__file__).resolve().parent / "megacap_selloff_jun2026.csv"


def snapshot(ticker: str, on: str) -> dict:
    """Return close price + key ratios for one ticker on one date."""
    price = prices.price_on(ticker, on)
    fund = edgar.get_fundamentals(ticker, on)
    est = estimates.get_estimates(ticker, fallback_ebitda=fund.get("ebitda_ttm"))
    m = metrics.compute_all(price, fund, est)
    return {
        "close": price["close"],
        "trailing_pe": m["trailing_pe"],
        "forward_pe": m["forward_pe"],
        "peg": m["peg_ratio"],
    }


def pct_change(old: float, new: float):
    if old is None or new is None or old == 0:
        return None
    return (new - old) / old * 100.0


def analyze(tickers=TICKERS, d_early=DATE_EARLY, d_late=DATE_LATE) -> list[dict]:
    rows = []
    for t in tickers:
        try:
            early = snapshot(t, d_early)
            late = snapshot(t, d_late)
            rows.append({
                "ticker": t,
                "close_early": early["close"],
                "close_late": late["close"],
                "pct_change": pct_change(early["close"], late["close"]),
                "trailing_pe_early": early["trailing_pe"],
                "trailing_pe_late": late["trailing_pe"],
                "forward_pe_early": early["forward_pe"],
                "forward_pe_late": late["forward_pe"],
                "peg_early": early["peg"],
                "peg_late": late["peg"],
            })
        except Exception as e:  # keep going if one ticker fails
            print(f"  ! {t}: {e}", file=sys.stderr)
            rows.append({"ticker": t, "error": str(e)})
    return rows


# --- formatting --------------------------------------------------------------
def _n(v, dp=2, suffix=""):
    return "n/a" if v is None else f"{v:.{dp}f}{suffix}"


def print_table(rows: list[dict], d_early: str, d_late: str) -> None:
    print(f"\nMega-cap selloff: {d_early} (Wed) -> {d_late} (Fri)\n")
    hdr = (f"{'Ticker':<7}{'Close ' + d_early[5:]:>12}{'Close ' + d_late[5:]:>12}"
           f"{'% chg':>9}{'PE(t) ' + d_early[5:]:>13}{'PE(t) ' + d_late[5:]:>13}"
           f"{'PEG ' + d_early[5:]:>12}{'PEG ' + d_late[5:]:>12}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if "error" in r:
            print(f"{r['ticker']:<7}  ERROR: {r['error']}")
            continue
        print(f"{r['ticker']:<7}"
              f"{_n(r['close_early']):>12}{_n(r['close_late']):>12}"
              f"{_n(r['pct_change'], 2, '%'):>9}"
              f"{_n(r['trailing_pe_early']):>13}{_n(r['trailing_pe_late']):>13}"
              f"{_n(r['peg_early']):>12}{_n(r['peg_late']):>12}")


def write_csv(rows: list[dict], path: Path) -> None:
    fields = ["ticker", "close_early", "close_late", "pct_change",
              "trailing_pe_early", "trailing_pe_late",
              "forward_pe_early", "forward_pe_late",
              "peg_early", "peg_late", "error"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def main() -> None:
    rows = analyze()
    print_table(rows, DATE_EARLY, DATE_LATE)
    write_csv(rows, OUT_CSV)
    print(f"\nSaved: {OUT_CSV}")
    print("Note: 2-day P/E & PEG changes are price-driven (fundamentals/consensus "
          "unchanged over the window).")


if __name__ == "__main__":
    main()
