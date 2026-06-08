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
# SEC will 403 generic/empty UAs. The contact email is read from the
# EDGAR_USER_AGENT env var only — no address is hardcoded here, so nothing
# personal ends up in source control. If unset, EDGAR requests raise a clear
# error (see edgar.py); the rest of the package still works offline.
EDGAR_USER_AGENT = os.environ.get("EDGAR_USER_AGENT")
# SEC hard limit is 10 req/s per IP; we self-throttle to 8 to leave headroom.
EDGAR_MAX_REQUESTS_PER_SEC = 8
EDGAR_MIN_INTERVAL = 1.0 / EDGAR_MAX_REQUESTS_PER_SEC  # seconds between requests

EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# --- Prices ------------------------------------------------------------------
# Prices come from yfinance (Yahoo). No key required. (Stooq was dropped: its
# CSV endpoint is now behind a JavaScript anti-bot challenge.)

# --- Cache freshness (days) --------------------------------------------------
# Fundamentals change quarterly; prices for past dates never change.
PRICE_CACHE_MAX_AGE_DAYS = 1        # extend the window if today is requested
FUNDAMENTALS_CACHE_MAX_AGE_DAYS = 30
ESTIMATES_CACHE_MAX_AGE_DAYS = 1    # forward consensus moves; refresh daily

# Network timeout (seconds)
HTTP_TIMEOUT = 30
