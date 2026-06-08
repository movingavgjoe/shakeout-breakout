"""Daily OHLCV prices from yfinance (Yahoo).

Stooq was the original source but its CSV endpoint is now behind a JavaScript
anti-bot challenge that plain HTTP clients can't pass, so prices come from
yfinance, which uses Yahoo's JSON endpoints (no key, no login).

Schema returned everywhere: Date, Open, High, Low, Close, Volume.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Union

import pandas as pd

from . import cache, config

DateLike = Union[str, date, datetime]

NEEDED = ["Date", "Open", "High", "Low", "Close", "Volume"]


def _to_date(d: DateLike) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _norm_key(ticker: str) -> str:
    return ticker.strip().lower().replace(".", "-")


def _fetch_yfinance(ticker: str, start_d: date, end_d: date) -> pd.DataFrame:
    import yfinance as yf  # lazy import

    tk = yf.Ticker(ticker)
    # history end is exclusive, so add a day; auto_adjust=False keeps the actual
    # traded close (the price used for market cap / P/E on that date).
    hist = tk.history(
        start=start_d.isoformat(),
        end=(end_d + timedelta(days=1)).isoformat(),
        auto_adjust=False,
    )
    if hist is None or hist.empty:
        raise ValueError(f"yfinance returned no data for {ticker} ({start_d}..{end_d})")

    hist = hist.reset_index()
    # The index column is "Date" for daily data; normalize and drop any timezone.
    if "Date" not in hist.columns and "Datetime" in hist.columns:
        hist = hist.rename(columns={"Datetime": "Date"})
    s = pd.to_datetime(hist["Date"])
    try:
        s = s.dt.tz_localize(None)      # tz-aware -> naive
    except TypeError:
        pass                            # already tz-naive
    hist["Date"] = s.dt.date

    missing = [c for c in NEEDED if c not in hist.columns]
    if missing:
        raise ValueError(f"yfinance missing columns {missing}; got {list(hist.columns)}")
    return hist[NEEDED].copy()


def fetch_prices(ticker: str, start: DateLike, end: DateLike) -> pd.DataFrame:
    """Daily OHLCV for [start, end] from yfinance, with CSV caching.

    Returns columns: Date, Open, High, Low, Close, Volume.
    """
    start_d, end_d = _to_date(start), _to_date(end)
    name = f"prices_{_norm_key(ticker)}_{start_d:%Y%m%d}_{end_d:%Y%m%d}"

    cached = cache.load(name, config.PRICE_CACHE_MAX_AGE_DAYS)
    if cached is not None and not cached.empty:
        cached["Date"] = pd.to_datetime(cached["Date"]).dt.date
        return cached

    df = _fetch_yfinance(ticker, start_d, end_d)
    cache.save(name, df)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    return df


def price_on(ticker: str, on: DateLike, lookback_days: int = 7) -> dict:
    """Price record for `on`, or the nearest prior trading day within lookback_days.

    Returns a dict: {date, open, high, low, close, volume}.
    """
    on_d = _to_date(on)
    start = on_d - timedelta(days=lookback_days)
    df = fetch_prices(ticker, start, on_d)
    df = df[df["Date"] <= on_d].sort_values("Date")
    if df.empty:
        raise ValueError(f"No trading day on/before {on_d} for {ticker}.")
    row = df.iloc[-1]
    return {
        "date": row["Date"],
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "volume": float(row["Volume"]),
    }
