"""Unit tests for the pure valuation math (no network)."""
import math

from src import metrics


def approx(a, b, tol=1e-6):
    return a is not None and b is not None and math.isclose(a, b, rel_tol=tol)


def test_market_cap_and_ev():
    mc = metrics.market_cap(close=100.0, shares=1_000_000)
    assert approx(mc, 100_000_000)
    ev = metrics.enterprise_value(mc, total_debt=20_000_000, cash=5_000_000)
    assert approx(ev, 115_000_000)


def test_ev_handles_missing_debt_cash():
    ev = metrics.enterprise_value(100.0, None, None)
    assert approx(ev, 100.0)


def test_trailing_and_forward_pe():
    assert approx(metrics.trailing_pe(150.0, 6.0), 25.0)
    assert approx(metrics.forward_pe(150.0, 7.5), 20.0)


def test_pe_zero_eps_returns_none():
    assert metrics.trailing_pe(150.0, 0.0) is None
    assert metrics.forward_pe(150.0, None) is None


def test_peg():
    # forward P/E 20, growth 10% -> PEG 2.0
    assert approx(metrics.peg_ratio(20.0, 0.10), 2.0)


def test_peg_negative_growth_is_none():
    assert metrics.peg_ratio(20.0, -0.05) is None
    assert metrics.peg_ratio(None, 0.10) is None


def test_price_to_fcf():
    assert approx(metrics.price_to_fcf(100_000_000, 5_000_000), 20.0)
    assert metrics.price_to_fcf(100_000_000, 0.0) is None


def test_ev_to_ebitda():
    assert approx(metrics.ev_to_ebitda(120_000_000, 10_000_000), 12.0)


def test_revenue_growth():
    assert approx(metrics.revenue_growth(115.0, 100.0), 0.15)
    assert metrics.revenue_growth(115.0, 0.0) is None


def test_growth_vs_multiple():
    # 20% growth at EV/EBITDA of 10 -> 2.0
    assert approx(metrics.growth_vs_multiple(0.20, 10.0), 2.0)


def test_fcf_margin():
    assert approx(metrics.fcf_margin(20.0, 100.0), 0.20)
    assert metrics.fcf_margin(20.0, None) is None


def test_compute_all_end_to_end():
    price = {"close": 150.0}
    fundamentals = {
        "shares_outstanding": 1_000_000,
        "total_debt": 20_000_000,
        "cash": 5_000_000,
        "eps_ttm": 6.0,
        "fcf_ttm": 7_500_000,
        "revenue_ttm": 115_000_000,
        "prior_revenue_ttm": 100_000_000,
    }
    est = {
        "forward_eps": 7.5,
        "earnings_growth": 0.10,
        "forward_ebitda": 12_500_000,
        "ebitda_is_forward": True,
    }
    m = metrics.compute_all(price, fundamentals, est)
    assert approx(m["market_cap"], 150_000_000)
    assert approx(m["enterprise_value"], 165_000_000)  # 150M + 20M - 5M
    assert approx(m["trailing_pe"], 25.0)
    assert approx(m["forward_pe"], 20.0)
    assert approx(m["peg_ratio"], 2.0)
    assert approx(m["price_to_fcf"], 20.0)            # 150M / 7.5M
    assert approx(m["ev_to_ebitda_forward"], 13.2)    # 165M / 12.5M
    assert approx(m["revenue_growth"], 0.15)
    assert approx(m["growth_vs_ev_ebitda"], 15.0 / 13.2)
    assert approx(m["fcf_margin"], 7_500_000 / 115_000_000)
