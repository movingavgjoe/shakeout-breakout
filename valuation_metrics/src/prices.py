"""Daily OHLCV prices from Stooq's free direct-CSV endpoint (no key, no login)."""
from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import Optional, Union

import pandas as pd
import requests

from . import cache, config

DateLike = Union[str, date, datetime]


def _to_date(d: DateLike) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _stooq_symbol(ticker: str) -> str:
    """Map a US ticker to Stooq's symbol convention (lowercase, .us suffix).

    Class-share dots become dashes on Stooq, e.g. BRK.B -> brk-b.us.
    """
    t = ticker.strip().lower().replace(".", "-")
    return f"{t}{config.STOOQ_SUFFIX}"


def fetch_prices(ticker: str, start: DateLike, end: DateLike) -> pd.DataFrame:
    """Download daily OHLCV for [start, end] from Stooq, with CSV caching.

    Returns a DataFrame with columns: Date, Open, High, Low, Close, Volume.
    """
    start_d, end_d = _to_date(start), _to_date(end)
    symbol = _stooq_symbol(ticker)
    name = f"prices_{symbol}_{start_d:%Y%m%d}_{end_d:%Y%m%d}"

    cached = cache.load(name, config.PRICE_CACHE_MAX_AGE_DAYS)
    if cached is not None and not cached.empty:
        cached["Date"] = pd.to_datetime(cached["Date"]).dt.date
        return cached

    url = config.STOOQ_CSV_URL.format(
        symbol=symbol, d1=f"{start_d:%Y%m%d}", d2=f"{end_d:%Y%m%d}"
    )
    resp = requests.get(url, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    text = resp.text.strip()

    # Stooq returns the literal "No data" when a symbol/range is empty.
    if not text or text.lower().startswith("no data") or "," not in text.splitlines()[0]:
        raise ValueError(
            f"Stooq returned no data for {symbol} ({start_d}..{end_d}). "
            "Check the ticker symbol / Stooq suffix."
        )

    df = pd.read_csv(io.StringIO(text))
    # Expected columns: Date, Open, High, Low, Close, Volume
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
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
