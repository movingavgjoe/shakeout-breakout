"""Pure valuation-metric math. No I/O — easy to unit test.

Every function returns None when an input is missing or a denominator is ~0,
so downstream code can render "n/a" instead of crashing.
"""
from __future__ import annotations

from typing import Optional

Number = Optional[float]


def _safe_div(a: Number, b: Number) -> Number:
    if a is None or b is None or abs(b) < 1e-12:
        return None
    return a / b


def market_cap(close: Number, shares: Number) -> Number:
    if close is None or shares is None:
        return None
    return close * shares


def enterprise_value(mktcap: Number, total_debt: Number, cash: Number) -> Number:
    if mktcap is None:
        return None
    return mktcap + (total_debt or 0.0) - (cash or 0.0)


def trailing_pe(close: Number, eps_ttm: Number) -> Number:
    return _safe_div(close, eps_ttm)


def forward_pe(close: Number, forward_eps: Number) -> Number:
    return _safe_div(close, forward_eps)


def peg_ratio(fwd_pe: Number, earnings_growth_fraction: Number) -> Number:
    """PEG = forward P/E divided by expected EPS growth in *percent points*.

    earnings_growth_fraction is a fraction (0.12 == 12%). Negative growth ->
    PEG is not meaningful, so we return None.
    """
    if fwd_pe is None or earnings_growth_fraction is None:
        return None
    growth_pct = earnings_growth_fraction * 100.0
    if growth_pct <= 0:
        return None
    return fwd_pe / growth_pct


def price_to_fcf(mktcap: Number, fcf_ttm: Number) -> Number:
    return _safe_div(mktcap, fcf_ttm)


def ev_to_ebitda(ev: Number, ebitda: Number) -> Number:
    return _safe_div(ev, ebitda)


def revenue_growth(revenue_ttm: Number, prior_revenue_ttm: Number) -> Number:
    """YoY revenue growth as a fraction (0.15 == 15%)."""
    if revenue_ttm is None or prior_revenue_ttm is None or abs(prior_revenue_ttm) < 1e-12:
        return None
    return (revenue_ttm - prior_revenue_ttm) / prior_revenue_ttm


def growth_vs_multiple(rev_growth_fraction: Number, multiple: Number) -> Number:
    """Revenue growth (in percent points) per unit of valuation multiple.

    Higher = more growth per turn of the multiple (cheaper for the growth).
    e.g. 20% growth at EV/EBITDA 10 -> 2.0.
    """
    if rev_growth_fraction is None or multiple is None or abs(multiple) < 1e-12:
        return None
    return (rev_growth_fraction * 100.0) / multiple


def fcf_margin(fcf_ttm: Number, revenue_ttm: Number) -> Number:
    return _safe_div(fcf_ttm, revenue_ttm)


def compute_all(price: dict, fundamentals: dict, estimates: dict) -> dict:
    """Assemble all seven metrics from the three data dicts."""
    close = price.get("close")
    shares = fundamentals.get("shares_outstanding")
    mcap = market_cap(close, shares)
    ev = enterprise_value(mcap, fundamentals.get("total_debt"), fundamentals.get("cash"))

    fwd_pe = forward_pe(close, estimates.get("forward_eps"))
    rev_growth = revenue_growth(
        fundamentals.get("revenue_ttm"), fundamentals.get("prior_revenue_ttm")
    )
    ev_ebitda = ev_to_ebitda(ev, estimates.get("forward_ebitda"))

    return {
        "market_cap": mcap,
        "enterprise_value": ev,
        "trailing_pe": trailing_pe(close, fundamentals.get("eps_ttm")),
        "forward_pe": fwd_pe,
        "peg_ratio": peg_ratio(fwd_pe, estimates.get("earnings_growth")),
        "price_to_fcf": price_to_fcf(mcap, fundamentals.get("fcf_ttm")),
        "ev_to_ebitda_forward": ev_ebitda,
        "revenue_growth": rev_growth,
        "growth_vs_ev_ebitda": growth_vs_multiple(rev_growth, ev_ebitda),
        "fcf_margin": fcf_margin(
            fundamentals.get("fcf_ttm"), fundamentals.get("revenue_ttm")
        ),
        "ebitda_is_forward": estimates.get("ebitda_is_forward", False),
    }
