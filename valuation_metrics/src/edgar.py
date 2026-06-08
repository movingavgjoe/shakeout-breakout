"""Trailing fundamentals from SEC EDGAR companyfacts (free, no key).

Point-in-time aware: only facts *filed on or before* the as-of date are used,
so a metric computed "as of" a past date does not peek at later restatements.

Self-throttled to 8 req/s (SEC's hard ceiling is 10 req/s per IP).

Caveats (documented intentionally):
  * EBITDA is not a reported line item; we approximate it as
    OperatingIncome + D&A, falling back to NetIncome + Interest + Taxes + D&A.
  * TTM is built by summing the 4 most recent ~quarterly periods; if clean
    quarters aren't available we fall back to the latest annual (10-K) value.
  * Total debt = long-term debt (+ current portion) when those tags exist.
"""
from __future__ import annotations

import time
from datetime import date, datetime
from typing import Optional

import pandas as pd
import requests

from . import cache, config

# ---- candidate XBRL tags (namespace, tag), tried in order --------------------
TAGS = {
    "revenue": [
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "Revenues"),
        ("us-gaap", "SalesRevenueNet"),
    ],
    "net_income": [("us-gaap", "NetIncomeLoss")],
    "eps_diluted": [("us-gaap", "EarningsPerShareDiluted")],
    "operating_income": [("us-gaap", "OperatingIncomeLoss")],
    "dep_amort": [
        ("us-gaap", "DepreciationDepletionAndAmortization"),
        ("us-gaap", "DepreciationAmortizationAndAccretionNet"),
        ("us-gaap", "DepreciationAndAmortization"),
    ],
    "interest_expense": [("us-gaap", "InterestExpense")],
    "income_tax": [("us-gaap", "IncomeTaxExpenseBenefit")],
    "operating_cash_flow": [
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
    ],
    "capex": [
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("us-gaap", "PaymentsToAcquireProductiveAssets"),
    ],
    "cash": [("us-gaap", "CashAndCashEquivalentsAtCarryingValue")],
    "lt_debt": [
        ("us-gaap", "LongTermDebtNoncurrent"),
        ("us-gaap", "LongTermDebt"),
    ],
    "current_debt": [
        ("us-gaap", "LongTermDebtCurrent"),
        ("us-gaap", "DebtCurrent"),
    ],
    "shares": [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
    ],
}

# --- throttling --------------------------------------------------------------
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    wait = config.EDGAR_MIN_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def _get_json(url: str) -> dict:
    if not config.EDGAR_USER_AGENT:
        raise RuntimeError(
            "SEC EDGAR requires a contact email in the User-Agent. "
            "Set the EDGAR_USER_AGENT environment variable, e.g.:\n"
            '  export EDGAR_USER_AGENT="shakeout-breakout you@example.com"'
        )
    _throttle()
    headers = {"User-Agent": config.EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    resp = requests.get(url, headers=headers, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# --- ticker -> CIK -----------------------------------------------------------
def get_cik(ticker: str) -> int:
    """Resolve a ticker to its zero-padded-capable CIK integer."""
    name = "edgar_company_tickers"
    df = cache.load(name, max_age_days=30)
    if df is None:
        data = _get_json(config.EDGAR_TICKERS_URL)
        rows = [
            {"ticker": v["ticker"].upper(), "cik": int(v["cik_str"]), "title": v["title"]}
            for v in data.values()
        ]
        df = pd.DataFrame(rows)
        cache.save(name, df)
    match = df[df["ticker"] == ticker.strip().upper()]
    if match.empty:
        raise ValueError(f"Ticker {ticker!r} not found in SEC ticker map.")
    return int(match.iloc[0]["cik"])


# --- fact extraction ---------------------------------------------------------
def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _collect(facts: dict, candidates, as_of: date):
    """Return (list_of_facts, unit) for the first candidate tag that has data.

    Each fact dict is normalized with parsed dates and only includes records
    filed on or before `as_of`.
    """
    for ns, tag in candidates:
        node = facts.get("facts", {}).get(ns, {}).get(tag)
        if not node:
            continue
        for unit, items in node.get("units", {}).items():
            out = []
            for f in items:
                try:
                    filed = _parse(f["filed"])
                    if filed > as_of:
                        continue
                    end = _parse(f["end"])
                    start = _parse(f["start"]) if f.get("start") else None
                    out.append(
                        {"val": float(f["val"]), "end": end, "start": start,
                         "filed": filed, "form": f.get("form", "")}
                    )
                except (KeyError, ValueError, TypeError):
                    continue
            if out:
                return out, unit
    return [], None


def _dedupe_by_end(items):
    """Keep, for each period end, the record with the latest filing date."""
    best = {}
    for f in items:
        key = (f["start"], f["end"])
        if key not in best or f["filed"] > best[key]["filed"]:
            best[key] = f
    return list(best.values())


def _ttm_flow(items, as_of: date) -> Optional[float]:
    """Trailing-twelve-month sum for a flow concept, as of `as_of`."""
    elig = [f for f in items if f["start"] and f["end"] <= as_of]
    elig = _dedupe_by_end(elig)
    for f in elig:
        f["dur"] = (f["end"] - f["start"]).days

    quarters = sorted(
        [f for f in elig if 80 <= f["dur"] <= 100],
        key=lambda f: f["end"], reverse=True,
    )
    if len(quarters) >= 4:
        top4 = quarters[:4]
        span = (top4[0]["end"] - top4[3]["start"]).days
        if 330 <= span <= 400:  # contiguous ~1 year
            return sum(f["val"] for f in top4)

    annuals = sorted(
        [f for f in elig if 350 <= f["dur"] <= 380],
        key=lambda f: f["end"], reverse=True,
    )
    if annuals:
        return annuals[0]["val"]
    return None


def _latest_point(items, as_of: date) -> Optional[float]:
    """Most recent instant (balance-sheet) value as of `as_of`."""
    elig = [f for f in items if f["end"] <= as_of]
    if not elig:
        return None
    elig.sort(key=lambda f: (f["end"], f["filed"]), reverse=True)
    return elig[0]["val"]


def _ttm_per_share(items, as_of: date) -> Optional[float]:
    """TTM for a per-share flow (EPS): sum of 4 trailing quarters, else annual."""
    return _ttm_flow(items, as_of)


# --- public API --------------------------------------------------------------
def get_fundamentals(ticker: str, as_of) -> dict:
    """Return TTM/point fundamentals for `ticker` as of date `as_of`.

    Keys: revenue_ttm, prior_revenue_ttm, net_income_ttm, eps_ttm, ebitda_ttm,
          operating_cash_flow_ttm, capex_ttm, fcf_ttm, cash, total_debt,
          shares_outstanding.
    """
    as_of_d = as_of if isinstance(as_of, date) else _parse(str(as_of))
    name = f"fundamentals_{ticker.upper()}_{as_of_d:%Y%m%d}"
    cached = cache.load(name, config.FUNDAMENTALS_CACHE_MAX_AGE_DAYS)
    if cached is not None and not cached.empty:
        return cached.iloc[0].to_dict()

    cik = get_cik(ticker)
    facts = _get_json(config.EDGAR_COMPANYFACTS_URL.format(cik=cik))

    def flow(key):
        items, _ = _collect(facts, TAGS[key], as_of_d)
        return _ttm_flow(items, as_of_d)

    def point(key):
        items, _ = _collect(facts, TAGS[key], as_of_d)
        return _latest_point(items, as_of_d)

    revenue_ttm = flow("revenue")
    net_income_ttm = flow("net_income")
    operating_income_ttm = flow("operating_income")
    dep_amort_ttm = flow("dep_amort")
    interest_ttm = flow("interest_expense")
    tax_ttm = flow("income_tax")
    ocf_ttm = flow("operating_cash_flow")
    capex_ttm = flow("capex")

    eps_items, _ = _collect(facts, TAGS["eps_diluted"], as_of_d)
    eps_ttm = _ttm_per_share(eps_items, as_of_d)

    cash = point("cash")
    lt_debt = point("lt_debt") or 0.0
    cur_debt = point("current_debt") or 0.0
    total_debt = (lt_debt + cur_debt) if (lt_debt or cur_debt) else None
    shares = point("shares")

    # EBITDA approximation
    ebitda_ttm = None
    if operating_income_ttm is not None and dep_amort_ttm is not None:
        ebitda_ttm = operating_income_ttm + dep_amort_ttm
    elif None not in (net_income_ttm, interest_ttm, tax_ttm, dep_amort_ttm):
        ebitda_ttm = net_income_ttm + interest_ttm + tax_ttm + dep_amort_ttm

    # Free cash flow (capex is reported as a positive outflow -> subtract)
    fcf_ttm = None
    if ocf_ttm is not None and capex_ttm is not None:
        fcf_ttm = ocf_ttm - abs(capex_ttm)

    # Prior-year TTM revenue (~1 year earlier) for the growth rate
    prior_revenue_ttm = None
    rev_items, _ = _collect(facts, TAGS["revenue"], as_of_d)
    if rev_items:
        try:
            one_yr_earlier = as_of_d.replace(year=as_of_d.year - 1)
            prior_revenue_ttm = _ttm_flow(rev_items, one_yr_earlier)
        except ValueError:
            prior_revenue_ttm = None

    result = {
        "ticker": ticker.upper(),
        "as_of": as_of_d.isoformat(),
        "cik": cik,
        "revenue_ttm": revenue_ttm,
        "prior_revenue_ttm": prior_revenue_ttm,
        "net_income_ttm": net_income_ttm,
        "eps_ttm": eps_ttm,
        "ebitda_ttm": ebitda_ttm,
        "operating_cash_flow_ttm": ocf_ttm,
        "capex_ttm": capex_ttm,
        "fcf_ttm": fcf_ttm,
        "cash": cash,
        "total_debt": total_debt,
        "shares_outstanding": shares,
    }
    cache.save(name, pd.DataFrame([result]))
    return result
