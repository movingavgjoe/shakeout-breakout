"""Entry point: get_metrics(ticker, date) and a small CLI.

Usage:
    python main.py AAPL 2026-05-01
    python main.py MSFT            # defaults to today

Data sources (all free):
    prices       -> Stooq direct CSV
    fundamentals -> SEC EDGAR companyfacts (8 req/s, point-in-time)
    estimates    -> yfinance (current consensus; proxy for past dates)
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from src import edgar, estimates, metrics, prices


def get_metrics(ticker: str, on=None) -> dict:
    """Compute the valuation metrics for `ticker` as of date `on` (default today)."""
    on_d = (
        date.today() if on is None
        else (on if isinstance(on, date) else datetime.strptime(on, "%Y-%m-%d").date())
    )

    price = prices.price_on(ticker, on_d)
    fundamentals = edgar.get_fundamentals(ticker, on_d)
    est = estimates.get_estimates(ticker, fallback_ebitda=fundamentals.get("ebitda_ttm"))
    computed = metrics.compute_all(price, fundamentals, est)

    return {
        "ticker": ticker.upper(),
        "requested_date": on_d.isoformat(),
        "price": price,
        "fundamentals": fundamentals,
        "estimates": est,
        "metrics": computed,
    }


def _fmt(v, pct=False):
    if v is None:
        return "n/a"
    if pct:
        return f"{v * 100:.1f}%"
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    return f"{v:.2f}"


def _print_report(r: dict) -> None:
    m = r["metrics"]
    p = r["price"]
    print(f"\n=== {r['ticker']}  (as of {r['requested_date']}) ===")
    print(f"Price on {p['date']}: close {p['close']:.2f}  "
          f"(O {p['open']:.2f} H {p['high']:.2f} L {p['low']:.2f}  vol {_fmt(p['volume'])})")
    print(f"  Market cap            {_fmt(m['market_cap'])}")
    print(f"  Enterprise value      {_fmt(m['enterprise_value'])}")
    print(f"  Trailing P/E          {_fmt(m['trailing_pe'])}")
    print(f"  Forward P/E           {_fmt(m['forward_pe'])}")
    print(f"  PEG ratio             {_fmt(m['peg_ratio'])}")
    print(f"  Price / FCF           {_fmt(m['price_to_fcf'])}")
    fwd_note = "" if m["ebitda_is_forward"] else "  (trailing EBITDA proxy)"
    print(f"  EV / EBITDA (fwd)     {_fmt(m['ev_to_ebitda_forward'])}{fwd_note}")
    print(f"  Revenue growth (YoY)  {_fmt(m['revenue_growth'], pct=True)}")
    print(f"  Growth / EV-EBITDA    {_fmt(m['growth_vs_ev_ebitda'])}")
    print(f"  FCF margin            {_fmt(m['fcf_margin'], pct=True)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Free-data valuation metrics for a ticker/date.")
    ap.add_argument("ticker")
    ap.add_argument("date", nargs="?", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--json", action="store_true", help="print raw JSON")
    args = ap.parse_args()

    result = get_metrics(args.ticker, args.date)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_report(result)


if __name__ == "__main__":
    main()
