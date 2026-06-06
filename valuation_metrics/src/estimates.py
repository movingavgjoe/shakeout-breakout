"""Forward estimates from yfinance (current analyst consensus).

IMPORTANT LIMITATION: yfinance returns *today's* consensus regardless of the
date you pass elsewhere in this package. For current-date analysis that's fine;
for a historical as-of date these forward figures are a present-day proxy, not
what consensus actually was on that day. This is an accepted tradeoff for a
free, no-key data source.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from . import cache, config


def _safe_get(info: dict, *keys) -> Optional[float]:
    for k in keys:
        v = info.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def get_estimates(ticker: str, fallback_ebitda: Optional[float] = None) -> dict:
    """Return forward EPS, forward EBITDA, and expected EPS growth.

    `fallback_ebitda` (e.g. trailing EBITDA from EDGAR) is used when yfinance has
    no forward EBITDA, so EV/EBITDA still computes (flagged via ebitda_is_forward).
    """
    name = f"estimates_{ticker.upper()}"
    cached = cache.load(name, config.ESTIMATES_CACHE_MAX_AGE_DAYS)
    if cached is not None and not cached.empty:
        return cached.iloc[0].to_dict()

    import yfinance as yf  # imported lazily so the rest of the pkg works offline

    tk = yf.Ticker(ticker)
    info = {}
    try:
        info = tk.info or {}
    except Exception:
        info = {}

    forward_eps = _safe_get(info, "forwardEps")
    forward_pe = _safe_get(info, "forwardPE")
    earnings_growth = _safe_get(info, "earningsGrowth", "earningsQuarterlyGrowth")

    # yfinance exposes a forward EBITDA only indirectly; trailing EBITDA is in
    # info["ebitda"]. Prefer an explicit forward value if present, else fall back.
    forward_ebitda = _safe_get(info, "forwardEbitda")
    ebitda_is_forward = forward_ebitda is not None
    if forward_ebitda is None:
        forward_ebitda = _safe_get(info, "ebitda")  # trailing, from yahoo
    if forward_ebitda is None:
        forward_ebitda = fallback_ebitda  # trailing, from EDGAR

    result = {
        "ticker": ticker.upper(),
        "forward_eps": forward_eps,
        "forward_pe": forward_pe,
        "earnings_growth": earnings_growth,  # fraction, e.g. 0.12 == 12%
        "forward_ebitda": forward_ebitda,
        "ebitda_is_forward": ebitda_is_forward,
    }
    cache.save(name, pd.DataFrame([result]))
    return result
