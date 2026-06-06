# valuation_metrics

Compute valuation metrics for a stock ticker on a given date, using **only free
data sources** (no API keys, no paid accounts).

## Metrics produced

- Trailing P/E
- Forward P/E
- PEG ratio
- Price / Free Cash Flow
- EV / EBITDA (forward)
- Revenue growth rate vs. valuation multiple
- Free cash flow margin

(plus market cap, enterprise value, and the raw OHLCV price record)

## Data sources

| Data | Source | Key? |
|------|--------|------|
| Daily OHLCV prices | [Stooq](https://stooq.com) direct CSV | none |
| Trailing fundamentals (revenue, EBITDA, EPS, OCF, capex, debt, cash, shares) | [SEC EDGAR companyfacts](https://www.sec.gov/edgar/sec-api-documentation) | none |
| Forward estimates (fwd EPS, fwd EBITDA, growth) | [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo) | none |

## Rate limits & etiquette

- **SEC EDGAR** — hard ceiling 10 req/s per IP; this package self-throttles to
  **8 req/s** and sends a descriptive `User-Agent` (required, or SEC returns 403).
  Set your own via the `EDGAR_USER_AGENT` env var. Fundamentals are cached, so
  EDGAR is hit at most once per ticker per quarter.
- **Stooq** — no documented limit; we cache each ticker/date-range CSV so repeat
  runs make zero network calls.
- **yfinance** — unofficial scraper; Yahoo throttles aggressively and can
  temporarily block your IP. Estimates are cached daily to minimize calls.

## Caching

All fetched data is cached as CSV in `cache/` (git-ignored). Past-date prices and
fundamentals never change, so re-runs are instant and limit-free. Delete files in
`cache/` to force a refresh.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py AAPL 2026-05-01      # metrics as of a date
python main.py MSFT                 # defaults to today
python main.py NVDA 2026-05-01 --json
```

Or from Python:

```python
from main import get_metrics
result = get_metrics("AAPL", "2026-05-01")
print(result["metrics"])
```

## Important limitations (by design, to stay free)

1. **Forward estimates are current consensus.** yfinance returns *today's*
   analyst consensus regardless of the `date` you request. For current analysis
   that's accurate; for a historical date it's a present-day proxy, not what
   consensus was on that day.
2. **EBITDA is approximated.** It is not a reported line item; we compute
   `OperatingIncome + D&A` (fallback `NetIncome + Interest + Taxes + D&A`). If
   yfinance has no forward EBITDA, EV/EBITDA falls back to a trailing EBITDA
   proxy (flagged in the output).
3. **TTM is best-effort.** Built from the 4 most recent ~quarterly filings;
   falls back to the latest annual (10-K) when clean quarters aren't available.
4. **Point-in-time fundamentals** use only filings dated on/before the requested
   date (no look-ahead bias) — this part *is* historically accurate.

## Layout

```
valuation_metrics/
├── main.py              # get_metrics(ticker, date) + CLI
├── requirements.txt
├── cache/               # git-ignored CSV cache
├── src/
│   ├── config.py        # paths, rate limits, endpoints
│   ├── cache.py         # CSV read/write + staleness
│   ├── prices.py        # Stooq OHLCV
│   ├── edgar.py         # SEC fundamentals (8 req/s, point-in-time)
│   ├── estimates.py     # yfinance forward consensus
│   └── metrics.py       # pure ratio math
└── tests/
    └── test_metrics.py  # math unit tests (no network)
```

## Tests

```bash
python -m pytest tests/ -q
```
