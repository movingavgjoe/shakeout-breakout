"""Central configuration: paths, rate limits, and data-source endpoints."""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -------------------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PACKAGE_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# --- SEC EDGAR ---------------------------------------------------------------
# SEC requires a descriptive User-Agent ("Sample Company name AdminContact@email").
# Override via the EDGAR_USER_AGENT env var. SEC will 403 generic/empty UAs.
EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT",
    "shakeout-breakout valuation_metrics nkharas74@gmail.com",
)
# SEC hard limit is 10 req/s per IP; we self-throttle to 8 to leave headroom.
EDGAR_MAX_REQUESTS_PER_SEC = 8
EDGAR_MIN_INTERVAL = 1.0 / EDGAR_MAX_REQUESTS_PER_SEC  # seconds between requests

EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# --- Stooq (prices) ----------------------------------------------------------
# Direct CSV endpoint: no key, no login. d1/d2 are YYYYMMDD, i=d for daily.
STOOQ_CSV_URL = "https://stooq.com/q/d/l/?s={symbol}&d1={d1}&d2={d2}&i=d"
STOOQ_SUFFIX = ".us"  # US-listed tickers

# --- Cache freshness (days) --------------------------------------------------
# Fundamentals change quarterly; prices for past dates never change.
PRICE_CACHE_MAX_AGE_DAYS = 1        # extend the window if today is requested
FUNDAMENTALS_CACHE_MAX_AGE_DAYS = 30
ESTIMATES_CACHE_MAX_AGE_DAYS = 1    # forward consensus moves; refresh daily

# Network timeout (seconds)
HTTP_TIMEOUT = 30
